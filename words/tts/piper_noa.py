#!/usr/bin/env python3
"""Голос Piper noa (иврит) — четвёртый голос слов и примеров для чтения.

Модель he_IL-noa-medium (Hugging Face thewh1teagle/piper-he-noa, CC BY 4.0 —
указано в DATA_SOURCES.md и в «Помощи»). Владелец выбрал её 21.11.2026 по
образцам: темп — на 20% медленнее обычного («Б комфортнее всего»),
предложение — целиком, слова через шесть пробелов, без знаков (вариант O;
почему не иначе — piper_ipa.фраза_для_модели).

Произношение — наша транскрипция (в ней выверены омографы), переведённая в
запись модели (piper_ipa.py). Где её нет или в ней «?» — разбор renikud.

Работает в своём окружении: Piper и renikud требуют Python 3.12.
    ~/tools/piper-env/bin/python words/tts/piper_noa.py sentences [--limit 20]
    ~/tools/piper-env/bin/python words/tts/piper_noa.py words [--limit 20] [--write-db]

Готовые непустые файлы пропускаются — повторный запуск продолжает с места.
Пути примеров в базу кладёт words/reading/load_to_db.py; пути слов —
`words --write-db` (ключ sound_4 в поле sounds).
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import numpy as np

ТУТ = Path(__file__).resolve().parent
sys.path.insert(0, str(ТУТ))
sys.path.insert(0, str(ТУТ.parent / "reading"))

from piper_ipa import (в_запись_модели, обрезать_тишину, первый_вариант,  # noqa: E402
                       фраза_для_модели)
from sounds import КОРЕНЬ, путь  # noqa: E402

МОДЕЛЬ = Path.home() / "tools" / "piper-voices" / "he_IL-noa" / "he_IL-noa-medium.onnx"
ТЕМП = 1.2          # length_scale: на 20% медленнее
ГОЛОС = "noa"
КЛЮЧ_СЛОВА = "sound_4"
ПРЕДЛОЖЕНИЯ = ТУТ.parent / "data" / "reading" / "he" / "sentences.json"


class Голос:
    def __init__(self):
        from piper import PiperVoice, SynthesisConfig
        from renikud_onnx import G2P
        self.voice = PiperVoice.load(str(МОДЕЛЬ))
        self.sr = self.voice.config.sample_rate
        self.syn = SynthesisConfig(speaker_id=0, length_scale=ТЕМП, noise_w_scale=0.6)
        self.g2p = G2P()

    def _звук(self, запись: str) -> np.ndarray:
        ids = self.voice.phonemes_to_ids(list(запись))
        a = self.voice.phoneme_ids_to_audio(ids, self.syn)
        return np.asarray(a[0] if isinstance(a, tuple) else a, dtype=np.float32)

    def запись(self, ipa: str, текст: str, фраза: bool) -> str:
        """Наша транскрипция, а если её нет или в ней дыра — renikud.

        renikud отдаёт запись уже в виде модели; для фразы из неё так же
        убираются знаки и слова разводятся шестью пробелами."""
        if ipa and "?" not in ipa:
            return фраза_для_модели(ipa) if фраза else в_запись_модели(ipa)
        разбор = self.g2p.phonemize(текст)
        if not фраза:
            return разбор
        чистый = "".join(ch for ch in разбор if ch not in ",.;:!?")
        return "      ".join(чистый.split())

    def синтез(self, запись: str) -> np.ndarray:
        return обрезать_тишину(self._звук(запись), self.sr)


def сохранить_mp3(звук: np.ndarray, sr: int, куда: Path) -> bool:
    if звук.size == 0:
        return False
    куда.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(звук, -1, 1) * 32767).astype(np.int16)
    with tempfile.TemporaryDirectory() as tmp:
        wav, mp3 = Path(tmp) / "a.wav", Path(tmp) / "a.mp3"
        with wave.open(str(wav), "wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr); f.writeframes(pcm.tobytes())
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                            "-b:a", "48k", str(mp3)])
        if r.returncode != 0 or not mp3.exists() or mp3.stat().st_size == 0:
            return False
        os.replace(mp3, куда)      # целиком или никак: оборванный файл не останется
    return True


def готов(f: Path) -> bool:
    return f.is_file() and f.stat().st_size > 0


def предложения(голос: Голос, предел: int) -> int:
    данные = json.loads(ПРЕДЛОЖЕНИЯ.read_text(encoding="utf-8"))
    задания, было = [], set()
    for номер in sorted(данные, key=int):
        for п in данные[номер]:
            т = п.get("text", "")
            if т and т not in было:
                было.add(т)
                задания.append((т, п.get("tr", "")))
    if предел:
        задания = задания[:предел]
    сделать = [(т, тр) for т, тр in задания if not готов(КОРЕНЬ / путь("he", ГОЛОС, т))]
    print(f"предложений {len(задания)}, сделать {len(сделать)}", flush=True)
    сбои = 0
    for i, (т, тр) in enumerate(сделать, 1):
        ok = сохранить_mp3(голос.синтез(голос.запись(тр, т, фраза=True)), голос.sr,
                           КОРЕНЬ / путь("he", ГОЛОС, т))
        сбои += not ok
        if i % 200 == 0 or i == len(сделать):
            print(f"  {i}/{len(сделать)}  сбоев {сбои}", flush=True)
    return сбои


def база():
    from pymongo import MongoClient
    db = MongoClient(os.getenv("MONGODB_URL", "mongodb://localhost:8527"),
                     serverSelectionTimeoutMS=5000)[os.getenv("MONGODB_DB_NAME", "language_learning_bot")]
    язык = db.languages.find_one({"name_ru": "Иврит"})
    if not язык:
        raise SystemExit("языка «Иврит» в базе нет")
    return db, язык["_id"]


def путь_слова(номер: int) -> str:
    """Как у остальных голосов иврита: файл по номеру слова (sounds/he/hila/4.mp3)."""
    return f"sounds/he/{ГОЛОС}/{номер}.mp3"


def слова(голос: Голос, предел: int, в_базу: bool) -> int:
    db, язык = база()
    q = db.words.find({"language_id": язык},
                      {"word_number": 1, "word_foreign": 1, "word_foreign_simple": 1,
                       "transcription": 1, "sounds": 1}).sort("word_number", 1)
    все = list(q.limit(предел) if предел else q)
    сделать = [w for w in все if not готов(КОРЕНЬ / путь_слова(w["word_number"]))]
    print(f"слов {len(все)}, сделать {len(сделать)}", flush=True)
    сбои = 0
    for i, w in enumerate(сделать, 1):
        текст = w.get("word_foreign_simple") or w.get("word_foreign") or ""
        ipa = первый_вариант(w.get("transcription", ""))
        ok = сохранить_mp3(голос.синтез(голос.запись(ipa, текст, фраза=False)), голос.sr,
                           КОРЕНЬ / путь_слова(w["word_number"]))
        сбои += not ok
        if i % 500 == 0 or i == len(сделать):
            print(f"  {i}/{len(сделать)}  сбоев {сбои}", flush=True)
    if в_базу:
        from pymongo import UpdateOne
        записи = []
        for w in все:
            p = путь_слова(w["word_number"])
            if not готов(КОРЕНЬ / p):
                continue
            try:
                звуки = json.loads(w.get("sounds") or "{}")
            except ValueError:
                звуки = {}
            if not isinstance(звуки, dict) or звуки.get(КЛЮЧ_СЛОВА) == p:
                continue
            звуки[КЛЮЧ_СЛОВА] = p
            записи.append(UpdateOne({"_id": w["_id"]}, {"$set": {"sounds": json.dumps(звуки)}}))
        if записи:
            db.words.bulk_write(записи, ordered=False)
        print(f"в базе добавлен {КЛЮЧ_СЛОВА}: {len(записи)} слов", flush=True)
    return сбои


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["sentences", "words"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--write-db", action="store_true", help="words: записать sound_4 в базу")
    a = ap.parse_args()
    начало = time.time()
    голос = Голос()
    сбои = (предложения(голос, a.limit) if a.what == "sentences"
            else слова(голос, a.limit, a.write_db))
    print(f"готово за {(time.time() - начало) / 60:.1f} мин, сбоев {сбои}", flush=True)
    return 0 if not сбои else 2


if __name__ == "__main__":
    sys.exit(main())
