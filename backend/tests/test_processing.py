from app import processing
from app.util import env_bool, extract_keywords
from conftest import SAMPLE_TRANSCRIPT


def test_extract_keywords_skips_stopwords_and_ranks_by_frequency():
    keywords = extract_keywords(SAMPLE_TRANSCRIPT, top_k=3)

    assert keywords[0] == "budget"
    assert "the" not in keywords
    assert len(keywords) == 3


def test_extract_keywords_keeps_accented_words_whole():
    text = "La stratégie marketing. Une stratégie claire pour le marché."

    keywords = extract_keywords(text)

    assert keywords[0] == "stratégie"
    assert "marché" in keywords


def test_extract_keywords_handles_empty_and_cjk_text():
    assert extract_keywords("") == []
    # CJK has no spaces between words, so no bogus sentence-long "keywords".
    assert extract_keywords("大家好，今天我们讨论新产品的开发进展。") == []


def test_extractive_summary_keeps_top_sentences_in_order():
    summary = processing.extractive_summary(SAMPLE_TRANSCRIPT, max_points=2)

    lines = summary.split("\n")
    assert len(lines) == 2
    assert all(line.startswith("• ") for line in lines)
    assert "budget" in lines[0] and "budget" in lines[1]
    order = [SAMPLE_TRANSCRIPT.index(line[2:]) for line in lines]
    assert order == sorted(order)


def test_extractive_summary_clips_unpunctuated_text():
    summary = processing.extractive_summary("word " * 200)

    assert summary.startswith("• word")
    assert summary.endswith("…")


def test_summarize_falls_back_when_openai_fails(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def failing(transcript):
        raise ConnectionError("network down")

    monkeypatch.setattr(processing, "_openai_summary", failing)

    assert processing.summarize(SAMPLE_TRANSCRIPT).startswith("• ")


def test_summarize_uses_openai_when_configured(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(processing, "_openai_summary",
                        lambda transcript: "- AI summary")

    assert processing.summarize(SAMPLE_TRANSCRIPT) == "- AI summary"


def test_summarize_empty_transcript():
    assert processing.summarize("   ") == ""


def test_env_bool(monkeypatch):
    monkeypatch.setenv("FLAG", "false")
    assert env_bool("FLAG") is False
    monkeypatch.setenv("FLAG", "True")
    assert env_bool("FLAG") is True
    monkeypatch.delenv("FLAG")
    assert env_bool("FLAG", default=True) is True
