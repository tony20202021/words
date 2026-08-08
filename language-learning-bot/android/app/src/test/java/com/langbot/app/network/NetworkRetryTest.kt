package com.langbot.app.network

import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * Быстрый провал вместо зависания.
 *
 * Симптом, с которого всё началось: сеть есть, а до сервера не достучаться —
 * нажатие «Дальше» или «Начать заново» выглядело как «ничего не происходит».
 * Клиент ждал connectTimeout=15 с плюс внутренний повтор OkHttp, и только потом
 * уходил в офлайн.
 */
class NetworkRetryTest {

    private lateinit var server: MockWebServer

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() = server.shutdown()

    @Test
    fun first_attempt_timeout_is_short_so_a_dead_server_fails_fast() {
        val first = BLSClient.CONNECT_TIMEOUTS_MS.first()
        assertTrue(
            "первая попытка обязана быть короткой, иначе экран замирает: ${first}мс",
            first <= 3_000
        )
    }

    @Test
    fun timeouts_grow_with_each_attempt() {
        val t = BLSClient.CONNECT_TIMEOUTS_MS
        assertTrue("нужно несколько попыток, а не одна", t.size >= 2)
        assertEquals("таймауты должны расти", t.sortedBy { it }, t)
    }

    @Test
    fun succeeds_on_the_first_attempt_without_bothering_the_user() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"acks":[]}"""))
        val seen = mutableListOf<NetworkRetry.Status>()

        val resp = NetworkRetry.call(onStatus = { seen.add(it) }) { api ->
            api.postResultsBatch(ResultsBatchRequest("u", "l", emptyList()))
        }

        assertNotNull(resp)
        assertEquals("лишних попыток быть не должно", 1, seen.size)
        assertEquals(1, seen.first().attempt)
    }

    @Test
    fun returns_null_after_every_attempt_failed_so_the_caller_goes_offline() = runBlocking {
        // Сервер закрыт: подключение отвергается сразу на всех попытках.
        server.shutdown()
        val seen = mutableListOf<NetworkRetry.Status>()

        val resp = NetworkRetry.call(onStatus = { seen.add(it) }) { api ->
            api.postResultsBatch(ResultsBatchRequest("u", "l", emptyList()))
        }

        assertNull("исчерпав попытки, возвращаем null — это сигнал уйти в офлайн", resp)
        assertEquals("должны быть использованы все попытки",
            BLSClient.attemptCount, seen.size)
    }

    @Test
    fun retries_after_a_failure_and_succeeds_on_a_later_attempt() = runBlocking {
        // Первый запрос обрывается, второй проходит.
        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AT_START))
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"acks":[]}"""))
        val seen = mutableListOf<NetworkRetry.Status>()

        val resp = NetworkRetry.call(onStatus = { seen.add(it) }) { api ->
            api.postResultsBatch(ResultsBatchRequest("u", "l", emptyList()))
        }

        assertNotNull("вторая попытка обязана вытянуть", resp)
        assertEquals(2, seen.size)
        assertNotNull("во второй статус должна попасть причина первой неудачи",
            seen[1].lastError)
    }

    @Test
    fun status_explains_what_is_happening_and_how_long_to_wait() {
        val first = NetworkRetry.Status(1, 3, 2_000, null)
        assertEquals("Соединяемся…", first.message)

        val second = NetworkRetry.Status(2, 3, 6_000, "ConnectException: refused")
        assertTrue(second.message, second.message.contains("Попытка 2 из 3"))
        assertTrue("пользователь должен понимать, сколько ждать",
            second.message.contains("6 с"))
        assertTrue(second.message, second.message.contains("нестабильно"))
    }

    @Test
    fun worst_case_wait_stays_bounded() {
        // Раньше ожидание было неограниченным по ощущениям: 15 с таймаут плюс
        // повтор внутри OkHttp. Теперь суммарное время предсказуемо и озвучено.
        assertTrue(
            "суммарное ожидание не должно превышать полминуты: ${NetworkRetry.worstCaseSeconds} с",
            NetworkRetry.worstCaseSeconds <= 30
        )
    }
}
