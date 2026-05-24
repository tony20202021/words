package com.langbot.app

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.langbot.app.databinding.ActivityLoginBinding
import com.langbot.app.network.BLSClient
import com.langbot.app.network.MobileActivateRequest
import com.langbot.app.prefs.UserPrefs
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Skip login if already authenticated
        val existingUserId = UserPrefs.getUserId(this)
        if (existingUserId != null) {
            BLSClient.init(UserPrefs.getBlsUrl(this))
            startActivity(Intent(this, LanguagesActivity::class.java))
            finish()
            return
        }

        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.etServerUrl.setText(UserPrefs.getBlsUrl(this))

        binding.btnLogin.setOnClickListener { attemptLogin() }
        binding.etCode.setOnEditorActionListener { _, _, _ -> attemptLogin(); true }
    }

    private fun attemptLogin() {
        val url = binding.etServerUrl.text.toString().trim().trimEnd('/')
        val code = binding.etCode.text.toString().trim().uppercase()

        if (url.isEmpty()) { showError("Введите адрес сервера"); return }
        if (code.length != 6) { showError("Код должен содержать 6 символов"); return }

        binding.btnLogin.isEnabled = false
        binding.tvError.visibility = View.GONE
        UserPrefs.saveBlsUrl(this, url)
        BLSClient.init(url)

        lifecycleScope.launch {
            try {
                val resp = BLSClient.api.activateMobileToken(MobileActivateRequest(code))
                if (resp.isSuccessful && resp.body() != null) {
                    val userId = resp.body()!!.user_id
                    UserPrefs.saveUserId(this@LoginActivity, userId)
                    startActivity(Intent(this@LoginActivity, LanguagesActivity::class.java))
                    finish()
                } else {
                    showError("Неверный или истёкший код")
                }
            } catch (e: Exception) {
                showError("Ошибка подключения: ${e.message}")
            } finally {
                binding.btnLogin.isEnabled = true
            }
        }
    }

    private fun showError(msg: String) {
        binding.tvError.text = msg
        binding.tvError.visibility = View.VISIBLE
    }
}
