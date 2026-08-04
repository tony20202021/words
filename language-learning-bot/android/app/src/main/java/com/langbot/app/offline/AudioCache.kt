package com.langbot.app.offline

import android.content.Context
import com.langbot.app.network.BLSClient
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * On-disk cache of pronunciation sounds (mp3) so audio plays while offline.
 * Files live under `filesDir/sounds/`. Dependency-free (HttpURLConnection).
 */
object AudioCache {
    private lateinit var appCtx: Context

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

    /** Download one sound into the cache if missing. Returns true if available locally afterwards. */
    fun ensure(path: String): Boolean {
        if (!ready() || path.isBlank()) return false
        val f = File(dir(), fileNameFor(path))
        if (f.exists() && f.length() > 0) return true
        return runCatching {
            val conn = (URL(BLSClient.soundUrl(path)).openConnection() as HttpURLConnection).apply {
                connectTimeout = 15000
                readTimeout = 30000
                requestMethod = "GET"
            }
            try {
                val tmp = File(f.absolutePath + ".tmp")
                conn.inputStream.use { input -> tmp.outputStream().use { out -> input.copyTo(out) } }
                if (tmp.length() > 0) tmp.renameTo(f) else tmp.delete()
            } finally {
                conn.disconnect()
            }
            f.exists() && f.length() > 0
        }.getOrDefault(false)
    }

    /** Best-effort prefetch of many sounds. Call from a background coroutine (blocks per file). */
    fun prefetch(paths: List<String>) {
        if (!ready()) return
        for (p in paths) if (p.isNotBlank()) ensure(p)
    }

    /** Number of cached sound files (excludes in-flight `.tmp`). */
    fun cachedCount(): Int =
        if (ready()) (dir().listFiles()?.count { it.extension != "tmp" } ?: 0) else 0
}
