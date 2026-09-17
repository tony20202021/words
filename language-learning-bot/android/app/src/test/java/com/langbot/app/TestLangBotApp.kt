package com.langbot.app

import com.langbot.app.prefs.UserPrefs

/**
 * Приложение, под которым идут ВСЕ тесты (см. test/resources/robolectric.properties).
 *
 * Зачем. Адрес сервера в UserPrefs по умолчанию — боевой, он зашит в приложение.
 * LangBotApp.onCreate инициализирует им клиента и тут же пытается отправить
 * накопленные офлайн результаты. В Robolectric приложение поднимает каждый тест,
 * поэтому прогон время от времени слал POST /results/batch в РАБОЧИЙ сервис —
 * с тестовыми данными и на запись. В журнале это выглядело как запрос с чужого
 * внешнего адреса: пакет уходил наружу и возвращался публичным адресом сервера.
 *
 * Здесь адрес подменяется на заведомо мёртвый. Тестам, которым нужен ответ,
 * никто не мешает вызвать BLSClient.init со своим MockWebServer.
 */
class TestLangBotApp : LangBotApp() {

    override fun onCreate() {
        UserPrefs.saveBlsUrl(this, DEAD_URL)
        super.onCreate()
    }

    companion object {
        /** Порт 1: соединение отвергается сразу, ждать нечего. */
        const val DEAD_URL = "http://127.0.0.1:1"
    }
}
