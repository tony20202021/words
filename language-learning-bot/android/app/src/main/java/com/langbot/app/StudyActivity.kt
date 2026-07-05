package com.langbot.app

import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.os.Bundle
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
import com.langbot.app.network.Card
import com.langbot.app.network.CardButton
import com.langbot.app.network.PickOption
import com.langbot.app.network.RateRequest
import com.langbot.app.network.SessionResponse
import com.langbot.app.network.StartSessionRequest
import com.langbot.app.prefs.UserPrefs
import kotlinx.coroutines.launch

class StudyActivity : AppCompatActivity() {

    private lateinit var binding: ActivityStudyBinding
    private lateinit var userId: String
    private lateinit var languageId: String
    private var sessionId: String? = null

    // MediaPlayer instances for the current card's sounds
    private val players = mutableListOf<MediaPlayer>()

    // Last pick-mode answer result: true=correct, false=wrong/dont_know, null=not a pick answer
    private var lastPickAnswerResult: Boolean? = null

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
            try {
                BLSClient.api.endSession(userId, languageId)
            } catch (_: Exception) { /* ignore — session may not exist */ }
            sessionId = null
            loadSession()
        }
    }

    // ── Session loading ────────────────────────────────────────────────────────

    private fun loadSession() {
        setLoading(true)
        lifecycleScope.launch {
            try {
                var resp = BLSClient.api.getSession(userId, languageId)
                if (!resp.isSuccessful || resp.body()?.session_id == null) {
                    resp = BLSClient.api.startSession(StartSessionRequest(userId, languageId))
                }
                handleResponse(resp.body())
            } catch (e: Exception) {
                Toast.makeText(this@StudyActivity, "[${e.javaClass.simpleName}] ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                setLoading(false)
            }
        }
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
                val url = BLSClient.soundUrl(soundPath)
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
                    try { player.seekTo(0); player.start() } catch (_: Exception) {
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
                    fun playAt(idx: Int) {
                        if (idx >= players.size) return
                        if (!preparedFlags[idx]) {
                            Toast.makeText(this, "Звуки ещё загружаются…", Toast.LENGTH_SHORT).show()
                            return
                        }
                        val p = players[idx]
                        p.setOnCompletionListener { playAt(idx + 1) }
                        try { p.seekTo(0); p.start() } catch (_: Exception) {}
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
        if (pickOptions != null && !card.show_answer) {
            // Pick mode: show option buttons vertically
            binding.buttonRow.orientation = LinearLayout.VERTICAL
            val targetModality = pickOptions.target_modality
            pickOptions.options.forEachIndexed { i, opt ->
                val btnText = if (targetModality == "sound") "🔊 Вариант ${i + 1}" else opt.target_text
                val b = MaterialButton(this)
                b.text = btnText
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
            // "Don't know" button
            val dontKnowBtn = MaterialButton(this)
            dontKnowBtn.text = "❓ Не знаю"
            dontKnowBtn.textSize = 13f
            dontKnowBtn.setPadding(8, 14, 8, 14)
            dontKnowBtn.setBackgroundColor(ContextCompat.getColor(this, android.R.color.transparent))
            dontKnowBtn.setTextColor(ContextCompat.getColor(this, R.color.btnSecondary))
            dontKnowBtn.strokeColor = ContextCompat.getColorStateList(this, R.color.btnSecondary)
            dontKnowBtn.strokeWidth = 2
            dontKnowBtn.setOnClickListener { onPickAnswer("dont_know") }
            binding.buttonRow.addView(dontKnowBtn)
        } else if (card.buttons.size >= 3) {
            binding.buttonRow.orientation = LinearLayout.VERTICAL
            val row1 = buildButtonRow(card.buttons.take(2))
            val row2 = buildButtonRow(card.buttons.drop(2))
            val row2lp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            row2lp.topMargin = dpToPx(4)
            row2.layoutParams = row2lp
            binding.buttonRow.addView(row1)
            binding.buttonRow.addView(row2)
        } else {
            binding.buttonRow.orientation = LinearLayout.HORIZONTAL
            val weight = 1f / card.buttons.size.coerceAtLeast(1)
            for (btn in card.buttons) {
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

        // "Ban this distractor" button after wrong pick-mode answer — placed below main buttons
        val lastWrongId = card.last_wrong_distractor_id
        binding.banButtonRow.removeAllViews()
        if (!lastWrongId.isNullOrEmpty()) {
            val banBtn = MaterialButton(this)
            banBtn.text = "🚫 Не показывать такую комбинацию"
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
                        val lp = LinearLayout.LayoutParams(
                            LinearLayout.LayoutParams.MATCH_PARENT,
                            LinearLayout.LayoutParams.WRAP_CONTENT)
                        lp.topMargin = dpToPx(4)
                        tv.layoutParams = lp
                        inner.addView(tv)
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

    private fun onButtonClick(btnId: String, rating: String?) {
        val sid = sessionId ?: return
        lastPickAnswerResult = null
        setLoading(true)
        lifecycleScope.launch {
            try {
                val resp = when (btnId) {
                    "know"        -> BLSClient.api.knowWord(sid)
                    "show_answer" -> BLSClient.api.showAnswer(sid)
                    "rate"        -> BLSClient.api.rateWord(sid, RateRequest(rating ?: "dont_know"))
                    "reconsider"  -> BLSClient.api.reconsider(sid)
                    "toggle_skip" -> BLSClient.api.toggleSkip(sid)
                    else          -> null
                }
                val body = resp?.body() ?: return@launch
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
            } catch (e: Exception) {
                Toast.makeText(this@StudyActivity, "[${e.javaClass.simpleName}] ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                setLoading(false)
            }
        }
    }

    private fun onPickAnswer(selectedWordId: String) {
        val sid = sessionId ?: return
        setLoading(true)
        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.pickAnswer(sid, mapOf("selected_word_id" to selectedWordId))
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
            } catch (e: Exception) {
                Toast.makeText(this@StudyActivity, "[${e.javaClass.simpleName}] ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                setLoading(false)
            }
        }
    }

    private fun onAddForbiddenPair(badWordId: String) {
        val sid = sessionId ?: return
        setLoading(true)
        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.addForbiddenPair(sid, mapOf("bad_word_id" to badWordId))
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
        b.setOnClickListener { onButtonClick(btn.id, btn.rating) }
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

    private fun dpToPx(dp: Int): Int =
        (dp * resources.displayMetrics.density + 0.5f).toInt()

    private fun releasePlayers() {
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
