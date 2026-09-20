package com.langbot.app

import android.content.Intent
import android.view.View
import android.view.ViewGroup
import android.widget.Switch
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import com.langbot.app.offline.OfflineCache
import com.langbot.app.offline.StoredBundle
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
import org.robolectric.annotation.GraphicsMode

/**
 * Настройки без сети.
 *
 * Экран целиком зависит от BLS, и раньше без сети показывал одну надпись «нет
 * связи» — хотя сервер присылает настройки вместе с офлайн-партией, и телефон
 * их просто выбрасывал. Теперь они сохраняются и показываются только для
 * чтения: менять их без сети нельзя, состав слов пересчитывает сервер.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class SettingsOfflineTest {

    private lateinit var server: MockWebServer
    @Volatile private var settingsCode = 200

    private val cachedSettings = mapOf<String, Any>(
        "use_check_date" to false,
        "skip_marked" to true,
        "show_big" to true,
        "start_word" to 1234.0,          // Gson отдаёт числа как Double
        "quiz_options_count" to 4.0,
    )

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        UserPrefs.saveUserId(ctx, "user-1")
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse =
                if (settingsCode == 200)
                    MockResponse().setResponseCode(200).setBody(
                        """{"use_check_date": true, "skip_marked": false, "start_word": 7}""")
                else MockResponse().setResponseCode(settingsCode)
        }
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() {
        runCatching { server.shutdown() }
        OfflineCache.saveBundle(StoredBundle("user-1", "lang-1", emptyList()))
    }

    private fun open(): SettingsActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), SettingsActivity::class.java)
            .putExtra("language_id", "lang-1")
            .putExtra("language_name", "Иврит")
        val a = Robolectric.buildActivity(SettingsActivity::class.java, intent).setup().get()
        Screenshots.pumpUntil("настройки отрисованы") {
            container(a).childCount > 0
        }
        return a
    }

    private fun container(a: SettingsActivity): ViewGroup =
        a.findViewById(R.id.settingsContainer)

    private fun <T : View> collect(root: View, type: Class<T>): List<T> {
        val out = mutableListOf<T>()
        fun walk(v: View) {
            if (type.isInstance(v)) out.add(type.cast(v)!!)
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(root)
        return out
    }

    private fun allText(a: SettingsActivity): String =
        collect(container(a), TextView::class.java).joinToString("\n") { it.text.toString() }

    private fun cacheBundleWithSettings() {
        OfflineCache.saveBundle(
            StoredBundle("user-1", "lang-1", emptyList(), cursor = 0, settings = cachedSettings))
    }

    @Test
    fun without_network_the_saved_settings_are_shown() {
        cacheBundleWithSettings()
        settingsCode = 500
        val a = open()

        val text = allText(a)
        assertTrue("нет объяснения, откуда значения: $text",
            text.contains("из сохранённой офлайн-партии"))
        assertTrue("не сказано, что менять нельзя: $text", text.contains("без сети нельзя"))
        assertTrue("не показаны переключатели: $text", text.contains("Учитывать дату проверки"))
        assertTrue("не показано числовое значение 1234: $text", text.contains("1234"))
    }

    @Test
    fun the_saved_settings_are_shown_as_they_were_and_cannot_be_changed() {
        cacheBundleWithSettings()
        settingsCode = 500
        val a = open()

        val switches = collect(container(a), Switch::class.java)
        assertEquals("переключателей должно быть столько же, сколько в списке",
            SettingsActivity.TOGGLE_SETTINGS.size, switches.size)
        assertTrue("без сети переключатели обязаны быть заблокированы",
            switches.none { it.isEnabled })

        // Значения — из сохранённой партии, а не значения по умолчанию.
        val rows = SettingsActivity.TOGGLE_SETTINGS.keys.toList()
        assertFalse("«учитывать дату» должно быть выключено, как в партии",
            switches[rows.indexOf("use_check_date")].isChecked)
        assertTrue("«пропускать исключённые» должно быть включено, как в партии",
            switches[rows.indexOf("skip_marked")].isChecked)

        // Числовые строки без сети не открывают окно ввода.
        val clickable = collect(container(a), ViewGroup::class.java).filter { it.isClickable }
        assertTrue("числовые настройки без сети не должны нажиматься: $clickable",
            clickable.isEmpty())
    }

    @Test
    fun without_a_saved_bundle_the_screen_still_says_there_is_no_connection() {
        OfflineCache.saveBundle(StoredBundle("user-1", "lang-1", emptyList()))
        settingsCode = 500
        val a = open()

        val text = allText(a)
        assertTrue("нет сообщения об отсутствии связи: $text", text.contains("Нет связи"))
        assertTrue("показывать нечего, а переключатели нарисованы: $text",
            collect(container(a), Switch::class.java).isEmpty())
    }

    @Test
    fun with_network_the_settings_come_from_the_server_and_stay_editable() {
        cacheBundleWithSettings()
        settingsCode = 200
        val a = open()

        val switches = collect(container(a), Switch::class.java)
        assertTrue("с сетью переключатели обязаны работать", switches.all { it.isEnabled })
        val rows = SettingsActivity.TOGGLE_SETTINGS.keys.toList()
        assertTrue("значение должно быть с сервера, а не из сохранённой партии",
            switches[rows.indexOf("use_check_date")].isChecked)
        assertFalse("значение из партии перебило серверное",
            switches[rows.indexOf("skip_marked")].isChecked)
        // Проверяем именно плашку, а не слово «офлайн»: оно есть и в подписи
        // настройки «Слов в офлайн-партии», которая видна всегда.
        assertFalse("плашки об отсутствии связи быть не должно",
            allText(a).contains("Нет связи с сервером"))
    }
}
