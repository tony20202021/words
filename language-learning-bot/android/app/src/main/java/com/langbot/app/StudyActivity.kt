package com.langbot.app

import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import com.google.android.material.card.MaterialCardView
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

    // Last pick-mode answer result: true=correct, false=wrong/dont_know, null=not a pick answer
    private var lastPickAnswerResult: Boolean? = null

    // ── Offline mode ──
    // Non-null while the study loop is running from the local cache (network is down).
    private var offline: OfflineEngine? = null
    // word_id of the currently rendered card — used to position the offline engine.
    private var lastWordId: String? = null
    // Guards against recording the current offline word's result more than once.
    private var offlineCurrentRecorded: Boolean = false

    companion object {
        private const val MENU_REFRESH = 1
        private const val MENU_STATS   = 2
        private const val MENU_RESTART = 3
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

        OfflineCache.init(this)  // defensive — normally done in LangBotApp
        AudioCache.init(this)

        loadSession()
    }

    override fun onDestroy() {
        super.onDestroy()
        releasePlayers()
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add(0, MENU_REFRESH, 0, "↺ Обновить")
        menu.add(0, MENU_STATS,   1, "📊 Статистика")
        menu.add(0, MENU_RESTART, 2, "🔄 Начать заново")
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
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
            AlertDialog.Builder(this)
                .setTitle("Начать заново?")
                .setMessage("Текущая сессия будет сброшена. Слова начнутся с начала.")
                .setPositiveButton("Начать") { _, _ -> restartSession() }
                .setNegativeButton("Отмена", null)
                .show()
            return true
        }
        return super.onOptionsItemSelected(item)
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
            OfflineCache.saveCursor(userId, languageId, 0)
            loadSession()
        }
    }

    // ── Session loading ────────────────────────────────────────────────────────

    private fun loadSession() {
        setLoading(true)
        lifecycleScope.launch {
            try {
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
                // Best-effort background chores once we're online again.
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

    /** Prefetch a fresh offline bundle in the background; never blocks the UI. */
    private fun prefetchBundleInBackground() {
        lifecycleScope.launch {
            runCatching {
                val resp = BLSClient.api.getBundle(userId, languageId)
                val body = resp.body()
                if (resp.isSuccessful && body != null && body.words.isNotEmpty()) {
                    OfflineCache.saveBundle(
                        StoredBundle(userId, languageId, body.words, cursor = 0)
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
     * произошло»: экран замирал на время таймаута. Переиспользуем плашку
     * restart_notice — она уже есть над карточкой.
     */
    private fun showConnectionStatus(status: NetworkRetry.Status) {
        if (status.attempt == 1) return   // первая попытка короткая, не мельтешим
        binding.tvRestartNotice.text = status.message
        binding.tvRestartNotice.visibility = View.VISIBLE
    }

    private fun clearConnectionStatus() {
        binding.tvRestartNotice.visibility = View.GONE
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
            "reveal_question" -> renderOfflineCurrent(showAnswer = false)

            // «Знаю»: записать оценку и ПОКАЗАТЬ ответ, не листая дальше — так же,
            // как онлайн know_word(). Раньше эта кнопка была помечена submit, и
            // офлайн перебрасывал сразу на следующее слово, минуя карточку с
            // переводом и транскрипцией.
            "record_and_reveal" -> {
                val r = btn.offline_rating ?: OfflineSemantics.ratingFor(btn.id, btn.rating)
                recordOffline(r)
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
        lastPickAnswerResult = rating == "know"
        recordOffline(rating)
        // Reveal the answer; the word is already banked, so any follow-up just advances.
        renderOfflineCurrent(showAnswer = true)
    }

    private fun recordOffline(rating: String) {
        val eng = offline ?: return
        if (offlineCurrentRecorded) return
        eng.record(rating)
        offlineCurrentRecorded = true
    }

    private fun advanceOffline() {
        val eng = offline ?: return
        eng.advance()
        offlineCurrentRecorded = false
        if (eng.atEnd()) showOfflineDone() else renderOfflineCurrent(showAnswer = false)
    }

    private fun renderOfflineCurrent(showAnswer: Boolean) {
        val eng = offline ?: return
        val card = if (showAnswer) eng.answerCard() else eng.frontCard()
        if (card == null) { showOfflineDone(); return }
        renderCard(card)
        showOfflineBanner()
    }

    private fun showOfflineBanner() {
        val pending = OfflineCache.pendingCount()
        binding.tvStaleSession.text =
            "📴 Офлайн — результаты сохраняются локально ($pending) и отправятся при подключении"
        binding.tvStaleSession.visibility = View.VISIBLE
    }

    private fun showOfflineDone() {
        offline = null
        flushOutboxInBackground()
        showAllDone()
        binding.tvStaleSession.text =
            "📴 Слова из офлайн-партии пройдены. Подключитесь к сети, чтобы продолжить и отправить результаты."
        binding.tvStaleSession.visibility = View.VISIBLE
    }

    private fun handleResponse(resp: SessionResponse?) {
        if (resp == null) { showError("Нет ответа от сервера"); return }
        sessionId = resp.session_id
        if (resp.session_stale) {
            binding.tvStaleSession.text =
                "⏰ Сессия устарела — вы давно не занимались. Можно продолжить или начать заново."
            binding.tvStaleSession.visibility = View.VISIBLE
        } else {
            binding.tvStaleSession.visibility = View.GONE
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
        val barTotal = meta.session_total?.takeIf { it > 0 }
        binding.tvBadge.visibility = View.GONE  // badge now lives inside cardContent

        // Restart notice above card
        if (!card.restart_notice.isNullOrEmpty()) {
            binding.tvRestartNotice.text = card.restart_notice
            binding.tvRestartNotice.visibility = View.VISIBLE
        } else {
            binding.tvRestartNotice.visibility = View.GONE
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
                    listenBtn.setOnClickListener { playSoundSequence(soundPaths) }
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
            // Кнопки под вариантами приходят из card.buttons. Раньше «Не знаю»
            // была зашита прямо здесь, а весь card.buttons в пик-режиме не
            // читался — вместе с ним пропадала «Пропускать», и настройка
            // show_skip_button тут молча не работала.
            for (btn in card.buttons) {
                binding.buttonRow.addView(makeCardButton(btn))
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
            binding.tvPickResult.text = if (pickResult) "✓  Правильно!" else "✗  Неверно"
            val bgColor = if (pickResult) Color.parseColor("#E8F5E9") else Color.parseColor("#FFEBEE")
            val textColor = if (pickResult) Color.parseColor("#2E7D32") else Color.parseColor("#C62828")
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
            tvCorrect.text = "${meta.correct_count} правильных"
            tvCorrect.textSize = 12f
            tvCorrect.setTextColor(Color.parseColor("#28a745"))
            leftCol.addView(tvCorrect)

            val tvIncorrect = TextView(this)
            tvIncorrect.text = "${meta.incorrect_count} ошибок"
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
            val groupOrder = listOf("radicals", "references", "tones")
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
                    "extra" -> {
                        val rows = item.rows
                        if (item.group != "radicals" && !rows.isNullOrEmpty()) {
                            // Таблица. Задать направление абзацу мало: иврит и
                            // русский идут одной строкой, и колонки не
                            // выстраиваются, а весь блок уезжает вправо по
                            // первому сильному символу. С колонками выравнивание
                            // становится свойством вёрстки, а не догадкой.
                            addExtraTable(inner, item.header, rows)
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
                val resp = NetworkRetry.call(onStatus = { showConnectionStatus(it) }) { api ->
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
                    // no more batches — show "all done"
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
        val p = activePlayer ?: return
        activePlayer = null
        if (players.contains(p)) {
            try { if (p.isPlaying) p.pause(); p.seekTo(0) } catch (_: Exception) {}
        } else {
            try { p.release() } catch (_: Exception) {}
        }
    }

    /** Play a list of sound paths sequentially, with a short pause between them. */
    private fun playSoundSequence(paths: List<String>) {
        if (paths.isEmpty()) return
        stopPlayback()
        val mine = playbackGen
        var idx = 0
        fun playNext() {
            if (mine != playbackGen || idx >= paths.size) return
            val path = paths[idx]; idx++
            // Prefer the offline-cached file; fall back to streaming from BLS.
            val source = AudioCache.sourceFor(path)
            val mp = MediaPlayer()
            fun done(released: MediaPlayer) {
                if (activePlayer === released) activePlayer = null
                if (mine == playbackGen) playbackHandler.postDelayed({ playNext() }, 350)
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
                val resp = NetworkRetry.call(onStatus = { showConnectionStatus(it) }) { api ->
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
                    handleResponse(batchBody ?: body); return@launch
                }
                lastPickAnswerResult = when {
                    selectedWordId == "dont_know" -> false
                    body.card?.last_wrong_distractor_id != null -> false
                    else -> true
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
                val resp = NetworkRetry.call(onStatus = { showConnectionStatus(it) }) { api ->
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

    private fun showAllDone() {
        binding.tvBadge.visibility = View.GONE
        binding.progressArea.visibility = View.GONE
        binding.bigWordArea.visibility = View.GONE
        binding.soundsRow.visibility = View.GONE
        binding.btnHints.visibility = View.GONE
        binding.extraCardsArea.visibility = View.GONE
        binding.buttonRow.removeAllViews()
        binding.cardContent.removeAllViews()
        addText("✅", 48f, false, Gravity.CENTER)
        addText("На сегодня всё повторено!", 20f, true, Gravity.CENTER)
        addText("Следующие слова появятся по расписанию.", 14f, false, Gravity.CENTER, "#888888")
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
    private fun addExtraTable(parent: LinearLayout, header: String?, rows: List<com.langbot.app.network.ExtraRow>) {
        if (!header.isNullOrBlank()) {
            val tv = TextView(this)
            tv.text = android.text.Html.fromHtml(header, android.text.Html.FROM_HTML_MODE_COMPACT)
            tv.textSize = 14f
            tv.setTextColor(Color.parseColor("#666666"))
            tv.textDirection = View.TEXT_DIRECTION_LTR
            tv.textAlignment = View.TEXT_ALIGNMENT_VIEW_START
            val hlp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            hlp.bottomMargin = dpToPx(4)
            tv.layoutParams = hlp
            parent.addView(tv)
        }
        for (row in rows) {
            val line = LinearLayout(this)
            line.orientation = LinearLayout.HORIZONTAL
            // Ряд слева направо независимо от содержимого ячеек.
            line.layoutDirection = View.LAYOUT_DIRECTION_LTR

            // Иврит: своя ячейка, внутри неё справа налево и прижат вправо —
            // так столбик читается как ивритский текст.
            val heb = TextView(this)
            heb.text = android.text.Html.fromHtml(
                row.foreign, android.text.Html.FROM_HTML_MODE_COMPACT)
            heb.textSize = 15f
            heb.textDirection = View.TEXT_DIRECTION_RTL
            heb.textAlignment = View.TEXT_ALIGNMENT_VIEW_END
            heb.layoutParams = LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f)

            // Русский: своя ячейка, слева направо и прижат влево.
            val ru = TextView(this)
            ru.text = if (row.marker.isBlank()) row.ru else "${row.marker} ${row.ru}"
            ru.textSize = 15f
            ru.textDirection = View.TEXT_DIRECTION_LTR
            ru.textAlignment = View.TEXT_ALIGNMENT_VIEW_START
            val rlp = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            rlp.marginStart = dpToPx(8)
            ru.layoutParams = rlp

            line.addView(heb)
            line.addView(ru)
            val llp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            llp.topMargin = dpToPx(3)
            line.layoutParams = llp
            parent.addView(line)
        }
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
