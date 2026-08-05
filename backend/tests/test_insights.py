from app.insights import generate_insights, generate_local_insights


def test_local_insights_extracts_outcomes():
    transcript = (
        "We agreed to ship the beta next Friday. "
        "Alex will prepare the launch checklist. "
        "The main risk is the pending security review. "
        "Should we invite the compliance team?"
    )

    insights = generate_local_insights(transcript)

    assert insights.provider == "local-heuristic"
    assert insights.overview
    assert any("agreed" in item.lower() for item in insights.decisions)
    assert any("Alex will" in item.task for item in insights.action_items)
    assert any("risk" in item.lower() for item in insights.risks)
    assert insights.open_questions


def test_default_provider_does_not_require_external_api(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LOCAL_LLM_BASE_URL", raising=False)

    insights = generate_insights("We decided to run a private local deployment.")

    assert insights.provider == "local-heuristic"
    assert insights.decisions


def test_explicit_unknown_provider_falls_back_locally(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "unsupported")

    insights = generate_insights("Taylor should document the deployment steps.")

    assert insights.provider == "local-heuristic"
    assert len(insights.action_items) == 1
