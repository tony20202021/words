/*
 * Поведение карточки слова: звук и индикатор загрузки.
 *
 * Раньше этот код лежал прямо в partials/word_card.html — то есть внутри
 * фрагмента, который HTMX подставляет по hx-swap. Скрипт из свопнутого
 * фрагмента браузер выполняет заново, и каждый ответ сервера добавлял ещё три
 * обработчика на document (htmx:afterSwap, htmx:responseError, htmx:sendError).
 * Снятия не было: после сессии в 50 слов их набиралось полторы сотни, и одна
 * сетевая ошибка запускала window.location.reload() десятки раз подряд.
 *
 * Теперь файл подключается из base.html ровно один раз за загрузку страницы, а
 * на кнопки карточки мы смотрим делегированием — свопы их больше не касаются.
 */

// ── Звук: одна дорожка на страницу ───────────────────────────────────────────
// Варианты произношения проигрываются цепочкой с паузой между ними. Без общего
// владельца нажатие на другой вариант просто запускало вторую цепочку, и они
// звучали одновременно — а нажимают именно потому, что по первому звуку уже
// понятно, что слово не то. Поэтому любое воспроизведение сначала обрывает
// предыдущее: и сам звук, и отложенный переход к следующему в цепочке.
var LBSounds = (function () {
  var gen = 0, current = null, timer = null;

  function stop() {
    // Счётчик поколений, а не только pause(): цепочку держит ещё и таймер
    // паузы, и без этого следующий звук всё равно зазвучал бы через 350 мс.
    gen++;
    if (timer) { clearTimeout(timer); timer = null; }
    if (current) {
      try { current.pause(); current.currentTime = 0; } catch (e) {}
      current.onended = null;
      current = null;
    }
  }

  function play(ids) {
    stop();
    var mine = gen, i = 0;
    (function next() {
      if (mine !== gen || i >= ids.length) return;
      var a = document.getElementById(ids[i++]);
      // Пропускаем звуки, которые не загрузились: onerror прячет обёртку.
      if (!a || (a.parentElement && a.parentElement.style.display === 'none')) { next(); return; }
      current = a;
      a.onended = function () { if (mine === gen) timer = setTimeout(next, 350); };
      // play() отклоняется и когда мы сами прервали его — проверка поколения внутри next().
      a.play().catch(function () { next(); });
    })();
  }

  return { play: play, stop: stop };
})();

function playSounds(ids) { LBSounds.play(ids); }

(function () {
  var _htmxTimeout = null;

  function onBtnClick() {
    // Уходим с карточки — звук предыдущей не должен доигрывать поверх следующей.
    // HTMX выбрасывает <audio> из DOM, но отсоединённый элемент продолжает играть.
    LBSounds.stop();
    clearTimeout(_htmxTimeout);
    _htmxTimeout = setTimeout(function () { window.location.reload(); }, 8000);
    var overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.style.display = 'flex';
    document.querySelectorAll('#word-area .btn-rate').forEach(function (b) {
      b.disabled = true;
      b.style.pointerEvents = 'none';
    });
  }

  function onDone() {
    clearTimeout(_htmxTimeout);
    // overlay is inside #word-area → removed by HTMX swap; hide explicitly on error
    var overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.style.display = 'none';
  }

  // Делегирование, а не навешивание на каждую кнопку: кнопки приезжают новыми
  // с каждым свопом, а обработчик остаётся один и переживает любое их число.
  document.addEventListener('click', function (e) {
    var target = e.target && e.target.closest ? e.target.closest('[hx-post]') : null;
    if (target) onBtnClick();
  });
  document.addEventListener('htmx:afterSwap', onDone);
  document.addEventListener('htmx:responseError', function () { onDone(); window.location.reload(); });
  document.addEventListener('htmx:sendError', function () { onDone(); window.location.reload(); });
})();
