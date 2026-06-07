package com.langbot.app

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
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
    private var updateBanner: android.widget.TextView? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLanguagesBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "LangBot"
        supportActionBar?.subtitle = "v${packageManager.getPackageInfo(packageName, 0).versionName}"

        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.recycler.adapter = adapter

        binding.swipeRefresh.setOnRefreshListener {
            loadLanguages()
            checkForUpdate()
        }

        checkForUpdate()
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
                binding.swipeRefresh.isRefreshing = false
            }
        }
    }

    companion object {
        private const val MENU_HELP      = 1
        private const val MENU_WEB       = 2
        private const val MENU_CONNECT   = 3
        private const val MENU_TELEGRAM  = 4
        private const val MENU_LOGOUT    = 5
        private const val WEB_URL        = "http://136.244.102.39:8800"
        private const val TELEGRAM_URL   = "https://t.me/language_learning_words_bot"
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add(0, MENU_HELP,     0, "? Помощь")
        menu.add(0, MENU_WEB,      1, "🌐 Веб-версия")
        menu.add(0, MENU_CONNECT,  2, "🔗 Код для веб")
        menu.add(0, MENU_TELEGRAM, 3, "🤖 Telegram-бот")
        menu.add(0, MENU_LOGOUT,   4, "Выйти")
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        when (item.itemId) {
            MENU_HELP -> {
                startActivity(Intent(this, HelpActivity::class.java))
                return true
            }
            MENU_WEB -> {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(WEB_URL)))
                return true
            }
            MENU_CONNECT -> {
                generateWebCode()
                return true
            }
            MENU_TELEGRAM -> {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(TELEGRAM_URL)))
                return true
            }
            MENU_LOGOUT -> {
                UserPrefs.clear(this)
                startActivity(Intent(this, LoginActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                })
                return true
            }
        }
        return super.onOptionsItemSelected(item)
    }

    private fun checkForUpdate() {
        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.getVersion()
                val body = resp.body() ?: return@launch
                val pkgInfo = packageManager.getPackageInfo(packageName, 0)
                @Suppress("DEPRECATION")
                val currentCode = pkgInfo.versionCode
                val root = binding.root as android.widget.LinearLayout
                updateBanner?.let { root.removeView(it) }
                updateBanner = null
                if (body.version_code > currentCode) {
                    val newVer = body.version
                    val banner = android.widget.TextView(this@LanguagesActivity)
                    banner.text = "⬆ Доступна версия $newVer — нажмите для обновления"
                    banner.textSize = 13f
                    banner.setTextColor(android.graphics.Color.WHITE)
                    banner.setBackgroundColor(android.graphics.Color.parseColor("#1565C0"))
                    banner.setPadding(32, 16, 32, 16)
                    banner.gravity = android.view.Gravity.CENTER
                    banner.setOnClickListener {
                        startActivity(Intent(Intent.ACTION_VIEW,
                            Uri.parse("$WEB_URL/download/android")))
                    }
                    root.addView(banner, 1)
                    updateBanner = banner
                }
            } catch (_: Exception) { /* version check is optional */ }
        }
    }

    private fun generateWebCode() {
        val userId = UserPrefs.getUserId(this) ?: return
        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.createMobileToken(mapOf("user_id" to userId))
                val code = resp.body()?.code
                if (code == null) {
                    Toast.makeText(this@LanguagesActivity, "Не удалось создать код", Toast.LENGTH_SHORT).show()
                    return@launch
                }
                val webUrl = "$WEB_URL/login?code=$code"

                // Custom dialog view
                val ctx = this@LanguagesActivity
                val layout = android.widget.LinearLayout(ctx)
                layout.orientation = android.widget.LinearLayout.VERTICAL
                val pad = (16 * resources.displayMetrics.density).toInt()
                layout.setPadding(pad * 2, pad, pad * 2, 0)

                val tvCode = android.widget.TextView(ctx)
                tvCode.text = code
                tvCode.textSize = 36f
                tvCode.setTypeface(null, android.graphics.Typeface.BOLD)
                tvCode.gravity = android.view.Gravity.CENTER
                tvCode.setTextColor(android.graphics.Color.parseColor("#1565C0"))
                tvCode.setOnClickListener {
                    val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    cm.setPrimaryClip(ClipData.newPlainText("code", code))
                    Toast.makeText(ctx, "Код скопирован", Toast.LENGTH_SHORT).show()
                }
                val tvCodeHint = android.widget.TextView(ctx)
                tvCodeHint.text = "нажмите на код, чтобы скопировать"
                tvCodeHint.textSize = 11f
                tvCodeHint.setTextColor(android.graphics.Color.parseColor("#aaaaaa"))
                tvCodeHint.gravity = android.view.Gravity.CENTER

                val tvNote = android.widget.TextView(ctx)
                tvNote.text = "Действует 10 минут · одноразовый"
                tvNote.textSize = 12f
                tvNote.setTextColor(android.graphics.Color.parseColor("#888888"))
                tvNote.gravity = android.view.Gravity.CENTER
                val noteLp = android.widget.LinearLayout.LayoutParams(
                    android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
                    android.widget.LinearLayout.LayoutParams.WRAP_CONTENT)
                noteLp.topMargin = (8 * resources.displayMetrics.density).toInt()
                tvNote.layoutParams = noteLp

                val tvUrl = android.widget.TextView(ctx)
                tvUrl.text = webUrl
                tvUrl.textSize = 12f
                tvUrl.setTextColor(android.graphics.Color.parseColor("#1565C0"))
                tvUrl.setPaintFlags(tvUrl.paintFlags or android.graphics.Paint.UNDERLINE_TEXT_FLAG)
                tvUrl.gravity = android.view.Gravity.CENTER
                val urlLp = android.widget.LinearLayout.LayoutParams(
                    android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
                    android.widget.LinearLayout.LayoutParams.WRAP_CONTENT)
                urlLp.topMargin = (12 * resources.displayMetrics.density).toInt()
                tvUrl.layoutParams = urlLp
                tvUrl.setOnClickListener {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(webUrl)))
                }

                layout.addView(tvCode)
                layout.addView(tvCodeHint)
                layout.addView(tvNote)
                layout.addView(tvUrl)

                // Load QR code
                try {
                    val qrResp = BLSClient.api.getQrCode(webUrl)
                    if (qrResp.isSuccessful) {
                        val bytes = qrResp.body()?.bytes()
                        if (bytes != null) {
                            val bmp = android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                            if (bmp != null) {
                                val ivQr = android.widget.ImageView(ctx)
                                ivQr.setImageBitmap(bmp)
                                val qrLp = android.widget.LinearLayout.LayoutParams(
                                    (200 * resources.displayMetrics.density).toInt(),
                                    (200 * resources.displayMetrics.density).toInt())
                                qrLp.gravity = android.view.Gravity.CENTER_HORIZONTAL
                                qrLp.topMargin = pad
                                ivQr.layoutParams = qrLp
                                layout.addView(ivQr)
                            }
                        }
                    }
                } catch (_: Exception) { /* QR is optional */ }

                AlertDialog.Builder(ctx)
                    .setTitle("Код для входа в веб")
                    .setView(layout)
                    .setPositiveButton("Скопировать код") { _, _ ->
                        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        cm.setPrimaryClip(ClipData.newPlainText("code", code))
                        Toast.makeText(ctx, "Код скопирован", Toast.LENGTH_SHORT).show()
                    }
                    .setNegativeButton("Закрыть", null)
                    .show()
            } catch (e: Exception) {
                Toast.makeText(this@LanguagesActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
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
            holder.b.btnSettings.setOnClickListener {
                startActivity(Intent(this@LanguagesActivity, SettingsActivity::class.java).apply {
                    putExtra("language_id", lang.id)
                    putExtra("language_name", "${lang.name_ru} (${lang.name_foreign})")
                })
            }
        }
    }
}
