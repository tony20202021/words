package com.langbot.app.network

import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertNotSame
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Какой клиент достаётся обычному вызову `BLSClient.api`.
 *
 * Короткий таймаут имеет смысл только там, где за ним стоит следующая попытка:
 * это первая попытка NetworkRetry. Общий клиент раньше был именно ею — connect
 * 2 с, read 4 с — и им пользовались все экраны без эскалации. Самое заметное
 * последствие: графики статистики на холодном кеше сервера генерируются
 * секундами, ответ не успевал прийти, исключение проглатывалось, и картинки
 * молча пропадали с экрана — вплоть до «Нет данных для графиков» при живом
 * сервере с данными.
 */
class BLSClientTimeoutsTest {

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
    fun default_client_is_separate_from_the_retry_ladder() {
        // У общего клиента своё сочетание таймаутов, и ни одна ступень лестницы
        // повторов не подходит целиком: у первой слишком короткий read, у
        // последней слишком длинный connect. Проверяем именно это — что он не
        // равен ни одной из них; сами значения проверяются тестами ниже.
        for (attempt in 0 until BLSClient.attemptCount) {
            assertNotSame(
                "общий клиент совпал со ступенью повторов №$attempt — " +
                    "значит один из двух таймаутов взят не тот",
                BLSClient.apiForAttempt(attempt), BLSClient.api,
            )
        }
    }

    @Test
    fun default_client_gives_up_fast_when_there_is_nowhere_to_connect() = runBlocking {
        // Connect и read отвечают на разные вопросы. Connect — «есть ли сеть», и
        // ответ нужен быстро: ради этого в приложении есть офлайн-режим. Взяв
        // самую терпеливую ступень целиком, мы заставили бы человека ждать 15
        // секунд, чтобы узнать, что сети нет.
        val dead = MockWebServer()
        dead.start()
        val deadUrl = dead.url("/").toString().trimEnd('/')
        dead.shutdown()
        BLSClient.init(deadUrl)

        val startedAt = System.currentTimeMillis()
        runCatching {
            BLSClient.api.postResultsBatch(ResultsBatchRequest("u", "l", emptyList()))
        }
        val elapsed = System.currentTimeMillis() - startedAt

        assertTrue(
            "на мёртвый адрес ушло $elapsed мс — офлайн должен обнаруживаться быстро",
            elapsed < 5_000,
        )
    }

    @Test
    fun slow_but_alive_server_is_not_dropped_by_the_default_client() = runBlocking {
        // Сервер жив, но отвечает медленно — так выглядит генерация графиков.
        // Пауза больше read timeout первой попытки (4 с) и много меньше read
        // timeout терпеливого клиента (30 с).
        server.enqueue(
            MockResponse().setResponseCode(200).setBody("""{"acks":[]}""")
                .setBodyDelay(SLOW_MS, TimeUnit.MILLISECONDS)
        )

        val resp = BLSClient.api.postResultsBatch(ResultsBatchRequest("u", "l", emptyList()))

        assertTrue("медленный, но живой ответ обязан дойти", resp.isSuccessful)
    }

    @Test
    fun first_attempt_client_still_gives_up_quickly_on_the_same_slow_answer() = runBlocking {
        // Обратная сторона: эскалацию ломать нельзя. Первая попытка обязана
        // оборваться быстро — ради этого NetworkRetry и существует.
        server.enqueue(
            MockResponse().setResponseCode(200).setBody("""{"acks":[]}""")
                .setBodyDelay(SLOW_MS, TimeUnit.MILLISECONDS)
        )

        val startedAt = System.currentTimeMillis()
        val failure = runCatching {
            BLSClient.apiForAttempt(0)
                .postResultsBatch(ResultsBatchRequest("u", "l", emptyList()))
        }.exceptionOrNull()
        val elapsed = System.currentTimeMillis() - startedAt

        assertTrue("короткая попытка обязана оборваться, а не ждать", failure is IOException)
        assertTrue("оборвалась через $elapsed мс — это уже не «быстро»", elapsed < SLOW_MS)
    }

    private companion object {
        /**
         * Дольше read timeout первой попытки (4 с), сильно короче терпеливого (30 с).
         *
         * Ровно 5 с брать не стоит: это настенное время, и оно уходит в каждый
         * прогон всего набора дважды. 4.5 с так же надёжно перекрывает 4 с.
         */
        const val SLOW_MS = 4_500L
    }
}
