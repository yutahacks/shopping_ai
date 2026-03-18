"""Shopping plan generation service using OpenAI Agents SDK.

This module provides the AI-powered shopping plan generation by
leveraging the OpenAI Agents SDK with structured output to produce
validated shopping plans from natural language requests.
"""

import yaml
from agents import Agent, ModelSettings, Runner
from pydantic import BaseModel, Field

from app.config import settings
from app.models.rules import ShoppingRules
from app.models.shopping import PlanRequest, ShoppingItem, ShoppingPlan


class PlanOutput(BaseModel):
    """Structured output schema for the AI planner agent.

    Attributes:
        items: List of shopping items to purchase.
        reasoning: Explanation of the generated plan in Japanese.
        rules_applied: List of rules that were applied during planning.
    """

    items: list[ShoppingItem] = Field(description="買い物リスト")
    reasoning: str = Field(description="プランの説明（日本語）")
    rules_applied: list[str] = Field(description="適用されたルールの説明")


SYSTEM_PROMPT_TEMPLATE = """あなたは日本のAmazon Fresh向けの買い物プランナーです。
ユーザーの料理・食材リクエストを分析し、必要な買い物リストを生成してください。

## 世帯情報

{profile_section}

## 現在のショッピングルール

{rules_yaml}

## 指示

1. ユーザーのリクエストに基づき、必要な食材・商品リストを生成してください。
2. 世帯情報（家族人数・年齢層・アレルギー等）を考慮して適切な量を算出してください。
3. 上記ルールを**厳守**してください：
   - `avoid`リストの食材は`excluded: true`に設定し、`exclusion_reason`を記入してください。
   - ただし、リクエストに`override_keyword`が含まれる場合はavoidルールを無効化してください。
   - `brands`ルールに一致する商品は、指定ブランドを`notes`に記入してください。
   - `price.strategy`に従って価格帯の選択方針を示してください。
   - `notes`の指示（例：有機野菜優先、国産優先）を反映してください。
4. 数量は具体的に記入してください（例：2個、300g、1袋）。
5. `estimated_price`は円単位の概算を入力してください（不明の場合はnull）。
6. `reasoning`では日本語でプランの説明をしてください。
7. `rules_applied`では適用したルールの説明を列挙してください。
"""


class ShoppingPlannerService:
    """Service for generating shopping plans via OpenAI Agents SDK.

    Uses the OpenAI Agents SDK with structured output to generate
    shopping plans from natural language requests, taking into account
    household profiles and shopping rules.
    """

    def __init__(self) -> None:
        """Initialize the planner service."""
        pass

    async def create_plan(
        self,
        request: PlanRequest,
        rules: ShoppingRules,
        profile_section: str = "世帯情報は未設定です。",
    ) -> ShoppingPlan:
        """Generate a shopping plan from a natural language request.

        Args:
            request: The user's shopping request with optional context.
            rules: Current shopping rules (avoid, brands, price, notes).
            profile_section: Formatted household profile text for the prompt.

        Returns:
            A validated ShoppingPlan with items, reasoning, and applied rules.

        Raises:
            Exception: If the AI agent fails to generate a valid plan.
        """
        rules_dict = rules.model_dump(exclude_none=True)
        rules_yaml = yaml.dump(
            rules_dict, allow_unicode=True, default_flow_style=False, sort_keys=False
        )

        system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{rules_yaml}", rules_yaml).replace(
            "{profile_section}", profile_section
        )

        agent = Agent(
            name="shopping_planner",
            instructions=system_prompt,
            model=settings.openai_model,
            model_settings=ModelSettings(temperature=0),
            output_type=PlanOutput,
        )

        user_message = request.request
        if request.context:
            user_message += f"\n\n追加情報: {request.context}"

        result = await Runner.run(agent, user_message)
        output: PlanOutput = result.final_output

        return ShoppingPlan(
            user_request=request.request,
            context=request.context,
            items=output.items,
            reasoning=output.reasoning,
            rules_applied=output.rules_applied,
        )
