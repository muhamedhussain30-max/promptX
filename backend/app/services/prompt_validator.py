"""
PromptValidator — server-authoritative forbidden-word detection.

Pipeline:
  1. Strip zero-width / invisible characters
  2. Decode HTML entities
  3. Normalize unicode (NFKC) — handles fullwidth chars, ligatures, etc.
  4. Collapse whitespace
  5. Apply leet-speak / common substitution reversals
  6. Tokenize with word-boundary awareness
  7. Match each token against forbidden words
  8. Flag spaced-letter bypass attempts (B E A R → BEAR)

Word-boundary matching:
  - "hat" matches "hat" but NOT "shatter", "chat", "hatred" is a judgement call:
    the spec says use word-boundary matching, so we ONLY reject whole-word matches.
  - Plural/possessive forms ARE matched (bears → bear root detected).

The server is authoritative; this same logic runs client-side as a UX hint.
"""
import re
import unicodedata
import html
from dataclasses import dataclass
from typing import Optional


# ── Leet-speak substitution map ────────────────────────────────────────────────
_LEET_MAP: dict[str, str] = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "6": "g",
    "7": "t",
    "8": "b",
    "9": "g",
    "@": "a",
    "$": "s",
    "!": "i",
    "+": "t",
    "(": "c",
    "|": "i",
}

# Characters that should be collapsed when between letters (punctuation bypass)
_PUNCT_BYPASS_RE = re.compile(r"(?<=[a-z])[.\-_*,;:'\"\s]+(?=[a-z])")

# Zero-width and invisible characters
_INVISIBLE_RE = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u00ad\u2060\u2061\u2062\u2063]"
)

# Spaced letters: "B E A R" or "B.E.A.R" or "b-e-a-r"
_SPACED_LETTERS_RE = re.compile(
    r"\b([a-z])(?:[\s.\-_,]{1,3}([a-z])){2,}\b"
)


@dataclass
class ValidationResult:
    is_valid: bool
    normalized_prompt: str
    forbidden_words_detected: list[str]
    suspicious: bool
    suspicious_reason: Optional[str]
    message: str


def _normalize(text: str) -> str:
    """Full normalization pipeline."""
    # 1. Remove invisible / zero-width chars
    text = _INVISIBLE_RE.sub("", text)

    # 2. Decode HTML entities (&amp; → &, &#98;&#101;&#97;&#114; → bear)
    text = html.unescape(text)

    # 3. NFKC unicode normalization (ａ → a, ﬁ → fi, etc.)
    text = unicodedata.normalize("NFKC", text)

    # 4. Lowercase
    text = text.lower()

    # 5. Apply leet-speak reversals (character by character)
    text = "".join(_LEET_MAP.get(ch, ch) for ch in text)

    return text


def _remove_punct_bypass(text: str) -> str:
    """Collapse punctuation/spacing inserted between letters of a word."""
    return _PUNCT_BYPASS_RE.sub("", text)


def _expand_spaced_letters(text: str) -> str:
    """
    Detect 'b e a r' style bypasses and collapse them.
    Returns text with those sequences joined.
    """
    def collapse_match(m: re.Match) -> str:
        # Remove all separators from the matched group
        return re.sub(r"[^a-z]", "", m.group(0))

    return _SPACED_LETTERS_RE.sub(collapse_match, text)


def _tokenize(text: str) -> list[str]:
    """
    Word-boundary tokenization. Returns individual word tokens.
    Strips possessive 's and common suffixes for root matching.
    """
    # Split on anything that's not alphanumeric
    tokens = re.findall(r"[a-z]+", text)
    return tokens


def _get_word_root(word: str) -> list[str]:
    """
    Returns the word and naive stemmed variants to catch plurals.
    Not a full stemmer — just handles the most common suffixes.
    """
    variants = [word]
    if word.endswith("s") and len(word) > 3:
        variants.append(word[:-1])      # bears → bear
    if word.endswith("es") and len(word) > 4:
        variants.append(word[:-2])      # constructions → construction
    if word.endswith("ing") and len(word) > 6:
        variants.append(word[:-3])      # constructing → construct
        variants.append(word[:-3] + "e")  # constructing → constructe (handles writing→write)
    if word.endswith("ed") and len(word) > 4:
        variants.append(word[:-2])      # constructed → construct
        variants.append(word[:-1])      # hated → hate
    return variants


def validate_prompt(raw_prompt: str, forbidden_words: list[str]) -> ValidationResult:
    """
    Validate a player's prompt against the forbidden word list.
    Returns a ValidationResult with full details.
    """
    if not raw_prompt or not raw_prompt.strip():
        return ValidationResult(
            is_valid=False,
            normalized_prompt="",
            forbidden_words_detected=[],
            suspicious=False,
            suspicious_reason=None,
            message="Prompt cannot be empty.",
        )

    # ── Step 1: Normalize the raw prompt ──────────────────────────────────────
    normalized = _normalize(raw_prompt)

    # ── Step 2: Detect spaced-letter bypass attempts ───────────────────────────
    suspicious = False
    suspicious_reason: Optional[str] = None
    expanded = _expand_spaced_letters(normalized)
    if expanded != normalized:
        suspicious = True
        suspicious_reason = "Spaced-letter bypass attempt detected"

    # ── Step 3: Remove punctuation bypasses ───────────────────────────────────
    cleaned = _remove_punct_bypass(expanded)

    # ── Step 4: Tokenize ───────────────────────────────────────────────────────
    tokens = _tokenize(cleaned)
    token_roots: list[list[str]] = [_get_word_root(t) for t in tokens]

    # Normalize forbidden words too
    forbidden_normalized = [_normalize(fw).strip() for fw in forbidden_words]

    # ── Step 5: Match ──────────────────────────────────────────────────────────
    detected: list[str] = []
    for fw, fw_orig in zip(forbidden_normalized, forbidden_words):
        fw_tokens = _tokenize(fw)  # forbidden phrase may be multi-word
        if not fw_tokens:
            continue

        if len(fw_tokens) == 1:
            # Single-word check — compare against token roots
            fw_root = fw_tokens[0]
            for roots in token_roots:
                if fw_root in roots:
                    detected.append(fw_orig.upper())
                    break
        else:
            # Multi-word forbidden phrase — check for substring in cleaned text
            if fw in cleaned:
                detected.append(fw_orig.upper())

    # Deduplicate while preserving order
    seen = set()
    deduped: list[str] = []
    for d in detected:
        if d not in seen:
            seen.add(d)
            deduped.append(d)

    is_valid = len(deduped) == 0

    if is_valid:
        message = "Prompt is valid! No forbidden words detected."
    else:
        message = f"Forbidden word{'s' if len(deduped) > 1 else ''} detected: {', '.join(deduped)}"

    return ValidationResult(
        is_valid=is_valid,
        normalized_prompt=normalized,  # Store the normalized form (not the fully cleaned one)
        forbidden_words_detected=deduped,
        suspicious=suspicious,
        suspicious_reason=suspicious_reason,
        message=message,
    )


def validate_prompt_quick(raw_prompt: str, forbidden_words: list[str]) -> bool:
    """Lightweight boolean check for use in hot paths."""
    result = validate_prompt(raw_prompt, forbidden_words)
    return result.is_valid
