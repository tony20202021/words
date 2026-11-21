# Источники данных и их лицензии

Часть данных в этом репозитории получена из чужих открытых источников. Ниже —
откуда взято, что из этого получилось и на каких условиях оно распространяется.
Лицензии ниже относятся к перечисленным файлам данных, а не к коду.

Приложение, бот и веб-версия показывают эти данные; в их «Помощи» есть
короткий перечень источников и ссылка на этот файл.

## Викисловарь

Источник: [английский](https://en.wiktionary.org) и
[русский](https://ru.wiktionary.org) Викисловари, авторы — участники
Викисловаря. Тексты Викисловаря доступны по лицензии
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) (и GNU FDL).

Как использован: огласовку, транскрипцию, часть речи и значение спорных слов
иврита (около 300) сверяли со статьями Викисловаря. В файлах
`words/hebrew_tools/reviews/*.json` вместе с нашими пояснениями приведены
короткие выдержки из статей: огласованная форма, транслитерация, часть речи.
Статьи изменены — из них взяты отдельные поля. Каждая выдержка относится к
статье Викисловаря с тем же заголовком, что и слово иврита в записи; авторы
статьи перечислены в истории её правок.

Файлы `words/hebrew_tools/reviews/*.json` распространяются по лицензии
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

## Викиданные

Ссылки вида `wd L214196` в тех же файлах — лексемы
[Викиданных](https://www.wikidata.org). Данные Викиданных — общественное
достояние ([CC0](https://creativecommons.org/publicdomain/zero/1.0/)).

## wordfreq

Источник: [wordfreq](https://github.com/rspeer/wordfreq) 3.1.1 — Robyn Speer.
(2022). rspeer/wordfreq: v3.0 (v3.0.2). Zenodo.
https://doi.org/10.5281/zenodo.7199437. Данные wordfreq доступны по лицензии
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

wordfreq сводит частоты из нескольких корпусов, в том числе:

- SUBTLEX (Marc Brysbaert и соавторы) — SUBTLEX is freely available data;
- [OpenSubtitles](https://www.opensubtitles.org);
- [Google Books Ngram Viewer](http://books.google.com/ngrams);
- Википедия, Leeds Internet Corpus, ParaCrawl.

Получено из него: `words/data/eng_freq/frequency.txt` — частотный список
английского. Порядок слов взят из wordfreq и изменён: убраны имена и мусор,
недостающие места добраны словами из глубины списка. Файл распространяется по
лицензии [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

## FrequencyWords

Источник: [FrequencyWords](https://github.com/hermitdave/FrequencyWords)
(Hermit Dave), частотный список иврита `content/2018/he/he_50k.txt`, собранный
по субтитрам [OpenSubtitles](https://www.opensubtitles.org) (корпус
[OpenSubtitles2018](http://opus.nlpl.eu/OpenSubtitles2018.php) в OPUS).
Содержимое FrequencyWords доступно по лицензии
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

Получено из него: список слов иврита в приложении и их номера. Список очищен:
убраны обрывки слов и мусор из субтитров, слова дополнены огласовкой,
транскрипцией и переводом. Сам список в репозиторий не входит.

## ipa-dict

Источник: [ipa-dict](https://github.com/open-dict-data/ipa-dict), лицензия MIT.
Английские данные (en_US) в нём основаны на cmudict-ipa (@lingz, MIT) с
ударениями от syllabify (@kylebgorman, MIT).

Получено из него: транскрипции английских слов в словаре и транскрипции
предложений `words/data/reading/en/sentences.json` (поле `tr`), собранные из них
по словам.

```
The MIT License (MIT)

Copyright (c) 2016 dohliam

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Голос noa для иврита (Piper)

Источник: модель синтеза речи
[piper-he-noa](https://huggingface.co/thewh1teagle/piper-he-noa) (he_IL-noa-medium,
автор — thewh1teagle), лицензия
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). По описанию модели,
она обучена на синтетической речи (Chatterbox) по предложениям из протоколов
Кнессета. Синтез — [Piper](https://github.com/OHF-Voice/piper1-gpl).

Получено из неё: четвёртый голос иврита, noa, — озвучка слов
(`backend/data/sounds/he/noa/`) и примеров для чтения
(`backend/data/sounds/he/reading/noa/`). Модель использована без изменений;
произношение подаётся ей нашей транскрипцией (`words/tts/piper_ipa.py`).
Сами звуковые файлы в репозиторий не входят — приложение получает их по сети.

## Списки имён

`words/data/eng_freq/names.txt` — подсказка «возможно, это имя», собрана из двух
списков:

- [dominictarr/random-name](https://github.com/dominictarr/random-name) (MIT);
  сами имена взяты оттуда из Moby Word List Грейди Уорда — общественное
  достояние;
- [hadley/data-baby-names](https://github.com/hadley/data-baby-names) — данные
  [Social Security Administration](https://www.ssa.gov/OACT/babynames/) США;
  работы федерального правительства США авторским правом не охраняются.
