package com.langbot.app

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.prefs.UserPrefs
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner

/**
 * Кого экран входа пропускает сразу.
 *
 * Установка, вошедшая старым приложением, имеет user_id без токена. Её надо
 * ОДИН раз провести через вход по коду — иначе она так и будет ходить без
 * токена и после включения принуждения перестанет работать. Но и зациклить
 * человека на входе нельзя: если сервер токена не выдал, вход всё равно
 * должен считаться состоявшимся.
 */
@RunWith(RobolectricTestRunner::class)
class LoginGateTest {

    private val ctx get() = ApplicationProvider.getApplicationContext<Context>()

    @Before
    fun setUp() {
        UserPrefs.clear(ctx)
    }

    private fun loginSkipped(): Boolean =
        Robolectric.buildActivity(LoginActivity::class.java).setup().get().isFinishing

    @Test
    fun install_from_before_tokens_goes_through_login_once() {
        UserPrefs.saveUserId(ctx, "u1")
        assertFalse("старая установка без токена обязана пройти вход", loginSkipped())
    }

    @Test
    fun login_with_token_is_skipped() {
        UserPrefs.saveUserId(ctx, "u1")
        UserPrefs.saveToken(ctx, "u1.sig")
        assertTrue(loginSkipped())
    }

    @Test
    fun login_without_server_token_does_not_loop() {
        UserPrefs.saveUserId(ctx, "u1")
        UserPrefs.saveToken(ctx, "")
        assertTrue("без токена от сервера вход не должен повторяться", loginSkipped())
    }

    @Test
    fun nobody_logged_in_sees_login() {
        assertFalse(loginSkipped())
    }
}
