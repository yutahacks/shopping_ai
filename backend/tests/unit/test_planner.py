"""Unit tests for ClaudePlannerService — mocks the Anthropic SDK."""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.models.rules import ShoppingRules, AvoidRule
from app.models.shopping import PlanRequest
from app.services.planner import ClaudePlannerService


MOCK_RESPONSE_JSON = {
    "items": [
        {"name": "牛肉", "quantity": "300g", "estimated_price": 800, "excluded": False},
        {"name": "玉ねぎ", "quantity": "2個", "estimated_price": 100, "excluded": False},
        {"name": "カレールー", "quantity": "1箱", "estimated_price": 300, "excluded": False},
        {
            "name": "じゃがいも",
            "quantity": "3個",
            "estimated_price": 150,
            "excluded": True,
            "exclusion_reason": "avoidルールにより除外",
        },
    ],
    "reasoning": "4人分のカレーに必要な食材をリストアップしました。じゃがいもはavoidルールにより除外しました。",
    "rules_applied": ["じゃがいもをavoidリストにより除外しました"],
}


@pytest.fixture
def planner() -> ClaudePlannerService:
    with patch("app.services.planner.anthropic.Anthropic"):
        return ClaudePlannerService()


def test_planner_parse_json_from_codeblock(planner: ClaudePlannerService) -> None:
    content = f"```json\n{json.dumps(MOCK_RESPONSE_JSON)}\n```"
    parsed = planner._parse_response(content)
    assert len(parsed["items"]) == 4


def test_planner_parse_plain_json(planner: ClaudePlannerService) -> None:
    content = json.dumps(MOCK_RESPONSE_JSON)
    parsed = planner._parse_response(content)
    assert parsed["reasoning"] != ""


@pytest.mark.asyncio
async def test_create_plan_applies_rules(planner: ClaudePlannerService) -> None:
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(type="text", text=json.dumps(MOCK_RESPONSE_JSON))
    ]
    planner._client.messages.create.return_value = mock_response

    rules = ShoppingRules(
        avoid=[AvoidRule(item_pattern="じゃがいも", reason="嫌い")]
    )
    request = PlanRequest(request="カレーを4人分作りたい")
    plan = await planner.create_plan(request, rules)

    assert plan.user_request == "カレーを4人分作りたい"
    assert len(plan.items) == 4
    excluded = [i for i in plan.items if i.excluded]
    assert len(excluded) == 1
    assert excluded[0].name == "じゃがいも"
