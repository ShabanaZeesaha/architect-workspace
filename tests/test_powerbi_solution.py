import os
from types import SimpleNamespace
from unittest.mock import Mock

import anthropic
import httpx
import pytest

from src.powerbi_solution import (
    InvalidMockupInputError,
    PowerBiSolutionError,
    generate_draft_powerbi_solution,
)
from src.powerbi_solution_template import DraftMockupMismatchError, InvalidDraftSolutionResponseError

_VALID_MOCKUP = {
    "pages": [
        {
            "title": "Regional Sales Overview",
            "visuals": [
                {"type": "bar_chart", "purpose": "Revenue by region"},
                {"type": "kpi_card", "purpose": "Total revenue"},
            ],
        }
    ]
}

_VALID_REPLY = """{
    "pages": [
        {
            "title": "Regional Sales Overview",
            "visuals": [
                {"type": "bar_chart", "purpose": "Revenue by region", "field_bindings": ["Sales[Region]"]},
                {"type": "kpi_card", "purpose": "Total revenue", "field_bindings": ["Total Revenue"]}
            ]
        }
    ]
}"""


def _mock_client(reply_text: str = _VALID_REPLY) -> Mock:
    response = SimpleNamespace(content=[SimpleNamespace(type="text", text=reply_text)])
    client = Mock()
    client.messages.create.return_value = response
    return client


def test_generate_draft_powerbi_solution_returns_pages_visuals_and_field_bindings():
    client = _mock_client()

    result = generate_draft_powerbi_solution(_VALID_MOCKUP, client=client)

    assert result["pages"][0]["title"] == "Regional Sales Overview"
    assert result["pages"][0]["visuals"][0]["field_bindings"] == ["Sales[Region]"]


def test_generate_draft_powerbi_solution_sends_the_mockup_in_the_prompt():
    client = _mock_client()

    generate_draft_powerbi_solution(_VALID_MOCKUP, client=client)

    _, kwargs = client.messages.create.call_args
    prompt_sent = kwargs["messages"][0]["content"]
    assert "Regional Sales Overview" in prompt_sent


def test_generate_draft_powerbi_solution_requires_no_api_key_and_makes_no_network_call(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = _mock_client()

    generate_draft_powerbi_solution(_VALID_MOCKUP, client=client)

    assert os.environ.get("ANTHROPIC_API_KEY") is None
    client.messages.create.assert_called_once()


def test_generate_draft_powerbi_solution_raises_invalid_mockup_input_without_calling_model():
    client = _mock_client()

    with pytest.raises(InvalidMockupInputError):
        generate_draft_powerbi_solution({"pages": []}, client=client)

    client.messages.create.assert_not_called()


def test_generate_draft_powerbi_solution_raises_invalid_mockup_input_for_non_dict():
    client = _mock_client()

    with pytest.raises(InvalidMockupInputError):
        generate_draft_powerbi_solution(["not", "a", "mockup"], client=client)

    client.messages.create.assert_not_called()


def test_generate_draft_powerbi_solution_raises_on_invalid_json():
    client = _mock_client(reply_text="this is not json")

    with pytest.raises(InvalidDraftSolutionResponseError):
        generate_draft_powerbi_solution(_VALID_MOCKUP, client=client)


def test_generate_draft_powerbi_solution_raises_on_missing_pages_field():
    client = _mock_client(reply_text='{"unexpected": "shape"}')

    with pytest.raises(InvalidDraftSolutionResponseError):
        generate_draft_powerbi_solution(_VALID_MOCKUP, client=client)


def test_generate_draft_powerbi_solution_raises_mismatch_on_dropped_visual():
    reply = """{
        "pages": [
            {
                "title": "Regional Sales Overview",
                "visuals": [
                    {"type": "bar_chart", "purpose": "Revenue by region", "field_bindings": ["f"]}
                ]
            }
        ]
    }"""
    client = _mock_client(reply_text=reply)

    with pytest.raises(DraftMockupMismatchError) as exc_info:
        generate_draft_powerbi_solution(_VALID_MOCKUP, client=client)

    assert "visual(s)" in exc_info.value.violations[0]


def test_generate_draft_powerbi_solution_raises_mismatch_on_renamed_page():
    reply = """{
        "pages": [
            {
                "title": "Renamed Page",
                "visuals": [
                    {"type": "bar_chart", "purpose": "Revenue by region", "field_bindings": ["f"]},
                    {"type": "kpi_card", "purpose": "Total revenue", "field_bindings": ["f"]}
                ]
            }
        ]
    }"""
    client = _mock_client(reply_text=reply)

    with pytest.raises(DraftMockupMismatchError) as exc_info:
        generate_draft_powerbi_solution(_VALID_MOCKUP, client=client)

    assert "Renamed Page" in exc_info.value.violations[0]


def test_generate_draft_powerbi_solution_raises_on_simulated_api_failure():
    client = Mock()
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    client.messages.create.side_effect = anthropic.APIConnectionError(request=request)

    with pytest.raises(PowerBiSolutionError):
        generate_draft_powerbi_solution(_VALID_MOCKUP, client=client)
