"""Unit tests for ShoppingPlannerService — mocks the OpenAI Agents SDK."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.rules import AvoidRule, ShoppingRules
from app.models.shopping import PlanRequest, ShoppingItem
from app.services.planner import PlanOutput, ShoppingPlannerService


MOCK_PLAN_OUTPUT = PlanOutput(
    items=[
        ShoppingItem(name="牛肉", quantity="300g", estimated_price=800, excluded=False),
        ShoppingItem(name="玉ねぎ", quantity="2個", estimated_price=100, excluded=False),
        ShoppingItem(name="カレールー", quantity="1箱", estimated_price=300, excluded=False),
        ShoppingItem(
            name="じゃがいも",
            quantity="3個",
            estimated_price=150,
            excluded=True,
            exclusion_reason="avoidルールにより除外",
        ),
    ],
    reasoning="4人分のカレーに必要な食材をリストアップしました。じゃがいもはavoidルールにより除外しました。",
    rules_applied=["じゃがいもをavoidリストにより除外しました"],
)


@pytest.fixture
def planner() -> ShoppingPlannerService:
    """Create a ShoppingPlannerService instance for testing."""
    return ShoppingPlannerService()


@pytest.mark.asyncio
async def test_create_plan_applies_rules(planner: ShoppingPlannerService) -> None:
    """Test that the planner correctly passes rules and returns structured output."""
    mock_result = MagicMock()
    mock_result.final_output = MOCK_PLAN_OUTPUT

    with patch("app.services.planner.Runner.run", new_callable=AsyncMock, return_value=mock_result):
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


@pytest.mark.asyncio
async def test_create_plan_with_context(planner: ShoppingPlannerService) -> None:
    """Test that additional context is included in the request."""
    mock_result = MagicMock()
    mock_result.final_output = MOCK_PLAN_OUTPUT

    with patch("app.services.planner.Runner.run", new_callable=AsyncMock, return_value=mock_result) as mock_run:
        rules = ShoppingRules()
        request = PlanRequest(request="カレー", context="予算2000円以内")
        await planner.create_plan(request, rules)

    call_args = mock_run.call_args
    user_message = call_args[0][1]
    assert "予算2000円以内" in user_message


@pytest.mark.asyncio
async def test_create_plan_with_profile(planner: ShoppingPlannerService) -> None:
    """Test that household profile info is included in the system prompt."""
    mock_result = MagicMock()
    mock_result.final_output = MOCK_PLAN_OUTPUT

    with patch("app.services.planner.Runner.run", new_callable=AsyncMock, return_value=mock_result) as mock_run:
        rules = ShoppingRules()
        request = PlanRequest(request="カレー")
        profile_text = "家族構成: 大人2名、子供1名"
        await planner.create_plan(request, rules, profile_section=profile_text)

    call_args = mock_run.call_args
    agent = call_args[0][0]
    assert "家族構成: 大人2名、子供1名" in agent.instructions
