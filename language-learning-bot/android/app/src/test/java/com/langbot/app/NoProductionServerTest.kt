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
            url.contains("77.81.226.56") || url.contains("8443") || url.contains("8543"),
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

/**
 * Перенос сохранённого адреса сервера при смене порта.
 *
 * Владелец свёл порты хозяйства к виду `85**`: TLS переехал 8443 → 8543.
 * Одной смены умолчания мало. При входе LoginActivity СОХРАНЯЕТ адрес в
 * настройки, и у всех, кто хоть раз входил, там лежит старый порт — обновление
 * приложения его не трогает. Такие установки продолжили бы ходить на 8443 и в
 * день, когда порт закроют, молча потеряли бы связь: с виду это «нет сети».
 */
@RunWith(RobolectricTestRunner::class)
class BlsUrlMigrationTest {

    private fun ctx(): Context = ApplicationProvider.getApplicationContext()

    @org.junit.Before
    fun setUp() {
        UserPrefs.clear(ctx())
        // Проверяем сам перенос, поэтому умолчание тут боевое, а не мёртвое.
        UserPrefs.defaultBlsUrl = "https://77.81.226.56:8543"
    }

    @org.junit.After
    fun tearDown() {
        UserPrefs.defaultBlsUrl = TestLangBotApp.DEAD_URL
        UserPrefs.clear(ctx())
    }

    @Test
    fun `сохранённый старый адрес переезжает на новый порт`() {
        UserPrefs.saveBlsUrl(ctx(), "https://77.81.226.56:8443")
        UserPrefs.migrateBlsUrl(ctx())
        assertEquals("https://77.81.226.56:8543", UserPrefs.getBlsUrl(ctx()))
    }

    @Test
    fun `свой адрес пользователя не трогаем`() {
        """Вписал свой сервер руками — это его выбор, переписывать нельзя."""
        UserPrefs.saveBlsUrl(ctx(), "https://my-own-server.example:9000")
        UserPrefs.migrateBlsUrl(ctx())
        assertEquals("https://my-own-server.example:9000", UserPrefs.getBlsUrl(ctx()))
    }

    @Test
    fun `без сохранённого адреса перенос ничего не создаёт`() {
        """Не входивший ни разу получает умолчание, а не запись в настройках."""
        UserPrefs.migrateBlsUrl(ctx())
        assertEquals("https://77.81.226.56:8543", UserPrefs.getBlsUrl(ctx()))
    }

    @Test
    fun `повторный перенос ничего не портит`() {
        UserPrefs.saveBlsUrl(ctx(), "https://77.81.226.56:8443")
        UserPrefs.migrateBlsUrl(ctx())
        UserPrefs.migrateBlsUrl(ctx())
        assertEquals("https://77.81.226.56:8543", UserPrefs.getBlsUrl(ctx()))
    }
}
