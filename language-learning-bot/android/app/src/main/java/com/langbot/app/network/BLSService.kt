package com.langbot.app.network

import okhttp3.ConnectionPool
import okhttp3.Dispatcher
import okhttp3.OkHttpClient
import okhttp3.ResponseBody
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

interface BLSApi {

    // Auth
    @POST("auth/mobile/activate")
    suspend fun activateMobileToken(@Body body: MobileActivateRequest): Response<MobileActivateResponse>

    @POST("auth/mobile/create")
    suspend fun createMobileToken(@Body body: Map<String, String>): Response<CreateMobileTokenResponse>

    // Languages
    @GET("languages/")
    suspend fun getLanguages(): Response<List<Language>>

    // Session
    @POST("session/start")
    suspend fun startSession(@Body body: StartSessionRequest): Response<SessionResponse>

    @GET("session/{user_id}/{language_id}")
    suspend fun getSession(
        @Path("user_id") userId: String,
        @Path("language_id") languageId: String,
    ): Response<SessionResponse>

    @POST("session/{session_id}/know")
    suspend fun knowWord(@Path("session_id") sessionId: String): Response<SessionResponse>

    @POST("session/{session_id}/show_answer")
    suspend fun showAnswer(@Path("session_id") sessionId: String): Response<SessionResponse>

    @POST("session/{session_id}/rate")
    suspend fun rateWord(
        @Path("session_id") sessionId: String,
        @Body body: RateRequest,
    ): Response<SessionResponse>

    @POST("session/{session_id}/reconsider")
    suspend fun reconsider(@Path("session_id") sessionId: String): Response<SessionResponse>

    @POST("session/{session_id}/toggle_skip")
    suspend fun toggleSkip(@Path("session_id") sessionId: String): Response<SessionResponse>

    @POST("session/{session_id}/next_batch")
    suspend fun nextBatch(
        @Path("session_id") sessionId: String,
        @Body body: Map<String, String> = emptyMap(),
    ): Response<SessionResponse>

    @POST("session/{session_id}/pick_answer")
    suspend fun pickAnswer(
        @Path("session_id") sessionId: String,
        @Body body: Map<String, String>,
    ): Response<SessionResponse>

    @POST("session/{session_id}/add_forbidden_pair")
    suspend fun addForbiddenPair(
        @Path("session_id") sessionId: String,
        @Body body: Map<String, String>,
    ): Response<SessionResponse>


    @DELETE("session/{user_id}/{language_id}")
    suspend fun endSession(
        @Path("user_id") userId: String,
        @Path("language_id") languageId: String,
    ): Response<Unit>

    // Offline
    @POST("session/{user_id}/{language_id}/bundle")
    suspend fun getBundle(
        @Path("user_id") userId: String,
        @Path("language_id") languageId: String,
    ): Response<BundleResponse>

    @POST("results/batch")
    suspend fun postResultsBatch(@Body body: ResultsBatchRequest): Response<ResultsBatchResponse>

    // Statistics
    @GET("statistics/{user_id}/{language_id}")
    suspend fun getStatistics(
        @Path("user_id") userId: String,
        @Path("language_id") languageId: String,
    ): Response<Statistics>

    @GET("statistics/chart_manifest")
    suspend fun getChartManifest(): Response<ChartManifestResponse>

    @GET("statistics/{user_id}/{language_id}/chart/{chart_name}")
    suspend fun getChart(
        @Path("user_id") userId: String,
        @Path("language_id") languageId: String,
        @Path("chart_name") chartName: String,
    ): Response<ResponseBody>

    @GET("statistics/{user_id}/{language_id}/monthly-chart/{chart_name}")
    suspend fun getMonthlyChart(
        @Path("user_id") userId: String,
        @Path("language_id") languageId: String,
        @Path("chart_name") chartName: String,
        @Query("show_all") showAll: Boolean = true,
    ): Response<ResponseBody>

    // Hints
    @GET("hints/{user_id}/{word_id}")
    suspend fun getHints(
        @Path("user_id") userId: String,
        @Path("word_id") wordId: String,
    ): Response<Map<String, String>>

    @PUT("hints/{user_id}/{word_id}")
    suspend fun setHint(
        @Path("user_id") userId: String,
        @Path("word_id") wordId: String,
        @Body body: HintUpdateRequest,
    ): Response<HintUpdateResponse>

    @DELETE("hints/{user_id}/{word_id}/{hint_type}")
    suspend fun deleteHint(
        @Path("user_id") userId: String,
        @Path("word_id") wordId: String,
        @Path("hint_type") hintType: String,
    ): Response<HintUpdateResponse>

    // Settings
    @GET("settings/{user_id}/{language_id}")
    suspend fun getSettings(
        @Path("user_id") userId: String,
        @Path("language_id") languageId: String,
    ): Response<Map<String, Any>>

    @POST("settings/{user_id}/{language_id}/{key}/toggle")
    suspend fun toggleSetting(
        @Path("user_id") userId: String,
        @Path("language_id") languageId: String,
        @Path("key") key: String,
    ): Response<Map<String, Any>>

    // Help
    @GET("help")
    suspend fun getHelp(): Response<HelpResponse>

    @GET("version")
    suspend fun getVersion(): Response<VersionResponse>

    @GET("qr")
    suspend fun getQrCode(@Query("url") url: String): Response<ResponseBody>

    @PUT("settings/{user_id}/{language_id}/{key}")
    suspend fun setSetting(
        @Path("user_id") userId: String,
        @Path("language_id") languageId: String,
        @Path("key") key: String,
        @Body body: @JvmSuppressWildcards Map<String, Any>,
    ): Response<Map<String, Any>>
}

object BLSClient {
    private var _api: BLSApi? = null

    /** Stored without trailing slash — use for constructing sound URLs. */
    var rawBaseUrl: String = ""
        private set

    /**
     * Таймауты подключения по попыткам, мс.
     *
     * Бывает, что сеть есть, а до сервера не достучаться: пакеты уходят в никуда
     * и TCP-подключение висит до таймаута. С одним таймаутом в 15 секунд (плюс
     * повтор внутри OkHttp) нажатие кнопки выглядело как «ничего не произошло».
     *
     * Живой сервер отвечает за десятки миллисекунд, поэтому первая попытка
     * короткая: есть связь — соединится сразу, нет — провалится сразу.
     * Дальше таймаут растёт, чтобы пережить действительно медленную сеть.
     */
    val CONNECT_TIMEOUTS_MS = listOf(2_000, 6_000, 15_000)

    /** Сколько ждём ОТВЕТА уже соединившегося сервера: графики строятся секундами. */
    const val READ_TIMEOUT_MS = 30_000L

    private var _apis: List<BLSApi> = emptyList()

    fun init(baseUrl: String) {
        rawBaseUrl = baseUrl.trimEnd('/')
        val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
        // Пул и диспетчер общие: клиенты отличаются только таймаутами.
        val pool = ConnectionPool()
        val dispatcher = Dispatcher()

        _apis = CONNECT_TIMEOUTS_MS.map { connectMs ->
            val okhttp = OkHttpClient.Builder()
                .addInterceptor(logging)
                .connectionPool(pool)
                .dispatcher(dispatcher)
                .connectTimeout(connectMs.toLong(), TimeUnit.MILLISECONDS)
                .readTimeout((connectMs * 2).toLong(), TimeUnit.MILLISECONDS)
                .writeTimeout(connectMs.toLong(), TimeUnit.MILLISECONDS)
                // Повторы делает NetworkRetry — иначе OkHttp молча удваивает
                // ожидание и попытки перестают быть предсказуемыми.
                .retryOnConnectionFailure(false)
                .build()
            Retrofit.Builder()
                .baseUrl("$rawBaseUrl/")
                .client(okhttp)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(BLSApi::class.java)
        }
        // Общий клиент для экранов без NetworkRetry. Два таймаута отвечают на
        // РАЗНЫЕ вопросы, и брать их из одной ступени неверно:
        //   connect — есть ли вообще сеть. Ответ нужен быстро: офлайн-режиму
        //             незачем держать человека в ожидании, ради этого и
        //             заводились кеш и офлайн-подсказка.
        //   read    — насколько медленно отвечает ЖИВОЙ сервер. Генерация
        //             графиков статистики на холодном кеше занимает секунды,
        //             и при read 4 с картинки молча пропадали с экрана.
        // Взять целиком самую терпеливую ступень значило бы ждать 15 секунд,
        // чтобы узнать, что сети нет.
        val patient = OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectionPool(pool)
            .dispatcher(dispatcher)
            .connectTimeout(CONNECT_TIMEOUTS_MS.first().toLong(), TimeUnit.MILLISECONDS)
            .readTimeout(READ_TIMEOUT_MS, TimeUnit.MILLISECONDS)
            .writeTimeout(READ_TIMEOUT_MS, TimeUnit.MILLISECONDS)
            .retryOnConnectionFailure(false)
            .build()
        _api = Retrofit.Builder()
            .baseUrl("$rawBaseUrl/")
            .client(patient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(BLSApi::class.java)
    }

    /** Клиент для попытки номер [attempt] (с нуля); дальше последнего — самый терпеливый. */
    fun apiForAttempt(attempt: Int): BLSApi =
        _apis.getOrElse(attempt) { _apis.lastOrNull() ?: api }

    val attemptCount: Int get() = _apis.size.coerceAtLeast(1)

    val api: BLSApi get() = _api ?: error("BLSClient not initialized — call BLSClient.init(url) first")

    val isInitialized: Boolean get() = _api != null

    /** Full URL for a sound path, routed through BLS sound proxy. */
    fun soundUrl(path: String): String = "$rawBaseUrl/sounds/$path"
}
