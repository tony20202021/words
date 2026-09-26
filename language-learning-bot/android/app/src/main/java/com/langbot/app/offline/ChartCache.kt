package com.langbot.app.offline

import android.content.Context
import java.io.File

/**
 * Картинки графиков с прошлого показа — на диске телефона.
 *
 * В метро связь есть, но слабая, и семнадцать картинок по 19 КБ тянутся так
 * долго, что экран статистики бесполезен. Условие «сети нет» при этом не
 * срабатывает: сеть-то есть.
 *
 * Поэтому экран открывается на сохранённых картинках сразу, а свежие приходят
 * следом и подменяют их. Если данные с прошлого раза не изменились — версия та
 * же, — качать нечего вовсе: один короткий запрос вместо семнадцати картинок.
 *
 * Хранится только экранный вариант: большие (для увеличения) весят вчетверо
 * больше и нужны редко, их по-прежнему подкачивает сам экран.
 */
object ChartCache {
    private lateinit var appCtx: Context
    private val lock = Any()

    fun init(ctx: Context) { appCtx = ctx.applicationContext }
    private fun ready() = ::appCtx.isInitialized

    private fun dir(user: String, language: String): File =
        File(File(appCtx.filesDir, "charts"), "${safe(user)}_${safe(language)}")

    /** Имена приходят с сервера — в имени файла им доверять нельзя. */
    private fun safe(s: String) = s.replace(Regex("[^A-Za-z0-9_-]"), "_")

    private fun file(user: String, language: String, type: Int, name: String) =
        File(dir(user, language), "${type}_${safe(name)}.png")

    private fun versionFile(user: String, language: String) =
        File(dir(user, language), "version.txt")

    fun get(user: String, language: String, type: Int, name: String): ByteArray? =
        synchronized(lock) {
            if (!ready()) return null
            val f = file(user, language, type, name)
            if (!f.exists() || f.length() == 0L) return null
            return runCatching { f.readBytes() }.getOrNull()
        }

    fun put(user: String, language: String, type: Int, name: String, bytes: ByteArray) {
        synchronized(lock) {
            if (!ready() || bytes.isEmpty()) return
            runCatching {
                dir(user, language).mkdirs()
                file(user, language, type, name).writeBytes(bytes)
            }
        }
    }

    /** Версия данных, под которую сохранены картинки. */
    fun version(user: String, language: String): String? = synchronized(lock) {
        if (!ready()) return null
        val f = versionFile(user, language)
        if (!f.exists()) return null
        return runCatching { f.readText().trim().ifEmpty { null } }.getOrNull()
    }

    /**
     * Запомнить версию. Вызывать ТОЛЬКО когда скачаны все картинки: иначе
     * недокачанный набор выдаст себя за полный, и недостающие уже не приедут.
     */
    fun saveVersion(user: String, language: String, version: String) {
        synchronized(lock) {
            if (!ready() || version.isBlank()) return
            runCatching {
                dir(user, language).mkdirs()
                versionFile(user, language).writeText(version)
            }
        }
    }

    fun clearVersion(user: String, language: String) {
        synchronized(lock) { runCatching { versionFile(user, language).delete() } }
    }

    /** Есть ли хоть одна сохранённая картинка — по ней решают, заполнять ли экран. */
    fun hasAny(user: String, language: String): Boolean = synchronized(lock) {
        if (!ready()) return false
        val d = dir(user, language)
        return d.isDirectory && (d.listFiles()?.any { it.name.endsWith(".png") } == true)
    }
}
