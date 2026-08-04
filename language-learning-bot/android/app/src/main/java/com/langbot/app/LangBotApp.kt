package com.langbot.app

import android.app.Application
import android.net.ConnectivityManager
import android.net.Network
import com.langbot.app.network.BLSClient
import com.langbot.app.offline.AudioCache
import com.langbot.app.offline.OfflineCache
import com.langbot.app.offline.OutboxSync
import com.langbot.app.prefs.UserPrefs
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

/**
 * Application entry point. Wires up the offline cache and an always-on network
 * watcher that flushes the results outbox whenever connectivity returns — so
 * results accumulated offline sync up on their own, even without opening a screen.
 */
class LangBotApp : Application() {

    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()

        OfflineCache.init(this)
        AudioCache.init(this)

        // BLSClient is normally initialised in LoginActivity; do it here too so the
        // background flush can reach the server before any activity is opened.
        if (!BLSClient.isInitialized) {
            BLSClient.init(UserPrefs.getBlsUrl(this))
        }

        registerNetworkFlush()

        // Best-effort flush at startup in case results are already pending.
        appScope.launch { runCatching { OutboxSync.flush() } }
    }

    private fun registerNetworkFlush() {
        val cm = getSystemService(ConnectivityManager::class.java) ?: return
        runCatching {
            cm.registerDefaultNetworkCallback(object : ConnectivityManager.NetworkCallback() {
                override fun onAvailable(network: Network) {
                    appScope.launch { runCatching { OutboxSync.flush() } }
                }
            })
        }
    }
}
