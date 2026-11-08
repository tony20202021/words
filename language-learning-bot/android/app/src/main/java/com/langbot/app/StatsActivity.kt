package com.langbot.app

import com.langbot.app.util.showAppIcon
import android.content.Intent
import android.graphics.BitmapFactory
import android.os.Bundle
import android.view.Gravity
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.langbot.app.databinding.ActivityStatsBinding
import com.langbot.app.network.BLSClient
import com.langbot.app.network.NetworkRetry
import com.langbot.app.network.Statistics
import com.langbot.app.prefs.UserPrefs
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.job
import java.util.concurrent.ConcurrentHashMap
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.withContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import androidx.annotation.VisibleForTesting
import android.graphics.Bitmap
import android.app.Dialog
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.awaitAll
import com.langbot.app.offline.ChartCache
import com.langbot.app.offline.OfflineNotice

class StatsActivity : AppCompatActivity() {

    private lateinit var binding: ActivityStatsBinding
    private lateinit var userId: String
    private lateinit var languageId: String
    private var languageName: String = ""

    companion object {
        const val MENU_STUDY     = 1
        const val MENU_LANGUAGES = 2

        /** Сколько больших картинок качать одновременно — не забивать канал. */
        const val ZOOM_PREFETCH_PARALLEL = 2

        // Запасной список на случай, когда манифест недоступен. Имена обязаны
        // совпадать с common/chart_manifest.py: сервер рисует график по имени и
        // на незнакомое отвечает 404, то есть пустым местом на экране.
        private val MONTHLY_CHARTS = listOf(
            "words_studied", "words_new", "words_known",
            "words_unknown_last_finish", "words_overdue_morning",
            "words_unknown_first_finish", "words_for_today",
        )

        private val FALLBACK_SECTIONS = listOf(
            Triple("📅 Распределение слов", listOf("words_for_today", "words_unknown", "check_interval"), "today"),
            Triple("📆 Прогресс за месяц", MONTHLY_CHARTS, "monthly_recent"),
            Triple("📊 Прогресс за всё время", MONTHLY_CHARTS, "monthly_all"),
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityStatsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        userId     = UserPrefs.getUserId(this) ?: run { finish(); return }
        languageId = intent.getStringExtra("language_id") ?: run { finish(); return }
        languageName = intent.getStringExtra("language_name") ?: ""

        setSupportActionBar(binding.toolbar)
        showAppIcon()
        supportActionBar?.title = "Статистика: ${languageName.ifEmpty { "Статистика" }}"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.swipeRefresh.setOnRefreshListener { loadStats() }

        loadStats()
    }

    /**
     * Куда уйти со статистики.
     *
     * «Назад» остаётся и ведёт туда, откуда пришли, — но откуда именно,
     * заранее не видно: на статистику попадают и из сессии обучения, и из
     * списка языков. Владелец: «она возвращает на предыдущий экран, и он может
     * быть разный — лучше добавить явно переход в обучение и переход на выбор
     * языков». Стрелка отвечает на вопрос «вернуться», меню — на вопрос
     * «пойти куда хочу».
     */
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add(0, MENU_STUDY,     0, "📚 К обучению")
        menu.add(0, MENU_LANGUAGES, 1, "🌐 Выбор языка")
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == MENU_STUDY) {
            goTo(StudyActivity::class.java)
            return true
        }
        if (item.itemId == MENU_LANGUAGES) {
            goTo(LanguagesActivity::class.java)
            return true
        }
        return super.onOptionsItemSelected(item)
    }

    /**
     * Переход к уже открытому экрану, а не к его второй копии.
     *
     * CLEAR_TOP со SINGLE_TOP снимают со стека всё, что лежит выше нужного
     * экрана, и отдают управление ему же. Без этого путь «обучение →
     * статистика → к обучению» клал бы вторую сессию поверх первой, и
     * «назад» пришлось бы жать дважды, проходя статистику по дороге.
     */
    private fun goTo(target: Class<*>) {
        startActivity(Intent(this, target).apply {
            putExtra("language_id", languageId)
            putExtra("language_name", languageName)
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
        })
    }

    /** Перезагрузить экран (для проверок — обычный путь «потянуть вниз»). */
    @VisibleForTesting
    fun refreshForTest() = loadStats()

    /**
     * Разобрать картинку для ленты — вдвое экономнее и не роняя приложение.
     *
     * Графики это плоские заливки, и RGB_565 на них не отличить от
     * полного цвета, зато памяти вдвое меньше: семнадцать картинок
     * шириной экрана занимали около 60 МБ. Нехватка памяти прилетает
     * как Error, а не Exception, — прежний перехват её не ловил, и
     * приложение просто исчезало. Ровно так это и выглядело у владельца:
     * «вылетает», а по возвращении — экран выбора языков.
     */
    fun decodeForList(bytes: ByteArray): Bitmap? = try {
        val opts = BitmapFactory.Options().apply {
            inPreferredConfig = Bitmap.Config.RGB_565
        }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, opts)
    } catch (e: OutOfMemoryError) {
        android.util.Log.w("StatsActivity", "не хватило памяти на график", e)
        null
    }

    /** Заново собрать две части экрана — числа и графики — и очистить их. */
    private fun prepareBoxes() {
        binding.statsContainer.removeAllViews()
        val summary = LinearLayout(this)
        summary.orientation = LinearLayout.VERTICAL
        summary.layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        val charts = LinearLayout(this)
        charts.orientation = LinearLayout.VERTICAL
        charts.layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        binding.statsContainer.addView(summary)
        binding.statsContainer.addView(charts)
        summaryBox = summary
        chartsBox = charts
    }

    private fun loadStats() {
        // Прежняя загрузка больше не нужна: её результат всё равно лёг бы
        // поверх новой — в те же места и теми же видами.
        chartsJob?.cancel()
        statsJob?.cancel()
        binding.progress.visibility = View.VISIBLE
        prepareBoxes()
        // Графики — сразу и независимо от сводки: они умеют начать с
        // сохранённых картинок, и ждать ради этого медленный ответ незачем.
        loadCharts()
        statsJob = lifecycleScope.launch {
            try {
                // С повторами и нарастающим таймаутом — как на экране занятия.
                //
                // Здесь стоял один запрос с самым коротким таймаутом соединения
                // (2 с). На вялой мобильной связи столько уходит на само
                // установление соединения, и статистика говорила «нет связи» в
                // ту минуту, когда слова грузились нормально: там лесенка
                // 2 → 6 → 15 секунд и три попытки.
                val statsResp = NetworkRetry.call { api -> api.getStatistics(userId, languageId) }
                if (statsResp != null && statsResp.isSuccessful && statsResp.body() != null) {
                    lastLoadFailed = false
                    summaryBox?.let { OfflineNotice.clear(it) }
                    renderStats(statsResp.body()!!)
                } else {
                    showWithoutSummary()
                }
            } catch (e: CancellationException) {
                // Отмена — не ошибка: так экран сообщает, что началась новая
                // загрузка. Прежде она ловилась наравне с обрывом связи, и
                // отменённая попытка дорисовывала свой блок графиков поверх
                // новой — отсюда копии разделов и вылеты.
                throw e
            } catch (e: Exception) {
                // Числа статистики офлайн показать неоткуда — они целиком
                // серверные. А вот графики с прошлого раза лежат на телефоне,
                // и это ровно тот случай, ради которого они сохранялись.
                showWithoutSummary()
            } finally {
                binding.progress.visibility = View.GONE
                binding.swipeRefresh.isRefreshing = false
            }
        }
    }

    /** Числа не пришли: говорим об этом в их части экрана. Графики идут своим ходом. */
    private fun showWithoutSummary() {
        lastLoadFailed = true
        val box = summaryBox ?: return
        box.removeAllViews()
        // Без сохранённых графиков объяснять надо подробно: экран иначе пуст.
        // С ними хватит короткой строки — картинки человек и так видит.
        if (ChartCache.hasAny(userId, languageId)) {
            val tv = TextView(this)
            tv.text = "📴 Связи нет — числа не обновились"
            tv.textSize = 13f
            tv.setTextColor(android.graphics.Color.parseColor("#856404"))
            tv.setBackgroundColor(android.graphics.Color.parseColor("#FFF3CD"))
            tv.setPadding(dpToPx(12), dpToPx(8), dpToPx(12), dpToPx(8))
            box.addView(tv)
        } else {
            OfflineNotice.show(box, "статистику")
        }
    }

    private fun loadCharts() {
        val charts = chartsBox ?: return
        // Section header
        val tvHeader = TextView(this)
        tvHeader.text = "Графики"
        tvHeader.textSize = 14f
        tvHeader.setTypeface(null, android.graphics.Typeface.BOLD)
        tvHeader.setTextColor(android.graphics.Color.parseColor("#888888"))
        tvHeader.gravity = android.view.Gravity.CENTER
        val headerLp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        headerLp.topMargin = 24; headerLp.bottomMargin = 8
        tvHeader.layoutParams = headerLp
        charts.addView(tvHeader)

        // Spinner while loading — centered
        val spinner = ProgressBar(this)
        val spinnerLp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        spinnerLp.gravity = android.view.Gravity.CENTER_HORIZONTAL
        spinner.layoutParams = spinnerLp
        val spinnerWrap = android.widget.LinearLayout(this)
        spinnerWrap.gravity = android.view.Gravity.CENTER_HORIZONTAL
        spinnerWrap.layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        spinnerWrap.addView(spinner)
        charts.addView(spinnerWrap)

        chartsJob = lifecycleScope.launch {
          try {
            var anyLoaded = false

            // Remove the initial spinnerWrap — each section has its own
            charts.removeView(spinnerWrap)

            // Состав экрана берём из запасного списка СРАЗУ, не дожидаясь
            // манифеста.
            //
            // Манифест идёт с повторами, а это до двадцати трёх секунд на
            // мёртвой связи. Всё это время экран стоял пустой, хотя картинки
            // с прошлого раза лежали на телефоне: ровно то, на что жаловался
            // владелец — «отрисовался пустой экран с крутяшкой, хотя до этого
            // графики смотрел». Запасной список совпадает с манифестом сервера;
            // если сервер всё же пришлёт другой, экран пересоберётся под него.
            val manifestNow = runCatching { BLSClient.api.getChartManifest().body() }.getOrNull()
            val sections = manifestNow?.sections?.map {
                Triple(it.header, it.charts, it.type)
            } ?: FALLBACK_SECTIONS

            // Сначала каркас: заголовки разделов и места под картинки — в порядке
            // манифеста. Потом все запросы разом. Прежде 17 картинок грузились
            // строго по очереди, и время складывалось: на слабом мобильном каждая
            // ждала, пока доедет предыдущая. Теперь каждая встаёт в своё место,
            // как только пришла, и порядок не зависит от того, какая ответит первой.
            class Slot(val holder: LinearLayout, val type: Int, val name: String, val title: String) {
                /** Картинка в этом месте: сохранённая с прошлого раза либо свежая. */
                var view: ImageView? = null
                /** Обёртка, в которой поверх картинки крутится ожидание. */
                var frame: android.widget.FrameLayout? = null
                var spinner: View? = null
                var fromCache = false
            }
            val sectionSlots = mutableListOf<Pair<View, List<Slot>>>()

            for ((i, section) in sections.withIndex()) {
                val (title, names, chartType) = section
                val type = when (chartType) {
                    "today" -> 0
                    "monthly_recent" -> 1
                    else -> 2
                }

                // Divider before sections 2 and 3
                if (i > 0) {
                    val div = View(this@StatsActivity)
                    div.setBackgroundColor(android.graphics.Color.parseColor("#E0E0E0"))
                    val divLp = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT, dpToPx(1))
                    divLp.topMargin = dpToPx(16); divLp.bottomMargin = dpToPx(16)
                    div.layoutParams = divLp
                    charts.addView(div)
                }

                // Section header
                val tvTitle = TextView(this@StatsActivity)
                tvTitle.text = title
                tvTitle.textSize = 15f
                tvTitle.setTypeface(null, android.graphics.Typeface.BOLD)
                tvTitle.setTextColor(android.graphics.Color.parseColor("#555555"))
                charts.addView(tvTitle)

                // Per-section spinner
                val secSpinner = ProgressBar(this@StatsActivity)
                val ssLp = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                ssLp.gravity = android.view.Gravity.CENTER_HORIZONTAL
                ssLp.topMargin = dpToPx(8)
                secSpinner.layoutParams = ssLp
                val ssWrap = android.widget.LinearLayout(this@StatsActivity)
                ssWrap.gravity = android.view.Gravity.CENTER_HORIZONTAL
                ssWrap.layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                ssWrap.addView(secSpinner)
                charts.addView(ssWrap)

                val slots = names.map { name ->
                    val holder = LinearLayout(this@StatsActivity)
                    holder.orientation = LinearLayout.VERTICAL
                    holder.layoutParams = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                    charts.addView(holder)
                    Slot(holder, type, name, title)
                }
                sectionSlots += ssWrap to slots
            }

            /** Поставить картинку в её место — или подменить ту, что уже стоит. */
            fun show(slot: Slot, bytes: ByteArray): Boolean {
                val bmp = decodeForList(bytes) ?: return false
                val existing = slot.view
                if (existing != null) {
                    existing.setImageBitmap(bmp)
                    existing.alpha = 1f
                    existing.setOnClickListener { openZoom(slot.type, slot.name, bmp) }
                } else {
                    val iv = ImageView(this@StatsActivity)
                    iv.setImageBitmap(bmp)
                    // Нажатие — полноэкранное увеличение пальцами.
                    iv.setOnClickListener { openZoom(slot.type, slot.name, bmp) }
                    iv.adjustViewBounds = true
                    iv.layoutParams = android.widget.FrameLayout.LayoutParams(
                        android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                        android.widget.FrameLayout.LayoutParams.WRAP_CONTENT)
                    // Обёртка нужна ради крутяшки поверх картинки: в столбце
                    // она встала бы под ней и уехала бы вниз экрана.
                    val frame = android.widget.FrameLayout(this@StatsActivity)
                    val lp = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT)
                    lp.bottomMargin = dpToPx(6)
                    frame.layoutParams = lp
                    frame.addView(iv)
                    slot.holder.addView(frame)
                    slot.view = iv
                    slot.frame = frame
                }
                return true
            }

            /** Картинка сохранённая: поверх неё крутится ожидание свежей. */
            fun markStale(slot: Slot) {
                val frame = slot.frame ?: return
                if (slot.spinner != null) return
                val pb = ProgressBar(this@StatsActivity)
                pb.layoutParams = android.widget.FrameLayout.LayoutParams(
                    android.widget.FrameLayout.LayoutParams.WRAP_CONTENT,
                    android.widget.FrameLayout.LayoutParams.WRAP_CONTENT,
                    android.view.Gravity.CENTER)
                frame.addView(pb)
                slot.spinner = pb
                // Лёгкое притемнение оставляем: на светлом графике крутяшку
                // иначе плохо видно.
                slot.view?.alpha = 0.7f
            }

            /** Ожидание закончилось: свежая пришла либо стало ясно, что не придёт. */
            fun markSettled(slot: Slot) {
                slot.spinner?.let { slot.frame?.removeView(it) }
                slot.spinner = null
                slot.view?.alpha = 1f
            }

            suspend fun loadInto(slot: Slot): Boolean = try {
                val bytes = fetchChart(slot.type, slot.name, "screen")
                if (bytes == null) false else {
                    val ok = show(slot, bytes)
                    if (ok) {
                        slot.fromCache = false
                        markSettled(slot)
                        ChartCache.put(userId, languageId, slot.type, slot.name, bytes)
                    }
                    ok
                }
            } catch (e: Exception) {
                android.util.Log.w("StatsActivity", "${slot.title}/${slot.name}: ${e.message}")
                false
            }

            // Сохранённые с прошлого раза — сразу, ещё до сети. В метро связь
            // есть, но слабая: семнадцать картинок тянутся так долго, что экран
            // бесполезен. Пока едут свежие, сохранённые показаны приглушённо.
            val allSlots = sectionSlots.flatMap { it.second }
            var fromCache = 0
            for (slot in allSlots) {
                val cached = ChartCache.get(userId, languageId, slot.type, slot.name) ?: continue
                if (show(slot, cached)) {
                    slot.fromCache = true
                    markStale(slot)
                    fromCache++
                }
            }
            if (fromCache > 0) sectionSlots.forEach { charts.removeView(it.first) }

            // Версия данных: если она та же, что у сохранённых картинок, качать
            // нечего вовсе — один короткий запрос вместо семнадцати картинок.
            val serverVersion = try {
                NetworkRetry.call { api -> api.getChartsVersion(userId, languageId) }
                    ?.body()?.version
            } catch (_: Exception) { null }
            val cachedVersion = ChartCache.version(userId, languageId)
            val upToDate = fromCache == allSlots.size && allSlots.isNotEmpty() &&
                    serverVersion != null && serverVersion == cachedVersion

            val loaded = if (upToDate) {
                allSlots.forEach { markSettled(it) }
                List(allSlots.size) { true }
            } else coroutineScope {
                sectionSlots.map { (spinnerView, slots) ->
                    async {
                        val results = slots.map { slot -> async { loadInto(slot) } }.awaitAll()
                        charts.removeView(spinnerView)
                        results
                    }
                }.awaitAll().flatten()
            }
            anyLoaded = loaded.any { it } || fromCache > 0
            allSlots.forEach { markSettled(it) }

            // Версию запоминаем, только когда СВЕЖИЕ приехали все: иначе
            // недокачанный набор выдаст себя за полный и больше не обновится.
            if (!upToDate && serverVersion != null && loaded.all { it } && loaded.isNotEmpty()) {
                ChartCache.saveVersion(userId, languageId, serverVersion)
            } else if (!upToDate && loaded.any { !it }) {
                ChartCache.clearVersion(userId, languageId)
            }
            // Сеть не ответила, но сохранённое показано — скажем, что оно старое.
            if (serverVersion == null && fromCache > 0 && loaded.none { it }) {
                allSlots.forEach { markSettled(it) }
                val tv = TextView(this@StatsActivity)
                tv.text = "📴 Связи нет — показаны графики с прошлого раза"
                tv.textSize = 13f
                tv.setTextColor(android.graphics.Color.parseColor("#856404"))
                tv.setBackgroundColor(android.graphics.Color.parseColor("#FFF3CD"))
                tv.setPadding(dpToPx(12), dpToPx(8), dpToPx(12), dpToPx(8))
                charts.addView(tv, 0)
            }

            // Экран заполнен лёгкими — теперь фоном большие, для увеличения.
            //
            // Кроме случая, когда лёгкие не качались вовсе: данные те же, что в
            // прошлый раз. Тогда и большие тянуть незачем — это ещё 17 запросов
            // по 39 КБ на канал, из-за которого всё и затевалось. Понадобятся
            // при увеличении — придут по нажатию (openZoom).
            if (!upToDate) {
                val shown = sectionSlots.flatMap { it.second }.zip(loaded)
                    .filter { it.second }.map { it.first.type to it.first.name }
                startZoomPrefetch(shown)
            }

            if (!anyLoaded) {
                val tv = TextView(this@StatsActivity)
                tv.text = "Нет данных для графиков"
                tv.textSize = 13f
                tv.setTextColor(android.graphics.Color.parseColor("#888888"))
                tv.gravity = android.view.Gravity.CENTER
                charts.addView(tv)
            }
          } catch (e: CancellationException) {
            throw e                      // отмена — это не ошибка
          } catch (e: OutOfMemoryError) {
            // Пустой экран без объяснения — худшее, чем это может кончиться.
            android.util.Log.w("StatsActivity", "не хватило памяти на графики", e)
            val tv = TextView(this@StatsActivity)
            tv.text = "Не хватило памяти на графики — попробуйте открыть заново"
            tv.textSize = 13f
            tv.gravity = android.view.Gravity.CENTER
            tv.setTextColor(android.graphics.Color.parseColor("#888888"))
            chartsBox?.addView(tv)
          } catch (e: Throwable) {
            // Лучше экран без графиков, чем вылет приложения: статистика не та
            // вещь, ради которой стоит терять сессию занятия. Throwable, а не
            // Exception: нехватка памяти — это Error, и именно она роняла.
            android.util.Log.w("StatsActivity", "графики не нарисованы: ${e.message}", e)
          }
        }
    }

    // Большие варианты картинок в СЖАТОМ виде: 40–55 КБ каждая. В память
    // (около 10 МБ на картинку) раскрывается только та, что открыта для
    // увеличения: все 17 разом заняли бы ~180 МБ и на многих телефонах уронили бы
    // приложение, а видимой разницы без увеличения нет — лента показывает
    // картинку шириной экрана.
    private val zoomBytes = ConcurrentHashMap<String, ByteArray>()
    private var zoomPrefetch: Job? = null

    // Одна загрузка экрана за раз.
    //
    // Без сети каждая попытка живёт долго: семнадцать запросов ждут таймаута.
    // Человек за это время дёргает экран ещё раз — и вторая загрузка начинала
    // рисовать в тот же контейнер, что и первая. Android падает, когда
    // добавляют картинку, у которой уже есть родитель; это и был «вылетает при
    // отключённой сети».
    private var statsJob: Job? = null
    private var chartsJob: Job? = null

    /** Последняя попытка не удалась — значит, стоит повторить, когда сможем. */
    private var lastLoadFailed = false

    // Экран из двух независимых частей: числа сверху и графики под ними.
    //
    // Раньше графики ждали, пока ответит сводка. В метро связь есть, но
    // медленная: сводка не падает, а тянется — и человек видел пустой экран с
    // крутяшкой, хотя картинки с прошлого раза лежали на телефоне. Теперь
    // графики рисуются сразу и сами по себе, а числа приходят, когда придут.
    private var summaryBox: LinearLayout? = null
    private var chartsBox: LinearLayout? = null

    // onResume приходит и сразу после onCreate, где загрузка уже идёт: второй
    // раз её запускать незачем.
    private var firstResume = true
    /** Картинки отпущены при уходе с экрана — при возвращении перечитать. */
    private var needsReload = false

    private fun zoomKey(type: Int, name: String) = "$type/$name"

    private suspend fun fetchChart(type: Int, name: String, res: String): ByteArray? {
        val resp = when (type) {
            0    -> BLSClient.api.getChart(userId, languageId, name, res)
            1    -> BLSClient.api.getMonthlyChart(userId, languageId, name, showAll = false, res = res)
            else -> BLSClient.api.getMonthlyChart(userId, languageId, name, showAll = true, res = res)
        }
        return if (resp.isSuccessful) resp.body()?.bytes() else null
    }

    /**
     * Подкачать большие варианты фоном, когда экран уже заполнен лёгкими. По две
     * за раз — не забивать канал. Уход с экрана подкачку прекращает (onStop).
     */
    private fun startZoomPrefetch(charts: List<Pair<Int, String>>) {
        zoomPrefetch?.cancel()
        zoomPrefetch = lifecycleScope.launch {
            val prefetch = coroutineContext.job
            val gate = Semaphore(ZOOM_PREFETCH_PARALLEL)
            charts.map { (type, name) ->
                async {
                    gate.withPermit {
                        // Место освобождается отменой соседа, и ждущий получал его,
                        // когда родитель уже отменён, а сам он ещё числился
                        // активным: третий запрос успевал уйти ПОСЛЕ ухода с экрана
                        // (поймал тест, по меткам времени). Поэтому сверяемся с
                        // родителем, а не с собой.
                        prefetch.ensureActive()
                        val key = zoomKey(type, name)
                        if (!zoomBytes.containsKey(key)) {
                            try {
                                fetchChart(type, name, "zoom")?.let { zoomBytes[key] = it }
                            } catch (e: CancellationException) {
                                throw e   // иначе уход с экрана подкачку бы не остановил
                            } catch (_: Exception) {
                                // большой нет — при увеличении останется лёгкая
                            }
                        }
                    }
                }
            }.awaitAll()
        }
    }

    /** Полноэкранное увеличение: сразу лёгкая картинка, большая — как придёт. */
    private fun openZoom(type: Int, name: String, screen: Bitmap) {
        val view = ZoomImageView(this)
        view.show(screen)
        // Рамка на время движения — та же, что у увеличения карточки слова, и
        // по видимой части экрана: иначе сверху её съедает строка состояния, а
        // снизу остаётся широкая чёрная полоса.
        val box = StudyActivity.zoomFrame(this, view, android.graphics.Color.BLACK)
        StudyActivity.framed(box, android.graphics.Color.BLACK, resources.displayMetrics.density)
        val dialog = Dialog(this, android.R.style.Theme_Black_NoTitleBar_Fullscreen)
        // Рост из середины при входе и уменьшение при возврате: без анимации
        // момент перехода терялся — экран просто подменялся другим.
        dialog.window?.attributes?.windowAnimations = R.style.ZoomDialogAnimation
        dialog.setContentView(box)
        var sharpening: Job? = null
        dialog.setOnDismissListener {
            sharpening?.cancel()
            StudyActivity.framed(box, android.graphics.Color.BLACK, resources.displayMetrics.density)
            // Большая картинка это около 10 МБ, но отпускаем её не в тот же миг:
            // onDismiss приходит в начале закрытия, и очистка съедала анимацию
            // уменьшения — окно гасло пустым.
            view.postDelayed({ view.setImageDrawable(null) }, StudyActivity.ZOOM_EXIT_MS)
        }
        dialog.show()
        box.postDelayed({ box.setBackgroundColor(android.graphics.Color.BLACK) },
                        StudyActivity.ZOOM_ENTER_MS)
        zoomDialog = dialog
        sharpening = lifecycleScope.launch {
            val key = zoomKey(type, name)
            val bytes = zoomBytes[key] ?: try {
                fetchChart(type, name, "zoom")?.also { zoomBytes[key] = it }
            } catch (e: CancellationException) {
                throw e
            } catch (_: Exception) {
                null
            } ?: return@launch
            val big = withContext(Dispatchers.Default) {
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            } ?: return@launch
            if (dialog.isShowing) view.sharpen(big)
        }
    }

    @VisibleForTesting
    internal var zoomDialog: Dialog? = null

    @VisibleForTesting
    internal val zoomPrefetchJob: Job? get() = zoomPrefetch

    /**
     * Вернулись на экран после неудачи — пробуем снова.
     *
     * Жалоба владельца: «рисует экран, что сети нет, и больше ничего не
     * обновляет, даже когда сеть восстанавливается». Обновление вниз работало,
     * но требовать его после каждой пропажи связи — значит перекладывать на
     * человека то, что видно приложению.
     */
    override fun onResume() {
        super.onResume()
        // Перечитываем, если прошлая попытка не удалась либо картинки отпущены
        // при уходе с экрана.
        if ((lastLoadFailed || needsReload) && !firstResume) loadStats()
        firstResume = false
        needsReload = false
    }

    override fun onStop() {
        super.onStop()
        // Ушли с экрана — большие картинки больше не нужны, канал не занимаем.
        zoomPrefetch?.cancel()
        chartsJob?.cancel()
        statsJob?.cancel()
        // Семнадцать картинок шириной экрана — это десятки мегабайт. Держать их
        // на невидимом экране незачем: приложению они ещё понадобятся под
        // карточки и звук. При возвращении экран перечитает их с диска.
        releaseChartBitmaps()
        needsReload = true
    }

    /** Отпустить картинки графиков: экран не виден, память нужнее занятию. */
    private fun releaseChartBitmaps() {
        fun walk(v: View) {
            if (v is ImageView) v.setImageDrawable(null)
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(binding.statsContainer)
        zoomBytes.clear()
    }

    private fun renderStats(s: Statistics) {
        val c = summaryBox ?: binding.statsContainer
        c.removeAllViews()

        addStatRow(c, "Знаю",              s.words_known.toString(),    "#28a745")
        addStatRow(c, "Изучено",           s.words_studied.toString(),  "#333333")
        addStatRow(c, "Всего слов",        s.total_words.toString(),    "#666666")
        addStatRow(c, "К повторению сегодня", s.words_for_today.toString(),
            if (s.words_for_today > 0) "#f0ad4e" else "#666666")
        addStatRow(c, "Прогресс (знаю / всего)",
            "%.1f%%".format(s.progress_percentage), "#17a2b8")
        if (s.words_known > 0 && s.words_studied > 0) {
            val pctKnown = s.words_known * 100.0 / s.words_studied
            addStatRow(c, "Прогресс (знаю / изучено)", "%.1f%%".format(pctKnown), "#007bff")
        }
        if (s.words_unknown > 0) {
            addStatRow(c, "Неизвестно", s.words_unknown.toString(), "#dc3545")
        }
        if (s.words_skipped > 0) {
            addStatRow(c, "Пропущено", s.words_skipped.toString(), "#ffc107")
        }
        // Слова, которым пора на повторение, но они лежат ниже порога
        // «начальный номер слова» и на занятии не появятся. Поведение отбора
        // намеренно оставлено прежним — человеку просто сказано, что
        // происходит: у живого пользователя так накопилось 2546 невидимых
        // повторений, и увидеть их было негде.
        if (s.words_hidden_by_start_word > 0) {
            addStatRow(c,
                "Ждут повторения, но отсечены (начальный номер = ${s.start_word})",
                s.words_hidden_by_start_word.toString(), "#dc3545")
        }
    }

    private fun dpToPx(dp: Int): Int =
        (dp * resources.displayMetrics.density + 0.5f).toInt()

    private fun addStatRow(parent: LinearLayout, label: String, value: String, valueColor: String) {
        val row = LinearLayout(this)
        row.orientation = LinearLayout.HORIZONTAL
        row.setPadding(0, 12, 0, 12)

        val divider = View(this)
        divider.setBackgroundColor(android.graphics.Color.parseColor("#E0E0E0"))
        divider.layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 1)

        val tvLabel = TextView(this)
        tvLabel.text = label
        tvLabel.textSize = 15f
        tvLabel.layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)

        val tvValue = TextView(this)
        tvValue.text = value
        tvValue.textSize = 18f
        tvValue.setTypeface(null, android.graphics.Typeface.BOLD)
        tvValue.setTextColor(android.graphics.Color.parseColor(valueColor))
        tvValue.gravity = Gravity.END

        row.addView(tvLabel)
        row.addView(tvValue)

        parent.addView(divider)
        parent.addView(row)
    }
}
