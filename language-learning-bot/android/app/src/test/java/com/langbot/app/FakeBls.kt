package com.langbot.app

import android.graphics.Bitmap
import com.google.gson.Gson
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import okio.Buffer
import java.io.ByteArrayOutputStream
import java.util.concurrent.atomic.AtomicInteger

/**
 * Поддельный сервер со своей памятью — для матрицы офлайн-проверок.
 *
 * Зачем он такой. Отдельные проверки до сих пор подсовывали заранее готовые
 * ответы, и это ловило вёрстку, но не ловило СЧЁТЧИКИ: они живут не в одном
 * ответе, а в череде «ответил — записалось — пришло следующее». Поэтому здесь
 * сервер помнит, на что человек ответил, и считает так же, как настоящий:
 * сколько пройдено, сколько правильных, сколько ошибок.
 *
 * Связь переключается полем [online]: «нет сети» это отказ соединения, а не
 * вежливый код ошибки, — именно так ведёт себя телефон в метро и в самолёте.
 */
class FakeBls(
    private val words: List<Int> = (1..6).toList(),
    private val userId: String = "user-1",
    private val languageId: String = "lang-1",
) {
    val server = MockWebServer()

    @Volatile var online: Boolean = true

    /**
     * Сервер делает работу, а ответ до телефона не доходит.
     *
     * Это не то же самое, что [online] = false: там связь рвётся ДО обработки,
     * и сервер остаётся на месте. А в метро бывает иначе — запрос доходит,
     * оценка записывается, сессия сдвигается, и только ответ теряется. Телефон
     * считает, что ничего не вышло, уходит в офлайн и записывает ответ ещё раз.
     * Подозрение владельца «при переключениях офлайн-онлайн перескакивает на
     * слово вперёд» ложится именно на этот случай.
     */
    @Volatile var dropResponses: Boolean = false
    /** Печатать ли путь каждого запроса — для разбора падающих проверок. */
    @Volatile var log: Boolean = false

    /** Сколько раз просили картинки графиков — по ним видно лишние закачки. */
    val chartRequests = AtomicInteger(0)
    val batchRequests = AtomicInteger(0)

    // ── состояние «сервера» ──────────────────────────────────────────────
    private val answers = linkedMapOf<String, String>()   // word_id → know|dont_know|skip
    private var cursor = 0
    private var sessionId = "sid-1"
    private val gson = Gson()

    val answered: Map<String, String> get() = answers

    private fun wordId(n: Int) = "w$n"

    private fun png(width: Int = 40): ByteArray {
        val out = ByteArrayOutputStream()
        Bitmap.createBitmap(width, 8, Bitmap.Config.ARGB_8888)
            .compress(Bitmap.CompressFormat.PNG, 100, out)
        return out.toByteArray()
    }

    /**
     * Счётчики — как у настоящего сервера: из того, что человек уже ответил.
     *
     * Важная тонкость, из-за которой подделка однажды врала. Настоящий BLS
     * ведёт две разные величины: правильные и ошибки он прибавляет СРАЗУ при
     * оценке (know_word, show_answer_word, reconsider_word), а историю ответов
     * пополняет только при переходе к следующему слову (rate_word). Поэтому
     * сразу после «Знаю» или после возврата «все-таки не знаю» счётчики уже
     * включают текущее слово, а история — ещё нет. Телефон по этой разнице
     * узнаёт, что текущее слово сервером уже посчитано.
     */
    private fun meta(pos: Int, wordNumber: Int): String {
        val correct = answers.values.count { it == "know" }
        val wrong = answers.values.count { it == "dont_know" }
        val passed = words.take(cursor).mapNotNull { answers[wordId(it)] }
        val history = passed.filter { it != "skip" }
            .joinToString(",") { "\"$it\"" }
        return """"word_id":"${wordId(wordNumber)}","word_number":$wordNumber,
            |"session_pos":$pos,"session_total":${words.size},
            |"correct_count":$correct,"incorrect_count":$wrong,
            |"result_history":[$history],"pending_result":null,"score_badge":null,
            |"words_for_today":${words.size},"show_session_counter":true,
            |"session_counter_text":"(в сессии: $pos из ${words.size})"""".trimMargin()
    }

    private fun card(showAnswer: Boolean, scored: Boolean = false): String {
        val n = words.getOrNull(cursor) ?: return ""
        val pos = cursor + 1
        val buttons = when {
            !showAnswer -> """[{"id":"know","text":"✅ Знаю","style":"success","rating":"know",
                |"offline_effect":"record_and_reveal","offline_rating":"know"},
                |{"id":"show_answer","text":"❓ Не знаю","style":"warn",
                |"offline_effect":"reveal_answer"}]""".trimMargin()
            scored -> """[{"id":"rate","text":"✅ К следующему слову","style":"success",
                |"rating":"know","offline_effect":"advance"},
                |{"id":"reconsider","text":"❌ Ой, все-таки не знаю","style":"outline-danger",
                |"offline_effect":"reveal_question","offline_rating":"dont_know"}]""".trimMargin()
            else -> """[{"id":"rate","text":"➡️ Дальше","style":"success","rating":"dont_know",
                |"offline_effect":"submit","offline_rating":"dont_know"}]""".trimMargin()
        }
        val content = if (showAnswer) """[{"type":"translation","text":"перевод-$n"}]"""
                      else """[{"type":"foreign","text":"слово-$n"}]"""
        return """{"show_answer":$showAnswer,"content":$content,"buttons":$buttons,
            |"extra_content":[],"sounds":[],"meta":{${meta(pos, n)}}}""".trimMargin()
    }

    private fun sessionResponse(showAnswer: Boolean, scored: Boolean = false): String {
        if (cursor >= words.size) return """{"session_id":"$sessionId","card":null,"no_words":true}"""
        return """{"session_id":"$sessionId","card":${card(showAnswer, scored)}}"""
    }

    private fun bundle(): String {
        val units = words.joinToString(",") { n ->
            val pos = words.indexOf(n) + 1
            """{"word_id":"${wordId(n)}","word_number":$n,
               |"card_front":${card(false).replace("\"word_number\":${words[cursor]}", "\"word_number\":$n")},
               |"card_answer":{"show_answer":true,"content":[{"type":"translation","text":"перевод-$n"}],
               |"buttons":[{"id":"rate","text":"➡️ Дальше","style":"success","rating":"dont_know",
               |"offline_effect":"submit","offline_rating":"dont_know"}],"extra_content":[],
               |"meta":{${meta(pos, n)}}},
               |"card_known":{"show_answer":true,"content":[{"type":"translation","text":"перевод-$n"}],
               |"buttons":[{"id":"rate","text":"✅ К следующему слову","style":"success",
               |"rating":"know","offline_effect":"advance"},
               |{"id":"reconsider","text":"❌ Ой, все-таки не знаю","style":"outline-danger",
               |"offline_effect":"reveal_question","offline_rating":"dont_know"}],
               |"extra_content":[],"meta":{${meta(pos, n)}}},"sounds":[]}""".trimMargin()
        }
        return """{"session_id":"$sessionId","words":[$units],"settings":{"offline_bundle_size":${words.size}},
            |"language_name_ru":"Иврит","total_words":${words.size},
            |"words_for_today":${words.size}}""".trimMargin()
    }

    private fun summary(): String {
        val known = answers.values.count { it == "know" }
        return """{"words_studied":${answers.size},"words_known":$known,"words_skipped":0,
            |"words_unknown":${answers.values.count { it == "dont_know" }},
            |"total_words":${words.size},"words_for_today":${words.size - answers.size},
            |"progress_percentage":${known * 100.0 / words.size}}""".trimMargin()
    }

    private fun ok(body: String) = MockResponse().setResponseCode(200).setBody(body)

    fun start() {
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                if (!online) {
                    // Нет сети — соединение обрывается, а не отвечает ошибкой.
                    return MockResponse().setSocketPolicy(
                        okhttp3.mockwebserver.SocketPolicy.DISCONNECT_AT_START)
                }
                val path = request.path ?: ""
                if (log) println("ЗАПРОС ${request.method} $path")
                if (dropResponses) {
                    // Работу делаем, ответ теряем — как оборванное соединение
                    // уже после обработки на сервере.
                    runCatching { route(path, request) }
                    return MockResponse().setSocketPolicy(
                        okhttp3.mockwebserver.SocketPolicy.DISCONNECT_AFTER_REQUEST)
                }
                return try { route(path, request) } catch (e: Throwable) {
                    println("ПАДЕНИЕ В ПОДДЕЛЬНОМ СЕРВЕРЕ на $path: $e")
                    MockResponse().setResponseCode(500)
                }
            }

            fun route(path: String, request: RecordedRequest): MockResponse {
                return when {
                    path.contains("chart_manifest") -> ok(
                        """{"sections":[{"header":"За месяц","charts":["words_studied","words_new"],
                           |"type":"monthly_recent"}],"captions":{}}""".trimMargin())
                    path.contains("charts_version") -> ok("""{"version":"v${answers.size}"}""")
                    path.contains("-chart/") || path.contains("/chart/") -> {
                        chartRequests.incrementAndGet()
                        MockResponse().setBody(Buffer().write(png()))
                    }
                    path.endsWith("/bundle") -> ok(bundle())
                    path.contains("results/batch") -> {
                        batchRequests.incrementAndGet()
                        val body = request.body.readUtf8()
                        Regex(""""word_id":"([^"]+)","rating":"([^"]+)"""").findAll(body).forEach {
                            answers[it.groupValues[1]] = it.groupValues[2]
                        }
                        val ids = Regex(""""event_id":"([^"]+)"""").findAll(body)
                            .map { it.groupValues[1] }.toList()
                        ok("""{"acks":[${ids.joinToString(",") {
                            """{"event_id":"$it","status":"ok"}""" }}]}""")
                    }
                    path.endsWith("/know") -> {
                        words.getOrNull(cursor)?.let { answers[wordId(it)] = "know" }
                        ok(sessionResponse(showAnswer = true, scored = true))
                    }
                    path.endsWith("/show_answer") -> ok(sessionResponse(showAnswer = true))
                    path.endsWith("/reconsider") -> {
                        words.getOrNull(cursor)?.let { answers[wordId(it)] = "dont_know" }
                        ok(sessionResponse(showAnswer = false))
                    }
                    path.endsWith("/rate") -> {
                        words.getOrNull(cursor)?.let { answers.putIfAbsent(wordId(it), "dont_know") }
                        cursor++
                        ok(sessionResponse(showAnswer = false))
                    }
                    path.contains("/session/") && request.method == "GET" -> {
                        cursor = words.indexOfFirst { wordId(it) !in answers }.let {
                            if (it < 0) words.size else it
                        }
                        ok(sessionResponse(showAnswer = false))
                    }
                    path.startsWith("/session/start") -> ok(sessionResponse(showAnswer = false))
                    path.contains("/settings/") -> ok("""{"use_check_date":true,"skip_marked":false}""")
                    path.startsWith("/statistics/") -> ok(summary())
                    path.startsWith("/languages") -> ok(
                        """[{"id":"lang-1","name_ru":"Иврит","name_foreign":"עברית"}]""")
                    else -> MockResponse().setResponseCode(404)
                }
            }
        }
        server.start()
    }

    fun url(): String = server.url("/").toString().trimEnd('/')
    fun shutdown() = runCatching { server.shutdown() }
}
