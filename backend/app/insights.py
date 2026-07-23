"""Structured meeting insight generation with privacy-aware provider routing."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from openai import OpenAI


@dataclass
class ActionItem:
    task: str
    owner: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    status: str = "open"


@dataclass
class StructuredInsights:
    overview: str
    key_points: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    provider: str = "local-heuristic"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？])\s+")
_ACTION_RE = re.compile(
    r"\b(?:action item|todo|to-do|follow up|follow-up|will|need to|must|should)\b",
    re.IGNORECASE,
)
_DECISION_RE = re.compile(
    r"\b(?:decided|decision|agreed|approved|we will|selected|chosen)\b",
    re.IGNORECASE,
)
_RISK_RE = re.compile(
    r"\b(?:risk|blocker|blocked|concern|issue|delay|dependency)\b",
    re.IGNORECASE,
)
_QUESTION_RE = re.compile(r"\?$|[？]$")


def _sentences(transcript: str) -> List[str]:
    normalized = " ".join(transcript.split())
    if not normalized:
        return []
    chunks = _SENTENCE_SPLIT.split(normalized)
    return [chunk.strip() for chunk in chunks if len(chunk.strip()) >= 8]


def _dedupe(values: List[str], limit: int = 8) -> List[str]:
    seen = set()
    output = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
        if len(output) >= limit:
            break
    return output


def generate_local_insights(transcript: str) -> StructuredInsights:
    """Generate deterministic structured output without external network calls."""
    sentences = _sentences(transcript)
    key_points = _dedupe(sentences[:5], limit=5)
    decisions = _dedupe([s for s in sentences if _DECISION_RE.search(s)])
    risks = _dedupe([s for s in sentences if _RISK_RE.search(s)])
    questions = _dedupe([s for s in sentences if _QUESTION_RE.search(s)])
    action_sentences = _dedupe([s for s in sentences if _ACTION_RE.search(s)])
    action_items = [ActionItem(task=sentence) for sentence in action_sentences]

    overview = " ".join(key_points[:2])
    if not overview:
        overview = "No meaningful meeting content was detected."

    return StructuredInsights(
        overview=overview,
        key_points=key_points,
        decisions=decisions,
        action_items=action_items,
        risks=risks,
        open_questions=questions,
        provider="local-heuristic",
    )


def _coerce_action_item(value: Any) -> Optional[ActionItem]:
    if isinstance(value, str) and value.strip():
        return ActionItem(task=value.strip())
    if not isinstance(value, dict):
        return None
    task = str(value.get("task", "")).strip()
    if not task:
        return None
    priority = value.get("priority")
    if priority not in {None, "low", "medium", "high"}:
        priority = None
    status = value.get("status")
    if status not in {"open", "in_progress", "done"}:
        status = "open"
    return ActionItem(
        task=task,
        owner=value.get("owner") or None,
        due_date=value.get("due_date") or None,
        priority=priority,
        status=status,
    )


def _normalize_payload(payload: Dict[str, Any], provider: str) -> StructuredInsights:
    actions = []
    for item in payload.get("action_items", []):
        parsed = _coerce_action_item(item)
        if parsed:
            actions.append(parsed)

    def strings(key: str) -> List[str]:
        values = payload.get(key, [])
        if not isinstance(values, list):
            return []
        return _dedupe([str(value).strip() for value in values if str(value).strip()])

    return StructuredInsights(
        overview=str(payload.get("overview", "")).strip(),
        key_points=strings("key_points"),
        decisions=strings("decisions"),
        action_items=actions[:12],
        risks=strings("risks"),
        open_questions=strings("open_questions"),
        provider=provider,
    )


def _llm_prompt(transcript: str) -> str:
    return (
        "Extract structured meeting outcomes. Return only valid JSON with keys: "
        "overview (string), key_points (string[]), decisions (string[]), "
        "action_items ({task, owner, due_date, priority, status}[]), "
        "risks (string[]), open_questions (string[]). Do not invent owners or "
        "dates; use null when absent. Transcript:\n" + transcript
    )


def generate_llm_insights(transcript: str, provider: str) -> StructuredInsights:
    if provider == "openai":
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    elif provider == "local":
        base_url = os.getenv("LOCAL_LLM_BASE_URL")
        if not base_url:
            return generate_local_insights(transcript)
        client = OpenAI(
            api_key=os.getenv("LOCAL_LLM_API_KEY", "local"),
            base_url=base_url,
        )
        model = os.getenv("LOCAL_LLM_MODEL", "meeting-insights")
    else:
        return generate_local_insights(transcript)

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You convert meeting transcripts into grounded structured JSON.",
            },
            {"role": "user", "content": _llm_prompt(transcript)},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    payload = json.loads(content)
    return _normalize_payload(payload, provider=provider)


def generate_insights(transcript: str) -> StructuredInsights:
    """Route insight generation according to explicit privacy configuration.

    AI_PROVIDER defaults to ``local`` so a clean install never sends transcript
    data to an external provider without an explicit operator choice.
    """
    provider = os.getenv("AI_PROVIDER", "local").strip().lower()
    try:
        return generate_llm_insights(transcript, provider)
    except Exception:
        # Processing should remain useful and retry-safe even when a model is down.
        fallback = generate_local_insights(transcript)
        fallback.provider = f"local-fallback:{provider}"
        return fallback
