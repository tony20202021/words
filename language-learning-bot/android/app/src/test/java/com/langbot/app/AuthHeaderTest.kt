package com.langbot.app

import com.langbot.app.network.BLSClient
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import java.util.concurrent.TimeUnit
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/**
 * Токен уходит в каждом запросе, а отказ сервера его сбрасывает.
 *
 * Прежде клиент представлялся одним user_id, а знание чужого id и было
 * доступом. Теперь BLS в режиме принуждения без токена отвечает 401 — и если
 * заголовок перестанет прикладываться, приложение молча перестанет работать.
 */
@RunWith(RobolectricTestRunner::class)
class AuthHeaderTest {

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
        BLSClient.onUnauthorized = null
        runCatching { server.shutdown() }
    }

    private fun requestHeader(): String? {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"version":"x","version_code":1}"""))
        runBlocking { BLSClient.api.getVersion() }
        return server.takeRequest(5, TimeUnit.SECONDS)?.getHeader("Authorization")
    }

    @Test
    fun token_is_sent_as_bearer() {
        BLSClient.token = "u1.sig"
        assertEquals("Bearer u1.sig", requestHeader())
    }

    @Test
    fun no_token_no_header() {
        BLSClient.token = null
        assertNull(requestHeader())
    }

    @Test
    fun empty_token_sends_nothing() {
        // "" — вход новым приложением без токена от сервера (см. UserPrefs.getToken).
        BLSClient.token = ""
        assertNull(requestHeader())
    }

    @Test
    fun rejection_by_server_is_reported() {
        var called = false
        BLSClient.onUnauthorized = { called = true }
        BLSClient.token = "revoked"
        server.enqueue(MockResponse().setResponseCode(401))
        runBlocking { BLSClient.api.getVersion() }
        assertTrue("401 должен сбрасывать токен", called)
    }
}
