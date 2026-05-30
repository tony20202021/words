package com.langbot.app

import android.os.Bundle
import android.view.View
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.langbot.app.network.BLSClient
import kotlinx.coroutines.launch

class HelpActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_help)

        val toolbar = findViewById<androidx.appcompat.widget.Toolbar>(R.id.toolbar)
        setSupportActionBar(toolbar)
        supportActionBar?.title = "Помощь"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        toolbar.setNavigationOnClickListener { finish() }

        val tvHelp = findViewById<TextView>(R.id.tvHelp)

        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.getHelp()
                if (resp.isSuccessful && resp.body() != null) {
                    tvHelp.text = resp.body()!!.text
                } else {
                    tvHelp.text = "Справка временно недоступна."
                }
            } catch (e: Exception) {
                Toast.makeText(this@HelpActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                tvHelp.text = "Справка временно недоступна."
            }
        }
    }
}
