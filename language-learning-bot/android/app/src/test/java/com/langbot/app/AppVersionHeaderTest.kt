package com.langbot.app

import com.langbot.app.network.BLSClient
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/**
 * Приложение сообщает серверу свою версию.
 *
 * Владелец спросил, как узнать, какая сборка стоит у пользователя. Узнать было
 * нельзя: наружу приложение представлялось только как «okhttp/4.12.0» — это
 * версия сетевой библиотеки, одинаковая у всех сборок от первой до нынешней.
 * Своей версии оно не сообщало нигде.
 *
 * Теперь версия идёт заголовком в каждом запросе и попадает в журналы nginx
 * сама. Оговорка, которая кодом не чинится: так видно только тех, кто
 * обновился ПОСЛЕ этой правки — сидящему на старой сборке нечем о себе
 * сообщить.
 */
@RunWith(RobolectricTestRunner::class)
class AppVersionHeaderTest {

    private lateinit var server: MockWebServer

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() {
        BLSClient.token = null
        runCatching { server.shutdown() }
    }

    /**
     * Запрос, который приложение действительно отправило.
     *
     * Ожидание со сроком, а не takeRequest() без аргументов: тот блокируется
     * навсегда, и если запрос не ушёл вовсе, падает не проверка, а весь
     * прогон. 07.11.2026 так и вышло — полтора часа на одном методе, потому
     * что токен в заголовке был русскими буквами и okhttp отказался его
     * отправлять, а runCatching съел исключение.
     */
    private fun спросить(): okhttp3.mockwebserver.RecordedRequest {
        server.enqueue(MockResponse().setBody("""{"version":"x","version_code":1}"""))
        val ошибка = runBlocking {
            runCatching { BLSClient.api.getVersion() }.exceptionOrNull()
        }
        val req = server.takeRequest(5, TimeUnit.SECONDS)
        assertNotNull("приложение не отправило запрос вовсе" +
            (ошибка?.let { ": ${it::class.simpleName}: ${it.message}" } ?: ""), req)
        return req!!
    }

    @Test
    fun every_request_tells_the_server_which_version_asks() {
        val версия = спросить().getHeader("X-App-Version")
        assertNotNull("запрос не называет версию приложения", версия)
        assertEquals(BuildConfig.VERSION_NAME, версия)
    }

    @Test
    fun the_header_is_a_real_version_and_not_a_placeholder() {
        /*
         * Опора против заглушки. BuildConfig собирается плагином, и если
         * buildConfig в buildFeatures выключить, поле станет недоступно или
         * пустым — заголовок при этом останется, а толку от него не будет.
         */
        val версия = спросить().getHeader("X-App-Version") ?: ""
        assertTrue("версия не похожа на номер: «$версия»",
            Regex("""^\d+\.\d+\.\d+$""").matches(версия))
    }

    @Test
    fun a_request_without_a_token_still_carries_the_version() {
        /*
         * Версия нужна и до входа: человек, у которого приложение не может
         * подключиться, запросы всё равно шлёт — и именно про него важнее
         * всего знать, какая у него сборка.
         */
        BLSClient.token = null
        assertNotNull(спросить().getHeader("X-App-Version"))
    }

    @Test
    fun the_token_still_goes_out_alongside_the_version() {
        /* Опора: добавляя заголовок, легко затереть сборку запроса целиком. */
        // Токен только латиницей: значения заголовков HTTP обязаны быть
        // ASCII, и okhttp на русские буквы бросает IllegalArgumentException
        // ещё до отправки.
        BLSClient.token = "test-token-42"
        val req = спросить()
        assertEquals("Bearer test-token-42", req.getHeader("Authorization"))
        assertNotNull(req.getHeader("X-App-Version"))
    }
}
