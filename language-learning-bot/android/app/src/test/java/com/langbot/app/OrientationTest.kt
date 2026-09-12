package com.langbot.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Портрет закреплён у всех экранов.
 *
 * По умолчанию поворот телефона уничтожает активность и создаёт её заново.
 * Экран учёбы на этом заново ходил в сеть за сессией из onCreate, терял
 * отметку прослушанного варианта и обрывал звук — то есть поворот стоил
 * сетевого запроса.
 *
 * Проверяем манифест, а не поведение: забыть атрибут у НОВОЙ активности легче
 * всего, и заметить это можно будет только перевернув телефон.
 */
class OrientationTest {

    private val manifest = File("src/main/AndroidManifest.xml").readText(Charsets.UTF_8)

    private val activityNames = Regex("""<activity[^>]*android:name="\.(\w+)"""", RegexOption.DOT_MATCHES_ALL)
        .findAll(manifest).map { it.groupValues[1] }.toList()

    @Test
    fun the_manifest_declares_every_screen() {
        // Если активность перестала объявляться, тест ниже проверял бы пустоту.
        assertTrue("активности в манифесте не найдены", activityNames.size >= 7)
        assertTrue("нет экрана учёбы: $activityNames", "StudyActivity" in activityNames)
    }

    @Test
    fun every_activity_is_locked_to_portrait() {
        val blocks = Regex("""<activity\b.*?(?:/>|</activity>)""", RegexOption.DOT_MATCHES_ALL)
            .findAll(manifest).map { it.value }.toList()
        assertEquals("блоков активностей не столько же, сколько имён",
            activityNames.size, blocks.size)

        val unlocked = blocks.filterNot { it.contains("""android:screenOrientation="portrait"""") }
            .map { Regex("""android:name="\.(\w+)"""").find(it)?.groupValues?.get(1) ?: "?" }
        assertTrue("без закреплённого портрета: $unlocked", unlocked.isEmpty())
    }
}
