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
 * «Получать сообщения» — переключатель в приложении.
 *
 * Настройка жила только в телеграм-боте и на сайте. У второго пользователя она
 * оказалась выключена, и он не получал ни напоминаний, ни объявлений — а
 * включить её из приложения было нечем: пункта там не было вовсе. Человек не
 * мог ни узнать причину, ни устранить её.
 *
 * Второй сторож здесь важнее первого. На сервере эта настройка включена по
 * умолчанию, а экран показывал отсутствующее значение выключенным: человек
 * читал бы «Получать сообщения: нет» там, где на деле «да», и полез бы
 * включать уже включённое.
 */
@RunWith(RobolectricTestRunner::class)
class ReceiveMessagesToggleTest {

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
        // Экран обязан быть разрушен: оставленный живым, он ломает соседние
        // проверки в общем прогоне — такое уже случалось.
        controller?.let { runCatching { it.pause().stop().destroy() } }
        runCatching { server.shutdown() }
    }

    private fun open(): SettingsActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(),
                            SettingsActivity::class.java)
            .putExtra("language_id", "lang-1")
            .putExtra("language_name", "Английский")
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
    fun the_setting_is_present_on_the_screen() {
        assertTrue("«receive_messages» не добавлен в список переключателей",
            SettingsActivity.TOGGLE_SETTINGS.containsKey("receive_messages"))
        assertEquals("Получать сообщения",
            SettingsActivity.TOGGLE_SETTINGS["receive_messages"])

        val a = open()
        val подписи = mutableListOf<String>()
        fun walk(v: View) {
            if (v is android.widget.TextView && v !is Switch) подписи.add(v.text.toString())
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(container(a))
        assertTrue("подписи «Получать сообщения» на экране нет: $подписи",
            подписи.any { it == "Получать сообщения" })
    }

    @Test
    fun a_missing_value_is_shown_as_enabled_because_the_server_defaults_to_yes() {
        /*
         * Главный сторож. Сервер держит эту настройку включённой по умолчанию
         * (DEFAULTS в settings_service.py). Пустой ответ значит «по умолчанию»,
         * а не «выключено».
         */
        settingsBody = "{}"
        val a = open()

        assertTrue("отсутствующее значение показано выключенным — человек " +
            "прочтёт «нет» там, где на деле «да»",
            switchFor(a, "receive_messages").isChecked)
    }

    @Test
    fun an_explicit_no_is_shown_as_disabled() {
        /* Опора против обратной ошибки: умолчание не должно затирать ответ. */
        settingsBody = """{"receive_messages": false}"""
        val a = open()

        assertFalse("явное «нет» показано включённым",
            switchFor(a, "receive_messages").isChecked)
    }

    @Test
    fun an_explicit_yes_is_shown_as_enabled() {
        settingsBody = """{"receive_messages": true}"""
        val a = open()

        assertTrue(switchFor(a, "receive_messages").isChecked)
    }

    @Test
    fun other_toggles_without_a_default_stay_off_when_absent() {
        /*
         * Опора против перегиба: умолчание задано только для тех настроек,
         * у которых оно действительно «включено» на сервере. Остальные при
         * пустом ответе обязаны остаться выключенными, иначе экран начнёт
         * врать уже про них.
         */
        settingsBody = "{}"
        val a = open()

        assertFalse("«show_debug»-подобные настройки не должны включаться сами",
            switchFor(a, "random_pick_mode").isChecked)
    }
}
