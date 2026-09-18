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
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.awaitAll
import com.langbot.app.offline.OfflineNotice

class StatsActivity : AppCompatActivity() {

    private lateinit var binding: ActivityStatsBinding
    private lateinit var userId: String
    private lateinit var languageId: String

    companion object {
        // Запасной список на случай, когда манифест недоступен. Имена обязаны
        // совпадать с common/chart_manifest.py: сервер рисует график по имени и
        // на незнакомое отвечает 404, то есть пустым местом на экране.
        private val MONTHLY_CHARTS = listOf(
            "words_studied", "words_new", "words_known",
            "words_unknown_morning", "words_overdue_morning",
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
                    OfflineNotice.clear(binding.statsContainer)
                    renderStats(statsResp.body()!!)
                    loadCharts()
                } else {
                    OfflineNotice.show(binding.statsContainer, "статистику")
                }
            } catch (e: Exception) {
                // Статистику офлайн показать неоткуда — она целиком серверная.
                OfflineNotice.show(binding.statsContainer, "статистику")
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

            // Сначала каркас: заголовки разделов и места под картинки — в порядке
            // манифеста. Потом все запросы разом. Прежде 17 картинок грузились
            // строго по очереди, и время складывалось: на слабом мобильном каждая
            // ждала, пока доедет предыдущая. Теперь каждая встаёт в своё место,
            // как только пришла, и порядок не зависит от того, какая ответит первой.
            class Slot(val holder: LinearLayout, val type: Int, val name: String, val title: String)
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

                val slots = names.map { name ->
                    val holder = LinearLayout(this@StatsActivity)
                    holder.orientation = LinearLayout.VERTICAL
                    holder.layoutParams = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                    binding.statsContainer.addView(holder)
                    Slot(holder, type, name, title)
                }
                sectionSlots += ssWrap to slots
            }

            suspend fun loadInto(slot: Slot): Boolean = try {
                val resp = when (slot.type) {
                    0    -> BLSClient.api.getChart(userId, languageId, slot.name)
                    1    -> BLSClient.api.getMonthlyChart(userId, languageId, slot.name, showAll = false)
                    else -> BLSClient.api.getMonthlyChart(userId, languageId, slot.name, showAll = true)
                }
                val bytes = if (resp.isSuccessful) resp.body()?.bytes() else null
                val bmp = bytes?.let { BitmapFactory.decodeByteArray(it, 0, it.size) }
                if (bmp == null) false else {
                    val iv = ImageView(this@StatsActivity)
                    iv.setImageBitmap(bmp)
                    iv.adjustViewBounds = true
                    val lp = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT)
                    lp.bottomMargin = dpToPx(6)
                    iv.layoutParams = lp
                    slot.holder.addView(iv)
                    true
                }
            } catch (e: Exception) {
                android.util.Log.w("StatsActivity", "${slot.title}/${slot.name}: ${e.message}")
                false
            }

            val loaded = coroutineScope {
                sectionSlots.map { (spinnerView, slots) ->
                    async {
                        val results = slots.map { slot -> async { loadInto(slot) } }.awaitAll()
                        binding.statsContainer.removeView(spinnerView)
                        results
                    }
                }.awaitAll().flatten()
            }
            anyLoaded = loaded.any { it }

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
