package com.langbot.app

import android.app.Dialog
import android.content.Intent
import android.graphics.Color
import android.graphics.Picture
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.PictureDrawable
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.os.Bundle
import androidx.annotation.VisibleForTesting
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.Menu
import android.view.MenuItem
import android.text.SpannableString
import android.text.Spanned
import android.text.TextPaint
import android.text.method.LinkMovementMethod
import android.text.style.ClickableSpan
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import com.google.android.material.card.MaterialCardView
import com.langbot.app.util.correct
import com.langbot.app.util.mistakes
import com.langbot.app.databinding.ActivityStudyBinding
import com.langbot.app.network.BLSClient
import com.langbot.app.network.NetworkRetry
import com.langbot.app.network.Card
import com.langbot.app.network.CardButton
import com.langbot.app.network.PickOption
import com.langbot.app.network.RateRequest
import com.langbot.app.network.SessionResponse
import com.langbot.app.network.StartSessionRequest
import com.langbot.app.offline.AudioCache
import com.langbot.app.offline.BundleRefresh
import com.langbot.app.offline.OfflineCache
import com.langbot.app.offline.OfflineEngine
import com.langbot.app.offline.OfflineSemantics
import com.langbot.app.offline.OutboxSync
import com.langbot.app.offline.StoredBundle
import com.langbot.app.prefs.UserPrefs
import kotlinx.coroutines.launch

class StudyActivity : AppCompatActivity() {

    private lateinit var binding: ActivityStudyBinding
    private lateinit var userId: String
    private lateinit var languageId: String
    private var sessionId: String? = null

    // MediaPlayer instances for the current card's sounds
    private val players = mutableListOf<MediaPlayer>()

    // ── Звук: одна дорожка на экран ─────────────────────────────────────────
    // Варианты произношения играются цепочкой с паузой между ними. Без общего
    // владельца нажатие на другой вариант запускало вторую цепочку поверх
    // первой — а нажимают именно потому, что по первому звуку уже понятно, что
    // слово не то. Обрывать нужно и звук, и отложенный переход к следующему.
    private var playbackGen = 0
    private var activePlayer: MediaPlayer? = null
    private val playbackHandler = Handler(Looper.getMainLooper())
    // Отложенное «соединяемся…»: показывается, только если первая попытка
    // затянулась. См. showConnectionStatus.
    private val connectionHandler = Handler(Looper.getMainLooper())

    // Last pick-mode answer result: true=correct, false=wrong/dont_know, null=not a pick answer
    /**
     * Чем кончился ответ в пик-режиме.
     *
     * Состояния три, а не два. Раньше был Boolean, и «не знаю» попадало в
     * ту же корзину, что и промах: экран отвечал «✗ Неверно». Жалоба
     * владельца: «я выбираю пункт не знаю, на следующем экране статус
     * неправильно — нелогично, я честно признался, что не знаю». Признание
     * незнания и ошибка — разные вещи, и выглядеть должны по-разному.
     */
    private enum class PickOutcome { CORRECT, WRONG, DONT_KNOW }

    private var lastPickAnswerResult: PickOutcome? = null

    // ── Offline mode ──
    // Non-null while the study loop is running from the local cache (network is down).
    private var offline: OfflineEngine? = null
    // word_id of the currently rendered card — used to position the offline engine.
    private var lastWordId: String? = null
    // Guards against recording the current offline word's result more than once.
    private var offlineCurrentRecorded: Boolean = false
    /** Накопленное ушло на сервер — значит, связь есть и офлайн пора закрывать. */
    private var backOnline: Boolean = false

    // Счётчики последней ОНЛАЙН-карточки — отсчёт для офлайна.
    //
    // Офлайн складывал свои ответы со счётчиками карточки из скачанной партии,
    // а они заморожены на времени скачивания — обычно нули. Поэтому в момент
    // пропажи связи «готово» падало с трёх на один, а полоска прогресса
    // откатывалась назад. Теперь офлайн продолжает с того места, на котором
    // человека застала пропажа.
    private var baseCorrect = 0
    private var baseWrong = 0
    private var baseHistory: List<String> = emptyList()
    /**
     * Слова, уже учтённые в отсчёте.
     *
     * После удачной отправки ответы уходят из очереди в отсчёт. Если то же
     * слово ответить ещё раз — а так и бывает после «ой, все-таки не знаю», —
     * оно посчиталось бы дважды, и счётчик сначала подскакивал, а потом падал
     * обратно, когда приходила правда с сервера.
     */
    private var baseWords: MutableSet<String> = mutableSetOf()
    // Засчитано ли текущее офлайновое слово знакомым: от этого зависит, какую
    // ответную сторону показывать — с «Ой, все-таки не знаю» или без.
    private var offlineScoredKnow: Boolean = false

    // Открытое окно увеличения карточки — закрывается вместе с экраном.
    @VisibleForTesting
    var cardZoomDialog: Dialog? = null
        private set

    companion object {
        /** Сколько слов в офлайн-партии, если настройка не задана. */
        const val DEFAULT_BUNDLE_SIZE = 100

        /**
         * Размер офлайн-партии из настроек. Gson отдаёт числа как Double, а
         * настройка могла прийти строкой из старой записи.
         */
        fun bundleSizeOf(settings: Map<String, Any>?): Int {
            val raw = settings?.get("offline_bundle_size")
            val value = when (raw) {
                is Number -> raw.toInt()
                is String -> raw.toIntOrNull() ?: 0
                else -> 0
            }
            return if (value > 0) value else DEFAULT_BUNDLE_SIZE
        }

        private const val MENU_REFRESH = 1
        private const val MENU_STATS   = 2
        private const val MENU_RESTART = 3
        private const val MENU_ZOOM    = 4

        /** Сколько длится уменьшение при возврате (res/anim/zoom_exit.xml). */
        const val ZOOM_EXIT_MS = 420L

        /**
         * Сколько попыток делать на ответ по карточке.
         *
         * Человек ждёт прямо сейчас, а ответ всё равно ляжет в очередь и уйдёт
         * позже. Полная лесенка — двадцать три секунды под пальцем; на слабой
         * связи в метро это и выглядело как «нажал и ничего не происходит».
         */
        const val ANSWER_ATTEMPTS = 2

        /** Сколько длится разворачивание при входе (res/anim/zoom_enter.xml). */
        const val ZOOM_ENTER_MS = 480L

        /**
         * Через сколько сказать, что ждём ответа, на ПЕРВОЙ попытке.
         *
         * Полсекунды — граница, за которой человек перестаёт считать, что
         * нажатие сработало. Живой сервер отвечает за десятки миллисекунд и до
         * этой границы не доживает, поэтому на обычном нажатии плашка не
         * появляется вовсе.
         */
        const val FIRST_WAIT_NOTICE_MS = 500L

        /** Пауза между голосами одного и того же слова. */
        const val BETWEEN_FILES_MS = 350L

        /** Пауза между разными вариантами ответа в пик-режиме. */
        const val BETWEEN_OPTIONS_MS = 800L

        /**
         * Сколько молчать перед следующим файлом.
         *
         * Внутри одного варианта пауза короткая — это одно и то же слово
         * разными голосами, и дробить его незачем. На границе вариантов
         * длиннее: под «▶ Все» они иначе сливаются в один поток, и сравнивать
         * становится нечего. Просьба владельца: «сделать чуть больше паузу
         * между разными строками».
         */
        @VisibleForTesting
        fun gapBefore(next: Int?, after: Int?): Long =
            if (next != after) BETWEEN_OPTIONS_MS else BETWEEN_FILES_MS

        /**
         * Рамка вокруг картинки, пока она разворачивается или сходится в точку.
         *
         * Просьба владельца: во время движения рамку видно, и понятно, что
         * уезжает целый лист, а не мигает экран. Пока картинку разглядывают,
         * рамка не нужна — снимается, когда движение закончилось.
         */
        fun framed(view: View, background: Int, density: Float) {
            val stroke = (3 * density + 0.5f).toInt()
            view.background = GradientDrawable().apply {
                setColor(background)
                setStroke(stroke, Color.parseColor("#222222"))
            }
        }

        /**
         * Обёртка для окна увеличения: рамка ложится по ВИДИМОЙ части экрана.
         *
         * Прежде рамка рисовалась прямо на картинке, растянутой во весь экран:
         * сверху её прятала строка состояния, а снизу оставалась широкая чёрная
         * полоса — место под навигацию. Обёртка с fitsSystemWindows отступает
         * от обеих полос, и рамка получается ровной со всех сторон.
         */
        fun zoomFrame(context: android.content.Context, content: View, background: Int): View {
            val box = android.widget.FrameLayout(context)
            box.fitsSystemWindows = true
            box.setBackgroundColor(background)
            box.addView(content, android.widget.FrameLayout.LayoutParams(
                android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                android.widget.FrameLayout.LayoutParams.MATCH_PARENT))
            return box
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityStudyBinding.inflate(layoutInflater)
        setContentView(binding.root)

        userId = UserPrefs.getUserId(this) ?: run { finish(); return }
        languageId = intent.getStringExtra("language_id") ?: run { finish(); return }
        val langName = intent.getStringExtra("language_name") ?: "Учёба"

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = langName
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.swipeRefresh.setOnRefreshListener {
            loadSession()
        }

        // Запасные ссылки отдельной строкой: нужны, только если в тексте
        // плашки не нашлось слов, на которые ссылку вешать. См. showNotice.
        listOf(binding.linkRestartNow, binding.linkRestartStale).forEach { link ->
            link.paintFlags = link.paintFlags or android.graphics.Paint.UNDERLINE_TEXT_FLAG
            link.setOnClickListener { confirmRestart() }
        }

        OfflineCache.init(this)  // defensive — normally done in LangBotApp
        AudioCache.init(this)

        loadSession()
    }

    override fun onDestroy() {
        super.onDestroy()
        releasePlayers()
        cardZoomDialog?.dismiss()
        cardZoomDialog = null
    }

    /**
     * Карточка целиком на весь экран, с увеличением пальцами.
     *
     * Увеличивать нужно не только графики: огласовки в таблицах — мелкие знаки
     * под буквами, и в обычном кегле их не разглядеть. Снимаем рисунок уже
     * собранного столбца карточки: в нём те же таблицы, подсветки и направление
     * письма, и при увеличении текст перерисовывается буквами, а не
     * растягивается пикселями, как было бы со снимком картинкой.
     *
     * Рисунок — весь столбец, включая то, что ниже края экрана: увеличение не
     * должно обрываться там, где кончилась видимая часть. Кнопки ответа в него
     * тоже попадают, но там они просто нарисованы и ничего не делают.
     *
     * @param from блок, по которому нажали: с него и открываем. null — от начала
     *             карточки (пункт меню «Увеличить»).
     */
    private fun openCardZoom(from: View?) {
        // Второе нажатие, пока первое окно ещё открыто, не открывает второе.
        //
        // Жалоба владельца: «если нажать быстро 2 раза — открываются 2
        // увеличенных картинки». Нажатие приходит и на блок карточки, и на
        // пункт меню, а поле cardZoomDialog помнит только последнее окно:
        // первое оставалось висеть под вторым, и закрыть его было нечем —
        // возврат убирал верхнее, а под ним оказывалось такое же.
        if (cardZoomDialog?.isShowing == true) return
        val content = binding.cardScrollContent
        if (content.width <= 0 || content.height <= 0) return
        val picture = Picture()
        content.draw(picture.beginRecording(content.width, content.height))
        picture.endRecording()

        val view = ZoomImageView(this)
        // Столбец карточки прозрачный: без фона под ним чернел бы фон окна.
        val box = zoomFrame(this, view, Color.WHITE)
        // Рамка — на время разворачивания, потом снимается.
        framed(box, Color.WHITE, resources.displayMetrics.density)
        val focus = from?.let { readableColumns(it, content) }
        view.showDrawing(
            PictureDrawable(picture),
            focus?.first ?: from?.let { topWithin(it, content) } ?: 0,
            focusLeftPx = focus?.second ?: 0,
            focusWidthPx = focus?.third ?: 0,
        )

        val dialog = Dialog(this, android.R.style.Theme_Black_NoTitleBar_Fullscreen)
        // Рост из середины при входе и уменьшение при возврате: без анимации
        // момент перехода терялся — экран просто подменялся другим.
        dialog.window?.attributes?.windowAnimations = R.style.ZoomDialogAnimation
        dialog.setContentView(box)
        dialog.setOnDismissListener {
            // onDismiss приходит В НАЧАЛЕ закрытия: здесь возвращаем рамку на
            // время схождения в точку, а картинку отпускаем, когда движение
            // закончится. Прежде очистка гасила картинку сразу, и уменьшение
            // играло на пустом окне.
            framed(box, Color.WHITE, resources.displayMetrics.density)
            view.postDelayed({ view.setImageDrawable(null) }, ZOOM_EXIT_MS)
            if (cardZoomDialog === dialog) cardZoomDialog = null
        }
        dialog.show()
        // Разглядывать карточку в рамке незачем — снимаем, когда доехала.
        box.postDelayed({ box.setBackgroundColor(Color.WHITE) }, ZOOM_ENTER_MS)
        cardZoomDialog = dialog
    }

    /**
     * Читаемые колонки таблицы в нажатом блоке: (верх, левый край, ширина).
     *
     * Жалоба владельца: «экран увеличения экстра-инфо открывается в размере в
     * точности как исходный» — то есть не увеличивает. Увеличивать надо по
     * тому, ради чего в таблицу и смотрят: по переводу и самому слову. Номер
     * слева и транскрипция справа при этом уезжают за край, и к ним можно
     * отлистнуть.
     *
     * Колонки находим по самой таблице, а не по числам: в строке четыре
     * ячейки, нужны вторая и третья. Если таблицы в блоке нет — возвращаем
     * null, и блок открывается как раньше, в натуральную величину.
     */
    private fun readableColumns(block: View, root: View): Triple<Int, Int, Int>? {
        val row = findTableRow(block) ?: return null
        val ru = row.getChildAt(1) ?: return null
        val foreign = row.getChildAt(2) ?: return null
        if (ru.width <= 0 || foreign.width <= 0) return null
        val table = row.parent as? View ?: return null
        val left = leftWithin(ru, root)
        // Сверху начинаем не с таблицы, а с её заголовка: по просьбе владельца
        // «чтобы влезал заголовок над таблицей». Без него на экране оказывалась
        // безымянная сетка — непонятно, огласовки это, однокоренные или группа
        // тега. По ширине ничего не меняется: заголовок стоит выше, а не левее.
        val anchor = headingAbove(table) ?: table
        return Triple(topWithin(anchor, root), left, ru.width + foreign.width)
    }

    /** Ближайшая надпись над таблицей — её заголовок, если он есть. */
    private fun headingAbove(table: View): View? {
        val parent = table.parent as? ViewGroup ?: return null
        for (i in parent.indexOfChild(table) - 1 downTo 0) {
            val v = parent.getChildAt(i)
            if (v.visibility != View.VISIBLE) continue
            return if (v is TextView && v.text.isNotBlank()) v else null
        }
        return null
    }

    /** Первая строка таблицы внутри блока: ряд ровно из четырёх ячеек. */
    private fun findTableRow(block: View): ViewGroup? {
        val group = block as? ViewGroup ?: return null
        if (group is LinearLayout && group.orientation == LinearLayout.HORIZONTAL &&
            group.childCount == 4 && (0 until 4).all { group.getChildAt(it) is TextView }) {
            return group
        }
        for (i in 0 until group.childCount) {
            val found = findTableRow(group.getChildAt(i))
            if (found != null) return found
        }
        return null
    }

    /** Насколько правее начала столбца стоит ячейка: сумма отступов по дереву. */
    private fun leftWithin(view: View, root: View): Int {
        var x = 0
        var v: View? = view
        while (v != null && v !== root) {
            x += v.left
            v = v.parent as? View
        }
        return x
    }

    /** Насколько ниже начала столбца стоит блок: сумма отступов по дереву. */
    private fun topWithin(view: View, root: View): Int {
        var y = 0
        var v: View? = view
        while (v != null && v !== root) {
            y += v.top
            v = v.parent as? View
        }
        return y
    }

    /** Нажатие на блок карточки — открыть его на весь экран. */
    private fun makeZoomable(block: View) {
        block.isClickable = true
        block.setOnClickListener { openCardZoom(block) }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add(0, MENU_ZOOM,    0, "🔍 Увеличить")
        menu.add(0, MENU_REFRESH, 1, "↺ Обновить")
        menu.add(0, MENU_STATS,   2, "📊 Статистика")
        menu.add(0, MENU_RESTART, 3, "🔄 Начать заново")
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == MENU_ZOOM) {
            openCardZoom(null)
            return true
        }
        if (item.itemId == MENU_REFRESH) {
            loadSession()
            return true
        }
        if (item.itemId == MENU_STATS) {
            startActivity(Intent(this, StatsActivity::class.java).apply {
                putExtra("language_id", languageId)
                putExtra("language_name", intent.getStringExtra("language_name") ?: "")
            })
            return true
        }
        if (item.itemId == MENU_RESTART) {
            confirmRestart()
            return true
        }
        return super.onOptionsItemSelected(item)
    }

    /**
     * Спросить и перезапустить. Одно и то же и для меню, и для кнопки в плашке:
     * плашка советует перезапустить сессию, и ход к этому должен быть прямо в
     * ней, а не через меню — но подтверждение нужно одинаковое, сброс круга
     * необратим.
     */
    private fun confirmRestart() {
        AlertDialog.Builder(this)
            .setTitle("Начать заново?")
            .setMessage("Текущая сессия будет сброшена. Слова начнутся с начала.")
            .setPositiveButton("Начать") { _, _ -> restartSession() }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun restartSession() {
        setLoading(true)
        lifecycleScope.launch {
            // Закрытие сессии на сервере — необязательный шаг: если он не дошёл,
            // локальный сброс всё равно должен произойти, иначе кнопка «Начать
            // заново» снова выглядит как ничего не делающая.
            NetworkRetry.call(onStatus = { showConnectionStatus(it) }) { api ->
                api.endSession(userId, languageId)
            }
            clearConnectionStatus()
            sessionId = null
            // Reset the offline side too. Without this, restarting with no network
            // fell through to enterOfflineFromStore(), which positions the engine at
            // lastWordId — so "начать заново" landed back on the very same word and
            // looked like it did nothing.
            lastWordId = null
            // Не просто в начало партии, а в начало ОСТАВШЕГОСЯ: онлайн сервер
            // пересчитывает набор на день и уже отвеченное не выдаёт, офлайн
            // должен вести себя так же.
            OfflineCache.excludeAnswered(userId, languageId)
            // Новый круг — счёт с нуля, в том числе офлайновый отсчёт.
            baseCorrect = 0; baseWrong = 0; baseHistory = emptyList()
            baseWords = mutableSetOf()
            OfflineCache.clearProgress(userId, languageId)
            loadSession()
        }
    }

    // ── Session loading ────────────────────────────────────────────────────────

    /** Перезагрузить сессию (для проверок — то же, что «потянуть вниз»). */
    @VisibleForTesting
    fun refreshForTest() = loadSession()

    /**
     * Поставить отметку «звучит сейчас» на вариант (для проверок).
     *
     * Сам звук в проверках не играет: MediaPlayer там заглушка, и дождаться от
     * неё перехода к следующему файлу нельзя. Проверяется то, что видно
     * человеку, — как отмечен звучащий вариант и снимается ли отметка.
     */
    @VisibleForTesting
    fun markPlayingForTest(option: Int?) = markPlayingOption(option)

    /** Плашка ожидания сети — для проверок: настоящую сеть тут не подождать. */
    @VisibleForTesting
    fun showWaitingForTest(status: NetworkRetry.Status) = showConnectionStatus(status)

    @VisibleForTesting
    fun clearWaitingForTest() = clearConnectionStatus()

    private fun loadSession() {
        setLoading(true)
        lifecycleScope.launch {
            try {
                // Накопленное офлайном отправляем ДО того, как спросить сессию.
                // Иначе сервер отвечает со старого места — того, где пропала
                // сеть, — мы его показываем, а пачка долетает следом и двигает
                // сессию. Со стороны это выглядит как возврат назад, а потом
                // перескок через слово.
                if (OfflineCache.pendingCount() > 0) {
                    runCatching { OutboxSync.flush() }
                }
                val resp = NetworkRetry.call(onStatus = { showConnectionStatus(it) }) { api ->
                    var r = api.getSession(userId, languageId)
                    if (!r.isSuccessful || r.body()?.session_id == null) {
                        r = api.startSession(StartSessionRequest(userId, languageId))
                    }
                    r
                }
                clearConnectionStatus()
                if (resp == null) {
                    // Сервер недостижим — учимся из кеша, не заставляя ждать впустую.
                    // Здесь нажатия пользователя не ждут применения, поэтому любое
                    // положение курсора годится: лишь бы было что показать.
                    if (enterOfflineFromStore() == OfflineEntry.NO_BUNDLE) {
                        showError("Нет сети и нет сохранённой сессии для офлайн-работы")
                    }
                    return@launch
                }
                offline = null  // back online
                handleResponse(resp.body())
                // Оставшееся (если что-то не подтвердилось) и свежая партия —
                // фоном, экран их не ждёт.
                flushOutboxInBackground()
                prefetchBundleInBackground()
            } catch (e: Exception) {
                // Network is down — fall back to the cached bundle if we have one.
                if (enterOfflineFromStore() == OfflineEntry.NO_BUNDLE) {
                    showError("Нет сети и нет сохранённой сессии для офлайн-работы")
                    Toast.makeText(this@StudyActivity, "[${e.javaClass.simpleName}] ${e.message}", Toast.LENGTH_LONG).show()
                }
            } finally {
                setLoading(false)
            }
        }
    }

    /**
     * Подкачать офлайн-партию фоном; экран её не ждёт.
     *
     * Сначала спрашиваем настройки — запрос лёгкий, одна запись, — и по ним
     * решаем, нужно ли качать саму партию: её размер теперь выбирает человек, и
     * на пятистах словах это около восьми мегабайт. Настройки сохраняем в любом
     * случае: без сети экран настроек показывает именно их.
     */
    private fun prefetchBundleInBackground() {
        lifecycleScope.launch {
            runCatching {
                val settings = BLSClient.api.getSettings(userId, languageId).body()
                val wanted = bundleSizeOf(settings)
                val stored = OfflineCache.loadBundle(userId, languageId)
                if (!BundleRefresh.needed(stored, wanted, System.currentTimeMillis())) {
                    if (settings != null && stored != null) {
                        OfflineCache.saveBundle(stored.copy(settings = settings))
                    }
                    return@runCatching
                }
                val resp = BLSClient.api.getBundle(userId, languageId)
                val body = resp.body()
                if (resp.isSuccessful && body != null && body.words.isNotEmpty()) {
                    OfflineCache.saveBundle(
                        StoredBundle(userId, languageId, body.words, cursor = 0,
                                     settings = body.settings.ifEmpty { settings ?: emptyMap() },
                                     requestedSize = wanted,
                                     savedAt = System.currentTimeMillis())
                    )
                    // Phase 3: pull each word's sounds into the on-disk cache so audio
                    // plays offline too. Returns immediately — AudioCache downloads in
                    // parallel on its own process-lifetime scope, so leaving this screen
                    // no longer cancels the download halfway.
                    AudioCache.prefetch(body.words.flatMap { it.sounds })
                }
            }
        }
    }

    /** Flush any accumulated offline results; never blocks the UI. */
    private fun flushOutboxInBackground() {
        lifecycleScope.launch { runCatching { OutboxSync.flush() } }
    }

    // ── Offline study loop ───────────────────────────────────────────────────────

    /**
     * Показать, что происходит с соединением, пока идут попытки.
     *
     * Без этого нажатие кнопки при недостижимом сервере выглядело как «ничего не
     * произошло»: экран замирал на время таймаута.
     *
     * Плашка лежит ПОВЕРХ карточки, а не в её столбце. Встроенная в поток, она
     * сдвигала всё вниз, и по нижней части экрана это читалось как переход к
     * следующему слову: приходилось перечитывать карточку, чтобы понять, что
     * ничего не изменилось. Своя плашка нужна и затем, чтобы не делить место с
     * restart_notice — то сообщение про саму сессию и к связи отношения не имеет.
     */
    private fun showConnectionStatus(status: NetworkRetry.Status) {
        connectionHandler.removeCallbacksAndMessages(null)
        if (status.attempt == 1) {
            // Первая попытка короткая: живой сервер отвечает за десятки мс, и
            // показывать «соединяемся» на каждое нажатие значило бы мигать
            // плашкой впустую. Но если ответа нет и через полсекунды, молчать
            // нельзя — жалоба владельца: «до первого сообщения про таймаут
            // непонятно, ждём или зависло».
            connectionHandler.postDelayed({
                binding.tvConnection.text = "⏳ ${status.message}"
                binding.tvConnection.visibility = View.VISIBLE
            }, FIRST_WAIT_NOTICE_MS)
            return
        }
        binding.tvConnection.text = status.message
        binding.tvConnection.visibility = View.VISIBLE
    }

    private fun clearConnectionStatus() {
        connectionHandler.removeCallbacksAndMessages(null)
        binding.tvConnection.visibility = View.GONE
    }

    /** Чем закончилась попытка уйти в офлайн. */
    private enum class OfflineEntry {
        /** Кеша нет — офлайн невозможен. */
        NO_BUNDLE,
        /** Офлайн начат, но с сохранённого места: слова с экрана в партии нет. */
        OTHER_WORD,
        /** Офлайн начат ровно на том слове, что было на экране. */
        SAME_WORD,
    }

    /**
     * Switch to offline mode using the cached bundle, positioned at the current word.
     *
     * Возвращает [OfflineEntry.OTHER_WORD], если слова с экрана в кеше нет:
     * движок тогда стоит на сохранённом курсоре, и применять к нему нажатие
     * пользователя нельзя — оценка ушла бы в outbox (и дальше на сервер) за
     * чужое слово, молча и без следов.
     */
    private fun enterOfflineFromStore(render: Boolean = true): OfflineEntry {
        val eng = OfflineEngine.fromStore(userId, languageId) ?: return OfflineEntry.NO_BUNDLE
        val sameWord = eng.positionAtWord(lastWordId)
        if (!eng.hasCurrent()) return OfflineEntry.NO_BUNDLE
        offline = eng
        offlineCurrentRecorded = false
        offlineScoredKnow = false
        // Экран открыт заново без связи: отсчёт берём с диска, иначе счётчики
        // покажут ноль, хотя человек сегодня уже занимался.
        if (baseCorrect == 0 && baseWrong == 0 && baseHistory.isEmpty()) {
            OfflineCache.loadProgress(userId, languageId)?.let {
                baseCorrect = it.correct; baseWrong = it.wrong; baseHistory = it.history
            }
        }
        // render=false, когда вызывающий тут же применит нажатие пользователя и
        // отрисует результат сам. Иначе экран рисовался ДВАЖДЫ: сначала вопрос
        // текущего слова, следом — результат действия. Со стороны это выглядело
        // как проскочивший экран: нажал «Знаю» при пропавшей сети и увидел, как
        // мимо мелькнул вопрос, прежде чем показался ответ.
        if (render) {
            renderOfflineCurrent(showAnswer = false)
        }
        Toast.makeText(this, "Нет сети — занимаемся офлайн", Toast.LENGTH_SHORT).show()
        return if (sameWord) OfflineEntry.SAME_WORD else OfflineEntry.OTHER_WORD
    }

    /** Ответ на слово, которого нет в офлайн-партии, записывать некуда — объясняем. */
    private fun warnOfflineWordMissing() {
        Toast.makeText(
            this,
            "Нет сети, а это слово не сохранено для офлайна — ответ не записан. " +
                    "Продолжаем с сохранённого места.",
            Toast.LENGTH_LONG,
        ).show()
    }

    /**
     * Apply a card-button action locally against the cached bundle.
     * Semantics come from the button itself (server-declared in the bundle);
     * OfflineSemantics is a compat fallback for bundles cached before those fields.
     */
    private fun handleOfflineAction(btn: CardButton) {
        offline ?: return
        val effect = btn.offline_effect ?: OfflineSemantics.effectFor(btn.id) ?: return
        when (effect) {
            "reveal_answer"   -> renderOfflineCurrent(showAnswer = true)

            // «Ой, все-таки не знаю»: записать поправку и ПЕРЕЙТИ ДАЛЬШЕ —
            // ровно то, что делает онлайн. Там /reconsider ставит «не знаю» и
            // сразу листает; офлайн же возвращал на вопрос того же слова, и
            // человеку приходилось отвечать «не знаю» второй раз, чтобы
            // сдвинуться. Жалоба владельца: «ожидаю что перейду на следующее
            // слово — так в онлайн режиме».
            //
            // Поправка без сети пишется более поздним ответом в очередь:
            // сервер применяет последний по времени, иначе отменить
            // засчитанное знакомым было бы нечем.
            //
            // Если оценки с кнопкой не пришло (старый сервер — действие
            // подставляет OfflineSemantics по id кнопки), листать нельзя:
            // поправку никто не записал, и переход потерял бы её молча.
            // Тогда остаётся прежнее поведение — назад к вопросу.
            "reveal_question" -> {
                val rating = btn.offline_rating
                if (rating != null) {
                    recordOffline(rating, correction = true)
                    advanceOffline()
                } else {
                    renderOfflineCurrent(showAnswer = false)
                }
            }

            // «Знаю»: записать оценку и ПОКАЗАТЬ ответ, не листая дальше — так же,
            // как онлайн know_word(). Раньше эта кнопка была помечена submit, и
            // офлайн перебрасывал сразу на следующее слово, минуя карточку с
            // переводом и транскрипцией.
            "record_and_reveal" -> {
                val r = btn.offline_rating ?: OfflineSemantics.ratingFor(btn.id, btn.rating)
                recordOffline(r, explicit = true)
                renderOfflineCurrent(showAnswer = true)
            }

            // Оценка уже записана — здесь только переход, иначе результат уйдёт дважды.
            "advance" -> advanceOffline()

            "submit" -> {
                val r = btn.offline_rating ?: OfflineSemantics.ratingFor(btn.id, btn.rating)
                recordOffline(r)
                advanceOffline()
            }
        }
    }

    /** Apply a pick-mode answer locally against the cached bundle. */
    private fun handleOfflinePick(selectedWordId: String) {
        val eng = offline ?: return
        val option = eng.frontCard()?.pick_options?.options?.firstOrNull { it.word_id == selectedWordId }
        // Rating is server-declared per option; fall back to is_correct for old bundles.
        val rating = when {
            selectedWordId == "dont_know" -> "dont_know"
            option?.offline_rating != null -> option.offline_rating
            else -> if (option?.is_correct == true) "know" else "dont_know"
        }
        lastPickAnswerResult = when {
            selectedWordId == "dont_know" -> PickOutcome.DONT_KNOW
            rating == "know" -> PickOutcome.CORRECT
            else -> PickOutcome.WRONG
        }
        recordOffline(rating)
        // Reveal the answer; the word is already banked, so any follow-up just advances.
        renderOfflineCurrent(showAnswer = true)
    }

    /**
     * Записать оценку текущего слова в очередь.
     *
     * @param correction поправка к уже записанному ответу («Ой, все-таки не
     *        знаю»). Защиту от повторной записи она обходит намеренно: сервер
     *        применяет ответы по времени, и более поздний перекрывает прежний —
     *        иначе отменить засчитанное знакомым без сети было бы нечем.
     */
    /**
     * @param correction поправка к уже записанному ответу («Ой, все-таки не
     *        знаю»): защиту от повторной записи обходит намеренно — сервер
     *        применяет ответы по времени, и более поздний перекрывает прежний.
     * @param explicit человек сам нажал оценку на карточке вопроса. Такой ответ
     *        тоже обходит защиту: после поправки он возвращается к вопросу и
     *        отвечает заново, и этот ответ обязан быть записан. Защита нужна
     *        только от АВТОМАТИЧЕСКОЙ второй записи — когда после «Знаю»
     *        нажимают «Дальше», и переход пытается записать ещё один ответ.
     */
    private fun recordOffline(rating: String, correction: Boolean = false,
                              explicit: Boolean = false) {
        val eng = offline ?: return
        if (offlineCurrentRecorded && !correction && !explicit) return
        eng.record(rating)
        probeNetworkInBackground()
        offlineCurrentRecorded = true
        offlineScoredKnow = rating == "know"
    }

    /**
     * Связь могла вернуться, пока мы занимались без неё.
     *
     * Жалоба владельца: «включил сеть, прошёл ещё несколько слов — плашка
     * офлайн не пропала». Сама по себе она и не пропадёт: выход из офлайна
     * происходит только при загрузке сессии. Поэтому после каждого ответа тихо
     * пробуем отправить накопленное: получилось — значит, сеть есть.
     */
    private fun probeNetworkInBackground() {
        if (offline == null) return
        lifecycleScope.launch {
            // Что сейчас показано из очереди: после удачной отправки эти ответы
            // из неё исчезнут, и счётчик просел бы на столько же. Поэтому
            // переносим их в отсчёт — они уже у сервера.
            val mine = OfflineCache.loadOutbox()
                .filter { it.userId == userId && it.languageId == languageId }
                .filterNot { offline?.isExcluded(it.word_id) == true }
                .sortedBy { it.ts }
                .associate { it.word_id to it.rating }
            val ok = runCatching {
                OutboxSync.flush()
                OfflineCache.pendingCount() == 0
            }.getOrDefault(false)
            if (ok) {
                val fresh = mine.filterKeys { it !in baseWords }
                baseCorrect += fresh.values.count { it == "know" }
                baseWrong += fresh.values.count { it == "dont_know" }
                baseHistory = baseHistory + fresh.values.filter { it != "skip" }
                baseWords.addAll(fresh.keys)
                OfflineCache.saveProgress(userId, languageId, baseCorrect, baseWrong, baseHistory)
                backOnline = true
            }
        }
    }

    private fun advanceOffline() {
        val eng = offline ?: return
        // Связь вернулась — дальше идём из сети, но не посреди карточки, а на
        // переходе к следующему слову: так экран не дёргается под рукой.
        if (backOnline) {
            backOnline = false
            offline = null
            loadSession()
            return
        }
        eng.advance()
        offlineCurrentRecorded = false
        offlineScoredKnow = false
        if (eng.atEnd()) showOfflineDone() else renderOfflineCurrent(showAnswer = false)
    }

    private fun renderOfflineCurrent(showAnswer: Boolean) {
        val eng = offline ?: return
        // Засчитанное знакомым показываем той стороной, где есть отмена:
        // офлайн раньше показывал карточку «до ответа», и отменить оценку было
        // нечем — слово уходило выученным, а интервал повторения растягивался.
        val card = when {
            !showAnswer -> eng.frontCard()
            offlineScoredKnow -> eng.knownCard()
            else -> eng.answerCard()
        }
        if (card == null) { showOfflineDone(); return }
        renderCard(withOfflineProgress(card))
        showOfflineBanner()
    }

    /**
     * Дописать в карточку то, что сделано офлайн: счётчики и полоску прогресса.
     *
     * Карточки партии отрисованы заранее, и счётчики в них заморожены на момент
     * скачивания — одинаковые у всех слов, потому что build_bundle двигает
     * вперёд только позицию. Внизу экрана поэтому ничего не менялось, сколько бы
     * слов человек ни прошёл офлайн.
     *
     * Считаем по outbox: там лежат ровно ответы, данные офлайн и ещё не
     * отправленные. Пропуски в счётчики не идут — онлайн они тоже не считаются
     * ни правильными, ни ошибками.
     */
    private fun withOfflineProgress(card: Card): Card {
        val eng = offline
        // Ответы прошлых кругов в счёт не идут: перезапуск вывел их из партии,
        // и засчитывать их в «готово» нового круга значило бы показывать
        // прогресс, которого в нём нет.
        // По одному ответу на СЛОВО, последнему по времени.
        //
        // В очереди на одно слово бывает несколько записей: поправка «ой,
        // все-таки не знаю» дописывает вторую, а повторный ответ — третью.
        // Считая записи, экран показывал «в сессии: 3» на первом же слове и
        // завышал «готово».
        val done = OfflineCache.loadOutbox()
            .filter { it.userId == userId && it.languageId == languageId }
            .filterNot { eng != null && eng.isExcluded(it.word_id) }
            .sortedBy { it.ts }
            .associate { it.word_id to it.rating }
            .filterKeys { it !in baseWords }      // уже в отсчёте — не считать снова
            .values.toList()
        val meta = card.meta
        // Размер круга берём у движка: в партии лежат все слова дня, а круг
        // после перезапуска короче на уже отвеченные.
        val total = eng?.total?.takeIf { it > 0 }
        if (done.isEmpty() && total == null) return card
        // Счётчик «в сессии: N из M» сервер присылает уже СТРОКОЙ, и в партии
        // он застывает на том, каким был при скачивании: у владельца висело
        // «124 из 121» — позиция из партии, размер из круга. Офлайн считаем
        // сами.
        //
        // Позицию берём у движка: его курсор — это и есть номер слова в круге,
        // с учётом выведенных перезапуском. Прежде позиция считалась по длине
        // очереди, и после ответов, уже ушедших на сервер, она откатывалась
        // назад: пройдя слово онлайн и продолжив без сети, экран показывал
        // «в сессии: 1», стоя на втором слове.
        val pos = eng?.let { it.cursor + 1 } ?: (done.size + 1)
        val counter = when {
            total == null -> meta.session_counter_text
            pos >= total -> "(завершающее в текущей сессии: $pos)"
            else -> "(в сессии: $pos из $total)"
        }
        return card.copy(meta = meta.copy(
            correct_count = baseCorrect + done.count { it == "know" },
            incorrect_count = baseWrong + done.count { it == "dont_know" },
            result_history = baseHistory + done.filter { it != "skip" },
            session_pos = pos,
            session_counter_text = counter,
            session_total = total ?: meta.session_total,
            words_for_today = total ?: meta.words_for_today,
        ))
    }

    /**
     * Показать плашку, сделав ссылкой сами слова о перезапуске.
     *
     * Жалоба владельца: «сделать не отдельной строкой, а прямо в тексте, на
     * словах о рекомендации перезапуска». Отдельная строка — это ещё один
     * предмет на экране; слово, по которому можно нажать, не занимает ничего.
     *
     * Текст плашки приходит с сервера, и слов в нём может не оказаться (сервер
     * старее приложения или текст переписали). Тогда показываем запасную
     * ссылку отдельной строкой: потерять ход к действию нельзя.
     */
    private fun showNotice(box: View, textView: TextView, fallback: View,
                           text: String, phrase: String?) {
        // Отдельная переменная, а не phrase: из «нашлось» компилятор не выводит
        // «не null», и ниже понадобилась бы длина.
        val words = phrase.orEmpty()
        val at = if (words.isEmpty()) -1 else text.indexOf(words)
        if (at < 0) {
            textView.text = text
            textView.movementMethod = null
            fallback.visibility = if (phrase == null) View.GONE else View.VISIBLE
        } else {
            val span = SpannableString(text)
            span.setSpan(object : ClickableSpan() {
                override fun onClick(widget: View) = confirmRestart()
                override fun updateDrawState(ds: TextPaint) {
                    // Цвет оставляем плашкин: синяя ссылка на жёлтом фоне
                    // выглядит чужой. Подчёркивание и насыщенность говорят
                    // «сюда можно нажать» не хуже.
                    ds.isUnderlineText = true
                    ds.isFakeBoldText = true
                }
            }, at, at + words.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            textView.text = span
            textView.movementMethod = LinkMovementMethod.getInstance()
            fallback.visibility = View.GONE
        }
        box.visibility = View.VISIBLE
    }

    private fun showOfflineBanner() {
        val pending = OfflineCache.pendingCount()
        // Без ссылки вовсе: сообщение об офлайне ничего не советует перезапускать.
        showNotice(binding.staleNotice, binding.tvStaleSession, binding.linkRestartStale,
                   "📴 Офлайн — результаты сохраняются локально ($pending) и отправятся при подключении",
                   phrase = null)
    }

    private fun showOfflineDone() {
        offline = null
        flushOutboxInBackground()
        showAllDone(offline = true)
        // Карточка уже говорит всё; плашка сверху повторяла бы её слово в слово.
        binding.staleNotice.visibility = View.GONE
    }

    private fun handleResponse(resp: SessionResponse?) {
        if (resp == null) { showError("Нет ответа от сервера"); return }
        sessionId = resp.session_id
        if (resp.session_stale) {
            // Плашка сама предлагает начать заново — эти слова и есть ссылка.
            showNotice(binding.staleNotice, binding.tvStaleSession, binding.linkRestartStale,
                       "⏰ Сессия устарела — вы давно не занимались. "
                       + "Можно продолжить или начать заново.",
                       phrase = "начать заново")
        } else {
            binding.staleNotice.visibility = View.GONE
        }
        val card = resp.card
        if (card == null) {
            showAllDone()
        } else {
            renderCard(card)
        }
    }

    // ── Card rendering ─────────────────────────────────────────────────────────

    private fun renderCard(card: Card) {
        val meta = card.meta
        if (meta.word_id.isNotEmpty()) lastWordId = meta.word_id
        // Пока мы в сети, запоминаем счётчики: с них продолжит офлайн.
        if (offline == null) {
            // И само место в круге — тоже. Курсор офлайн-партии двигали только
            // офлайновые ответы; экран, открытый без сети, садился на то место,
            // где курсор застыл в прошлый раз, и это выглядело как перескок на
            // чужое слово. См. OfflineCache.rememberPlace.
            if (meta.word_id.isNotEmpty()) {
                OfflineCache.rememberPlace(userId, languageId, meta.word_id)
            }
            baseCorrect = meta.correct_count
            baseWrong = meta.incorrect_count
            baseHistory = meta.result_history
            // Сервер посчитал всё сам — своих «уже учтённых» больше нет.
            //
            // Кроме одного случая: текущее слово сервер МОГ уже засчитать, а
            // карточку показать как вопрос. Так бывает после возврата «ой,
            // все-таки не знаю»: BLS ставит счёт 0, прибавляет ошибку и
            // возвращает к вопросу. Если человек в этот момент отвечает без
            // сети, его ответ попадает в очередь — и прибавлялся к счётчикам
            // ВТОРЫМ: на одном слове выходило «готово 2».
            //
            // Узнаём по разнице: правильные с ошибками сервер прибавляет сразу
            // при оценке, а историю ответов пополняет только на переходе к
            // следующему слову. Значит, счётчики впереди истории ровно тогда,
            // когда текущее слово уже посчитано, но ещё не пройдено.
            baseWords = mutableSetOf()
            val alreadyScored =
                meta.correct_count + meta.incorrect_count > meta.result_history.size
            if (alreadyScored && meta.word_id.isNotEmpty()) baseWords.add(meta.word_id)
            // И на диск: экран могут открыть заново уже без связи.
            OfflineCache.saveProgress(userId, languageId, baseCorrect, baseWrong, baseHistory)
        }
        val barTotal = meta.session_total?.takeIf { it > 0 }
        binding.tvBadge.visibility = View.GONE  // badge now lives inside cardContent
        binding.divider.visibility = View.VISIBLE  // экран завершения его прячет

        // Restart notice above card
        if (!card.restart_notice.isNullOrEmpty()) {
            showNotice(binding.restartNotice, binding.tvRestartNotice, binding.linkRestartNow,
                       card.restart_notice, phrase = "перезапустить сессию")
        } else {
            binding.restartNotice.visibility = View.GONE
        }

        // Main content — header row (word number + badge) then content items
        binding.cardContent.removeAllViews()

        // Header row: word number left, badge right
        val headerRow = LinearLayout(this)
        headerRow.orientation = LinearLayout.HORIZONTAL
        headerRow.layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)

        // Left column: word number + session position
        val leftCol = LinearLayout(this)
        leftCol.orientation = LinearLayout.VERTICAL
        leftCol.layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)

        var headerHasContent = false
        meta.word_number?.let { n ->
            val numText = buildString {
                append("Слово номер: ")
                append(n)
                meta.words_studied.takeIf { it > 0 }?.let { append(" / $it") }
                meta.total_words.takeIf   { it > 0 }?.let { append(" / $it") }
            }
            val tvNum = TextView(this)
            val span = android.text.SpannableString(numText)
            val numStart = "Слово номер: ".length
            span.setSpan(android.text.style.StyleSpan(android.graphics.Typeface.BOLD),
                numStart, numText.length, android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            tvNum.text = span
            tvNum.textSize = 14f
            tvNum.setTextColor(Color.parseColor("#888888"))
            leftCol.addView(tvNum)

            when {
                meta.is_new_word && meta.new_word_label.isNotEmpty() -> {
                    val tvNew = TextView(this)
                    tvNew.text = meta.new_word_label
                    tvNew.textSize = 14f
                    tvNew.setTextColor(Color.parseColor("#aaaaaa"))
                    leftCol.addView(tvNew)
                }
                meta.show_session_counter && meta.session_counter_text.isNotEmpty() -> {
                    val tvSess = TextView(this)
                    tvSess.text = meta.session_counter_text
                    tvSess.textSize = 14f
                    tvSess.setTextColor(Color.parseColor("#aaaaaa"))
                    leftCol.addView(tvSess)
                }
            }
            headerHasContent = true
        }
        headerRow.addView(leftCol)

        // Right column: 2 badges (current state + new state after answer)
        val badge = meta.score_badge
        if (badge != null) {
            val badgeCol = LinearLayout(this)
            badgeCol.orientation = LinearLayout.VERTICAL
            badgeCol.gravity = Gravity.END
            val badgeColLp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            badgeColLp.gravity = Gravity.CENTER_VERTICAL
            badgeCol.layoutParams = badgeColLp

            fun makeBadge(text: String, colorHex: String): TextView {
                val tv = TextView(this)
                tv.text = text
                tv.textSize = 11f
                tv.setTextColor(Color.WHITE)
                tv.setPadding(dpToPx(6), dpToPx(3), dpToPx(6), dpToPx(3))
                val bg = GradientDrawable()
                bg.cornerRadius = dpToPx(4).toFloat()
                bg.setColor(Color.parseColor(colorHex))
                tv.background = bg
                val lp = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                lp.gravity = Gravity.END
                tv.layoutParams = lp
                return tv
            }

            fun badgeColor(variant: String?) = when (variant) {
                "success" -> "#28a745"
                "danger"  -> "#f0a0a0"
                else      -> "#6c757d"
            }

            badgeCol.addView(makeBadge(badge.text, badgeColor(badge.variant)))

            if (!badge.new_next_date.isNullOrEmpty()) {
                val badge2Text = "след. ${badge.new_next_date}" +
                    if (badge.new_interval != null) " — ${badge.new_interval}д" else ""
                val tvB2 = makeBadge(badge2Text, badgeColor(badge.new_variant ?: badge.variant))
                val lp2 = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                lp2.topMargin = dpToPx(3)
                tvB2.layoutParams = lp2
                badgeCol.addView(tvB2)
            } else if (!badge.next_date.isNullOrEmpty()) {
                val tvDate = TextView(this)
                tvDate.text = "след. ${badge.next_date}"
                tvDate.textSize = 10f
                tvDate.setTextColor(Color.parseColor("#888888"))
                tvDate.gravity = Gravity.END
                val lpDate = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                lpDate.topMargin = dpToPx(2)
                tvDate.layoutParams = lpDate
                badgeCol.addView(tvDate)
            }
            headerRow.addView(badgeCol)
            headerHasContent = true
        }

        if (headerHasContent) {
            val lp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            lp.bottomMargin = dpToPx(8)
            headerRow.layoutParams = lp
            binding.cardContent.addView(headerRow)
        }

        for (item in card.content) {
            when (item.type) {
                "foreign"       -> addText(item.text, 44f, true, Gravity.CENTER)
                "translation"   -> addText(item.text, 22f, false, Gravity.CENTER)
                "transcription" -> addText(item.text, 22f, false, Gravity.CENTER, "#666666")
                "label"         -> addText(item.text, 13f, false, Gravity.START, "#888888")
                "hint"          -> addText(item.text, 13f, false, Gravity.START, "#888888")
                "notice"        -> addNotice(item.text, item.variant)
            }
        }

        // Sounds
        releasePlayers()
        binding.soundsRow.removeAllViews()
        if (card.sounds.isNotEmpty()) {
            val preparedFlags = BooleanArray(card.sounds.size) { false }
            card.sounds.forEachIndexed { i, soundPath ->
                // Сначала кеш, потом сеть — общее правило на всех, кто заводит
                // MediaPlayer. Кнопки карточки когда-то тянули звук по сети
                // всегда, поэтому офлайн молчали при скачанных файлах.
                val url = AudioCache.sourceFor(soundPath)
                val player = MediaPlayer()
                player.setAudioAttributes(
                    AudioAttributes.Builder()
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .build()
                )
                player.setOnPreparedListener { preparedFlags[i] = true }
                try { player.setDataSource(url) } catch (_: Exception) {}
                player.prepareAsync()
                players.add(player)

                val btn = MaterialButton(this)
                btn.text = if (card.sounds.size > 1) "🔊 ${i + 1}" else "🔊"
                btn.setOnClickListener {
                    if (!preparedFlags[i]) {
                        Toast.makeText(this, "Звук ещё загружается…", Toast.LENGTH_SHORT).show()
                        return@setOnClickListener
                    }
                    stopPlayback()
                    try {
                        player.seekTo(0); player.start(); activePlayer = player
                    } catch (_: Exception) {
                        Toast.makeText(this, "Звук недоступен", Toast.LENGTH_SHORT).show()
                    }
                }
                val lp = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                lp.marginEnd = 8
                btn.layoutParams = lp
                binding.soundsRow.addView(btn)
            }

            // "Play all" button — plays sounds sequentially
            if (card.sounds.size > 1) {
                val allBtn = MaterialButton(this)
                allBtn.text = "▶ Все"
                allBtn.setOnClickListener {
                    stopPlayback()
                    val mine = playbackGen
                    fun playAt(idx: Int) {
                        if (mine != playbackGen || idx >= players.size) return
                        if (!preparedFlags[idx]) {
                            Toast.makeText(this, "Звуки ещё загружаются…", Toast.LENGTH_SHORT).show()
                            return
                        }
                        val p = players[idx]
                        p.setOnCompletionListener {
                            if (activePlayer === it) activePlayer = null
                            if (mine == playbackGen) playbackHandler.postDelayed({ playAt(idx + 1) }, 350)
                        }
                        try { p.seekTo(0); p.start(); activePlayer = p } catch (_: Exception) {}
                    }
                    playAt(0)
                }
                allBtn.layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                binding.soundsRow.addView(allBtn)
            }

            binding.soundsRow.visibility = View.VISIBLE
        } else {
            binding.soundsRow.visibility = View.GONE
        }

        // Action buttons / pick mode options
        binding.buttonRow.removeAllViews()
        val pickOptions = card.pick_options
        // Кнопка запрета комбинации рисуется отдельной строкой ниже, поэтому в
        // общий ряд она попасть не должна — иначе появилась бы дважды.
        val mainButtons = card.buttons.filter { it.id != "ban_pair" }
        // Какой звуковой вариант уже прослушали. Кнопки одинаковые, звук
        // отзвучал и не оставил следа — без отметки после второго-третьего
        // прослушивания уже не вспомнить, что где.
        listenButtons.clear()
        playedSoundOption = null
        playingSoundOption = null
        val soundGroups = mutableListOf<SoundGroup>()
        if (pickOptions != null && !card.show_answer) {
            // Pick mode: show option buttons vertically
            binding.buttonRow.orientation = LinearLayout.VERTICAL
            val targetModality = pickOptions.target_modality
            pickOptions.options.forEachIndexed { i, opt ->
                if (targetModality == "sound") {
                    // Separate "listen" (plays all sound variants) from "select"
                    val row = LinearLayout(this)
                    row.orientation = LinearLayout.HORIZONTAL

                    val listenBtn = MaterialButton(this)
                    listenBtn.text = "🔊 ▶ ${i + 1}"
                    listenBtn.textSize = 15f
                    listenBtn.setPadding(16, 20, 16, 20)
                    listenBtn.setBackgroundColor(ContextCompat.getColor(this, android.R.color.white))
                    listenBtn.setTextColor(ContextCompat.getColor(this, R.color.btnSecondary))
                    listenBtn.strokeColor = ContextCompat.getColorStateList(this, R.color.btnSecondary)
                    listenBtn.strokeWidth = 2
                    val soundPaths = opt.target_text.split("|").filter { it.isNotBlank() }
                    listenButtons.add(listenBtn)
                    soundGroups.add(SoundGroup(i, soundPaths))
                    listenBtn.setOnClickListener {
                        playedSoundOption = i
                        markPlayedOption()
                        playGroups(listOf(SoundGroup(i, soundPaths)))
                    }
                    val listenLp = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                    listenLp.marginEnd = dpToPx(4)
                    listenBtn.layoutParams = listenLp
                    row.addView(listenBtn)

                    val selectBtn = MaterialButton(this)
                    selectBtn.text = "Выбрать ${i + 1}"
                    selectBtn.textSize = 17f
                    selectBtn.setPadding(16, 20, 16, 20)
                    selectBtn.setBackgroundColor(ContextCompat.getColor(this, android.R.color.white))
                    selectBtn.setTextColor(ContextCompat.getColor(this, R.color.btnPrimary))
                    selectBtn.strokeColor = ContextCompat.getColorStateList(this, R.color.btnPrimary)
                    selectBtn.strokeWidth = 2
                    selectBtn.setOnClickListener { onPickAnswer(opt.word_id) }
                    val selectLp = LinearLayout.LayoutParams(
                        0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
                    selectBtn.layoutParams = selectLp
                    row.addView(selectBtn)

                    val rowLp = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                    rowLp.bottomMargin = dpToPx(4)
                    row.layoutParams = rowLp
                    binding.buttonRow.addView(row)
                } else {
                    val b = MaterialButton(this)
                    b.text = opt.target_text
                    b.textSize = 17f
                    b.isSingleLine = false
                    b.maxLines = 4
                    b.setPadding(16, 20, 16, 20)
                    b.setBackgroundColor(ContextCompat.getColor(this, android.R.color.white))
                    b.setTextColor(ContextCompat.getColor(this, R.color.btnPrimary))
                    b.strokeColor = ContextCompat.getColorStateList(this, R.color.btnPrimary)
                    b.strokeWidth = 2
                    b.setOnClickListener { onPickAnswer(opt.word_id) }
                    val lp = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                    lp.bottomMargin = dpToPx(4)
                    b.layoutParams = lp
                    binding.buttonRow.addView(b)
                }
            }
            // «▶ Все» — проиграть варианты подряд, по порядку.
            //
            // Кнопок прослушивания столько же, сколько вариантов, и чтобы
            // сравнить их между собой, приходилось жать каждую по очереди,
            // удерживая предыдущую в памяти на слух. Одна кнопка проигрывает
            // все, подсвечивая тот, что звучит сейчас.
            val playAll = if (soundGroups.size > 1) {
                MaterialButton(this).apply {
                    text = "▶ Все"
                    textSize = 15f
                    setPadding(16, 20, 16, 20)
                    setBackgroundColor(ContextCompat.getColor(
                        this@StudyActivity, android.R.color.white))
                    setTextColor(ContextCompat.getColor(this@StudyActivity, R.color.btnSecondary))
                    strokeColor = ContextCompat.getColorStateList(
                        this@StudyActivity, R.color.btnSecondary)
                    strokeWidth = 2
                    setOnClickListener {
                        // Снимаем отметку «прослушан»: она отвечает на вопрос
                        // «что я слушал отдельно», а после проигрывания всех
                        // подряд ответа нет — слушали всё. Иначе на экране
                        // горят две подсветки сразу: бегущая «звучит сейчас» и
                        // застрявшая от прошлого одиночного нажатия, и какая
                        // из них про что — не понять.
                        playedSoundOption = null
                        markPlayedOption()
                        playGroups(soundGroups)
                    }
                }
            } else null

            // Кнопки под вариантами приходят из card.buttons. Раньше «Не знаю»
            // была зашита прямо здесь, а весь card.buttons в пик-режиме не
            // читался — вместе с ним пропадала «Пропускать», и настройка
            // show_skip_button тут молча не работала.
            val cardButtons = card.buttons.map { makeCardButton(it) }
            if (playAll != null && cardButtons.isNotEmpty()) {
                // «Все» встаёт в один ряд с «Не знаю»: обе про вопрос целиком,
                // а не про отдельный вариант, — и ряд вариантов на них
                // заканчивается, вместо того чтобы продолжаться ещё одной
                // кнопкой, похожей на вариант.
                val row = LinearLayout(this)
                row.orientation = LinearLayout.HORIZONTAL
                playAll.layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                ).apply { marginEnd = dpToPx(4) }
                row.addView(playAll)
                cardButtons.first().layoutParams = LinearLayout.LayoutParams(
                    0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
                row.addView(cardButtons.first())
                row.layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                ).apply { bottomMargin = dpToPx(4) }
                binding.buttonRow.addView(row)
                cardButtons.drop(1).forEach { binding.buttonRow.addView(it) }
            } else {
                playAll?.let { binding.buttonRow.addView(it) }
                cardButtons.forEach { binding.buttonRow.addView(it) }
            }
        } else if (mainButtons.size >= 3) {
            binding.buttonRow.orientation = LinearLayout.VERTICAL
            val row1 = buildButtonRow(mainButtons.take(2))
            val row2 = buildButtonRow(mainButtons.drop(2))
            val row2lp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            row2lp.topMargin = dpToPx(4)
            row2.layoutParams = row2lp
            binding.buttonRow.addView(row1)
            binding.buttonRow.addView(row2)
        } else {
            binding.buttonRow.orientation = LinearLayout.HORIZONTAL
            val weight = 1f / mainButtons.size.coerceAtLeast(1)
            for (btn in mainButtons) {
                val b = makeCardButton(btn)
                val lp = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, weight)
                lp.marginStart = 4; lp.marginEnd = 4
                b.layoutParams = lp
                binding.buttonRow.addView(b)
            }
        }

        // Hint management button
        val wordId = meta.word_id
        val hintsEnabled = meta.hint_enabled_types.isNotEmpty()
        if (card.show_answer && wordId.isNotBlank() && hintsEnabled) {
            binding.btnHints.visibility = View.VISIBLE
            binding.btnHints.setOnClickListener {
                startActivity(Intent(this, HintsActivity::class.java).apply {
                    putExtra("user_id", userId)
                    putExtra("word_id", wordId)
                    putExtra("language_id", languageId)
                    putStringArrayListExtra("enabled_types",
                        ArrayList(meta.hint_enabled_types))
                })
            }
        } else {
            binding.btnHints.visibility = View.GONE
        }

        // Запрет комбинации — отдельной строкой под основными кнопками: она
        // шире и другого цвета, это осознанная вёрстка. Но КОГДА её показывать,
        // решает card_builder, а не экран: кнопка приходит в buttons[] с
        // id="ban_pair", и правило лежит в одном месте на все три клиента.
        val banBtn0 = card.buttons.firstOrNull { it.id == "ban_pair" }
        val lastWrongId = banBtn0?.bad_word_id
        binding.banButtonRow.removeAllViews()
        if (!lastWrongId.isNullOrEmpty()) {
            val banBtn = MaterialButton(this)
            banBtn.text = banBtn0?.text ?: "🚫 Не показывать такую комбинацию"
            banBtn.textSize = 13f
            banBtn.setPadding(16, 14, 16, 14)
            banBtn.setBackgroundColor(ContextCompat.getColor(this, android.R.color.transparent))
            banBtn.setTextColor(Color.parseColor("#e6a817"))
            banBtn.strokeColor = android.content.res.ColorStateList.valueOf(Color.parseColor("#e6a817"))
            banBtn.strokeWidth = 2
            banBtn.setOnClickListener { onAddForbiddenPair(lastWrongId) }
            banBtn.layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            binding.banButtonRow.addView(banBtn)
            binding.banButtonRow.visibility = View.VISIBLE
        } else {
            binding.banButtonRow.visibility = View.GONE
        }

        // Pick mode result banner
        val pickResult = lastPickAnswerResult
        if (card.show_answer && pickResult != null) {
            // «Не знал» — не ошибка, и цвет у него не красный: человек не
            // промахнулся, а сказал правду о себе. Красным остаётся только
            // промах — выбранный и неверный вариант.
            binding.tvPickResult.text = when (pickResult) {
                PickOutcome.CORRECT -> "✓  Правильно!"
                PickOutcome.WRONG -> "✗  Неверно"
                PickOutcome.DONT_KNOW -> "？  Не знал"
            }
            val bgColor = when (pickResult) {
                PickOutcome.CORRECT -> Color.parseColor("#E8F5E9")
                PickOutcome.WRONG -> Color.parseColor("#FFEBEE")
                PickOutcome.DONT_KNOW -> Color.parseColor("#FFF3CD")
            }
            val textColor = when (pickResult) {
                PickOutcome.CORRECT -> Color.parseColor("#2E7D32")
                PickOutcome.WRONG -> Color.parseColor("#C62828")
                PickOutcome.DONT_KNOW -> Color.parseColor("#856404")
            }
            binding.tvPickResult.setBackgroundColor(bgColor)
            binding.tvPickResult.setTextColor(textColor)
            binding.tvPickResult.visibility = View.VISIBLE
        } else {
            binding.tvPickResult.visibility = View.GONE
            if (!card.show_answer) lastPickAnswerResult = null
        }

        // Segmented progress bars (like web: two thin rows of segments per word)
        if (barTotal != null) {
            binding.progressArea.visibility = View.VISIBLE
            binding.progressArea.removeAllViews()

            binding.progressArea.addView(buildSegmentBar(
                meta.result_history, "know", "#28a745", "#e9ecef", "#adb5bd",
                barTotal, meta.pending_result, "know", roundTop = true
            ))
            val gap = View(this)
            gap.layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dpToPx(2))
            binding.progressArea.addView(gap)
            binding.progressArea.addView(buildSegmentBar(
                meta.result_history, "dont_know", "#dc3545", "#e9ecef", "#adb5bd",
                barTotal, meta.pending_result, "dont_know", roundTop = false
            ))

            // Counts row
            val countsRow = LinearLayout(this)
            countsRow.orientation = LinearLayout.HORIZONTAL
            val countsLp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT)
            countsLp.topMargin = dpToPx(4)
            countsRow.layoutParams = countsLp

            val leftCol = LinearLayout(this)
            leftCol.orientation = LinearLayout.VERTICAL
            leftCol.layoutParams = LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f)

            val tvCorrect = TextView(this)
            tvCorrect.text = correct(meta.correct_count)
            tvCorrect.textSize = 12f
            tvCorrect.setTextColor(Color.parseColor("#28a745"))
            leftCol.addView(tvCorrect)

            val tvIncorrect = TextView(this)
            tvIncorrect.text = mistakes(meta.incorrect_count)
            tvIncorrect.textSize = 12f
            tvIncorrect.setTextColor(Color.parseColor("#dc3545"))
            leftCol.addView(tvIncorrect)

            countsRow.addView(leftCol)

            val tvDone = TextView(this)
            val done = meta.correct_count + meta.incorrect_count
            tvDone.text = "готово $done из $barTotal"
            tvDone.textSize = 12f
            tvDone.setTextColor(Color.parseColor("#666666"))
            tvDone.gravity = Gravity.END or Gravity.BOTTOM
            countsRow.addView(tvDone)

            binding.progressArea.addView(countsRow)
        } else {
            binding.progressArea.visibility = View.GONE
        }

        // bigWordArea is no longer standalone — big_word is shown in extraCardsArea
        binding.bigWordArea.visibility = View.GONE

        // Extra content — web order: radicals → references → tones; one card per group
        // big_word gets its own card at the top
        binding.extraCardsArea.removeAllViews()
        val extraOrdered = run {
            // Группы тегов идут последними: это самый длинный блок (числительные
            // — 21 строка), и выше он отодвигал бы огласовки с однокоренными за
            // нижний край экрана.
            val groupOrder = listOf("radicals", "references", "tones", "tags")
            val byGroup = card.extra_content.groupBy { it.group ?: "" }
            val sorted = groupOrder.flatMap { byGroup[it] ?: emptyList() }
            val rest = card.extra_content.filter { (it.group ?: "") !in groupOrder }
            sorted + rest
        }
        val bw = card.big_word
        val hasBigWord = bw != null && bw.word.isNotEmpty()

        if (hasBigWord) {
            val cardView = MaterialCardView(this)
            cardView.layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = dpToPx(8) }
            val inner = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dpToPx(16), dpToPx(16), dpToPx(16), dpToPx(16))
            }
            val tvBig = TextView(this)
            tvBig.text = bw!!.word
            tvBig.textSize = 96f
            tvBig.setTypeface(null, android.graphics.Typeface.BOLD)
            tvBig.gravity = Gravity.CENTER
            inner.addView(tvBig)
            if (bw.transcription.isNotEmpty()) {
                val tvTr = TextView(this)
                tvTr.text = "[${bw.transcription}]"
                tvTr.textSize = 24f
                tvTr.setTextColor(Color.parseColor("#666666"))
                tvTr.gravity = Gravity.CENTER
                inner.addView(tvTr)
            }
            cardView.addView(inner)
            makeZoomable(cardView)
            binding.extraCardsArea.addView(cardView)
        }

        val grouped = linkedMapOf<String, MutableList<com.langbot.app.network.ExtraContentItem>>()
        for (item in extraOrdered) {
            val g = item.group ?: ""
            grouped.getOrPut(g) { mutableListOf() }.add(item)
        }
        for ((_, items) in grouped) {
            val cardView = MaterialCardView(this)
            cardView.layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = dpToPx(8) }
            val inner = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dpToPx(16), dpToPx(16), dpToPx(16), dpToPx(16))
            }
            for (item in items) {
                when (item.type) {
                    "label" -> {
                        val tv = TextView(this)
                        tv.text = item.text
                        tv.textSize = 12f
                        tv.setTextColor(Color.parseColor("#888888"))
                        inner.addView(tv)
                    }
                    "tag_group" -> {
                        // Четыре колонки: номер в частотном словаре, перевод,
                        // транскрипция, само слово. Строка текущего слова
                        // подсвечена — иначе в списке из двадцати одного
                        // числительного своё не найти.
                        addTagTable(inner, item.rows ?: emptyList())
                    }
                    "extra" -> {
                        val rows = item.rows
                        if (item.group != "radicals" && !rows.isNullOrEmpty()) {
                            // Таблица. Задать направление абзацу мало: иврит и
                            // русский идут одной строкой, и колонки не
                            // выстраиваются, а весь блок уезжает вправо по
                            // первому сильному символу. С колонками выравнивание
                            // становится свойством вёрстки, а не догадкой.
                            addExtraTable(inner, item.header_foreign, item.header_ru, item.header, rows)
                        } else {
                            // Радикалы (моноширинный столбик) и старые
                            // офлайн-партии, где разобранных строк ещё нет.
                            val tv = TextView(this)
                            if (item.group == "radicals") {
                                tv.text = item.text
                                tv.typeface = android.graphics.Typeface.MONOSPACE
                            } else {
                                val htmlText = item.text.replace("\n", "<br>")
                                tv.text = android.text.Html.fromHtml(
                                    htmlText, android.text.Html.FROM_HTML_MODE_COMPACT)
                            }
                            tv.textSize = 15f
                            tv.textDirection = View.TEXT_DIRECTION_LTR
                            tv.textAlignment = View.TEXT_ALIGNMENT_VIEW_START
                            val lp = LinearLayout.LayoutParams(
                                LinearLayout.LayoutParams.MATCH_PARENT,
                                LinearLayout.LayoutParams.WRAP_CONTENT)
                            lp.topMargin = dpToPx(4)
                            tv.layoutParams = lp
                            inner.addView(tv)
                        }
                    }
                }
            }
            cardView.addView(inner)
            makeZoomable(cardView)
            binding.extraCardsArea.addView(cardView)
        }

        binding.extraCardsArea.visibility =
            if (binding.extraCardsArea.childCount > 0) View.VISIBLE else View.GONE
    }

    // ── Button click handler ────────────────────────────────────────────────────

    private fun onButtonClick(btn: CardButton) {
        // «Не знаю» в пик-режиме — это pick_answer с dont_know, а не show_answer:
        // ответ засчитывается как незнание, и показывается баннер результата.
        // Путь тот же, что у выбора варианта, включая офлайн-ветку.
        if (btn.id == "pick_dont_know") { onPickAnswer("dont_know"); return }
        if (offline != null) { handleOfflineAction(btn); return }
        val sid = sessionId ?: return
        val btnId = btn.id
        val rating = btn.rating
        lastPickAnswerResult = null
        setLoading(true)
        lifecycleScope.launch {
            try {
                // Быстрый провал с эскалацией: первая попытка короткая, дальше
                // таймаут растёт. Пока идут попытки — пользователь видит статус,
                // а не замерший экран.
                // Незнакомая кнопка — сети не касаемся вовсе.
                if (btnId !in setOf("know", "show_answer", "rate", "reconsider", "toggle_skip")) {
                    return@launch
                }
                val resp = NetworkRetry.call(onStatus = { showConnectionStatus(it) },
                                              attempts = ANSWER_ATTEMPTS) { api ->
                    when (btnId) {
                        "know"        -> api.knowWord(sid)
                        "show_answer" -> api.showAnswer(sid)
                        "rate"        -> api.rateWord(sid, RateRequest(rating ?: "dont_know"))
                        "reconsider"  -> api.reconsider(sid)
                        else          -> api.toggleSkip(sid)
                    }
                }
                clearConnectionStatus()

                if (resp == null) {
                    // Сервер недостижим — работаем из кеша, действие применяем локально.
                    // На ветке SAME_WORD рисует handleOfflineAction, поэтому сюда
                    // промежуточный кадр не нужен; на остальных рисовать некому.
                    when (enterOfflineFromStore(render = false)) {
                        OfflineEntry.SAME_WORD  -> handleOfflineAction(btn)
                        OfflineEntry.OTHER_WORD -> {
                            renderOfflineCurrent(showAnswer = false)
                            warnOfflineWordMissing()
                        }
                        OfflineEntry.NO_BUNDLE  ->
                            showError("Нет сети и нет сохранённой сессии для офлайн-работы")
                    }
                    return@launch
                }

                val body = resp.body() ?: return@launch
                if (body.batch_exhausted) {
                    val batchSid = body.session_id ?: sid
                    val batch = BLSClient.api.nextBatch(batchSid)
                    val batchBody = batch.body()
                    if (batchBody?.loaded == true || batchBody?.card != null) {
                        handleResponse(batchBody)
                        return@launch
                    }
                    if (!batch.isSuccessful) {
                        // Сессии на сервере нет — BLS держит их в памяти, и любой
                        // его перезапуск их стирает. Это не «на сегодня всё»:
                        // начинаем сессию заново, сервер наберёт слова сам.
                        loadSession()
                        return@launch
                    }
                    // Слов больше нет на самом деле — сервер ответил успешно и пусто.
                    handleResponse(batchBody ?: body)
                    return@launch
                }
                handleResponse(body)
                flushOutboxInBackground()
            } catch (e: Exception) {
                // Network dropped — switch to the cached bundle and apply this action locally.
                when (enterOfflineFromStore(render = false)) {
                    OfflineEntry.SAME_WORD  -> handleOfflineAction(btn)
                    OfflineEntry.OTHER_WORD -> {
                        renderOfflineCurrent(showAnswer = false)
                        warnOfflineWordMissing()
                    }
                    OfflineEntry.NO_BUNDLE  -> Toast.makeText(
                        this@StudyActivity,
                        "[${e.javaClass.simpleName}] ${e.message}", Toast.LENGTH_SHORT).show()
                }
            } finally {
                setLoading(false)
            }
        }
    }

    /**
     * Оборвать текущее воспроизведение.
     *
     * Плееры карточки переиспользуются между нажатиями, поэтому им pause+seek:
     * stop() перевёл бы их в состояние Stopped и потребовал повторной подготовки.
     * Одноразовые плееры цепочки, наоборот, освобождаем — они могут быть ещё в
     * состоянии Preparing, где pause() бросает, а release() безопасен всегда.
     */
    private fun stopPlayback() {
        playbackGen++
        playbackHandler.removeCallbacksAndMessages(null)
        markPlayingOption(null)
        val p = activePlayer ?: return
        activePlayer = null
        if (players.contains(p)) {
            try { if (p.isPlaying) p.pause(); p.seekTo(0) } catch (_: Exception) {}
        } else {
            try { p.release() } catch (_: Exception) {}
        }
    }

    /** Чьи это звуки и какие файлы: номер варианта пик-режима или null. */
    private data class SoundGroup(val option: Int?, val paths: List<String>)

    /** Play a list of sound paths sequentially, with a short pause between them. */
    private fun playSoundSequence(paths: List<String>) =
        playGroups(listOf(SoundGroup(null, paths)))

    /**
     * Проиграть подряд несколько вариантов, подсвечивая звучащий.
     *
     * Кнопки прослушивания в пик-режиме неразличимы на вид — «▶ 1», «▶ 2»,
     * «▶ 3», — и при воспроизведении всех подряд было не понять, который
     * сейчас звучит. Поэтому проигрыватель тут один на все группы: он знает,
     * чей файл ставит, и держит подсветку на нужной кнопке.
     */
    private fun playGroups(groups: List<SoundGroup>) {
        val flat = groups.flatMap { g -> g.paths.map { g.option to it } }
        if (flat.isEmpty()) return
        stopPlayback()
        val mine = playbackGen
        var idx = 0
        fun playNext() {
            if (mine != playbackGen) return
            if (idx >= flat.size) { markPlayingOption(null); return }
            val (option, path) = flat[idx]; idx++
            markPlayingOption(option)
            val gap = gapBefore(next = flat.getOrNull(idx)?.first, after = option)
            // Prefer the offline-cached file; fall back to streaming from BLS.
            val source = AudioCache.sourceFor(path)
            val mp = MediaPlayer()
            fun done(released: MediaPlayer) {
                if (activePlayer === released) activePlayer = null
                if (mine == playbackGen) playbackHandler.postDelayed({ playNext() }, gap)
            }
            try {
                mp.setDataSource(source)
                // Подготовка асинхронная: пока она идёт, нас могли уже прервать.
                mp.setOnPreparedListener {
                    if (mine != playbackGen) { it.release() } else { it.start() }
                }
                mp.setOnCompletionListener { it.release(); done(it) }
                mp.setOnErrorListener { p, _, _ -> p.release(); done(p); true }
                activePlayer = mp
                mp.prepareAsync()
            } catch (_: Exception) {
                mp.release()
                if (activePlayer === mp) activePlayer = null
                playNext()
            }
        }
        playNext()
    }

    private fun onPickAnswer(selectedWordId: String) {
        if (offline != null) { handleOfflinePick(selectedWordId); return }
        val sid = sessionId ?: return
        setLoading(true)
        lifecycleScope.launch {
            try {
                // Как и в onButtonClick: короткая первая попытка с эскалацией.
                // Общий BLSClient.api — самый терпеливый клиент, и ждать на нём
                // 15 с, чтобы потом всё равно уйти в офлайн, пользователю незачем.
                val resp = NetworkRetry.call(onStatus = { showConnectionStatus(it) },
                                              attempts = ANSWER_ATTEMPTS) { api ->
                    api.pickAnswer(sid, mapOf("selected_word_id" to selectedWordId))
                }
                clearConnectionStatus()
                if (resp == null) {
                    when (enterOfflineFromStore()) {
                        OfflineEntry.SAME_WORD  -> handleOfflinePick(selectedWordId)
                        OfflineEntry.OTHER_WORD -> warnOfflineWordMissing()
                        OfflineEntry.NO_BUNDLE  ->
                            showError("Нет сети и нет сохранённой сессии для офлайн-работы")
                    }
                    return@launch
                }
                val body = resp.body() ?: return@launch
                if (body.batch_exhausted) {
                    lastPickAnswerResult = null
                    val batchSid = body.session_id ?: sid
                    val batch = BLSClient.api.nextBatch(batchSid)
                    val batchBody = batch.body()
                    if (batchBody?.loaded == true || batchBody?.card != null) {
                        handleResponse(batchBody); return@launch
                    }
                    // Сессии нет (перезапуск BLS) — не «всё», а новая сессия.
                    if (!batch.isSuccessful) { loadSession(); return@launch }
                    handleResponse(batchBody ?: body); return@launch
                }
                lastPickAnswerResult = when {
                    selectedWordId == "dont_know" -> PickOutcome.DONT_KNOW
                    body.card?.last_wrong_distractor_id != null -> PickOutcome.WRONG
                    else -> PickOutcome.CORRECT
                }
                handleResponse(body)
                flushOutboxInBackground()
            } catch (e: Exception) {
                when (enterOfflineFromStore()) {
                    OfflineEntry.SAME_WORD  -> handleOfflinePick(selectedWordId)
                    OfflineEntry.OTHER_WORD -> warnOfflineWordMissing()
                    OfflineEntry.NO_BUNDLE  -> Toast.makeText(
                        this@StudyActivity,
                        "[${e.javaClass.simpleName}] ${e.message}", Toast.LENGTH_SHORT).show()
                }
            } finally {
                setLoading(false)
            }
        }
    }

    private fun onAddForbiddenPair(badWordId: String) {
        if (offline != null) {
            Toast.makeText(this, "Недоступно офлайн", Toast.LENGTH_SHORT).show()
            return
        }
        val sid = sessionId ?: return
        setLoading(true)
        lifecycleScope.launch {
            try {
                // Кнопка в цикле учёбы: ждать на терпеливом клиенте нечего,
                // нужен быстрый провал с эскалацией, как у остальных нажатий.
                val resp = NetworkRetry.call(onStatus = { showConnectionStatus(it) },
                                              attempts = ANSWER_ATTEMPTS) { api ->
                    api.addForbiddenPair(sid, mapOf("bad_word_id" to badWordId))
                }
                clearConnectionStatus()
                if (resp == null) {
                    Toast.makeText(this@StudyActivity, "Нет связи с сервером — не сохранено",
                        Toast.LENGTH_SHORT).show()
                    return@launch
                }
                val body = resp.body() ?: return@launch
                handleResponse(body)
            } catch (e: Exception) {
                Toast.makeText(this@StudyActivity, "[${e.javaClass.simpleName}] ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                setLoading(false)
            }
        }
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    private fun makeCardButton(btn: CardButton): MaterialButton {
        val b = MaterialButton(this)
        b.text = btn.text
        b.textSize = 13f
        b.setPadding(8, 18, 8, 18)
        when (btn.style) {
            "success" -> b.setBackgroundColor(ContextCompat.getColor(this, R.color.btnSuccess))
            "outline-danger" -> {
                b.setBackgroundColor(ContextCompat.getColor(this, android.R.color.transparent))
                b.setTextColor(ContextCompat.getColor(this, R.color.btnDanger))
                b.strokeColor = ContextCompat.getColorStateList(this, R.color.btnDanger)
                b.strokeWidth = 2
            }
            "outline-secondary" -> {
                b.setBackgroundColor(ContextCompat.getColor(this, android.R.color.transparent))
                b.setTextColor(ContextCompat.getColor(this, R.color.btnSecondary))
                b.strokeColor = ContextCompat.getColorStateList(this, R.color.btnSecondary)
                b.strokeWidth = 2
            }
        }
        b.setOnClickListener { onButtonClick(btn) }
        return b
    }

    private fun buildButtonRow(buttons: List<CardButton>): LinearLayout {
        val row = LinearLayout(this)
        row.orientation = LinearLayout.HORIZONTAL
        row.gravity = Gravity.CENTER_VERTICAL
        row.layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        val weight = 1f / buttons.size
        for (btn in buttons) {
            val b = makeCardButton(btn)
            val lp = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, weight)
            lp.marginStart = 4; lp.marginEnd = 4
            b.layoutParams = lp
            row.addView(b)
        }
        return row
    }

    /**
     * Экран «слова кончились» — отдельное состояние, а не карточка с вынутым
     * содержимым. Прежде здесь пряталось лишь то, что вспомнили, и на экране
     * оставались хвосты прошлой карточки: плашка «✓ Правильно!» последнего
     * ответа в режиме выбора и голый разделитель над пустотой. Прятать надо
     * всё, что renderCard показывает для конкретного слова, — он же всё это
     * и вернёт, когда придёт следующая карточка.
     */
    @VisibleForTesting
    internal fun showAllDone(offline: Boolean = false) {
        binding.tvBadge.visibility = View.GONE
        binding.restartNotice.visibility = View.GONE
        binding.progressArea.visibility = View.GONE
        binding.bigWordArea.visibility = View.GONE
        binding.soundsRow.visibility = View.GONE
        binding.btnHints.visibility = View.GONE
        binding.extraCardsArea.visibility = View.GONE
        binding.tvPickResult.visibility = View.GONE
        binding.banButtonRow.visibility = View.GONE
        binding.divider.visibility = View.GONE
        binding.buttonRow.removeAllViews()
        binding.banButtonRow.removeAllViews()
        binding.cardContent.removeAllViews()
        lastPickAnswerResult = null
        if (offline) {
            // Без сети «на сегодня всё» знать нельзя: кончилась лишь скачанная
            // партия. Прежде здесь крупно писалось «всё повторено», а строкой
            // ниже — «подключитесь, чтобы продолжить»: одно опровергало другое.
            addText("📴", 48f, false, Gravity.CENTER)
            addText("Офлайн-партия пройдена", 20f, true, Gravity.CENTER)
            addText("Подключитесь к сети — появятся следующие слова, а результаты отправятся.",
                14f, false, Gravity.CENTER, "#888888")
        } else {
            addText("✅", 48f, false, Gravity.CENTER)
            addText("На сегодня всё повторено!", 20f, true, Gravity.CENTER)
            addText("Следующие слова появятся по расписанию.", 14f, false, Gravity.CENTER, "#888888")
        }
    }

    private fun showError(msg: String) {
        binding.cardContent.removeAllViews()
        addText(msg, 14f, false, Gravity.CENTER, "#D32F2F")
    }

    private fun addText(text: String, sizeSp: Float, bold: Boolean, gravity: Int,
                        colorHex: String? = null) {
        val tv = TextView(this)
        tv.text = text
        tv.textSize = sizeSp
        if (bold) tv.setTypeface(null, android.graphics.Typeface.BOLD)
        tv.gravity = gravity
        colorHex?.let { tv.setTextColor(android.graphics.Color.parseColor(it)) }
        val lp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT,
        )
        lp.bottomMargin = 8
        tv.layoutParams = lp
        binding.cardContent.addView(tv)
    }

    private fun addNotice(text: String, variant: String?) {
        val tv = TextView(this)
        tv.text = text
        tv.textSize = 13f
        tv.setPadding(16, 10, 16, 10)
        val bgColor = when (variant) {
            "success" -> "#d4edda"
            "danger"  -> "#f8d7da"
            "info"    -> "#d1ecf1"
            else      -> "#e2e3e5"
        }
        val bg = android.graphics.drawable.GradientDrawable()
        bg.cornerRadius = 8f
        bg.setColor(android.graphics.Color.parseColor(bgColor))
        tv.background = bg
        val lp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT,
        )
        lp.bottomMargin = 8
        tv.layoutParams = lp
        binding.cardContent.addView(tv)
    }

    private fun buildSegmentBar(
        history: List<String>, matchValue: String,
        activeColor: String, inactiveColor: String, bgColor: String,
        total: Int, pendingResult: String?, pendingMatchValue: String,
        roundTop: Boolean,
    ): LinearLayout {
        val bar = LinearLayout(this)
        bar.orientation = LinearLayout.HORIZONTAL
        val bg = GradientDrawable()
        val r = dpToPx(3).toFloat()
        bg.cornerRadii = if (roundTop)
            floatArrayOf(r, r, r, r, 0f, 0f, 0f, 0f)
        else
            floatArrayOf(0f, 0f, 0f, 0f, r, r, r, r)
        bg.setColor(Color.parseColor(bgColor))
        bar.background = bg
        bar.layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dpToPx(6))
        bar.clipToOutline = true

        val addSeg = { colorHex: String ->
            val seg = View(this)
            seg.setBackgroundColor(Color.parseColor(colorHex))
            seg.layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1f)
            bar.addView(seg)
        }

        for (result in history) addSeg(if (result == matchValue) activeColor else inactiveColor)

        if (pendingResult != null)
            addSeg(if (pendingResult == pendingMatchValue) activeColor else inactiveColor)

        val filled = history.size + (if (pendingResult != null) 1 else 0)
        repeat(total - filled) {
            val seg = View(this)
            seg.setBackgroundColor(Color.TRANSPARENT)
            seg.layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1f)
            bar.addView(seg)
        }
        return bar
    }

    /**
     * Блок огласовок/однокоренных таблицей: иврит в своей колонке, русский в своей.
     *
     * Так выравнивание задаёт вёрстка, а не двунаправленный алгоритм. Раньше это
     * был один TextView со всеми строками, и каждая строка получала направление
     * по первому сильному символу — ивритской букве, — из-за чего весь блок
     * уезжал вправо вместе с русским хвостом. Направление, выставленное на View,
     * этого не исправляло: иврит и русский всё равно шли одной строкой.
     */
    /**
     * Блок огласовок/однокоренных таблицей: иврит в своей колонке, русский в своей.
     *
     * Так выравнивание задаёт вёрстка, а не двунаправленный алгоритм. Раньше это
     * был один TextView со всеми строками, и каждая строка получала направление
     * по первому сильному символу — ивритской букве, — из-за чего весь блок
     * уезжал вправо вместе с русским хвостом. Направление, выставленное на View,
     * этого не исправляло: иврит и русский всё равно шли одной строкой.
     */
    private fun addExtraTable(
        parent: LinearLayout,
        headerForeign: String?,
        headerRu: String?,
        header: String?,
        rows: List<com.langbot.app.network.ExtraRow>,
    ) {
        val table = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutDirection = View.LAYOUT_DIRECTION_LTR
            background = GradientDrawable().apply {
                setStroke(dpToPx(1), Color.parseColor("#d0d0d0"))
                setColor(Color.TRANSPARENT)
            }
        }
        // Заголовок — такая же строка таблицы: он тоже двуязычный и отдельной
        // строкой уезжал вправо по первой ивритской букве.
        if (!headerForeign.isNullOrBlank() || !headerRu.isNullOrBlank()) {
            table.addView(extraTableRow(headerForeign ?: "", headerRu ?: "", "", null,
                                        headerCell = true))
        } else if (!header.isNullOrBlank()) {
            table.addView(extraTableRow(header, "", "", null, headerCell = true))
        }
        for (row in rows) {
            table.addView(extraTableRow(row.foreign, row.ru, row.ipa, row.rank,
                headerCell = false, studied = row.studied))
        }
        val lp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        lp.topMargin = dpToPx(4)
        table.layoutParams = lp
        parent.addView(table)
    }

    /** Одна строка таблицы: две ячейки с границами, у каждой своё направление. */
    /** Таблица группы тега: № | перевод | транскрипция | слово. */
    /** Кнопки прослушивания звуковых вариантов, прослушанный и звучащий. */
    private val listenButtons = mutableListOf<MaterialButton>()
    private var playedSoundOption: Int? = null
    private var playingSoundOption: Int? = null

    /**
     * Отметить прослушанный вариант.
     *
     * Кнопки в пик-режиме по звуку неразличимы — «▶ 1», «▶ 2», «▶ 3», — а звук
     * отзвучал и следа не оставил. После второго-третьего прослушивания уже не
     * вспомнить, что именно только что играло. Залитый фон держит ответ на
     * экране, пока варианты не сменятся.
     */
    private fun markPlayedOption() = paintListenButtons()

    /**
     * Отметить вариант, который звучит ПРЯМО СЕЙЧАС.
     *
     * Это другая отметка, чем «прослушан»: та остаётся надолго и отвечает на
     * вопрос «что я уже слушал», а эта живёт ровно столько, сколько играет
     * звук. Без неё кнопка «▶ Все» проигрывала варианты подряд, и уследить, на
     * каком из них ты сейчас, было нельзя.
     */
    private fun markPlayingOption(option: Int?) {
        if (playingSoundOption == option) return
        playingSoundOption = option
        paintListenButtons()
    }

    /** Вид кнопок прослушивания: звучит сейчас / уже слушали / ещё нет. */
    private fun paintListenButtons() {
        listenButtons.forEachIndexed { i, btn ->
            val playing = i == playingSoundOption
            val played = i == playedSoundOption
            val bg = when {
                playing -> R.color.btnPrimary
                played -> R.color.btnSecondary
                else -> android.R.color.white
            }
            btn.setBackgroundColor(ContextCompat.getColor(this, bg))
            btn.setTextColor(ContextCompat.getColor(
                this, if (playing || played) android.R.color.white else R.color.btnSecondary))
            btn.text = when {
                playing -> "🔈 ${i + 1}"
                played -> "🔊 ${i + 1}"
                else -> "🔊 ▶ ${i + 1}"
            }
        }
    }

    private fun addTagTable(parent: LinearLayout, rows: List<com.langbot.app.network.ExtraRow>) {
        val table = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutDirection = View.LAYOUT_DIRECTION_LTR
        }
        val lp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        lp.topMargin = dpToPx(4)
        table.layoutParams = lp
        rows.forEach { table.addView(tagTableRow(it)) }
        parent.addView(table)
    }

    private fun tagTableRow(row: com.langbot.app.network.ExtraRow): LinearLayout {
        val line = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutDirection = View.LAYOUT_DIRECTION_LTR
        }
        // Подсветка своей строки: фон ячеек, а не рамка — рамка спорила бы с
        // сеткой таблицы.
        // Своя строка жёлтым, непройденные серым: видно и где ты сейчас, и
        // докуда дошёл по набору.
        val bg = when {
            row.self -> Color.parseColor("#fff3cd")
            !row.studied -> Color.parseColor("#f2f2f2")
            else -> Color.TRANSPARENT
        }

        fun cell(text: String, weight: Float, rtl: Boolean, big: Boolean, muted: Boolean,
                 single: Boolean = false): TextView {
            val tv = TextView(this)
            tv.text = text
            // Номер не переносится: «1105» разрывалось на «11» и «05». Если места
            // всё же не хватит, текст обрежется многоточием, а это ловит проверка
            // вёрстки в ScreenshotTest — молча испорченным он не останется.
            if (single) {
                tv.maxLines = 1
                tv.ellipsize = android.text.TextUtils.TruncateAt.END
            }
            tv.textSize = if (big) 20f else 14f
            if (muted) tv.setTextColor(Color.parseColor("#777777"))
            // Текст непройденного тоже бледнее — одной заливки мало, если
            // строка стоит между двумя такими же.
            if (!row.studied && !row.self) tv.setTextColor(Color.parseColor("#9a9a9a"))
            if (row.self) tv.setTypeface(null, android.graphics.Typeface.BOLD)
            tv.textDirection = if (rtl) View.TEXT_DIRECTION_RTL else View.TEXT_DIRECTION_LTR
            tv.textAlignment = if (rtl) View.TEXT_ALIGNMENT_VIEW_END else View.TEXT_ALIGNMENT_VIEW_START
            tv.setPadding(dpToPx(6), dpToPx(4), dpToPx(6), dpToPx(4))
            tv.background = GradientDrawable().apply {
                setStroke(dpToPx(1), Color.parseColor("#d0d0d0"))
                setColor(bg)
            }
            tv.layoutParams = LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.MATCH_PARENT, weight)
            return tv
        }

        // Порядок колонок: номер, перевод, слово, транскрипция. Слово стоит
        // перед транскрипцией — читают его, а транскрипция уточняет.
        line.addView(cell(row.rank?.toString() ?: "", 1.5f,
            rtl = false, big = false, muted = true, single = true))
        line.addView(cell(row.ru, 3f, rtl = false, big = false, muted = false))
        line.addView(cell(row.foreign, 3f, rtl = true, big = true, muted = false))
        line.addView(cell(if (row.ipa.isBlank()) "" else "[${row.ipa}]", 2.5f,
            rtl = false, big = false, muted = true))
        return line
    }

    /**
     * Строка таблицы доп. информации — те же четыре колонки, что у группы тега:
     * номер, перевод, слово, транскрипция.
     *
     * Прежде колонок было две, и слово с транскрипцией шли одной ячейкой: две
     * соседние таблицы на одной карточке выглядели по-разному. У огласовок
     * номера нет — колонка пустая, зато ширины совпадают.
     */
    private fun extraTableRow(foreign: String, ru: String, ipa: String, rank: Int?,
                              headerCell: Boolean, studied: Boolean = true): LinearLayout {
        val line = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutDirection = View.LAYOUT_DIRECTION_LTR
        }

        fun cell(html: String, rtl: Boolean, big: Boolean, weight: Float,
                 muted: Boolean = false, single: Boolean = false): TextView {
            val tv = TextView(this)
            tv.text = android.text.Html.fromHtml(html, android.text.Html.FROM_HTML_MODE_COMPACT)
            // Иврит крупнее: огласовка — мелкие знаки под буквами, и в общем
            // кегле её просто не разглядеть, а ради неё блок и заводился.
            tv.textSize = if (big) 22f else 15f
            if (muted) tv.setTextColor(Color.parseColor("#777777"))
            // Номер не переносится: «1105» рвалось на «11» и «05».
            if (single) {
                tv.maxLines = 1
                tv.ellipsize = android.text.TextUtils.TruncateAt.END
            }
            tv.textDirection = if (rtl) View.TEXT_DIRECTION_RTL else View.TEXT_DIRECTION_LTR
            tv.textAlignment = if (rtl) View.TEXT_ALIGNMENT_VIEW_END else View.TEXT_ALIGNMENT_VIEW_START
            if (headerCell) tv.setTextColor(Color.parseColor("#666666"))
            // До этого слова человек ещё не дошёл: строку гасим, но оставляем —
            // у глагола иначе от парадигмы почти ничего не видно.
            if (!studied) tv.setTextColor(Color.parseColor("#9a9a9a"))
            tv.setPadding(dpToPx(6), dpToPx(4), dpToPx(6), dpToPx(4))
            tv.background = GradientDrawable().apply {
                setStroke(dpToPx(1), Color.parseColor("#d0d0d0"))
                setColor(when {
                    headerCell -> Color.parseColor("#f5f5f5")
                    !studied -> Color.parseColor("#f2f2f2")
                    else -> Color.TRANSPARENT
                })
            }
            tv.layoutParams = LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.MATCH_PARENT, weight)
            return tv
        }

        // Ширины те же, что у таблицы тега: номер, перевод, слово, транскрипция.
        line.addView(cell(rank?.toString() ?: "", rtl = false, big = false, weight = 1.5f,
                          muted = true, single = true))
        line.addView(cell(ru, rtl = false, big = false, weight = 3f))
        line.addView(cell(foreign, rtl = true, big = !headerCell, weight = 3f))
        line.addView(cell(if (ipa.isBlank()) "" else "[$ipa]", rtl = false, big = false,
                          weight = 2.5f, muted = true))
        line.layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        return line
    }

    private fun dpToPx(dp: Int): Int =
        (dp * resources.displayMetrics.density + 0.5f).toInt()

    private fun releasePlayers() {
        // Плееры цепочки вариантов не лежат в players, поэтому их обрывает именно
        // это: без него звук предыдущей карточки доигрывал поверх следующей.
        stopPlayback()
        for (p in players) {
            try { if (p.isPlaying) p.stop(); p.release() } catch (_: Exception) {}
        }
        players.clear()
    }

    private fun setLoading(on: Boolean) {
        binding.loadingBar.visibility = if (on) View.VISIBLE else View.GONE
        if (!on) binding.swipeRefresh.isRefreshing = false
    }
}
