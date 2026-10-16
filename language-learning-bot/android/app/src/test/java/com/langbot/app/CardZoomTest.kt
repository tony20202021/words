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
        // Из меню «Увеличить» открывается вся карточка с начала, и там
        // натуральная величина по-прежнему верна: увеличивать нечего — на
        // экране весь столбец, а не одна таблица.
        val a = open("tag_group")
        val column = column(a)
        a.onOptionsItemSelected(org.robolectric.fakes.RoboMenuItem(4 /* MENU_ZOOM */))
        val zoom = shownView(a, column.width, 891)

        assertEquals("карточка открылась не в натуральную величину",
            1f, zoom.currentScale, 0.01f)
        assertEquals("карточку нельзя увеличить впятеро",
            5f, zoom.maxScale, 0.01f)
        // Уменьшить до вписанной в экран — чтобы увидеть её целиком.
        assertTrue("карточку нельзя уменьшить до целой: ${zoom.minScale}",
            zoom.minScale < 1f)
    }

    /** Первая строка таблицы внутри блока: ряд ровно из четырёх ячеек. */
    private fun tableRow(v: View): ViewGroup? {
        val g = v as? ViewGroup ?: return null
        if (g is android.widget.LinearLayout &&
            g.orientation == android.widget.LinearLayout.HORIZONTAL &&
            g.childCount == 4 &&
            (0 until 4).all { g.getChildAt(it) is android.widget.TextView }) return g
        for (i in 0 until g.childCount) tableRow(g.getChildAt(i))?.let { return it }
        return null
    }

    /** Ближайшая надпись над таблицей — её заголовок. */
    private fun headingAbove(table: View): View? {
        val parent = table.parent as? ViewGroup ?: return null
        for (i in parent.indexOfChild(table) - 1 downTo 0) {
            val v = parent.getChildAt(i)
            if (v.visibility != View.VISIBLE) continue
            return if (v is android.widget.TextView && v.text.isNotBlank()) v else null
        }
        return null
    }

    private fun topWithin(v: View, root: View): Int {
        var y = 0
        var cur: View? = v
        while (cur != null && cur !== root) { y += cur.top; cur = cur.parent as? View }
        return y
    }

    @Test
    fun a_tapped_table_opens_enlarged_on_its_readable_columns() {
        """
        Просьба владельца: «экран увеличения экстра инфо открывается в размере
        в точности как исходный — надо крупнее; по ширине чтобы примерно было
        показано 2 столбика, русский перевод и иностранное слово; по высоте
        чтобы верхняя граница таблицы была по верхней границе экрана».

        Читают в таблице две колонки из четырёх — перевод и само слово. Их и
        растягиваем на всю ширину; номер слева и транскрипция справа уезжают
        за край, к ним можно отлистнуть.
        """
        val a = open("tag_group")
        val column = column(a)
        val block = blocks(a).getChildAt(0)
        val row = tableRow(block)
        assertNotNull("в блоке нет таблицы — проверять нечего", row)
        val readable = row!!.getChildAt(1).width + row.getChildAt(2).width
        assertTrue("колонки не разложены", readable > 0)
        val table = row.parent as View
        val tableTop = topWithin(table, column)
        val heading = headingAbove(table)
        assertNotNull("над таблицей нет заголовка — проверять нечего", heading)
        val headingTop = topWithin(heading!!, column)

        block.performClick()
        // Окно берём не выше остатка карточки под заголовком: иначе сдвиг
        // упрётся в нижний край, вернётся назад и проверял бы уже не это.
        val margin = column.width * ZoomImageView.FOCUS_MARGIN
        val scale = (column.width - 2 * margin) / readable
        val screen = minOf(891, ((column.height - headingTop) * scale).toInt())
        assertTrue("под таблицей почти ничего нет — проверять нечего", screen >= 200)
        val zoom = shownView(a, column.width, screen)

        assertEquals("две читаемые колонки заняли не ту ширину",
            scale, zoom.currentScale, 0.02f)
        assertTrue("таблица открылась в исходном размере — это не увеличение",
            zoom.currentScale > 1.1f)
        // Просьба владельца: сверху не по границе таблицы, а чтобы влез
        // заголовок над ней, и тоже чуть с запасом.
        assertEquals("показ начался не с заголовка над таблицей",
            margin - headingTop * zoom.currentScale, translationY(zoom), 2f)
        val headingOnScreen = translationY(zoom) + headingTop * zoom.currentScale
        assertTrue("заголовок оказался за верхним краем: $headingOnScreen",
            headingOnScreen >= 0f)
        assertTrue("начали всё-таки с сетки, а не с заголовка",
            translationY(zoom) + tableTop * zoom.currentScale > headingOnScreen)
    }

    @Test
    fun the_table_lines_stay_inside_the_screen() {
        """
        Просьба владельца: «чуть уменьшить финальный размер, чтобы были чуть
        видны линии таблицы сверху и по бокам».

        Раньше читаемые колонки занимали ровно всю ширину, и границы колонок
        стояли по самому краю экрана — половина каждой уходила за него. Теперь
        по краям остаётся отступ, и по нему же видно краешек соседних колонок:
        понятно, что можно отлистнуть.
        """
        val a = open("tag_group")
        val column = column(a)
        val block = blocks(a).getChildAt(0)
        val row = tableRow(block)!!
        val readable = row.getChildAt(1).width + row.getChildAt(2).width
        val table = row.parent as View
        val top = topWithin(headingAbove(table) ?: table, column)

        block.performClick()
        val margin = column.width * ZoomImageView.FOCUS_MARGIN
        val scale = (column.width - 2 * margin) / readable
        val screen = minOf(891, ((column.height - top) * scale).toInt())
        val zoom = shownView(a, column.width, screen)

        assertTrue("отступ по краям не оставлен — линии таблицы режутся краем",
            margin > 1f)
        assertEquals("верх прижат к краю экрана вплотную",
            margin - top * zoom.currentScale, translationY(zoom), 2f)
        assertTrue("увеличение съело отступ и снова встало впритык",
            zoom.currentScale < column.width.toFloat() / readable)
    }

    @Test
    fun a_block_without_a_table_still_opens_at_its_own_size() {
        """
        Увеличение по колонкам — свойство таблицы, а не всякого блока. У блока
        без таблицы растягивать нечего, и он открывается как раньше: в
        натуральную величину, с той высоты, по которой нажали.
        """
        val a = open("tag_group")
        val column = column(a)
        val plain = (0 until blocks(a).childCount)
            .map { blocks(a).getChildAt(it) }
            .firstOrNull { tableRow(it) == null }
            ?: return    // в этой карточке все блоки с таблицами — проверять нечего
        val expectedTop = topWithin(plain, column)
        plain.performClick()
        val zoom = shownView(a, column.width, minOf(891, column.height - expectedTop))
        assertEquals("блок без таблицы открылся не в натуральную величину",
            1f, zoom.currentScale, 0.01f)
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
    @Test
    fun a_double_tap_opens_only_one_window() {
        """
        Жалоба владельца: «если нажать быстро 2 раза — открываются 2
        увеличенных картинки».

        Поле cardZoomDialog помнит только последнее окно, поэтому первое
        оставалось висеть под вторым: возврат убирал верхнее, а под ним было
        такое же. Второе нажатие при открытом окне теперь ничего не делает.
        """
        val a = open("tag_group")
        val block = blocks(a).getChildAt(0)

        block.performClick()
        val first = a.cardZoomDialog
        assertNotNull("окно увеличения не открылось", first)

        block.performClick()
        assertTrue("второе нажатие открыло второе окно поверх первого",
            a.cardZoomDialog === first)
        assertTrue("первое окно закрылось от второго нажатия", first!!.isShowing)

        // И то же через пункт меню: путь другой, окно должно остаться одно.
        a.onOptionsItemSelected(org.robolectric.fakes.RoboMenuItem(4 /* MENU_ZOOM */))
        assertTrue("пункт меню открыл второе окно поверх первого",
            a.cardZoomDialog === first)

        // Закрыли — и следующее нажатие снова открывает.
        first.dismiss()
        org.robolectric.shadows.ShadowLooper.idleMainLooper()
        block.performClick()
        assertNotNull("после закрытия окно больше не открывается", a.cardZoomDialog)
    }

}
