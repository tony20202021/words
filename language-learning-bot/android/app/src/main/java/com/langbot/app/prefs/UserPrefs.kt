package com.langbot.app.prefs

import android.content.Context

private const val PREFS = "langbot"
private const val KEY_USER_ID = "user_id"
private const val KEY_BLS_URL = "bls_url"

object UserPrefs {
    fun getUserId(ctx: Context): String? =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_USER_ID, null)

    fun saveUserId(ctx: Context, userId: String) =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(KEY_USER_ID, userId).apply()

    fun getBlsUrl(ctx: Context): String =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_BLS_URL, "http://136.244.102.39:8531") ?: "http://136.244.102.39:8531"

    fun saveBlsUrl(ctx: Context, url: String) =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(KEY_BLS_URL, url).apply()

    fun clear(ctx: Context) =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
}
