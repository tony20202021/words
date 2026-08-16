package com.langbot.app

import com.langbot.app.util.correct
import com.langbot.app.util.mistakes
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * Счётчики под карточкой. Дефект «1 ошибок» прожил всё время существования
 * экрана и не был виден ни в одном тесте — его нашёл снимок экрана.
 */
class RussianPluralTest {

    @Test
    fun mistakes_agree_with_the_number() {
        assertEquals("0 ошибок", mistakes(0))
        assertEquals("1 ошибка", mistakes(1))
        assertEquals("2 ошибки", mistakes(2))
        assertEquals("4 ошибки", mistakes(4))
        assertEquals("5 ошибок", mistakes(5))
        assertEquals("21 ошибка", mistakes(21))
        assertEquals("22 ошибки", mistakes(22))
    }

    @Test
    fun the_teens_take_the_many_form() {
        // Единственное место, где правило не сводится к последней цифре.
        assertEquals("11 ошибок", mistakes(11))
        assertEquals("12 ошибок", mistakes(12))
        assertEquals("14 ошибок", mistakes(14))
        assertEquals("111 ошибок", mistakes(111))
        assertEquals("112 ошибок", mistakes(112))
    }

    @Test
    fun correct_answers_agree_too() {
        assertEquals("1 правильный", correct(1))
        assertEquals("2 правильных", correct(2))
        assertEquals("5 правильных", correct(5))
        assertEquals("11 правильных", correct(11))
    }
}
