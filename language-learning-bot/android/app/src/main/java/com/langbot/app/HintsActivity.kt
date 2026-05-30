package com.langbot.app

import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import com.langbot.app.databinding.ActivityHintsBinding
import com.langbot.app.network.BLSClient
import com.langbot.app.network.HintUpdateRequest
import kotlinx.coroutines.launch

class HintsActivity : AppCompatActivity() {

    private lateinit var binding: ActivityHintsBinding
    private lateinit var userId: String
    private lateinit var wordId: String
    private lateinit var languageId: String
    private lateinit var enabledTypes: List<String>

    companion object {
        val ALL_HINT_TYPES = linkedMapOf(
            "meaning"             to ("🧠" to "Ассоциация (рус)"),
            "phoneticsound"       to ("🎵" to "Звучание по слогам"),
            "phoneticassociation" to ("💡" to "Ассоциация фонетики"),
            "writing"             to ("✍️" to "Написание"),
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityHintsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        userId      = intent.getStringExtra("user_id") ?: run { finish(); return }
        wordId      = intent.getStringExtra("word_id") ?: run { finish(); return }
        languageId  = intent.getStringExtra("language_id") ?: run { finish(); return }
        enabledTypes = intent.getStringArrayListExtra("enabled_types") ?: ALL_HINT_TYPES.keys.toList()

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "💡 Подсказки"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        loadHints()
    }

    private fun loadHints() {
        binding.progress.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.getHints(userId, wordId)
                if (resp.isSuccessful && resp.body() != null) {
                    renderHints(resp.body()!!)
                } else {
                    Toast.makeText(this@HintsActivity, "Ошибка загрузки", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@HintsActivity, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                binding.progress.visibility = View.GONE
            }
        }
    }

    private fun renderHints(hints: Map<String, String>) {
        val container = binding.hintsContainer
        container.removeAllViews()

        // Only show enabled types
        val typesToShow = ALL_HINT_TYPES.filter { it.key in enabledTypes }

        for ((ht, iconLabel) in typesToShow) {
            val (icon, label) = iconLabel
            val value = hints[ht]?.trim() ?: ""

            // Section label
            val tvLabel = TextView(this)
            tvLabel.text = "$icon $label"
            tvLabel.textSize = 14f
            tvLabel.setTypeface(null, android.graphics.Typeface.BOLD)
            tvLabel.setTextColor(android.graphics.Color.parseColor("#444444"))
            val labelLp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
            labelLp.topMargin = 16
            tvLabel.layoutParams = labelLp
            container.addView(tvLabel)

            // Current value or placeholder
            val tvValue = TextView(this)
            tvValue.text = if (value.isNotEmpty()) value else "(не задано)"
            tvValue.textSize = 14f
            tvValue.setTextColor(
                if (value.isNotEmpty()) android.graphics.Color.parseColor("#222222")
                else android.graphics.Color.parseColor("#AAAAAA")
            )
            val valueLp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
            valueLp.topMargin = 4
            valueLp.bottomMargin = 8
            tvValue.layoutParams = valueLp
            container.addView(tvValue)

            // Buttons row
            val btnRow = LinearLayout(this)
            btnRow.orientation = LinearLayout.HORIZONTAL
            val btnLp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
            btnLp.bottomMargin = 8
            btnRow.layoutParams = btnLp

            val btnEdit = MaterialButton(this)
            btnEdit.text = if (value.isNotEmpty()) "✏️ Изменить" else "➕ Добавить"
            btnEdit.setOnClickListener { showEditDialog(ht, label, value) { loadHints() } }
            val editLp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
            editLp.marginEnd = 8
            btnEdit.layoutParams = editLp
            btnRow.addView(btnEdit)

            if (value.isNotEmpty()) {
                val btnDelete = MaterialButton(this, null,
                    com.google.android.material.R.attr.materialButtonOutlinedStyle)
                btnDelete.text = "🗑 Удалить"
                btnDelete.setOnClickListener { confirmDelete(ht, label) { loadHints() } }
                btnRow.addView(btnDelete)
            }

            container.addView(btnRow)

            // Divider
            val divider = View(this)
            divider.setBackgroundColor(android.graphics.Color.parseColor("#E0E0E0"))
            divider.layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 1
            )
            container.addView(divider)
        }
    }

    private fun showEditDialog(hintType: String, label: String, currentValue: String,
                               onSaved: () -> Unit) {
        val et = EditText(this)
        et.setText(currentValue)
        et.setSelection(et.text.length)
        et.minLines = 2
        et.hint = "Введите подсказку..."
        val wrapper = LinearLayout(this)
        wrapper.setPadding(48, 16, 48, 8)
        wrapper.addView(et)

        AlertDialog.Builder(this)
            .setTitle(label)
            .setView(wrapper)
            .setPositiveButton("Сохранить") { _, _ ->
                val text = et.text.toString().trim()
                if (text.isEmpty()) {
                    Toast.makeText(this, "Подсказка не может быть пустой", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                saveHint(hintType, text, onSaved)
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun saveHint(hintType: String, text: String, onSaved: () -> Unit) {
        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.setHint(
                    userId, wordId,
                    HintUpdateRequest(hintType, text, languageId)
                )
                if (resp.isSuccessful && resp.body()?.ok == true) {
                    Toast.makeText(this@HintsActivity, "Сохранено ✅", Toast.LENGTH_SHORT).show()
                    onSaved()
                } else {
                    Toast.makeText(this@HintsActivity, "Ошибка сохранения", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@HintsActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun confirmDelete(hintType: String, label: String, onDeleted: () -> Unit) {
        AlertDialog.Builder(this)
            .setTitle("Удалить подсказку?")
            .setMessage("«$label» будет удалена.")
            .setPositiveButton("Удалить") { _, _ -> deleteHint(hintType, onDeleted) }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun deleteHint(hintType: String, onDeleted: () -> Unit) {
        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.deleteHint(userId, wordId, hintType)
                if (resp.isSuccessful) {
                    Toast.makeText(this@HintsActivity, "Удалено 🗑", Toast.LENGTH_SHORT).show()
                    onDeleted()
                } else {
                    Toast.makeText(this@HintsActivity, "Ошибка удаления", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@HintsActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
