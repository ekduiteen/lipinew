"""Final response cleanup and delivery formatting for LIPI.

Two public functions:
    finalize_reply(text, hearing)  — content-level cleanup (sentence limit,
                                     filler removal, question cap, word limit).
                                     Called once in sessions.py after LLM output.

    clean_for_tts(text)            — format-level cleanup (markdown, brackets,
                                     URLs, ellipsis).  Called in tts.py just
                                     before bytes are sent to the ML service so
                                     the TTS engine never speaks raw punctuation.
"""

from __future__ import annotations

import re

from services.hearing import HearingResult


_PAREN_RE = re.compile(r"\([^)]*\)")
_MULTISPACE_RE = re.compile(r"\s+")

# ── TTS format-noise patterns ─────────────────────────────────────────────────
_MARKDOWN_RE = re.compile(r"[*_~`#>|\\]")
_BRACKET_ACTION_RE = re.compile(r"\[[^\]]*\]")   # [laughs], [sighs], [NOTE: …]
_ANGLE_TAG_RE = re.compile(r"<[^>]+>")            # <em>, </em>, <br/> etc.
_URL_RE = re.compile(r"https?://\S+")
_MULTI_DOTS_RE = re.compile(r"\.{2,}")            # collapse … or .... to a single .
_REPEATED_WORD_RE = re.compile(r"\b([A-Za-z]+)\s+\1\b", re.IGNORECASE)
_REPEATED_DEVANAGARI_RE = re.compile(r"([\u0900-\u097F]+)\s+\1")
_GENERIC_FILLER_PATTERNS = (
    "Teach me more",
    "teach me more",
    "Can you explain further",
    "Tell me more about this in detail",
    "I will continue learning",
    "That is very interesting",
    "मलाई अझ धेरै सिकाऊ",
    "अझै सिकाउनुस्",
    "रोचक छ",
)
_REPETITIVE_CLOSERS = {
    "तिमीलाई कस्तो छ?",
    "तिमीलाई के-के कुरा सिक्न मन छ?",
    "तिमीले भन्न खोजेको के हो?",
}
_LESSON_META_PATTERNS = (
    "तिमीले यी शब्दहरू सिकाइरहेका छौ",
    "तिमी नेपाली भाषा सिक्दै छौ",
    "मलाई तिमी भनेर सम्बोधन गर्छौ",
    "तिमी के भन्न खोज्दै छौ",
)
_LEARNER_META_PATTERNS = (
    "तपाईंले मलाई सिकाउनुभयो",
    "तपाईंले नेवारीमा",
    "तपाईंले भन्नुभयो",
    "म सिक्नको लागि",
    "मलाई यो नयाँ कुरा सिक्न",
    "मलाई धेरै रमाइलो लाग्यो",
    "मलाई धेरै मन लाग्यो",
    "म विद्यार्थी हुँ",
    "Oh, I understand",
    "I understand,",
    "you are teaching me",
    "I am excited to learn",
)


def finalize_reply(text: str, hearing: HearingResult) -> str:
    cleaned = _PAREN_RE.sub(" ", text)
    for marker in _GENERIC_FILLER_PATTERNS:
        cleaned = cleaned.replace(marker, " ")
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")
    cleaned = _MULTISPACE_RE.sub(" ", cleaned).strip()
    cleaned = _REPEATED_WORD_RE.sub(r"\1", cleaned)
    cleaned = _REPEATED_DEVANAGARI_RE.sub(r"\1", cleaned)

    if not cleaned:
        return build_empty_reply(hearing)

    sentences = [part.strip() for part in re.split(r"(?<=[।!?])\s+", cleaned) if part.strip()]
    if len(sentences) > 1 and sentences[-1] in _REPETITIVE_CLOSERS:
        sentences = sentences[:-1]
    sentences = _strip_meta_heavy_sentences(sentences)
    if len(sentences) > 2:
        sentences = sentences[:2]
    cleaned = " ".join(sentences).strip()

    for pattern in _LESSON_META_PATTERNS:
        cleaned = cleaned.replace(pattern, " ").strip()

    if cleaned.count("?") > 1:
        first = cleaned.find("?")
        cleaned = cleaned[: first + 1] + cleaned[first + 1 :].replace("?", "")
    if cleaned.count("？") > 1:
        first = cleaned.find("？")
        cleaned = cleaned[: first + 1] + cleaned[first + 1 :].replace("？", "")

    words = cleaned.split()
    if len(words) > 28:
        clipped = " ".join(words[:28]).rstrip(",;:-")
        cleaned = clipped if clipped.endswith(("।", "?", "!")) else clipped + "।"

    return _MULTISPACE_RE.sub(" ", cleaned).strip()


def _strip_meta_heavy_sentences(sentences: list[str]) -> list[str]:
    if not sentences:
        return sentences

    filtered: list[str] = []
    for sentence in sentences:
        if any(pattern in sentence for pattern in _LEARNER_META_PATTERNS):
            continue
        filtered.append(sentence)

    if filtered:
        return filtered

    # If every sentence was meta-heavy, keep at most the shortest one rather than
    # returning nothing and forcing an unrelated fallback.
    shortest = min(sentences, key=len)
    return [shortest]


def build_empty_reply(hearing: HearingResult) -> str:
    if hearing.mode == "english":
        return "Sorry, can you say that once more?"
    if hearing.mode == "mixed":
        return "म अलि बुझिनँ. फेरि भन्न सक्छौ?"
    return "म अलि बुझिनँ। फेरि भन्न सक्छौ?"


def clean_for_tts(text: str) -> str:
    """Strip formatting noise that would be spoken aloud by a TTS engine.

    This is a lightweight, format-only pass — it does NOT change content
    or length.  Call it just before sending text to the TTS service.

    finalize_reply() handles content (sentence limits, filler removal, etc.)
    and must run *before* this function in the pipeline.
    """
    if not text:
        return text

    # Remove URLs — TTS would spell out "h t t p s colon slash slash …"
    text = _URL_RE.sub("", text)

    # Remove bracketed stage directions — [laughs], [NOTE: use tapai]
    text = _BRACKET_ACTION_RE.sub("", text)

    # Remove HTML/XML-like tags
    text = _ANGLE_TAG_RE.sub("", text)

    # Remove markdown decoration characters
    text = _MARKDOWN_RE.sub("", text)

    # Collapse ellipsis (… or ....) to a single period so the TTS pauses
    # naturally instead of saying "dot dot dot"
    text = _MULTI_DOTS_RE.sub(".", text)

    return _MULTISPACE_RE.sub(" ", text).strip()
