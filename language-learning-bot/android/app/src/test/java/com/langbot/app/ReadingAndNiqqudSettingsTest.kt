package com.langbot.app

import android.content.Intent
import android.view.View
import android.view.ViewGroup
import android.widget.Switch
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.android.controller.ActivityController

/**
 * Две новые галки: «предложения для чтения» и «упрощённое написание».
 *
 * Обе на сервере включены по умолчанию (DEFAULTS в settings_service.py). Это и
 * есть главная опасность: экран показывает отсутствующее значение выключенным,
 * и человек читает «нет» там, где на деле «да». Ровно так уже вышло с
 * «Получать сообщения» — настройка работала, а экран утверждал обратное, и
 * понять причину было нельзя.
 */
@RunWith(RobolectricTestRunner::class)
class ReadingAndNiqqudSettingsTest {

    private lateinit var server: MockWebServer
    @Volatile private var settingsBody = "{}"
    private var controller: ActivityController<SettingsActivity>? = null

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        UserPrefs.saveUserId(ctx, "user-1")
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse =
                MockResponse().setResponseCode(200).setBody(settingsBody)
        }
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() {
        controller?.let { runCatching { it.pause().stop().destroy() } }
        runCatching { server.shutdown() }
    }

    private fun open(): SettingsActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(),
                            SettingsActivity::class.java)
            .putExtra("language_id", "lang-1")
            .putExtra("language_name", "Иврит")
        val c = Robolectric.buildActivity(SettingsActivity::class.java, intent).setup()
        controller = c
        val a = c.get()
        Screenshots.pumpUntil("настройки отрисованы") {
            container(a).childCount > 0
        }
        return a
    }

    private fun container(a: SettingsActivity): ViewGroup =
        a.findViewById(R.id.settingsContainer)

    private fun switches(a: SettingsActivity): List<Switch> {
        val out = mutableListOf<Switch>()
        fun walk(v: View) {
            if (v is Switch) out.add(v)
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(container(a))
        return out
    }

    private fun switchFor(a: SettingsActivity, key: String): Switch {
        val место = SettingsActivity.TOGGLE_SETTINGS.keys.toList().indexOf(key)
        assertTrue("переключателя «$key» нет в списке", место >= 0)
        return switches(a)[место]
    }

    @Test
    fun both_settings_are_listed_on_the_screen() {
        assertEquals("Показывать предложения для чтения",
            SettingsActivity.TOGGLE_SETTINGS["show_reading"])
        assertEquals("Показывать упрощённое написание",
            SettingsActivity.TOGGLE_SETTINGS["show_simplified"])

        val a = open()
        val подписи = mutableListOf<String>()
        fun walk(v: View) {
            if (v is android.widget.TextView && v !is Switch) подписи.add(v.text.toString())
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(container(a))
        assertTrue("подписи про предложения для чтения на экране нет: $подписи",
            подписи.any { it == "Показывать предложения для чтения" })
        assertTrue("подписи про упрощённое написание на экране нет: $подписи",
            подписи.any { it == "Показывать упрощённое написание" })
    }

    @Test
    fun missing_values_are_shown_as_enabled_because_the_server_defaults_to_yes() {
        settingsBody = "{}"
        val a = open()
        assertTrue("«предложения для чтения» показаны выключенными, хотя на " +
            "сервере по умолчанию включены",
            switchFor(a, "show_reading").isChecked)
        assertTrue("«упрощённое написание» показано выключенным, хотя на " +
            "сервере по умолчанию включено",
            switchFor(a, "show_simplified").isChecked)
    }

    @Test
    fun an_explicit_no_is_shown_as_disabled() {
        /* Опора против обратной ошибки: умолчание не должно затирать ответ. */
        settingsBody = """{"show_reading": false, "show_simplified": false}"""
        val a = open()
        assertFalse("явное «нет» для предложений показано включённым",
            switchFor(a, "show_reading").isChecked)
        assertFalse("явное «нет» для упрощённого написания показано включённым",
            switchFor(a, "show_simplified").isChecked)
    }
}
