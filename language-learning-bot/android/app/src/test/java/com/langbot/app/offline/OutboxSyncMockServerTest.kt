package com.langbot.app.offline

import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/**
 * Drives OutboxSync.flush against a stub BLS.
 *
 * The contract that matters: an event leaves the outbox only when the server
 * acknowledges it ("ok" or "duplicate"). Anything else — HTTP error, unknown
 * status, no network — must keep the event queued, otherwise a study result is
 * silently lost.
 */
@RunWith(RobolectricTestRunner::class)
class OutboxSyncMockServerTest {

    private lateinit var server: MockWebServer
    private val u = "user-1"
    private val l = "lang-1"

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }

        server = MockWebServer()
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun flush_posts_to_results_batch_and_drops_acked_events() = runBlocking {
        OfflineCache.addResult(u, l, "w1", "know")
        OfflineCache.addResult(u, l, "w2", "dont_know")
        val ids = OfflineCache.loadOutbox().map { it.event_id }

        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """{"acks":[{"event_id":"${ids[0]}","status":"ok"},
                            {"event_id":"${ids[1]}","status":"ok"}]}"""
            )
        )

        OutboxSync.flush()

        val req = server.takeRequest()
        assertTrue(req.path!!, req.path!!.endsWith("/results/batch"))
        assertEquals("POST", req.method)
        val body = req.body.readUtf8()
        assertTrue(body, body.contains("\"user_id\":\"$u\""))
        assertTrue(body, body.contains("\"w1\""))
        assertTrue(body, body.contains("\"w2\""))

        assertEquals("acked events must leave the outbox", 0, OfflineCache.pendingCount())
    }

    @Test
    fun flush_treats_duplicate_as_acked() = runBlocking {
        OfflineCache.addResult(u, l, "w1", "know")
        val id = OfflineCache.loadOutbox().first().event_id

        server.enqueue(
            MockResponse().setResponseCode(200)
                .setBody("""{"acks":[{"event_id":"$id","status":"duplicate"}]}""")
        )

        OutboxSync.flush()
        assertEquals("duplicate means the server already has it", 0, OfflineCache.pendingCount())
    }

    @Test
    fun flush_keeps_events_when_the_server_errors() = runBlocking {
        OfflineCache.addResult(u, l, "w1", "know")
        server.enqueue(MockResponse().setResponseCode(500))

        OutboxSync.flush()
        assertEquals("a 500 must not lose the result", 1, OfflineCache.pendingCount())
    }

    @Test
    fun flush_keeps_events_the_server_did_not_acknowledge() = runBlocking {
        OfflineCache.addResult(u, l, "w1", "know")
        OfflineCache.addResult(u, l, "w2", "know")
        val ids = OfflineCache.loadOutbox().map { it.event_id }

        // Only the first event is acked; the second must stay queued.
        server.enqueue(
            MockResponse().setResponseCode(200)
                .setBody("""{"acks":[{"event_id":"${ids[0]}","status":"ok"}]}""")
        )

        OutboxSync.flush()

        val left = OfflineCache.loadOutbox()
        assertEquals(1, left.size)
        assertEquals(ids[1], left.first().event_id)
    }

    @Test
    fun flush_ignores_unknown_ack_statuses() = runBlocking {
        OfflineCache.addResult(u, l, "w1", "know")
        val id = OfflineCache.loadOutbox().first().event_id

        server.enqueue(
            MockResponse().setResponseCode(200)
                .setBody("""{"acks":[{"event_id":"$id","status":"rejected"}]}""")
        )

        OutboxSync.flush()
        assertEquals("only ok/duplicate may drop an event", 1, OfflineCache.pendingCount())
    }

    @Test
    fun flush_on_an_empty_outbox_makes_no_request() = runBlocking {
        OutboxSync.flush()
        assertEquals(0, server.requestCount)
    }

    @Test
    fun flush_groups_events_per_user_and_language() = runBlocking {
        OfflineCache.addResult(u, l, "w1", "know")
        OfflineCache.addResult(u, "lang-2", "w2", "know")

        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"acks":[]}"""))
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"acks":[]}"""))

        OutboxSync.flush()

        assertEquals("one request per (user, language) pair", 2, server.requestCount)
        assertEquals("nothing acked — everything stays", 2, OfflineCache.pendingCount())
    }
}
