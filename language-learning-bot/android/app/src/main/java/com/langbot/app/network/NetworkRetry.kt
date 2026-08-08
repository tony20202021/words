package com.langbot.app.network

/**
 * Несколько попыток запроса с растущим таймаутом и понятным статусом.
 *
 * Проблема, которую решает: сеть есть, а до сервера не достучаться. Один
 * длинный таймаут превращал нажатие кнопки в «ничего не происходит» на 15–45
 * секунд, после чего приложение всё равно уходило в офлайн. Пользователь за это
 * время не видел ни ответа, ни объяснения.
 *
 * Схема: первая попытка короткая (живой сервер отвечает за десятки мс), дальше
 * таймаут растёт. Между попытками вызывается [onStatus], чтобы экран мог
 * сказать, что происходит и сколько ещё ждать. Все попытки исчерпаны — вернётся
 * null, и вызывающий переходит в офлайн.
 */
object NetworkRetry {

    /** Что показать пользователю между попытками. */
    data class Status(
        val attempt: Int,        // номер текущей попытки, с 1
        val total: Int,          // сколько всего будет попыток
        val timeoutMs: Int,      // таймаут этой попытки
        val lastError: String?,  // чем закончилась предыдущая
    ) {
        /** Готовый текст для экрана. */
        val message: String
            get() = if (attempt == 1) {
                "Соединяемся…"
            } else {
                "Соединение нестабильно. Попытка $attempt из $total, " +
                        "ждём до ${timeoutMs / 1000} с…"
            }
    }

    /**
     * Выполнить [block] с эскалацией таймаута.
     *
     * @param onStatus вызывается перед каждой попыткой
     * @param block получает клиент с таймаутом текущей попытки
     * @return результат или null, если ни одна попытка не удалась
     */
    suspend fun <T : Any> call(
        onStatus: (Status) -> Unit = {},
        block: suspend (BLSApi) -> T,
    ): T? {
        val total = BLSClient.attemptCount
        var lastError: String? = null

        for (attempt in 0 until total) {
            onStatus(
                Status(
                    attempt = attempt + 1,
                    total = total,
                    timeoutMs = BLSClient.CONNECT_TIMEOUTS_MS.getOrElse(attempt) {
                        BLSClient.CONNECT_TIMEOUTS_MS.last()
                    },
                    lastError = lastError,
                )
            )
            try {
                return block(BLSClient.apiForAttempt(attempt))
            } catch (e: Exception) {
                lastError = "${e.javaClass.simpleName}: ${e.message}"
            }
        }
        return null
    }

    /** Суммарное ожидание в худшем случае — для текста «переходим в офлайн». */
    val worstCaseSeconds: Int
        get() = BLSClient.CONNECT_TIMEOUTS_MS.sum() / 1000
}
