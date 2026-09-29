package com.langbot.app

import android.content.Intent
import android.graphics.Matrix
import android.graphics.drawable.PictureDrawable
import android.view.View
import android.view.ViewGroup
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File

/**
 * Увеличение карточки слова.
 *
 * Владелец просил увеличивать не только картинки: таблицы экстра инфо — текст,
 * и огласовки в них в обычном кегле не разглядеть. Нажатие на блок открывает
 * карточку целиком на весь экран.
 *
 * Проверяется то, ради чего это делалось: открывается ВСЯ карточка, включая
 * то, что ниже края экрана; открывается в натуральную величину, а не вписанной
 * в экран (вписанная была бы мельче исходной и совсем нечитаемой); и открывается
 * с того блока, по которому нажали.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(qualifiers = "w411dp-h891dp-xhdpi")
class CardZoomTest {

    private lateinit var server: MockWebServer
    private var cardJson: String = "{}"

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        UserPrefs.saveUserId(ctx, "user-1")
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                return if ((request.path ?: "").startsWith("/session/")) {
                    MockResponse().setResponseCode(200)
                        .setBody("""{"session_id":"sid-1","card":$cardJson}""")
                } else MockResponse().setResponseCode(404)
            }
        }
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() {
        runCatching { server.shutdown() }
    }

    private fun open(fixture: String): StudyActivity {
        val file = File("src/test/resources/cards/$fixture.json")
        assertTrue("нет фикстуры $fixture — сначала make_card_fixtures.py", file.exists())
        cardJson = file.readText()
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", "lang-1")
            .putExtra("language_name", "Иврит")
        val activity = Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
        Screenshots.pumpUntil("$fixture: карточка отрисована") {
            activity.findViewById<ViewGroup>(R.id.extraCardsArea).childCount > 0
        }
        Screenshots.render(Screenshots.scrollColumnOrRoot(activity, R.id.swipeRefresh))
        return activity
    }

    private fun column(a: StudyActivity): ViewGroup = a.findViewById(R.id.cardScrollContent)
    private fun blocks(a: StudyActivity): ViewGroup = a.findViewById(R.id.extraCardsArea)

    /** Окно увеличения не раскладывается само: размер ему задаёт тест. */
    private fun shownView(a: StudyActivity, w: Int, h: Int): ZoomImageView {
        val dialog = a.cardZoomDialog
        assertNotNull("окно увеличения не открылось", dialog)
        assertTrue("окно увеличения закрыто", dialog!!.isShowing)
        val content = dialog.findViewById<ViewGroup>(android.R.id.content)
        val zoom = generateSequence(content?.getChildAt(0)) { v ->
            (v as? ViewGroup)?.getChildAt(0)
        }.filterIsInstance<ZoomImageView>().firstOrNull()
        assertNotNull("в окне нет увеличиваемой карточки: ${content?.getChildAt(0)}", zoom)
        zoom!!.measure(View.MeasureSpec.makeMeasureSpec(w, View.MeasureSpec.EXACTLY),
                       View.MeasureSpec.makeMeasureSpec(h, View.MeasureSpec.EXACTLY))
        zoom.layout(0, 0, w, h)
        return zoom
    }

    private fun translationY(view: ZoomImageView): Float =
        FloatArray(9).also { view.imageMatrix.getValues(it) }[Matrix.MTRANS_Y]

    @Test
    fun tapping_a_table_opens_the_whole_card_not_just_the_visible_part() {
        val a = open("tag_group")
        val column = column(a)
        val block = blocks(a).getChildAt(blocks(a).childCount - 1)
        assertTrue("по блоку экстра инфо нельзя нажать", block.isClickable)
        block.performClick()

        val zoom = shownView(a, column.width, 891)
        val drawing = zoom.drawable as? PictureDrawable
        assertNotNull("карточка показана не рисунком: ${zoom.drawable}", drawing)
        assertEquals("в рисунок попала не вся ширина карточки",
            column.width, drawing!!.intrinsicWidth)
        // Столбец длиннее экрана: увеличение не должно обрываться там, где
        // кончается видимая часть.
        assertEquals("в рисунок попала не вся карточка",
            column.height, drawing.intrinsicHeight)
    }

    @Test
    fun opening_and_closing_are_animated() {
        """
        Просьба владельца: «путается момент перехода». Окно теперь вырастает из
        середины и уменьшается обратно, а не подменяется мгновенно.
        """
        val a = open("tag_group")
        blocks(a).getChildAt(0).performClick()

        val window = a.cardZoomDialog!!.window!!
        assertEquals("переход в увеличение без анимации",
            R.style.ZoomDialogAnimation, window.attributes.windowAnimations)
    }

    @Test
    fun the_picture_is_framed_while_it_moves_and_bare_while_it_is_read() {
        """
        Просьба владельца: рамка вокруг картинки, пока она разворачивается и
        пока сходится обратно в точку. Читать карточку в рамке незачем.
        """
        val a = open("tag_group")
        blocks(a).getChildAt(0).performClick()
        val dialog = a.cardZoomDialog!!
        val box = dialog.findViewById<ViewGroup>(android.R.id.content).getChildAt(0) as ViewGroup
        val zoom = box.getChildAt(0) as ZoomImageView

        // Рамка — на обёртке: она отступает от строки состояния и от полосы
        // навигации, поэтому ложится ровно со всех сторон.
        assertTrue("во время разворачивания рамки нет: ${box.background}",
            box.background is android.graphics.drawable.GradientDrawable)

        // Рамка снимается отложенной задачей: в тестах часы виртуальные, и
        // просто «покрутить looper» мало — надо продвинуть время.
        org.robolectric.shadows.ShadowLooper.idleMainLooper(
            StudyActivity.ZOOM_ENTER_MS + 50, java.util.concurrent.TimeUnit.MILLISECONDS)
        assertTrue("после движения рамка осталась: ${box.background}",
            box.background !is android.graphics.drawable.GradientDrawable)

        dialog.dismiss()
        // Закрытие приходит через очередь сообщений — даём ей провернуться.
        org.robolectric.shadows.ShadowLooper.idleMainLooper()
        assertTrue("на возврате рамка не вернулась: ${box.background}",
            box.background is android.graphics.drawable.GradientDrawable)
    }

    @Test
    fun the_picture_stays_while_the_closing_animation_plays() {
        """
        Владелец: «уменьшение при возврате не видно». onDismiss приходит в
        начале закрытия, и прежняя очистка гасила картинку до того, как отыграет
        анимация: окно уезжало пустым.
        """
        val a = open("tag_group")
        blocks(a).getChildAt(0).performClick()
        val dialog = a.cardZoomDialog!!
        val box = dialog.findViewById<ViewGroup>(android.R.id.content).getChildAt(0) as ViewGroup
        val zoom = box.getChildAt(0) as ZoomImageView

        dialog.dismiss()
        assertNotNull("картинку стёрли до конца анимации", zoom.drawable)
    }

    @Test
    fun the_card_opens_at_its_own_size_and_can_be_enlarged_five_times() {
        val a = open("tag_group")
        val column = column(a)
        blocks(a).getChildAt(0).performClick()
        val zoom = shownView(a, column.width, 891)

        assertEquals("карточка открылась не в натуральную величину",
            1f, zoom.currentScale, 0.01f)
        assertEquals("карточку нельзя увеличить впятеро",
            5f, zoom.maxScale, 0.01f)
        // Уменьшить до вписанной в экран — чтобы увидеть её целиком.
        assertTrue("карточку нельзя уменьшить до целой: ${zoom.minScale}",
            zoom.minScale < 1f)
    }

    @Test
    fun the_tapped_table_is_what_opens_first() {
        val a = open("tag_group")
        val column = column(a)
        val block = blocks(a).getChildAt(0)
        val expectedTop = blocks(a).top + block.top
        assertTrue("блок стоит в самом верху — проверять нечего", expectedTop > 0)
        // Окно берём не выше остатка карточки под блоком: иначе сдвиг упрётся в
        // нижний край, вернётся назад и проверял бы уже не выбор блока.
        val screen = minOf(891, column.height - expectedTop)
        assertTrue("под блоком почти ничего нет (карточка ${column.height}, " +
            "блок на $expectedTop) — проверять нечего", screen >= 200)
        block.performClick()

        val zoom = shownView(a, column.width, screen)
        assertEquals("окно открылось не на том блоке, по которому нажали",
            -expectedTop.toFloat(), translationY(zoom), 2f)
    }

    @Test
    fun the_menu_opens_the_card_from_its_top() {
        val a = open("tag_group")
        val column = column(a)
        a.onOptionsItemSelected(org.robolectric.fakes.RoboMenuItem(4 /* MENU_ZOOM */))
        val zoom = shownView(a, column.width, 891)
        assertEquals("пункт меню открыл карточку не с начала",
            0f, translationY(zoom), 2f)
    }
}
