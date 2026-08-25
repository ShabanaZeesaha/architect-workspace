import os
from types import SimpleNamespace
from unittest.mock import Mock

import anthropic
import httpx
import pytest

from src.email_analysis import (
    REQUIRED_FIELDS,
    EmailAnalysisError,
    InvalidEmailAnalysisResponseError,
    analyze_email,
)

_VALID_REPLY = """{
    "business_objectives": ["Increase visibility into quarterly regional sales"],
    "scope": ["Q1 2026 regional sales"],
    "kpis": ["Total Revenue"],
    "filters": ["Region"],
    "calculations": ["Net Margin = Revenue - Cost"],
    "visual_requirements": ["Bar chart comparing revenue by region"],
    "reporting_expectations": ["Weekly summary email"]
}"""


def _mock_client(reply_text: str = _VALID_REPLY) -> Mock:
    response = SimpleNamespace(content=[SimpleNamespace(type="text", text=reply_text)])
    client = Mock()
    client.messages.create.return_value = response
    return client


def test_analyze_email_returns_all_required_fields_for_valid_response():
    client = _mock_client()

    result = analyze_email("Need a sales dashboard broken down by region", client=client)

    assert set(result.keys()) == set(REQUIRED_FIELDS)
    for field in REQUIRED_FIELDS:
        assert isinstance(result[field], list)
    assert result["business_objectives"] == ["Increase visibility into quarterly regional sales"]


def test_analyze_email_requires_no_api_key_and_makes_no_network_call(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = _mock_client()

    analyze_email("Need a sales dashboard", client=client)

    assert os.environ.get("ANTHROPIC_API_KEY") is None
    client.messages.create.assert_called_once()


def test_analyze_email_raises_on_invalid_json():
    client = _mock_client(reply_text="this is not json")

    with pytest.raises(InvalidEmailAnalysisResponseError):
        analyze_email("Need a sales dashboard", client=client)


def test_analyze_email_raises_on_missing_field():
    incomplete_reply = '{"business_objectives": ["Grow revenue"]}'
    client = _mock_client(reply_text=incomplete_reply)

    with pytest.raises(InvalidEmailAnalysisResponseError):
        analyze_email("Need a sales dashboard", client=client)


def test_analyze_email_raises_on_simulated_api_failure():
    client = Mock()
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    client.messages.create.side_effect = anthropic.APIConnectionError(request=request)

    with pytest.raises(EmailAnalysisError):
        analyze_email("Need a sales dashboard", client=client)
