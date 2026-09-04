import os
from types import SimpleNamespace
from unittest.mock import Mock

import anthropic
import httpx
import pytest

from src.design_recommendation import (
    RECOMMENDATION_FIELDS,
    DesignRecommendationError,
    IncompleteRequirementsError,
    InvalidDesignRecommendationResponseError,
    generate_design_recommendations,
)

_COMPLETE_ANALYSIS = {
    "business_objectives": ["Increase visibility into quarterly regional sales"],
    "scope": ["Q1 2026 regional sales"],
    "kpis": ["Total Revenue"],
    "filters": ["Region"],
    "calculations": ["Net Margin = Revenue - Cost"],
    "visual_requirements": ["Bar chart comparing revenue by region"],
    "reporting_expectations": ["Weekly summary email"],
}

_VALID_REPLY = """{
    "data_model": ["Sales fact table", "Region dimension table"],
    "relationships": ["Sales.RegionID -> Region.RegionID"],
    "transformations": ["Aggregate sales by region and quarter"],
    "validation_checks": ["Sales amounts are non-negative"],
    "kpi_definitions": ["Total Revenue = SUM(Sales[Amount])"],
    "dax_measures": ["Total Revenue := SUM(Sales[Amount])"],
    "report_pages": ["Regional Sales Overview"],
    "slicers": ["Region", "Quarter"],
    "visual_design": ["Bar chart comparing revenue by region"]
}"""


def _mock_client(reply_text: str = _VALID_REPLY) -> Mock:
    response = SimpleNamespace(content=[SimpleNamespace(type="text", text=reply_text)])
    client = Mock()
    client.messages.create.return_value = response
    return client


def test_generate_design_recommendations_returns_all_recommendation_fields():
    client = _mock_client()

    result = generate_design_recommendations(_COMPLETE_ANALYSIS, client=client)

    assert set(result.keys()) == set(RECOMMENDATION_FIELDS)
    for field in RECOMMENDATION_FIELDS:
        assert isinstance(result[field], list)
    assert result["data_model"] == ["Sales fact table", "Region dimension table"]


def test_generate_design_recommendations_passes_field_mapping_into_the_prompt():
    client = _mock_client()
    field_mapping = {"Total Revenue": "kpis"}

    generate_design_recommendations(_COMPLETE_ANALYSIS, field_mapping=field_mapping, client=client)

    _, kwargs = client.messages.create.call_args
    prompt_sent = kwargs["messages"][0]["content"]
    assert "Total Revenue" in prompt_sent
    assert "kpis" in prompt_sent


def test_generate_design_recommendations_requires_no_api_key_and_makes_no_network_call(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = _mock_client()

    generate_design_recommendations(_COMPLETE_ANALYSIS, client=client)

    assert os.environ.get("ANTHROPIC_API_KEY") is None
    client.messages.create.assert_called_once()


def test_generate_design_recommendations_raises_incomplete_requirements_without_calling_model():
    analysis = dict(_COMPLETE_ANALYSIS, kpis=[], filters=[])
    client = _mock_client()

    with pytest.raises(IncompleteRequirementsError) as exc_info:
        generate_design_recommendations(analysis, client=client)

    assert exc_info.value.missing_fields == ["kpis", "filters"]
    client.messages.create.assert_not_called()


def test_generate_design_recommendations_raises_on_invalid_json():
    client = _mock_client(reply_text="this is not json")

    with pytest.raises(InvalidDesignRecommendationResponseError):
        generate_design_recommendations(_COMPLETE_ANALYSIS, client=client)


def test_generate_design_recommendations_raises_on_missing_field():
    incomplete_reply = '{"data_model": ["Sales fact table"]}'
    client = _mock_client(reply_text=incomplete_reply)

    with pytest.raises(InvalidDesignRecommendationResponseError):
        generate_design_recommendations(_COMPLETE_ANALYSIS, client=client)


def test_generate_design_recommendations_raises_on_simulated_api_failure():
    client = Mock()
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    client.messages.create.side_effect = anthropic.APIConnectionError(request=request)

    with pytest.raises(DesignRecommendationError):
        generate_design_recommendations(_COMPLETE_ANALYSIS, client=client)
