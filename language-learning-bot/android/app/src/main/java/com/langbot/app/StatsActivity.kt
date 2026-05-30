package com.langbot.app

import android.graphics.BitmapFactory
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.langbot.app.databinding.ActivityStatsBinding
import com.langbot.app.network.BLSClient
import com.langbot.app.network.Statistics
import com.langbot.app.prefs.UserPrefs
import kotlinx.coroutines.async
import kotlinx.coroutines.launch

class StatsActivity : AppCompatActivity() {

    private lateinit var binding: ActivityStatsBinding
    private lateinit var userId: String
    private lateinit var languageId: String

    companion object {
        private val TODAY_CHARTS   = listOf("words_for_today", "words_unknown", "check_interval")
        private val MONTHLY_CHARTS = listOf("words_studied", "words_new", "words_known",
                                            "words_unknown_before", "words_unknown_after", "words_for_today")
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityStatsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        userId     = UserPrefs.getUserId(this) ?: run { finish(); return }
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
                val statsDeferred = async { BLSClient.api.getStatistics(userId, languageId) }
                val statsResp = statsDeferred.await()
                if (statsResp.isSuccessful && statsResp.body() != null) {
                    renderStats(statsResp.body()!!)
                    loadCharts()
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

    private fun loadCharts() {
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
        binding.statsContainer.addView(tvHeader)

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
        binding.statsContainer.addView(spinnerWrap)

        lifecycleScope.launch {
            var anyLoaded = false

            fun sectionLabel(text: String) {
                val tv = TextView(this@StatsActivity)
                tv.text = text
                tv.textSize = 12f
                tv.setTextColor(android.graphics.Color.parseColor("#888888"))
                tv.gravity = android.view.Gravity.CENTER
                val lp = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                lp.topMargin = 16; lp.bottomMargin = 4
                tv.layoutParams = lp
                binding.statsContainer.addView(tv)
            }

            fun addChartImage(bytes: ByteArray) {
                val bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return
                val iv = ImageView(this@StatsActivity)
                iv.setImageBitmap(bmp)
                iv.adjustViewBounds = true
                val lp = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                lp.bottomMargin = 8
                iv.layoutParams = lp
                binding.statsContainer.addView(iv)
            }

            // Today charts
            sectionLabel("Распределение слов")
            for (name in TODAY_CHARTS) {
                try {
                    val resp = BLSClient.api.getChart(userId, languageId, name)
                    if (resp.isSuccessful) {
                        resp.body()?.bytes()?.let { addChartImage(it); anyLoaded = true }
                    }
                } catch (e: Exception) {
                    android.util.Log.w("StatsActivity", "today/$name: ${e.message}")
                }
            }

            // Monthly charts (last 30 days)
            sectionLabel("Прогресс за месяц")
            for (name in MONTHLY_CHARTS) {
                try {
                    val resp = BLSClient.api.getMonthlyChart(userId, languageId, name, showAll = false)
                    if (resp.isSuccessful) {
                        resp.body()?.bytes()?.let { addChartImage(it); anyLoaded = true }
                    }
                } catch (e: Exception) {
                    android.util.Log.w("StatsActivity", "monthly-recent/$name: ${e.message}")
                }
            }

            // Monthly charts (all time)
            sectionLabel("Прогресс за всё время")
            for (name in MONTHLY_CHARTS) {
                try {
                    val resp = BLSClient.api.getMonthlyChart(userId, languageId, name, showAll = true)
                    if (resp.isSuccessful) {
                        resp.body()?.bytes()?.let { addChartImage(it); anyLoaded = true }
                    }
                } catch (e: Exception) {
                    android.util.Log.w("StatsActivity", "monthly/$name: ${e.message}")
                }
            }

            binding.statsContainer.removeView(spinnerWrap)
            if (!anyLoaded) {
                val tv = TextView(this@StatsActivity)
                tv.text = "Нет данных для графиков"
                tv.textSize = 13f
                tv.setTextColor(android.graphics.Color.parseColor("#888888"))
                tv.gravity = android.view.Gravity.CENTER
                binding.statsContainer.addView(tv)
            }
        }
    }

    private fun renderStats(s: Statistics) {
        val c = binding.statsContainer
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
