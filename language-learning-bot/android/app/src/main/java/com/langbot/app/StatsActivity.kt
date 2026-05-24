package com.langbot.app

import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.langbot.app.databinding.ActivityStatsBinding
import com.langbot.app.network.BLSClient
import com.langbot.app.network.Statistics
import com.langbot.app.prefs.UserPrefs
import kotlinx.coroutines.launch
import kotlin.math.roundToInt

class StatsActivity : AppCompatActivity() {

    private lateinit var binding: ActivityStatsBinding
    private lateinit var userId: String
    private lateinit var languageId: String

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityStatsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        userId = UserPrefs.getUserId(this) ?: run { finish(); return }
        languageId = intent.getStringExtra("language_id") ?: run { finish(); return }
        val langName = intent.getStringExtra("language_name") ?: "Статистика"

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Статистика: $langName"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        loadStats()
    }

    private fun loadStats() {
        binding.progress.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.getStatistics(userId, languageId)
                if (resp.isSuccessful && resp.body() != null) {
                    renderStats(resp.body()!!)
                } else {
                    Toast.makeText(this@StatsActivity, "Ошибка загрузки", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@StatsActivity, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                binding.progress.visibility = View.GONE
            }
        }
    }

    private fun renderStats(s: Statistics) {
        val c = binding.statsContainer
        c.removeAllViews()

        if (s.total_words > 0) {
            val pct = (s.progress_percentage).roundToInt()
            val bar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal)
            bar.max = 100
            bar.progress = pct
            bar.progressTintList = android.content.res.ColorStateList.valueOf(
                android.graphics.Color.parseColor("#28a745"))
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 20)
            lp.bottomMargin = 16
            bar.layoutParams = lp
            c.addView(bar)
        }

        addStatRow(c, "Знаю", s.words_known.toString(), "#28a745")
        addStatRow(c, "Изучено", s.words_studied.toString(), "#333333")
        addStatRow(c, "Всего слов", s.total_words.toString(), "#666666")
        addStatRow(c, "К повторению сегодня", s.words_for_today.toString(),
            if (s.words_for_today > 0) "#f0ad4e" else "#666666")
        addStatRow(c, "Прогресс (знаю / всего)",
            "%.1f%%".format(s.progress_percentage), "#17a2b8")
        if (s.words_known > 0 && s.words_studied > 0) {
            val pctKnown = s.words_known * 100.0 / s.words_studied
            addStatRow(c, "Прогресс (знаю / изучено)", "%.1f%%".format(pctKnown), "#007bff")
        }
        if (s.words_skipped > 0) {
            addStatRow(c, "Пропущено", s.words_skipped.toString(), "#ffc107")
        }
    }

    private fun addStatRow(parent: LinearLayout, label: String, value: String, valueColor: String) {
        val row = LinearLayout(this)
        row.orientation = LinearLayout.HORIZONTAL
        row.setPadding(0, 12, 0, 12)
        val divider = View(this)
        divider.setBackgroundColor(android.graphics.Color.parseColor("#E0E0E0"))
        val divLp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 1)
        divider.layoutParams = divLp

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
