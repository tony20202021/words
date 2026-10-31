package com.langbot.app.prefs

import android.content.Context

private const val PREFS = "langbot"
private const val KEY_USER_ID = "user_id"
private const val KEY_BLS_URL = "bls_url"
private const val KEY_TOKEN = "token"

object UserPrefs {
    /**
     * Адрес сервера, если пользователь своего не задавал. Это production, и
     * поле изменяемое ради одного: тесты подменяют его на мёртвый адрес.
     * Подмены одной только записи в настройках не хватало — любой тест,
     * вызвавший clear(), стирал её, и следующий запрос уходил в рабочий сервис.
     */
    @Volatile var defaultBlsUrl: String = "https://77.81.226.56:8543"

    /**
     * Прежние адреса, с которых надо переехать на текущий.
     *
     * Порт сменился 8443 → 8543: владелец свёл все порты хозяйства к виду 85**.
     * Одной смены умолчания мало — при входе LoginActivity СОХРАНЯЕТ адрес в
     * настройки, и у всех, кто хоть раз входил, там лежит старый порт. После
     * обновления приложения они продолжили бы ходить на 8443 и однажды упёрлись
     * бы в закрытый порт, причём молча: с виду это «нет сети».
     */
    private val legacyUrls = setOf("https://77.81.226.56:8443")

    /**
     * Перевести сохранённый адрес на новый порт.
     *
     * Трогаем только known-адреса из [legacyUrls]: если человек вписал свой
     * сервер руками, это его выбор, и переписывать его нельзя.
     */
    fun migrateBlsUrl(ctx: Context) {
        val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val saved = prefs.getString(KEY_BLS_URL, null) ?: return
        if (saved in legacyUrls) {
            prefs.edit().putString(KEY_BLS_URL, defaultBlsUrl).apply()
        }
    }

    fun getUserId(ctx: Context): String? =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_USER_ID, null)

    fun saveUserId(ctx: Context, userId: String) =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(KEY_USER_ID, userId).apply()

    fun getBlsUrl(ctx: Context): String =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_BLS_URL, defaultBlsUrl) ?: defaultBlsUrl

    fun saveBlsUrl(ctx: Context, url: String) =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(KEY_BLS_URL, url).apply()

    /**
     * Токен для BLS. Три состояния, и различать их важно:
     *   null — вход был сделан старым приложением, до токенов. Такую установку
     *          один раз отправляем на экран входа — там она получит токен.
     *   ""   — вход новым приложением, но сервер токена не выдал. Считаем вход
     *          состоявшимся, иначе экран входа показывался бы снова и снова.
     *   иное — токен; прикладывается к каждому запросу.
     */
    fun getToken(ctx: Context): String? =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_TOKEN, null)

    fun saveToken(ctx: Context, token: String) =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(KEY_TOKEN, token).apply()

    fun clearToken(ctx: Context) =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .remove(KEY_TOKEN).apply()

    fun clear(ctx: Context) =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
}
