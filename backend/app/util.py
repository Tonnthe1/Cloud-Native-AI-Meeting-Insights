import re
from typing import List
from pydub import AudioSegment

def get_audio_duration_seconds(filepath: str) -> float:
    audio = AudioSegment.from_file(filepath)
    return round(len(audio) / 1000.0, 2)

_STOPWORDS = {
    "the","a","an","and","or","but","if","then","else","for","on","in","of",
    "to","is","am","are","was","were","be","been","with","by","as","at","that",
    "this","it","its","from","we","you","i","they","he","she","them","our",
    "your","their","not","no","yes","do","did","done","can","could","should",
}

def extract_keywords(text: str, top_k: int = 8) -> List[str]:
    if not text:
        return []
    tokens = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text.lower())
    freq = {}
    for t in tokens:
        if t in _STOPWORDS:
            continue
        freq[t] = freq.get(t, 0) + 1
    sorted_terms = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [t for t, _ in sorted_terms[:top_k]]
