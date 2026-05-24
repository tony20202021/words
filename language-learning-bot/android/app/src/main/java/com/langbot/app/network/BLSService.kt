package com.langbot.app.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

interface BLSApi {

    // Auth
    @POST("auth/mobile/activate")
    suspend fun activateMobileToken(@Body body: MobileActivateRequest): Response<MobileActivateResponse>

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
    suspend fun nextBatch(@Path("session_id") sessionId: String, @Body body: Map<String, String> = emptyMap()): Response<SessionResponse>

    @DELETE("session/{user_id}/{language_id}")
    suspend fun endSession(
        @Path("user_id") userId: String,
        @Path("language_id") languageId: String,
    ): Response<Unit>

    // Statistics
    @GET("statistics/{user_id}/{language_id}")
    suspend fun getStatistics(
        @Path("user_id") userId: String,
        @Path("language_id") languageId: String,
    ): Response<Statistics>
}

object BLSClient {
    private var _api: BLSApi? = null

    fun init(baseUrl: String) {
        val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
        val okhttp = OkHttpClient.Builder().addInterceptor(logging).build()
        _api = Retrofit.Builder()
            .baseUrl(if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/")
            .client(okhttp)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(BLSApi::class.java)
    }

    val api: BLSApi get() = _api ?: error("BLSClient not initialized — call BLSClient.init(url) first")
}
