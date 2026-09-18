package com.langbot.app

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.prefs.UserPrefs
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/**
 * Прогон не должен разговаривать с боевым сервером.
 *
 * Это уже случалось и осталось незамеченным: приложение при старте отправляет
 * накопленные офлайн результаты, а адрес по умолчанию — production. В журнале
 * рабочего BLS появлялись POST /results/batch с тестовыми данными; спасло лишь
 * то, что пользователя с таким идентификатором нет. Тест закрепляет, что
 * подмена адреса на месте.
 */
@RunWith(RobolectricTestRunner::class)
class NoProductionServerTest {

    @Test
    fun tests_run_against_a_dead_address_not_production() {
        val ctx = ApplicationProvider.getApplicationContext<Context>()
        val url = UserPrefs.getBlsUrl(ctx)

        assertEquals(
            "приложение тестов обязано подменять адрес сервера",
            TestLangBotApp.DEAD_URL, url,
        )
        assertFalse(
            "в тестах не должно быть боевого адреса: $url",
            url.contains("77.81.226.56") || url.contains("8443"),
        )
    }

    @Test
    fun clearing_settings_does_not_bring_production_back() {
        // Так тест уже однажды ушёл в рабочий сервис: LoginGateTest чистил
        // настройки, и адрес по умолчанию снова оказывался боевым.
        val ctx = ApplicationProvider.getApplicationContext<Context>()
        UserPrefs.clear(ctx)
        assertEquals(TestLangBotApp.DEAD_URL, UserPrefs.getBlsUrl(ctx))
    }
}
