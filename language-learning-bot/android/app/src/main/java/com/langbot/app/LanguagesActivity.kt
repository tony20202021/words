package com.langbot.app

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.langbot.app.databinding.ActivityLanguagesBinding
import com.langbot.app.databinding.ItemLanguageBinding
import com.langbot.app.network.BLSClient
import com.langbot.app.network.Language
import com.langbot.app.prefs.UserPrefs
import kotlinx.coroutines.launch

class LanguagesActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLanguagesBinding
    private val adapter = LanguageAdapter()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLanguagesBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.recycler.adapter = adapter

        loadLanguages()
    }

    override fun onResume() {
        super.onResume()
        loadLanguages()
    }

    private fun loadLanguages() {
        binding.progress.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.getLanguages()
                if (resp.isSuccessful) {
                    adapter.items = resp.body() ?: emptyList()
                    adapter.notifyDataSetChanged()
                }
            } catch (e: Exception) {
                Toast.makeText(this@LanguagesActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progress.visibility = View.GONE
            }
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add(0, 1, 0, "Выйти")
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == 1) {
            UserPrefs.clear(this)
            startActivity(Intent(this, LoginActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            })
        }
        return super.onOptionsItemSelected(item)
    }

    inner class LanguageAdapter : RecyclerView.Adapter<LanguageAdapter.VH>() {
        var items: List<Language> = emptyList()

        inner class VH(val b: ItemLanguageBinding) : RecyclerView.ViewHolder(b.root)

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(ItemLanguageBinding.inflate(LayoutInflater.from(parent.context), parent, false))

        override fun getItemCount() = items.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val lang = items[position]
            holder.b.tvForeign.text = lang.name_foreign
            holder.b.tvRu.text = lang.name_ru
            holder.b.btnStudy.setOnClickListener {
                startActivity(Intent(this@LanguagesActivity, StudyActivity::class.java).apply {
                    putExtra("language_id", lang.id)
                    putExtra("language_name", lang.name_foreign)
                })
            }
            holder.b.btnStats.setOnClickListener {
                startActivity(Intent(this@LanguagesActivity, StatsActivity::class.java).apply {
                    putExtra("language_id", lang.id)
                    putExtra("language_name", lang.name_foreign)
                })
            }
        }
    }
}
