package com.langbot.app

import android.text.Spanned
import android.text.style.URLSpan
import android.widget.TextView
import com.langbot.app.network.BLSClient
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner

/**
 * Ссылка на источники данных в «Помощи» нажимается.
 *
 * Данные Викисловаря, wordfreq и FrequencyWords идут по лицензии CC BY-SA 4.0:
 * источник нужно указать там, где данные показываются. Отдельного «о
 * программе» в приложении нет — есть «Помощь» (владелец, 20.11.2026). Текст
 * справки приходит с сервера, а нажимаемой ссылка становится только здесь.
 */
@RunWith(RobolectricTestRunner::class)
class HelpSourcesLinkTest {

    private lateinit var server: MockWebServer
    private val url = "https://github.com/tony20202021/words/blob/main/DATA_SOURCES.md"

    @Before
    fun setUp() {
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse =
                if (request.path.orEmpty().startsWith("/help"))
                    MockResponse().setBody("""{"text":"Источники данных: подробно — $url"}""")
                else MockResponse().setResponseCode(404)
        }
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() { runCatching { server.shutdown() } }

    @Test
    fun the_data_sources_address_in_help_is_a_link() {
        val a = Robolectric.buildActivity(HelpActivity::class.java).setup().get()
        val tv = a.findViewById<TextView>(R.id.tvHelp)
        Screenshots.pumpUntil("справка пришла") { tv.text.contains("Источники") }
        val spans = (tv.text as? Spanned)?.getSpans(0, tv.text.length, URLSpan::class.java).orEmpty()
        assertTrue("адрес источников в справке не ссылка: ${tv.text}",
            spans.any { it.url == url })
    }
}
