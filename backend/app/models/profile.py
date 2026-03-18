"""Household profile models for family-aware shopping planning."""

from pydantic import BaseModel, Field


class FamilyMember(BaseModel):
    """A single family member's profile.

    Attributes:
        name: Display name of the family member.
        age_group: Age category (adult, child, infant).
        allergies: List of food allergies.
        dislikes: List of disliked foods.
    """

    name: str = Field(..., description="名前")
    age_group: str = Field(
        "adult",
        description="年齢区分: adult=大人, child=子供(4-12歳), infant=乳幼児(0-3歳)",
    )
    allergies: list[str] = Field(default_factory=list, description="アレルギー食材")
    dislikes: list[str] = Field(default_factory=list, description="苦手な食材")


class HouseholdProfile(BaseModel):
    """Household profile for family-aware shopping.

    Attributes:
        members: List of family members.
        food_preferences: General food preferences (e.g., 和食中心).
        weekly_budget: Optional weekly grocery budget in yen.
        notes: Free-form notes about the household.
    """

    members: list[FamilyMember] = Field(default_factory=list, description="家族メンバー")
    food_preferences: str | None = Field(
        None,
        description="食事の傾向（例：和食中心、洋食多め）",
    )
    weekly_budget: int | None = Field(None, description="1週間の食費予算（円）")
    notes: str | None = Field(None, description="その他メモ")

    def to_prompt_section(self) -> str:
        """Format the profile as a text section for the AI prompt.

        Returns:
            A formatted string describing the household for the AI planner.
        """
        if not self.members:
            return "世帯情報は未設定です。"

        adults = sum(1 for m in self.members if m.age_group == "adult")
        children = sum(1 for m in self.members if m.age_group == "child")
        infants = sum(1 for m in self.members if m.age_group == "infant")

        lines = [f"家族構成: {len(self.members)}人（大人{adults}名"]
        if children:
            lines[0] += f"、子供{children}名"
        if infants:
            lines[0] += f"、乳幼児{infants}名"
        lines[0] += "）"

        all_allergies: list[str] = []
        all_dislikes: list[str] = []
        for m in self.members:
            for a in m.allergies:
                if a not in all_allergies:
                    all_allergies.append(a)
            for d in m.dislikes:
                if d not in all_dislikes:
                    all_dislikes.append(d)

        if all_allergies:
            lines.append(f"アレルギー: {', '.join(all_allergies)}")
        if all_dislikes:
            lines.append(f"苦手な食材: {', '.join(all_dislikes)}")
        if self.food_preferences:
            lines.append(f"食事の傾向: {self.food_preferences}")
        if self.weekly_budget:
            lines.append(f"週間予算: {self.weekly_budget:,}円")
        if self.notes:
            lines.append(f"メモ: {self.notes}")

        return "\n".join(lines)
