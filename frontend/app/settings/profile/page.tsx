"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useProfile } from "@/hooks/useProfile";
import type { FamilyMember, HouseholdProfile } from "@/lib/types";

export default function ProfilePage() {
  const { profile, loading, saving, saveProfile } = useProfile();

  if (loading) {
    return <div className="max-w-2xl mx-auto p-6">読み込み中...</div>;
  }

  if (!profile) {
    return <div className="max-w-2xl mx-auto p-6">プロファイルの読み込みに失敗しました</div>;
  }

  return <ProfileEditor profile={profile} saving={saving} onSave={saveProfile} />;
}

function ProfileEditor({
  profile,
  saving,
  onSave,
}: {
  profile: HouseholdProfile;
  saving: boolean;
  onSave: (profile: HouseholdProfile) => Promise<HouseholdProfile | null>;
}) {
  const [draft, setDraft] = useState<HouseholdProfile>(profile);
  const [newMember, setNewMember] = useState<FamilyMember>({
    name: "",
    age_group: "adult",
    allergies: [],
    dislikes: [],
  });
  const [allergyInput, setAllergyInput] = useState("");
  const [dislikeInput, setDislikeInput] = useState("");

  const handleSave = async () => {
    const result = await onSave(draft);
    if (result) toast.success("プロファイルを保存しました");
    else toast.error("保存に失敗しました");
  };

  const addMember = () => {
    if (!newMember.name.trim()) return;
    setDraft((d) => ({ ...d, members: [...d.members, { ...newMember }] }));
    setNewMember({ name: "", age_group: "adult", allergies: [], dislikes: [] });
    setAllergyInput("");
    setDislikeInput("");
  };

  const removeMember = (idx: number) => {
    setDraft((d) => ({ ...d, members: d.members.filter((_, i) => i !== idx) }));
  };

  const addAllergy = () => {
    if (!allergyInput.trim()) return;
    setNewMember((m) => ({
      ...m,
      allergies: [...m.allergies, allergyInput.trim()],
    }));
    setAllergyInput("");
  };

  const addDislike = () => {
    if (!dislikeInput.trim()) return;
    setNewMember((m) => ({
      ...m,
      dislikes: [...m.dislikes, dislikeInput.trim()],
    }));
    setDislikeInput("");
  };

  const ageGroupLabel = (ag: string) => {
    switch (ag) {
      case "adult": return "大人";
      case "child": return "子供";
      case "infant": return "乳幼児";
      default: return ag;
    }
  };

  return (
    <main className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/settings" className="text-muted-foreground hover:text-foreground">
            ← 戻る
          </Link>
          <h1 className="text-xl font-bold">家族プロファイル</h1>
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? "保存中..." : "保存"}
        </Button>
      </div>

      {/* Current members */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">家族メンバー</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {draft.members.length === 0 && (
            <p className="text-sm text-muted-foreground">メンバーが登録されていません</p>
          )}
          {draft.members.map((member, idx) => (
            <div key={idx} className="flex items-start gap-2 p-3 border rounded-md">
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{member.name}</span>
                  <Badge variant="outline">{ageGroupLabel(member.age_group)}</Badge>
                </div>
                {member.allergies.length > 0 && (
                  <p className="text-xs text-destructive">
                    アレルギー: {member.allergies.join(", ")}
                  </p>
                )}
                {member.dislikes.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    苦手: {member.dislikes.join(", ")}
                  </p>
                )}
              </div>
              <button
                onClick={() => removeMember(idx)}
                className="text-destructive text-sm"
              >
                削除
              </button>
            </div>
          ))}

          {/* Add member form */}
          <div className="border-t pt-3 space-y-3">
            <p className="text-sm font-medium">メンバーを追加</p>
            <div className="flex gap-2">
              <Input
                placeholder="名前"
                value={newMember.name}
                onChange={(e) => setNewMember((m) => ({ ...m, name: e.target.value }))}
                className="flex-1"
              />
              <select
                value={newMember.age_group}
                onChange={(e) =>
                  setNewMember((m) => ({
                    ...m,
                    age_group: e.target.value as FamilyMember["age_group"],
                  }))
                }
                className="border rounded-md px-3 py-2 text-sm"
              >
                <option value="adult">大人</option>
                <option value="child">子供(4-12歳)</option>
                <option value="infant">乳幼児(0-3歳)</option>
              </select>
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="アレルギー食材"
                value={allergyInput}
                onChange={(e) => setAllergyInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addAllergy())}
                className="flex-1"
              />
              <Button variant="outline" size="sm" onClick={addAllergy}>
                追加
              </Button>
            </div>
            {newMember.allergies.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {newMember.allergies.map((a, i) => (
                  <Badge key={i} variant="destructive" className="text-xs">
                    {a}
                  </Badge>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <Input
                placeholder="苦手な食材"
                value={dislikeInput}
                onChange={(e) => setDislikeInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addDislike())}
                className="flex-1"
              />
              <Button variant="outline" size="sm" onClick={addDislike}>
                追加
              </Button>
            </div>
            {newMember.dislikes.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {newMember.dislikes.map((d, i) => (
                  <Badge key={i} variant="secondary" className="text-xs">
                    {d}
                  </Badge>
                ))}
              </div>
            )}
            <Button variant="outline" onClick={addMember} className="w-full">
              メンバーを登録
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Preferences */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">食事・予算の設定</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>食事の傾向</Label>
            <Input
              placeholder="例：和食中心、洋食多め"
              value={draft.food_preferences ?? ""}
              onChange={(e) =>
                setDraft((d) => ({ ...d, food_preferences: e.target.value || undefined }))
              }
            />
          </div>
          <div className="space-y-2">
            <Label>週間予算（円）</Label>
            <Input
              type="number"
              placeholder="未設定"
              value={draft.weekly_budget ?? ""}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  weekly_budget: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
              className="w-40"
            />
          </div>
          <div className="space-y-2">
            <Label>その他メモ</Label>
            <Textarea
              placeholder="例：子供が小学校に入ったのでお弁当用の食材も必要"
              value={draft.notes ?? ""}
              onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value || undefined }))}
              rows={3}
            />
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
