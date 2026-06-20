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
        private val FALLBACK_SECTIONS = listOf(
            Triple("📅 Распределение слов", listOf("words_for_today", "words_unknown", "check_interval"), "today"),
            Triple("📆 Прогресс за месяц", listOf("words_studied", "words_new", "words_known",
                "words_unknown_before", "words_unknown_first_finish", "words_unknown_last_finish", "words_for_today"), "monthly_recent"),
            Triple("📊 Прогресс за всё время", listOf("words_studied", "words_new", "words_known",
                "words_unknown_before", "words_unknown_first_finish", "words_unknown_last_finish", "words_for_today"), "monthly_all"),
        )
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

        binding.swipeRefresh.setOnRefreshListener { loadStats() }

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
                binding.swipeRefresh.isRefreshing = false
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

            // Remove the initial spinnerWrap — each section has its own
            binding.statsContainer.removeView(spinnerWrap)

            val manifest = try {
                BLSClient.api.getChartManifest().body()
            } catch (_: Exception) { null }

            val sections = manifest?.sections?.map {
                Triple(it.header, it.charts, it.type)
            } ?: FALLBACK_SECTIONS

            for ((i, section) in sections.withIndex()) {
                val (title, names, chartType) = section
                val type = when (chartType) {
                    "today" -> 0
                    "monthly_recent" -> 1
                    else -> 2
                }
                val showAll = chartType == "monthly_all"

                // Divider before sections 2 and 3
                if (i > 0) {
                    val div = View(this@StatsActivity)
                    div.setBackgroundColor(android.graphics.Color.parseColor("#E0E0E0"))
                    val divLp = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT, dpToPx(1))
                    divLp.topMargin = dpToPx(16); divLp.bottomMargin = dpToPx(16)
                    div.layoutParams = divLp
                    binding.statsContainer.addView(div)
                }

                // Section header
                val tvTitle = TextView(this@StatsActivity)
                tvTitle.text = title
                tvTitle.textSize = 15f
                tvTitle.setTypeface(null, android.graphics.Typeface.BOLD)
                tvTitle.setTextColor(android.graphics.Color.parseColor("#555555"))
                binding.statsContainer.addView(tvTitle)

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
                binding.statsContainer.addView(ssWrap)

                // Load charts for this section
                for (name in names) {
                    try {
                        val resp = when (type) {
                            0    -> BLSClient.api.getChart(userId, languageId, name)
                            1    -> BLSClient.api.getMonthlyChart(userId, languageId, name, showAll = false)
                            else -> BLSClient.api.getMonthlyChart(userId, languageId, name, showAll = true)
                        }

                        if (resp.isSuccessful) {
                            val bytes = resp.body()?.bytes() ?: continue
                            val bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: continue
                            val iv = ImageView(this@StatsActivity)
                            iv.setImageBitmap(bmp)
                            iv.adjustViewBounds = true
                            val lp = LinearLayout.LayoutParams(
                                LinearLayout.LayoutParams.MATCH_PARENT,
                                LinearLayout.LayoutParams.WRAP_CONTENT)
                            lp.bottomMargin = dpToPx(6)
                            iv.layoutParams = lp
                            binding.statsContainer.addView(iv)
                            anyLoaded = true
                        }
                    } catch (e: Exception) {
                        android.util.Log.w("StatsActivity", "$title/$name: ${e.message}")
                    }
                }

                // Hide section spinner when done
                binding.statsContainer.removeView(ssWrap)
            }

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
        if (s.words_unknown > 0) {
            addStatRow(c, "Неизвестно", s.words_unknown.toString(), "#dc3545")
        }
        if (s.words_skipped > 0) {
            addStatRow(c, "Пропущено", s.words_skipped.toString(), "#ffc107")
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
