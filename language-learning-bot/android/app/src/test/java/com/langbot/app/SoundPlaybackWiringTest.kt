package com.langbot.app

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Проигрывание звука на карточке: одна дорожка на экран.
 *
 * Зачем
 * -----
 * В пик-режиме вариант ответа — это набор звуков, который играется цепочкой с
 * паузой между ними. Учащийся слышит первый звук, понимает, что слово не то, и
 * жмёт следующий вариант. Если предыдущая цепочка не оборвана, варианты звучат
 * одновременно — ломается ровно то сравнение, ради которого режим существует.
 *
 * Что этот тест НЕ проверяет
 * -------------------------
 * Он смотрит на разводку в исходнике, а не на поведение MediaPlayer: ни один
 * тест в проекте не поднимает StudyActivity, а состояния MediaPlayer живут в
 * системе. Тест ловит регрессию вида «добавили ещё одну кнопку звука и забыли
 * оборвать предыдущее» — то, как этот баг и появился.
 */
class SoundPlaybackWiringTest {

    private val source: String by lazy {
        File("src/main/java/com/langbot/app/StudyActivity.kt").readText()
    }

    /** Тело функции от её сигнатуры до следующей объявленной функции. */
    private fun body(signature: String): String {
        val start = source.indexOf(signature)
        assertTrue("не найдено: $signature", start >= 0)
        val rest = source.substring(start + signature.length)
        val end = rest.indexOf("\n    private fun ").let { if (it < 0) rest.length else it }
        return rest.substring(0, end)
    }

    @Test
    fun `каждое начало воспроизведения обрывает предыдущее`() {
        // Три места, откуда стартует звук: одиночный вариант, «все звуки слова»
        // и цепочка варианта пик-режима.
        val starts = Regex("""\bstopPlayback\(\)""").findAll(source).count()
        assertTrue("stopPlayback() вызывается $starts раз, ожидалось не меньше 4", starts >= 4)

        // Цепочка вариантов пик-режима — то самое место из жалобы.
        val seq = body("private fun playSoundSequence(paths: List<String>) {")
        assertTrue("цепочка не обрывает предыдущее", seq.contains("stopPlayback()"))
        assertTrue("цепочка не привязана к поколению", seq.contains("val mine = playbackGen"))
    }

    @Test
    fun `отложенный переход по цепочке отсекается по поколению`() {
        // Паузу держит Handler, а не MediaPlayer: оборвав только звук, мы всё
        // равно получили бы следующий через 350 мс.
        val seq = body("private fun playSoundSequence(paths: List<String>) {")
        assertTrue(seq.contains("if (mine != playbackGen || idx >= paths.size) return"))
        assertTrue(seq.contains("if (mine == playbackGen) playbackHandler.postDelayed"))
        assertFalse("postDelayed мимо владельца — отменить такое нечем",
                    seq.contains("binding.root.postDelayed"))
    }

    @Test
    fun `stopPlayback снимает и звук, и отложенные переходы`() {
        val stop = body("private fun stopPlayback() {")
        assertTrue(stop.contains("playbackGen++"))
        assertTrue(stop.contains("playbackHandler.removeCallbacksAndMessages(null)"))
    }

    @Test
    fun `плееры карточки и одноразовые останавливаются по-разному`() {
        // Плееры карточки переиспользуются между нажатиями: stop() перевёл бы их
        // в Stopped и потребовал повторной подготовки. Одноразовые могут быть
        // ещё в Preparing, где pause() бросает, а release() безопасен всегда.
        val stop = body("private fun stopPlayback() {")
        assertTrue(stop.contains("players.contains(p)"))
        assertTrue(stop.contains("p.pause()"))
        assertTrue(stop.contains("p.release()"))
    }

    @Test
    fun `источник звука везде один - сначала кеш, потом сеть`() {
        // Офлайн карточка молчала: кнопки звука тянули файл по сети, хотя
        // AudioCache скачал его заранее. Мест, заводящих MediaPlayer, два —
        // кнопки карточки и цепочка пик-режима; оба обязаны спрашивать кеш.
        val viaCache = Regex("""AudioCache\.sourceFor\(""").findAll(source).count()
        assertTrue("источник берётся мимо кеша: AudioCache.sourceFor встречается $viaCache раз",
                   viaCache >= 2)
        assertFalse("прямой URL в обход кеша — это и есть тот баг",
                    source.contains("BLSClient.soundUrl("))
    }

    @Test
    fun `переход к следующему слову глушит звук предыдущего`() {
        // Плееры цепочки не лежат в players, поэтому обрывает их именно это.
        val release = body("private fun releasePlayers() {")
        assertTrue("releasePlayers не обрывает цепочку", release.contains("stopPlayback()"))
    }

    @Test
    fun `прерванная подготовка не запускает звук задним числом`() {
        // prepareAsync асинхронный: пока он идёт, пользователь успевает нажать
        // другой вариант. Без проверки готовый звук стартовал бы уже поверх нового.
        val seq = body("private fun playSoundSequence(paths: List<String>) {")
        val prepared = seq.substring(seq.indexOf("setOnPreparedListener"))
        assertTrue(prepared.take(200).contains("mine != playbackGen"))
    }
}
