import os
import re
from collections import Counter
from typing import List


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean env var; only 1/true/yes/on (any case) count as true."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> List[str]:
    """Read a comma-separated env var into a list of non-empty items."""
    return [item.strip() for item in os.getenv(name, default).split(",")
            if item.strip()]


_STOPWORDS = {
    # English
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "for", "on",
    "in", "of", "to", "is", "am", "are", "was", "were", "be", "been", "with",
    "by", "as", "at", "that", "this", "it", "its", "from", "we", "you", "i",
    "they", "he", "she", "them", "our", "your", "their", "not", "no", "yes",
    "do", "did", "done", "can", "could", "should", "would", "will", "shall",
    "have", "has", "had", "having", "does", "doing", "just", "also", "very",
    "really", "about", "into", "over", "than", "too", "all", "any", "some",
    "there", "here", "these", "those", "what", "which", "who", "whom", "when",
    "where", "why", "how", "so", "because", "out", "up", "down", "off",
    "more", "most", "other", "such", "only", "own", "same", "now", "one",
    "get", "got", "going", "gonna", "know", "think", "like", "yeah", "okay",
    "right", "well", "actually", "maybe", "thing", "things", "lot", "let",
    "want", "need", "make", "see", "say", "said", "mean", "kind", "sort",
    "us", "me", "my", "him", "his", "her", "hers", "ours", "yours", "theirs",
    "don", "doesn", "didn", "isn", "aren", "wasn", "weren", "won", "wouldn",
    "couldn", "shouldn", "haven", "hasn", "hadn", "can't", "ll", "ve", "re",
    # Spanish
    "que", "los", "las", "del", "por", "para", "con", "una", "uno", "como",
    "pero", "más", "este", "esta", "estos", "estas", "hay", "muy", "también",
    "sus", "nos", "ser", "son", "fue", "está", "están", "vamos",
    # French
    "les", "des", "une", "est", "pour", "pas", "qui", "dans", "sur",
    "avec", "nous", "vous", "ils", "elles", "sont", "mais", "plus", "aux",
    "cette", "ces", "leur", "leurs", "été", "être", "avons", "allons",
}

# Runs of letters in any alphabet (so accented words stay whole), allowing
# inner hyphens. Han characters and kana are excluded: those scripts don't
# separate words with spaces, so a regex can't find word boundaries there.
_CJK = "぀-ヿ㐀-䶿一-鿿豈-﫿"
_LETTER = rf"[^\W\d_{_CJK}]"
_WORD_RE = re.compile(rf"{_LETTER}+(?:-{_LETTER}+)*")


def keyword_counts(text: str) -> Counter:
    """Count non-stopword terms (3+ letters) in text."""
    return Counter(
        token for token in _WORD_RE.findall((text or "").lower())
        if len(token) >= 3 and token not in _STOPWORDS
    )


def extract_keywords(text: str, top_k: int = 8) -> List[str]:
    """Return the most frequent non-stopword terms in text."""
    return [term for term, _ in keyword_counts(text).most_common(top_k)]
