"""
Meeting processing pipeline shared by the worker and the API's synchronous
fallback: faster-whisper transcription, summarization and keyword extraction.
"""

import logging
import os
import re
import threading
from dataclasses import dataclass
from typing import List, Optional

from app.models import Meeting, MeetingStatus
from app.util import extract_keywords, keyword_counts

logger = logging.getLogger(__name__)

FW_MODEL = os.getenv("FW_MODEL", "base.en")
FW_DEVICE = os.getenv("FW_DEVICE", "cpu")
FW_COMPUTE_TYPE = os.getenv("FW_COMPUTE_TYPE", "float32")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
# Longer transcripts are truncated before summarization so the request stays
# within the model's context window.
SUMMARY_MAX_CHARS = int(os.getenv("SUMMARY_MAX_CHARS", "48000"))

_SUMMARY_PROMPT = (
    "Summarize the following meeting transcript in bullet points, "
    "highlight action items, key decisions, and follow-up tasks. "
    "Use clear English. Transcript:\n"
)

_model = None
_model_lock = threading.Lock()


def get_whisper_model():
    """Load the faster-whisper model on first use and reuse it afterwards."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                # Imported lazily so the API doesn't pay for it unless it
                # actually transcribes (worker disabled or unreachable).
                from faster_whisper import WhisperModel
                logger.info(f"Loading faster-whisper model: {FW_MODEL}")
                _model = WhisperModel(FW_MODEL, device=FW_DEVICE,
                                      compute_type=FW_COMPUTE_TYPE)
                logger.info("faster-whisper model loaded")
    return _model


def is_model_loaded() -> bool:
    return _model is not None


@dataclass
class Transcription:
    text: str
    language: Optional[str]
    duration_seconds: Optional[float]


def transcribe(file_path: str) -> Transcription:
    """Transcribe an audio file in any common format.

    faster-whisper decodes and resamples audio itself (via PyAV), so there is
    no need for an ffmpeg conversion step or a temporary WAV file.
    """
    model = get_whisper_model()
    segments, info = model.transcribe(file_path, beam_size=5,
                                      vad_filter=True)
    text = " ".join(seg.text.strip() for seg in segments).strip()
    duration = getattr(info, "duration", None)
    return Transcription(
        text=text,
        language=getattr(info, "language", None),
        duration_seconds=round(duration, 2) if duration is not None else None,
    )


def summarize(transcript: str) -> str:
    """Summarize a transcript with OpenAI.

    Falls back to an extractive summary when OPENAI_API_KEY isn't set or the
    request fails, so meetings still get a usable summary.
    """
    if not transcript.strip():
        return ""
    if not os.getenv("OPENAI_API_KEY"):
        logger.info("OPENAI_API_KEY not set; using extractive summary")
        return extractive_summary(transcript)
    try:
        return _openai_summary(transcript) or extractive_summary(transcript)
    except Exception as e:
        logger.warning(f"OpenAI summary failed, using extractive summary: "
                       f"{e}")
        return extractive_summary(transcript)


def _openai_summary(transcript: str) -> str:
    from openai import OpenAI

    client = OpenAI(timeout=60.0)
    completion = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a meeting assistant."},
            {"role": "user",
             "content": _SUMMARY_PROMPT + transcript[:SUMMARY_MAX_CHARS]},
        ],
        temperature=0.2,
        max_tokens=512,
    )
    return (completion.choices[0].message.content or "").strip()


# Sentence ends: ASCII punctuation followed by whitespace, or CJK
# punctuation (those scripts don't put spaces between sentences).
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+|(?<=[。！？])\s*")
_MAX_POINT_CHARS = 300


def extractive_summary(transcript: str, max_points: int = 5) -> str:
    """Pick the sentences that best cover the transcript's frequent terms.

    Sentences are scored by the frequency of their keywords across the whole
    transcript and returned as bullet points in their original order.
    """
    sentences = [s.strip() for s in _SENTENCE_END_RE.split(transcript)
                 if len(s.strip()) >= 20]
    if not sentences:
        sentences = [transcript.strip()]

    counts = keyword_counts(transcript)

    def score(sentence: str) -> float:
        terms = keyword_counts(sentence)
        if not terms:
            return 0.0
        total = sum(terms.values())
        return sum(counts[t] * n for t, n in terms.items()) / total ** 0.5

    # sorted() is stable, so ties (e.g. no keywords at all) keep their
    # original order and the summary falls back to the opening sentences.
    ranked = sorted(range(len(sentences)),
                    key=lambda i: score(sentences[i]), reverse=True)
    chosen = sorted(ranked[:max_points])

    def clip(sentence: str) -> str:
        if len(sentence) <= _MAX_POINT_CHARS:
            return sentence
        return sentence[:_MAX_POINT_CHARS].rstrip() + "…"

    return "\n".join(f"• {clip(sentences[i])}" for i in chosen)


@dataclass
class ProcessingResult:
    transcript: str
    summary: str
    language: Optional[str]
    duration_seconds: Optional[float]
    keywords: List[str]


def process_audio(file_path: str) -> ProcessingResult:
    """Run the full pipeline on an uploaded audio file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    transcription = transcribe(file_path)
    logger.info(f"Transcribed {file_path}: language="
                f"{transcription.language}, "
                f"{len(transcription.text)} chars")
    return ProcessingResult(
        transcript=transcription.text,
        summary=summarize(transcription.text),
        language=transcription.language,
        duration_seconds=transcription.duration_seconds,
        keywords=extract_keywords(transcription.text, top_k=8),
    )


def apply_result(meeting: Meeting, result: ProcessingResult) -> None:
    """Store a processing result on a meeting and mark it completed."""
    meeting.transcript = result.transcript
    meeting.summary = result.summary
    meeting.language = result.language
    meeting.duration_seconds = result.duration_seconds
    meeting.keywords = ",".join(result.keywords) or None
    meeting.status = MeetingStatus.COMPLETED
    meeting.error_message = None
