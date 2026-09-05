import os
from types import SimpleNamespace
from unittest.mock import Mock

import anthropic
import httpx
import pytest

from src.dashboard_mockup import (
    DashboardMockupError,
    IncompleteRecommendationError,
    InvalidRecommendationInputError,
    find_missing_mockup_input_fields,
    generate_dashboard_mockup,
)
from src.dashboard_mockup_template import (
    InvalidDashboardMockupResponseError,
    MockupTemplateMismatchError,
)

_COMPLETE_RECOMMENDATION = {
    "data_model": ["Sales fact table", "Region dimension table"],
    "relationships": ["Sales.RegionID -> Region.RegionID"],
    "transformations": ["Aggregate sales by region and quarter"],
    "validation_checks": ["Sales amounts are non-negative"],
    "kpi_definitions": ["Total Revenue = SUM(Sales[Amount])"],
    "dax_measures": ["Total Revenue := SUM(Sales[Amount])"],
    "report_pages": ["Regional Sales Overview"],
    "slicers": ["Region", "Quarter"],
    "visual_design": ["Bar chart comparing revenue by region"],
}

_VALID_REPLY = """{
    "pages": [
        {
            "title": "Regional Sales Overview",
            "visuals": [
                {"type": "bar_chart", "purpose": "Revenue by region"},
                {"type": "kpi_card", "purpose": "Total revenue"}
            ]
        }
    ]
}"""


def _mock_client(reply_text: str = _VALID_REPLY) -> Mock:
    response = SimpleNamespace(content=[SimpleNamespace(type="text", text=reply_text)])
    client = Mock()
    client.messages.create.return_value = response
    return client


def test_generate_dashboard_mockup_returns_pages_and_visuals():
    client = _mock_client()

    result = generate_dashboard_mockup(_COMPLETE_RECOMMENDATION, client=client)

    assert result["pages"][0]["title"] == "Regional Sales Overview"
    assert result["pages"][0]["visuals"][0]["type"] == "bar_chart"


def test_generate_dashboard_mockup_sends_the_recommendation_in_the_prompt():
    client = _mock_client()

    generate_dashboard_mockup(_COMPLETE_RECOMMENDATION, client=client)

    _, kwargs = client.messages.create.call_args
    prompt_sent = kwargs["messages"][0]["content"]
    assert "Regional Sales Overview" in prompt_sent


def test_generate_dashboard_mockup_requires_no_api_key_and_makes_no_network_call(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = _mock_client()

    generate_dashboard_mockup(_COMPLETE_RECOMMENDATION, client=client)

    assert os.environ.get("ANTHROPIC_API_KEY") is None
    client.messages.create.assert_called_once()


def test_generate_dashboard_mockup_raises_incomplete_recommendation_without_calling_model():
    recommendation = dict(_COMPLETE_RECOMMENDATION, report_pages=[], visual_design=[])
    client = _mock_client()

    with pytest.raises(IncompleteRecommendationError) as exc_info:
        generate_dashboard_mockup(recommendation, client=client)

    assert exc_info.value.missing_fields == ["report_pages", "visual_design"]
    client.messages.create.assert_not_called()


def test_generate_dashboard_mockup_raises_on_invalid_json():
    client = _mock_client(reply_text="this is not json")

    with pytest.raises(InvalidDashboardMockupResponseError):
        generate_dashboard_mockup(_COMPLETE_RECOMMENDATION, client=client)


def test_generate_dashboard_mockup_raises_on_missing_pages_field():
    client = _mock_client(reply_text='{"unexpected": "shape"}')

    with pytest.raises(InvalidDashboardMockupResponseError):
        generate_dashboard_mockup(_COMPLETE_RECOMMENDATION, client=client)


def test_generate_dashboard_mockup_raises_template_mismatch_on_unapproved_visual_type():
    reply = '{"pages": [{"title": "Overview", "visuals": [{"type": "3d_scatter_globe", "purpose": "x"}]}]}'
    client = _mock_client(reply_text=reply)

    with pytest.raises(MockupTemplateMismatchError) as exc_info:
        generate_dashboard_mockup(_COMPLETE_RECOMMENDATION, client=client)

    assert "3d_scatter_globe" in exc_info.value.violations[0]


def test_generate_dashboard_mockup_raises_template_mismatch_on_page_with_no_visuals():
    reply = '{"pages": [{"title": "Empty Page", "visuals": []}]}'
    client = _mock_client(reply_text=reply)

    with pytest.raises(MockupTemplateMismatchError) as exc_info:
        generate_dashboard_mockup(_COMPLETE_RECOMMENDATION, client=client)

    assert "Empty Page" in exc_info.value.violations[0]


def test_generate_dashboard_mockup_raises_on_simulated_api_failure():
    client = Mock()
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    client.messages.create.side_effect = anthropic.APIConnectionError(request=request)

    with pytest.raises(DashboardMockupError):
        generate_dashboard_mockup(_COMPLETE_RECOMMENDATION, client=client)


def test_find_missing_mockup_input_fields_returns_empty_list_for_a_complete_recommendation():
    missing = find_missing_mockup_input_fields(_COMPLETE_RECOMMENDATION)

    assert missing == []


def test_find_missing_mockup_input_fields_returns_the_names_of_empty_fields():
    recommendation = dict(_COMPLETE_RECOMMENDATION, report_pages=[])

    missing = find_missing_mockup_input_fields(recommendation)

    assert missing == ["report_pages"]


def test_find_missing_mockup_input_fields_raises_for_non_dict_input():
    with pytest.raises(InvalidRecommendationInputError):
        find_missing_mockup_input_fields(["not", "a", "dict"])
