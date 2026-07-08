"""
Quiz (pick-mode) service.

Generates multiple-choice options for the current word.
The user sees a "source" (determined by show_mode) and must pick the correct
"target" from N+1 options (1 correct + N distractors).

Probability weighting:
  p(word_number) ∝ 1/word_number, with a floor so the ratio between the
  most-probable and least-probable word never exceeds PROB_MAX_RATIO.
  This makes high-frequency words (low numbers) more likely as distractors
  while still keeping lower-frequency words reachable.

  Boost: words the user answered incorrectly (score=0 in user_word_data) get
  a probability boost equal to the maximum weight (i.e. weight of word #1).
  NOTE: boost applies only for words already in the session batch (whose
  user_word_data is loaded). Cross-batch boost is a future improvement.
"""

import random
import math
import json
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple
from app.logger import setup_logger

logger = setup_logger(__name__)

PROB_MAX_RATIO = 20  # max(weight) / min(weight) cap

# Modalities that can be used as quiz source / target
MODALITIES = ["translation", "foreign", "transcription", "sound"]


def _unit_count(text: str) -> int:
    """
    Count the meaningful units in a text for word-count filtering.
    For CJK text (Chinese characters, no spaces) each character is one syllable,
    so we count characters. For all other text we count whitespace-separated words.
    """
    if any('一' <= c <= '鿿' for c in text):
        return len(text)
    return len(text.split())


def _strip_tones(text: str) -> str:
    """Remove combining diacritical marks (tone marks) from pinyin/transcription text."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def _shared_unit_set(correct_text: str, target_modality: str) -> Set[str]:
    """
    Returns the set of 'units' from the correct answer used to boost distractors
    that share parts with the correct answer (making the question harder).
    - foreign + CJK: individual characters (e.g. {'结', '构'} for '结构')
    - transcription: tone-stripped syllables (e.g. {'jie', 'gou'} for '[jié gòu]')
    - other modalities: empty set (no boost)
    """
    if target_modality == "foreign":
        if any('一' <= c <= '鿿' for c in correct_text):
            return set(correct_text)
    elif target_modality == "transcription":
        stripped = _strip_tones(correct_text.lower())
        cleaned = stripped.replace('[', '').replace(']', '').strip()
        return {s for s in cleaned.split() if s}
    return set()


def _shares_units(text: str, correct_units: Set[str], target_modality: str) -> bool:
    """True if text shares at least one unit (char or syllable) with correct_units."""
    if not correct_units:
        return False
    if target_modality == "foreign":
        return any(c in correct_units for c in text)
    if target_modality == "transcription":
        stripped = _strip_tones(text.lower())
        cleaned = stripped.replace('[', '').replace(']', '').strip()
        return bool({s for s in cleaned.split() if s} & correct_units)
    return False


def _collect_distractors(
    candidates: List[Dict],
    correct_id: str,
    correct_text: str,
    forbidden_ids: Set[str],
    n: int,
    target_modality: str,
    correct_units: Set[str],
    unit_count_filter: Optional[int] = None,
) -> List[Dict]:
    """
    Collect up to n distractors from candidates, preferring those that share
    units (chars/syllables) with the correct answer to produce harder questions.
    Shared-unit candidates appear first; others fill remaining slots.
    Optionally filters by unit count.
    """
    shared: List[Dict] = []
    other: List[Dict] = []
    for c in candidates:
        cid = str(c.get("_id") or c.get("id") or "")
        if cid == correct_id or cid in forbidden_ids:
            continue
        text = _get_text_for_modality(c, target_modality)
        if not text or text == correct_text:
            continue
        if unit_count_filter is not None and _unit_count(text) != unit_count_filter:
            continue
        entry = {"word_id": cid, "target_text": text, "is_correct": False}
        if _shares_units(text, correct_units, target_modality):
            shared.append(entry)
        else:
            other.append(entry)
        if len(shared) + len(other) >= n * 4:
            break
    return (shared + other)[:n]


def _weighted_sample(word_numbers: List[int], count: int, exclude: int) -> List[int]:
    """
    Sample `count` unique word numbers from `word_numbers` (excluding `exclude`),
    using weights inversely proportional to log10(word_number).
    Ratio between word #1 and word #1000 is ~4x (log10 scale:
    1→×1, 10→×2, 100→×3, 1000→×4), much flatter than the old 1/n formula.
    """
    pool = [n for n in word_numbers if n != exclude]
    if not pool:
        return []
    count = min(count, len(pool))

    raw = [1.0 / (math.log10(n) + 1) for n in pool]
    max_w = max(raw)
    floor_w = max_w / PROB_MAX_RATIO
    weights = [max(w, floor_w) for w in raw]

    # random.choices allows repeats — use without-replacement loop
    chosen: List[int] = []
    remaining = list(zip(pool, weights))
    for _ in range(count):
        if not remaining:
            break
        nums, wts = zip(*remaining)
        idx = random.choices(range(len(nums)), weights=wts, k=1)[0]
        chosen.append(nums[idx])
        remaining = [r for i, r in enumerate(remaining) if i != idx]
    return chosen


def _get_text_for_modality(word: Dict[str, Any], modality: str) -> Optional[str]:
    """Extract the display text for a given modality from a word dict."""
    if modality == "translation":
        return (word.get("translation") or "").strip() or None
    if modality == "foreign":
        return (word.get("word_foreign") or "").strip() or None
    if modality == "transcription":
        t = (word.get("transcription") or "").strip()
        return f"[{t}]" if t else None
    if modality == "sound":
        raw = word.get("sounds")
        if not raw:
            return None
        try:
            data = json.loads(raw)
            if isinstance(data, str):
                data = json.loads(data)
            urls = [data[k] for k in sorted(data.keys()) if data[k]]
            return urls[0] if urls else None
        except Exception:
            return None
    return None


def _choose_target_modality(show_mode: str, settings: Dict[str, Any]) -> str:
    """
    Pick a target modality different from show_mode, from the enabled pool.
    Pool: always [translation, foreign]; add transcription / sound when enabled.
    """
    pool = ["translation", "foreign"]
    if settings.get("random_transcription", True):
        pool.append("transcription")
    if settings.get("random_sound", True) and settings.get("show_sounds", True):
        pool.append("sound")

    candidates = [m for m in pool if m != show_mode]
    if not candidates:
        # fallback: use something different from show_mode
        candidates = [m for m in MODALITIES if m != show_mode]
    return random.choice(candidates)


async def generate_quiz_options(
    session: Dict[str, Any],
    word: Dict[str, Any],
    api_client,
) -> Optional[Dict[str, Any]]:
    """
    Generate quiz options for the current word.

    Returns a dict:
      {
        "target_modality": str,
        "options": [
          {"word_id": str, "target_text": str, "is_correct": bool},
          ...
        ]
      }
    or None if quiz mode is not possible (not enough words, no valid target text, etc.).
    """
    settings = session.get("settings", {})
    words_studied = session.get("words_studied", 0)
    n_distractors = int(settings.get("quiz_options_count", 3))
    language_id = session.get("language_id", "")
    show_mode = session.get("show_mode", "foreign")
    current_word_number = (word or {}).get("word_number", 0)

    # Need at least 1 distractor
    if words_studied < 2:
        logger.info("quiz: not enough studied words, skipping pick mode")
        return None

    target_modality = _choose_target_modality(show_mode, settings)

    # Correct answer text
    correct_text = _get_text_for_modality(word, target_modality)
    if not correct_text:
        logger.info(f"quiz: no text for target_modality={target_modality} on current word")
        return None

    correct_id = str(word.get("_id") or word.get("id") or word.get("word_id") or "")
    forbidden_ids = set((word.get("user_word_data") or {}).get("forbidden_quiz_pairs") or [])

    # When source is foreign or transcription, distractors must match the word
    # count of the correct answer — otherwise trivial to guess by counting words.
    apply_word_count_filter = show_mode in ("foreign", "transcription")
    correct_word_count = _unit_count(correct_text) if apply_word_count_filter else 0

    # Shared-unit boost: prefer distractors sharing chars (CJK) or syllables (transcription)
    # with the correct answer — produces harder, more plausible questions.
    correct_units = _shared_unit_set(correct_text, target_modality)

    # Boost: words in the current session batch that have score=0 get high weight
    session_words = session.get("words", [])
    boosted_numbers = {
        w.get("word_number")
        for w in session_words
        if w.get("word_number") and
        ((w.get("user_word_data") or {}).get("score") == 0)
    }

    # Generate candidate word numbers using weighted sampling.
    # Fetch more candidates when unit-count filter or shared-unit boost is active.
    has_strict_filter = apply_word_count_filter or bool(correct_units)
    fetch_multiplier = 12 if has_strict_filter else 4
    fetch_n = min(n_distractors * fetch_multiplier, words_studied - 1)
    fetch_n = max(fetch_n, n_distractors + 1)

    all_numbers = list(range(1, words_studied + 1))
    # Apply boost: duplicate boosted numbers proportionally (simple approach)
    boosted_pool = all_numbers + [n for n in boosted_numbers if 1 <= n <= words_studied] * (PROB_MAX_RATIO - 1)
    candidate_numbers = _weighted_sample(boosted_pool, fetch_n, current_word_number)

    if not candidate_numbers:
        return None

    # Batch-fetch candidate words from backend
    resp = await api_client.get_words_by_numbers_for_quiz(language_id, candidate_numbers)
    if not resp or not resp.get("success") or not resp.get("result"):
        logger.warning("quiz: failed to fetch distractor words")
        return None

    candidates = resp["result"]

    # Augment with targeted same-unit-count candidates from backend index.
    # This guarantees same-count distractors even for rare multi-char words.
    if apply_word_count_filter and target_modality in ("foreign", "transcription"):
        unit_resp = await api_client.get_words_by_unit_count(
            language_id, target_modality, correct_word_count, words_studied,
            limit=n_distractors * 4,
        )
        if unit_resp and unit_resp.get("success") and unit_resp.get("result"):
            seen_ids = {str(c.get("_id") or c.get("id") or "") for c in candidates}
            for w in unit_resp["result"]:
                wid = str(w.get("_id") or w.get("id") or w.get("word_id") or "")
                if wid not in seen_ids:
                    candidates.append(w)
                    seen_ids.add(wid)

    # Collect distractors: shared-unit candidates first, others fill remaining slots.
    # Apply unit-count filter to avoid trivially-guessable options by word length.
    distractors = _collect_distractors(
        candidates, correct_id, correct_text, forbidden_ids,
        n_distractors, target_modality, correct_units,
        unit_count_filter=correct_word_count if apply_word_count_filter else None,
    )

    # If unit-count filter left too few distractors, retry without it.
    if apply_word_count_filter and len(distractors) < max(1, n_distractors // 2):
        logger.info(f"quiz: unit-count filter yielded only {len(distractors)} distractors, retrying without")
        distractors = _collect_distractors(
            candidates, correct_id, correct_text, forbidden_ids,
            n_distractors, target_modality, correct_units,
            unit_count_filter=None,
        )

    if not distractors:
        logger.info("quiz: no valid distractors found")
        return None

    options = [{"word_id": correct_id, "target_text": correct_text, "is_correct": True}] + distractors
    random.shuffle(options)

    return {"target_modality": target_modality, "options": options}
