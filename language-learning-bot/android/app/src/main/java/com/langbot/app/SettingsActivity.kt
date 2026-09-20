package com.langbot.app

import android.os.Bundle
import android.text.InputType
import android.view.View
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.langbot.app.databinding.ActivitySettingsBinding
import com.langbot.app.network.BLSClient
import com.langbot.app.prefs.UserPrefs
import kotlinx.coroutines.launch
import com.langbot.app.offline.OfflineCache
import com.langbot.app.offline.OfflineNotice

class SettingsActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySettingsBinding
    private lateinit var userId: String
    private lateinit var languageId: String

    companion object {
        val TOGGLE_SETTINGS = linkedMapOf(
            "skip_marked"                   to "Пропускать исключённые слова",
            "show_skip_button"              to "Показывать кнопку Пропускать",
            "use_check_date"                to "Учитывать дату проверки",
            "show_check_date"               to "Показывать дату проверки",
            "show_hint_meaning"             to "Подсказка: ассоциация (рус)",
            "show_hint_phoneticsound"       to "Подсказка: звучание по слогам",
            "show_hint_phoneticassociation" to "Подсказка: ассоциация фонетики",
            "show_hint_writing"             to "Подсказка: написание",
            "show_big"                      to "Крупное написание",
            "show_radicals"                 to "Показывать радикалы",
            "show_references"               to "Показывать ссылки",
        "show_tags"                     to "Показывать группы слов",
            "show_tones"                    to "Показывать тоны",
            "show_sounds"                   to "Показывать звуки",
            "random_transcription"          to "Доп. использовать транскрипцию",
            "random_sound"                  to "Доп. использовать звук",
            "random_pick_mode"              to "Режим выбора (pick mode)",
        )

        val NUMERIC_SETTINGS = linkedMapOf(
            "start_word"                 to "Начальное слово",
            "reset_same_day_hours"       to "Сброс: перерыв за день (ч)",
            "reset_cross_midnight_hours" to "Сброс: час после полуночи",
            "unknown_limit_new_words"    to "Лимит неизвестных слов",
            "max_check_interval"         to "Макс. интервал повторения (дни)",
            "quiz_options_count"         to "Вариантов в режиме выбора",
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        userId     = UserPrefs.getUserId(this) ?: run { finish(); return }
        languageId = intent.getStringExtra("language_id") ?: run { finish(); return }
        val langName = intent.getStringExtra("language_name") ?: "Настройки"

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "⚙️ $langName"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.swipeRefresh.setOnRefreshListener { loadSettings() }

        loadSettings()
    }

    private fun loadSettings() {
        binding.progress.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.getSettings(userId, languageId)
                if (resp.isSuccessful && resp.body() != null) {
                    OfflineNotice.clear(binding.settingsContainer)
                    renderSettings(resp.body()!!)
                } else {
                    showFromOfflineBundle()
                }
            } catch (e: Exception) {
                showFromOfflineBundle()
            } finally {
                binding.progress.visibility = View.GONE
                binding.swipeRefresh.isRefreshing = false
            }
        }
    }

    /**
     * Без сети — показать настройки из сохранённой офлайн-партии.
     *
     * Экран сам по себе целиком зависит от BLS, и раньше без сети на нём была
     * одна надпись «нет связи» — хотя показать было что: сервер присылает
     * настройки вместе с офлайн-партией, а телефон их выбрасывал. Теперь они
     * сохраняются и показываются только для чтения: менять их без сети
     * бессмысленно, потому что состав слов пересчитывает сервер.
     */
    private fun showFromOfflineBundle() {
        val cached = OfflineCache.loadBundle(userId, languageId)?.settings
        if (cached.isNullOrEmpty()) {
            OfflineNotice.show(binding.settingsContainer, "настройки")
            return
        }
        renderSettings(cached, readOnly = true)
    }

    private fun renderSettings(settings: Map<String, Any>, readOnly: Boolean = false) {
        val container = binding.settingsContainer
        container.removeAllViews()

        if (readOnly) addOfflineBanner(container)

        addSectionHeader(container, "Переключатели")

        for ((key, label) in TOGGLE_SETTINGS) {
            val value = when (val v = settings[key]) {
                is Boolean -> v
                is Double  -> v != 0.0
                is String  -> v == "true"
                else       -> false
            }

            val row = LinearLayout(this)
            row.orientation = LinearLayout.HORIZONTAL
            row.setPadding(0, 16, 0, 16)

            val tvLabel = TextView(this)
            tvLabel.text = label
            tvLabel.textSize = 15f
            tvLabel.layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            row.addView(tvLabel)

            val sw = Switch(this)
            sw.isChecked = value
            sw.setOnCheckedChangeListener(null)
            sw.isEnabled = !readOnly
            row.addView(sw)
            // Без сети слушатель не вешаем вовсе: выключенный переключатель уже
            // не нажать, но и случайное программное переключение не должно
            // отправлять запрос, которому некуда идти.
            if (!readOnly) sw.setOnCheckedChangeListener { _, _ -> toggleSetting(key) }

            container.addView(row)
            addDivider(container)
        }

        addSectionHeader(container, "Числовые значения")

        for ((key, label) in NUMERIC_SETTINGS) {
            val rawValue = settings[key]
            val current = when (rawValue) {
                is Double -> rawValue.toInt()
                is Int    -> rawValue
                is String -> rawValue.toIntOrNull() ?: 0
                else      -> 0
            }

            val row = LinearLayout(this)
            row.orientation = LinearLayout.HORIZONTAL
            row.setPadding(0, 16, 0, 16)

            val tvLabel = TextView(this)
            tvLabel.text = label
            tvLabel.textSize = 15f
            tvLabel.layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            row.addView(tvLabel)

            val tvValue = TextView(this)
            tvValue.text = current.toString()
            tvValue.textSize = 15f
            tvValue.setTextColor(android.graphics.Color.parseColor(
                if (readOnly) "#9A9A9A" else "#1565C0"))
            tvValue.setPadding(16, 0, 0, 0)
            row.addView(tvValue)

            // Стрелка обещает, что строка нажимается. Без сети не обещаем.
            if (!readOnly) {
                val tvArrow = TextView(this)
                tvArrow.text = " ›"
                tvArrow.textSize = 18f
                tvArrow.setTextColor(android.graphics.Color.parseColor("#BBBBBB"))
                row.addView(tvArrow)
                row.setOnClickListener { showNumericDialog(label, key, current, tvValue) }
            }
            container.addView(row)
            addDivider(container)
        }
    }

    /** Откуда взялись значения и почему их не поменять. */
    private fun addOfflineBanner(container: LinearLayout) {
        val tv = TextView(this)
        tv.text = "📴 Нет связи с сервером\n\n" +
            "Настройки показаны из сохранённой офлайн-партии — такими они были, " +
            "когда партия скачалась. Менять их без сети нельзя: какие слова " +
            "показывать, решает сервер."
        tv.textSize = 14f
        tv.setTextColor(android.graphics.Color.parseColor("#856404"))
        tv.setBackgroundColor(android.graphics.Color.parseColor("#FFF3CD"))
        tv.setPadding(24, 24, 24, 24)
        val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,
                                           LinearLayout.LayoutParams.WRAP_CONTENT)
        lp.bottomMargin = 16
        tv.layoutParams = lp
        container.addView(tv)
    }

    private fun addSectionHeader(container: LinearLayout, title: String) {
        val tv = TextView(this)
        tv.text = title
        tv.textSize = 13f
        tv.setTextColor(android.graphics.Color.parseColor("#888888"))
        tv.setTypeface(null, android.graphics.Typeface.BOLD)
        val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        lp.topMargin = 24; lp.bottomMargin = 4
        tv.layoutParams = lp
        container.addView(tv)
    }

    private fun addDivider(container: LinearLayout) {
        val divider = View(this)
        divider.setBackgroundColor(android.graphics.Color.parseColor("#E0E0E0"))
        divider.layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 1)
        container.addView(divider)
    }

    private fun showNumericDialog(label: String, key: String, current: Int, tvValue: TextView) {
        val input = EditText(this)
        input.inputType = InputType.TYPE_CLASS_NUMBER
        input.setText(current.toString())
        input.selectAll()

        AlertDialog.Builder(this)
            .setTitle(label)
            .setView(input)
            .setPositiveButton("Сохранить") { _, _ ->
                val newVal = input.text.toString().toIntOrNull()
                if (newVal == null) {
                    Toast.makeText(this, "Введите целое число", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                tvValue.text = newVal.toString()
                saveNumericSetting(key, newVal)
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun toggleSetting(key: String) {
        lifecycleScope.launch {
            try {
                // Исключение бросается только при обрыве связи; ответ 4xx/5xx
                // Retrofit отдаёт спокойно. Игнорируя статус, мы оставляли
                // переключатель в положении, которого на сервере нет.
                val resp = BLSClient.api.toggleSetting(userId, languageId, key)
                if (!resp.isSuccessful) {
                    Toast.makeText(this@SettingsActivity,
                        "Не удалось сохранить (${resp.code()})", Toast.LENGTH_SHORT).show()
                    loadSettings()
                }
            } catch (e: Exception) {
                Toast.makeText(this@SettingsActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                loadSettings()
            }
        }
    }

    private fun saveNumericSetting(key: String, value: Int) {
        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.setSetting(userId, languageId, key, mapOf("value" to value))
                if (!resp.isSuccessful) {
                    Toast.makeText(this@SettingsActivity, "Ошибка сохранения (${resp.code()})", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@SettingsActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                loadSettings()
            }
        }
    }
}
