package com.langbot.app.offline

import android.content.Context
import android.util.Log
import com.langbot.app.network.BLSClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.ConcurrentHashMap

/**
 * On-disk cache of pronunciation sounds (mp3) so audio plays while offline.
 * Files live under `filesDir/sounds/`. Downloads use HttpURLConnection.
 *
 * Prefetch runs on a process-lifetime scope, NOT on an Activity scope: a bundle
 * carries ~200 sounds and leaving StudyActivity used to cancel the download
 * halfway, leaving most words silent offline.
 */
object AudioCache {
    private const val TAG = "AudioCache"

    /** Concurrent downloads. Files are small (~3 KB); the win is round-trip overlap. */
    private const val PARALLELISM = 6

    private lateinit var appCtx: Context

    /** Survives Activity teardown — prefetch must finish even if the user navigates away. */
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    /** Paths currently being downloaded, so overlapping prefetches don't duplicate work. */
    private val inFlight: MutableSet<String> = ConcurrentHashMap.newKeySet()

    fun init(ctx: Context) { appCtx = ctx.applicationContext }
    private fun ready() = ::appCtx.isInitialized

    private fun dir(): File = File(appCtx.filesDir, "sounds").apply { if (!exists()) mkdirs() }

    /** Deterministic, filesystem-safe filename for a server sound path. Pure (no I/O). */
    fun fileNameFor(path: String): String =
        path.trim().trimStart('/').replace(Regex("[^A-Za-z0-9._-]"), "_")

    /** Local cached file for a sound path, or null if not cached yet. */
    fun cachedFile(path: String): File? {
        if (!ready() || path.isBlank()) return null
        val f = File(dir(), fileNameFor(path))
        return if (f.exists() && f.length() > 0) f else null
    }

    /**
     * Откуда играть звук: сначала кеш на диске, потом сеть.
     *
     * Одно место на всех, кто заводит MediaPlayer (кнопки карточки и цепочка
     * пик-режима): офлайн они молчали ровно потому, что тянули звук по сети,
     * хотя файлы уже лежали на диске.
     */
    fun sourceFor(path: String): String =
        cachedFile(path)?.absolutePath ?: BLSClient.soundUrl(path)

    /** Download one sound into the cache if missing. Returns true if available locally afterwards. */
    fun ensure(path: String): Boolean {
        if (!ready() || path.isBlank()) return false
        val f = File(dir(), fileNameFor(path))
        if (f.exists() && f.length() > 0) return true
        val url = BLSClient.soundUrl(path)
        return runCatching {
            val conn = (URL(url).openConnection() as HttpURLConnection).apply {
                connectTimeout = 15000
                readTimeout = 30000
                requestMethod = "GET"
            }
            try {
                val code = conn.responseCode
                if (code !in 200..299) {
                    Log.w(TAG, "download failed HTTP $code for $url")
                    return false
                }
                // Write to a temp file first so a partial download never looks cached.
                val tmp = File(f.absolutePath + ".tmp")
                conn.inputStream.use { input -> tmp.outputStream().use { out -> input.copyTo(out) } }
                if (tmp.length() > 0) tmp.renameTo(f) else tmp.delete()
            } finally {
                conn.disconnect()
            }
            f.exists() && f.length() > 0
        }.getOrElse { e ->
            Log.w(TAG, "download error for $url: ${e.javaClass.simpleName}: ${e.message}")
            false
        }
    }

    /**
     * Fire-and-forget prefetch of many sounds, in parallel, on the process scope.
     * Returns immediately; safe to call repeatedly (already-cached and in-flight
     * paths are skipped).
     */
    fun prefetch(paths: List<String>) {
        if (!ready()) return
        val todo = paths
            .filter { it.isNotBlank() && cachedFile(it) == null }
            .distinct()
            .filter { inFlight.add(it) }
        if (todo.isEmpty()) return

        scope.launch {
            var ok = 0
            var failed = 0
            runCatching {
                val gate = Semaphore(PARALLELISM)
                coroutineScope {
                    todo.map { p ->
                        async {
                            try {
                                gate.withPermit { ensure(p) }
                            } finally {
                                inFlight.remove(p)
                            }
                        }
                    }.forEach { if (it.await()) ok++ else failed++ }
                }
            }.onFailure { e ->
                Log.w(TAG, "prefetch aborted: ${e.javaClass.simpleName}: ${e.message}")
            }
            todo.forEach { inFlight.remove(it) }
            Log.i(TAG, "prefetch finished: requested=${todo.size} ok=$ok failed=$failed cached=${cachedCount()}")
        }
    }

    /** Number of cached sound files (excludes in-flight `.tmp`). */
    fun cachedCount(): Int =
        if (ready()) (dir().listFiles()?.count { it.extension != "tmp" } ?: 0) else 0
}
