import json
import anthropic
from app.config import settings
from app.models.rules import ShoppingRules
from app.models.shopping import PlanRequest, ShoppingItem, ShoppingPlan


SYSTEM_PROMPT_TEMPLATE = """あなたは日本のAmazon Fresh向けの買い物プランナーです。
ユーザーの料理・食材リクエストを分析し、必要な買い物リストをJSON形式で生成してください。

## 現在のショッピングルール

{rules_yaml}

## 指示

1. ユーザーのリクエストに基づき、必要な食材・商品リストを生成してください。
2. 上記ルールを**厳守**してください：
   - `avoid`リストの食材は`excluded: true`に設定し、`exclusion_reason`を記入してください。
   - ただし、リクエストに`override_keyword`が含まれる場合はavoidルールを無効化してください。
   - `brands`ルールに一致する商品は、指定ブランドを`notes`に記入してください。
   - `price.strategy`に従って価格帯の選択方針を示してください。
   - `notes`の指示（例：有機野菜優先、国産優先）を反映してください。
3. 数量は具体的に記入してください（例：2個、300g、1袋）。
4. `estimated_price`は円単位の概算を入力してください（不明の場合はnull）。
5. `reasoning`では日本語でプランの説明をしてください。
6. `rules_applied`では適用したルールの説明を列挙してください。

## 出力形式

以下のJSONスキーマに厳密に従ってください：

```json
{
  "items": [
    {
      "name": "商品名",
      "quantity": "数量",
      "estimated_price": 200,
      "excluded": false,
      "exclusion_reason": null,
      "substitution": null,
      "notes": null
    }
  ],
  "reasoning": "プランの説明",
  "rules_applied": ["適用ルール1", "適用ルール2"]
}
```
"""


class ClaudePlannerService:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def create_plan(
        self,
        request: PlanRequest,
        rules: ShoppingRules,
    ) -> ShoppingPlan:
        import asyncio
        return await asyncio.to_thread(self._create_plan_sync, request, rules)

    def _create_plan_sync(
        self,
        request: PlanRequest,
        rules: ShoppingRules,
    ) -> ShoppingPlan:
        import yaml

        rules_dict = rules.model_dump(exclude_none=True)
        rules_yaml = yaml.dump(rules_dict, allow_unicode=True, default_flow_style=False, sort_keys=False)

        system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{rules_yaml}", rules_yaml)

        user_message = request.request
        if request.context:
            user_message += f"\n\n追加情報: {request.context}"

        response = self._client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        content = next(
            (block.text for block in response.content if block.type == "text"),
            "",
        )

        parsed = self._parse_response(content)

        items = [ShoppingItem.model_validate(item) for item in parsed.get("items", [])]

        return ShoppingPlan(
            user_request=request.request,
            context=request.context,
            items=items,
            reasoning=parsed.get("reasoning", ""),
            rules_applied=parsed.get("rules_applied", []),
        )

    def _parse_response(self, content: str) -> dict:
        # Try to extract JSON from markdown code block
        import re

        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Try to parse the whole content as JSON
        content_stripped = content.strip()
        if content_stripped.startswith("{"):
            return json.loads(content_stripped)

        raise ValueError(f"Could not parse Claude response as JSON: {content[:200]}")
