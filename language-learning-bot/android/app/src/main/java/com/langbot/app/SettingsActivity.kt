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

class SettingsActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySettingsBinding
    private lateinit var userId: String
    private lateinit var languageId: String

    companion object {
        val TOGGLE_SETTINGS = linkedMapOf(
            "skip_marked"                   to "Пропускать исключённые слова",
            "use_check_date"                to "Учитывать дату проверки",
            "show_check_date"               to "Показывать дату проверки",
            "show_hint_meaning"             to "Подсказка: ассоциация (рус)",
            "show_hint_phoneticsound"       to "Подсказка: звучание по слогам",
            "show_hint_phoneticassociation" to "Подсказка: ассоциация фонетики",
            "show_hint_writing"             to "Подсказка: написание",
            "show_big"                      to "Крупное написание",
            "show_writing_images"           to "Показывать картинки написания",
            "show_radicals"                 to "Показывать радикалы",
            "show_references"               to "Показывать ссылки",
            "show_tones"                    to "Показывать тоны",
            "show_sounds"                   to "Показывать звуки",
            "random_foreign"                to "Случайно начинать с иностр. слова",
            "random_transcription"          to "Случайно начинать с транскрипции",
            "random_sound"                  to "Случайно начинать со звука",
        )

        val NUMERIC_SETTINGS = linkedMapOf(
            "start_word"              to "Начальное слово",
            "reset_session_days"      to "Сброс сессии (дни)",
            "reset_session_hours"     to "Сброс сессии (часы)",
            "unknown_limit_new_words" to "Лимит неизвестных слов",
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

        loadSettings()
    }

    private fun loadSettings() {
        binding.progress.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.getSettings(userId, languageId)
                if (resp.isSuccessful && resp.body() != null) {
                    renderSettings(resp.body()!!)
                } else {
                    Toast.makeText(this@SettingsActivity, "Ошибка загрузки", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@SettingsActivity, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                binding.progress.visibility = View.GONE
            }
        }
    }

    private fun renderSettings(settings: Map<String, Any>) {
        val container = binding.settingsContainer
        container.removeAllViews()

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
            row.addView(sw)
            sw.setOnCheckedChangeListener { _, _ -> toggleSetting(key) }

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
            tvValue.setTextColor(android.graphics.Color.parseColor("#1565C0"))
            tvValue.setPadding(16, 0, 0, 0)
            row.addView(tvValue)

            val tvArrow = TextView(this)
            tvArrow.text = " ›"
            tvArrow.textSize = 18f
            tvArrow.setTextColor(android.graphics.Color.parseColor("#BBBBBB"))
            row.addView(tvArrow)

            row.setOnClickListener { showNumericDialog(label, key, current, tvValue) }
            container.addView(row)
            addDivider(container)
        }
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
                BLSClient.api.toggleSetting(userId, languageId, key)
            } catch (e: Exception) {
                Toast.makeText(this@SettingsActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                loadSettings()
            }
        }
    }

    private fun saveNumericSetting(key: String, value: Int) {
        lifecycleScope.launch {
            try {
                BLSClient.api.setSetting(userId, languageId, key, mapOf("value" to value))
            } catch (e: Exception) {
                Toast.makeText(this@SettingsActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                loadSettings()
            }
        }
    }
}
