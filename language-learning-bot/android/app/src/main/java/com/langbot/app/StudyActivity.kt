package com.langbot.app

import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import com.langbot.app.databinding.ActivityStudyBinding
import com.langbot.app.network.BLSClient
import com.langbot.app.network.Card
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

        loadSession()
    }

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
                Toast.makeText(this@StudyActivity, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                setLoading(false)
            }
        }
    }

    private fun handleResponse(resp: SessionResponse?) {
        if (resp == null) { showError("Нет ответа от сервера"); return }
        sessionId = resp.session_id
        val card = resp.card
        if (card == null) {
            showAllDone()
        } else {
            renderCard(card)
        }
    }

    private fun renderCard(card: Card) {
        val meta = card.meta
        val barTotal = meta.session_total?.takeIf { it > 0 } ?: 1

        // Badge
        val badge = meta.score_badge
        if (badge != null) {
            binding.tvBadge.text = badge.text + if (!badge.next_date.isNullOrEmpty()) " · ${badge.next_date}" else ""
            binding.tvBadge.visibility = View.VISIBLE
        } else {
            binding.tvBadge.visibility = View.GONE
        }

        // Content
        binding.cardContent.removeAllViews()
        for (item in card.content) {
            when (item.type) {
                "foreign" -> addText(item.text, 36f, true, Gravity.CENTER)
                "translation" -> addText(item.text, 22f, false, Gravity.CENTER)
                "transcription" -> addText("[${item.text}]", 18f, false, Gravity.CENTER, "#666666")
                "label" -> addText(item.text, 13f, false, Gravity.CENTER or Gravity.START, "#888888")
                "hint" -> addText(item.text, 13f, false, Gravity.START, "#888888")
                "notice" -> addNotice(item.text, item.variant)
            }
        }

        // Buttons
        binding.buttonRow.removeAllViews()
        val weight = 1f / card.buttons.size
        for (btn in card.buttons) {
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
            val lp = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, weight)
            lp.marginStart = 4; lp.marginEnd = 4
            b.layoutParams = lp
            b.setOnClickListener { onButtonClick(btn.id, btn.rating) }
            binding.buttonRow.addView(b)
        }

        // Progress
        if (barTotal > 0) {
            binding.progressArea.visibility = View.VISIBLE
            val correctPct = (meta.correct_count * 100 / barTotal)
            val incorrectPct = (meta.incorrect_count * 100 / barTotal)
            binding.progressCorrect.progress = correctPct
            binding.progressIncorrect.progress = incorrectPct
            binding.tvCorrect.text = "${meta.correct_count} правильных"
            binding.tvIncorrect.text = "${meta.incorrect_count} ошибок"
            val done = meta.session_pos - 1
            binding.tvDone.text = "готово $done из $barTotal"
        } else {
            binding.progressArea.visibility = View.GONE
        }
    }

    private fun onButtonClick(btnId: String, rating: String?) {
        val sid = sessionId ?: return
        setLoading(true)
        lifecycleScope.launch {
            try {
                val resp = when (btnId) {
                    "know" -> BLSClient.api.knowWord(sid)
                    "show_answer" -> BLSClient.api.showAnswer(sid)
                    "rate" -> BLSClient.api.rateWord(sid, RateRequest(rating ?: "dont_know"))
                    "reconsider" -> BLSClient.api.reconsider(sid)
                    "toggle_skip" -> BLSClient.api.toggleSkip(sid)
                    else -> null
                }
                val body = resp?.body()
                if (body != null) {
                    // If no card, try loading next batch
                    if (body.card == null && body.session_id != null) {
                        val batch = BLSClient.api.nextBatch(body.session_id!!)
                        val batchBody = batch.body()
                        if (batchBody?.card != null) { handleResponse(batchBody); return@launch }
                    }
                    handleResponse(body)
                }
            } catch (e: Exception) {
                Toast.makeText(this@StudyActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                setLoading(false)
            }
        }
    }

    private fun showAllDone() {
        binding.tvBadge.visibility = View.GONE
        binding.progressArea.visibility = View.GONE
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
        val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT)
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
            "danger" -> "#f8d7da"
            "info" -> "#d1ecf1"
            else -> "#e2e3e5"
        }
        val bg = android.graphics.drawable.GradientDrawable()
        bg.cornerRadius = 8f
        bg.setColor(android.graphics.Color.parseColor(bgColor))
        tv.background = bg
        val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT)
        lp.bottomMargin = 8
        tv.layoutParams = lp
        binding.cardContent.addView(tv)
    }

    private fun setLoading(on: Boolean) {
        binding.loadingBar.visibility = if (on) View.VISIBLE else View.GONE
    }
}
