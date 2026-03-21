"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { FamilyMember, HouseholdProfile, CookieStatus } from "@/lib/types";

type Step = "cookie" | "profile" | "rules" | "complete";

const STEPS: { key: Step; label: string }[] = [
  { key: "cookie", label: "Cookie設定" },
  { key: "profile", label: "家族構成" },
  { key: "rules", label: "ルール設定" },
  { key: "complete", label: "完了" },
];

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("cookie");

  const currentIndex = STEPS.findIndex((s) => s.key === step);

  return (
    <main className="max-w-2xl mx-auto p-4 sm:p-6 space-y-6">
      <h1 className="text-2xl font-bold text-center">初期セットアップ</h1>
      <p className="text-center text-muted-foreground text-sm">
        Amazon Fresh 買い物アシスタントの初期設定を行います
      </p>

      {/* Progress indicator */}
      <div className="flex justify-center gap-2">
        {STEPS.map((s, idx) => (
          <div
            key={s.key}
            className={`flex items-center gap-1 text-xs ${
              idx <= currentIndex ? "text-primary font-medium" : "text-muted-foreground"
            }`}
          >
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                idx < currentIndex
                  ? "bg-primary text-primary-foreground"
                  : idx === currentIndex
                    ? "border-2 border-primary text-primary"
                    : "border border-muted-foreground"
              }`}
            >
              {idx < currentIndex ? "✓" : idx + 1}
            </div>
            <span className="hidden sm:inline">{s.label}</span>
          </div>
        ))}
      </div>

      {step === "cookie" && <CookieStep onNext={() => setStep("profile")} />}
      {step === "profile" && (
        <ProfileStep
          onNext={() => setStep("rules")}
          onBack={() => setStep("cookie")}
        />
      )}
      {step === "rules" && (
        <RulesStep
          onNext={() => setStep("complete")}
          onBack={() => setStep("profile")}
        />
      )}
      {step === "complete" && <CompleteStep onFinish={() => router.push("/")} />}
    </main>
  );
}

function CookieStep({ onNext }: { onNext: () => void }) {
  const [cookieJson, setCookieJson] = useState("");
  const [status, setStatus] = useState<CookieStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);
  const [showManual, setShowManual] = useState(false);

  const handleBrowserLogin = async () => {
    setLoginLoading(true);
    try {
      const newStatus = await api.settings.browserLogin();
      setStatus(newStatus);
      toast.success("ログインに成功しました。Cookieを自動取得しました。");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "ブラウザログインに失敗しました");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleUpload = async () => {
    setLoading(true);
    try {
      const cookies = JSON.parse(cookieJson);
      if (!Array.isArray(cookies)) throw new Error("配列形式で入力してください");
      const newStatus = await api.settings.uploadCookies(cookies);
      setStatus(newStatus);
      setCookieJson("");
      toast.success("Cookieをアップロードしました");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "アップロードに失敗しました");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">ステップ1: Amazon Cookie設定</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Amazon Freshを操作するためにAmazon.co.jpへのログインが必要です。
          ボタンを押すとブラウザが開くので、通常通りログインしてください。
        </p>

        {status?.is_valid && (
          <div className="flex items-center gap-2">
            <Badge className="bg-green-100 text-green-800">有効</Badge>
            <span className="text-sm">{status.cookie_count}件のCookie</span>
          </div>
        )}

        <Button
          onClick={handleBrowserLogin}
          disabled={loginLoading || loading}
          className="w-full"
          size="lg"
        >
          {loginLoading ? "ブラウザでログイン中..." : "Amazonにブラウザでログイン"}
        </Button>

        {loginLoading && (
          <p className="text-xs text-muted-foreground text-center">
            ブラウザが開きます。Amazonにログインしてください（2FA対応）。
            ログイン完了後、自動的にCookieが保存されます。
          </p>
        )}

        <div className="border-t pt-3">
          <button
            onClick={() => setShowManual(!showManual)}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {showManual ? "▼ 手動アップロードを閉じる" : "▶ Cookie JSONを手動でアップロード"}
          </button>

          {showManual && (
            <div className="mt-3 space-y-3">
              <Textarea
                placeholder='[{"name": "session-id", "value": "...", "domain": ".amazon.co.jp", ...}]'
                value={cookieJson}
                onChange={(e) => setCookieJson(e.target.value)}
                rows={6}
                className="font-mono text-xs"
              />
              <Button
                onClick={handleUpload}
                disabled={loading || !cookieJson.trim()}
                variant="outline"
                className="w-full"
              >
                {loading ? "アップロード中..." : "JSONをアップロード"}
              </Button>
            </div>
          )}
        </div>

        <div className="flex justify-end">
          <Button variant="outline" onClick={onNext}>
            {status?.is_valid ? "次へ →" : "スキップ →"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ProfileStep({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [foodPreferences, setFoodPreferences] = useState("");
  const [weeklyBudget, setWeeklyBudget] = useState<string>("");
  const [newName, setNewName] = useState("");
  const [newAgeGroup, setNewAgeGroup] = useState<FamilyMember["age_group"]>("adult");
  const [saving, setSaving] = useState(false);

  const addMember = () => {
    if (!newName.trim()) return;
    setMembers((m) => [...m, { name: newName.trim(), age_group: newAgeGroup, allergies: [], dislikes: [] }]);
    setNewName("");
  };

  const removeMember = (idx: number) => {
    setMembers((m) => m.filter((_, i) => i !== idx));
  };

  const handleSave = async () => {
    if (weeklyBudget && (Number(weeklyBudget) < 0 || !Number.isInteger(Number(weeklyBudget)))) {
      toast.error("週間予算は0以上の整数で入力してください");
      return;
    }
    setSaving(true);
    try {
      const profile: HouseholdProfile = {
        members,
        food_preferences: foodPreferences || undefined,
        weekly_budget: weeklyBudget ? Number(weeklyBudget) : undefined,
      };
      await api.profile.update(profile);
      toast.success("プロファイルを保存しました");
      onNext();
    } catch {
      toast.error("保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  const preventSubmit = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") e.preventDefault();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">ステップ2: 家族構成</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          家族構成を登録すると、AIが人数や年齢に合わせた量を提案します。
        </p>

        {members.map((member, idx) => (
          <div key={idx} className="flex items-center gap-2 p-2 border rounded-md">
            <span className="text-sm font-medium">{member.name}</span>
            <Badge variant="outline">
              {member.age_group === "adult" ? "大人" : member.age_group === "child" ? "子供" : "乳幼児"}
            </Badge>
            <button onClick={() => removeMember(idx)} className="ml-auto text-destructive text-sm">
              削除
            </button>
          </div>
        ))}

        <div className="flex gap-2">
          <Input
            placeholder="名前"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addMember();
              }
            }}
            className="flex-1"
          />
          <select
            value={newAgeGroup}
            onChange={(e) => setNewAgeGroup(e.target.value as FamilyMember["age_group"])}
            className="border rounded-md px-3 py-2 text-sm"
          >
            <option value="adult">大人</option>
            <option value="child">子供</option>
            <option value="infant">乳幼児</option>
          </select>
          <Button type="button" variant="outline" onClick={addMember}>追加</Button>
        </div>

        <div className="space-y-2">
          <Label>食事の傾向（任意）</Label>
          <Input
            placeholder="例：和食中心、洋食多め"
            value={foodPreferences}
            onChange={(e) => setFoodPreferences(e.target.value)}
            onKeyDown={preventSubmit}
          />
        </div>

        <div className="space-y-2">
          <Label>週間予算（任意）</Label>
          <Input
            type="number"
            placeholder="円"
            value={weeklyBudget}
            onChange={(e) => {
              const v = e.target.value;
              if (v === "" || (/^\d+$/.test(v) && Number(v) >= 0)) {
                setWeeklyBudget(v);
              }
            }}
            onKeyDown={preventSubmit}
            min={0}
            step={1}
            className="w-40"
          />
        </div>

        <div className="flex gap-3">
          <Button type="button" variant="outline" onClick={onBack}>← 戻る</Button>
          <Button type="button" onClick={handleSave} disabled={saving} className="flex-1">
            {saving ? "保存中..." : members.length > 0 ? "保存して次へ →" : "スキップ →"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function RulesStep({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      if (notes.trim()) {
        const rules = await api.rules.get();
        rules.notes = notes;
        await api.rules.update(rules);
        toast.success("ルールを保存しました");
      }
      onNext();
    } catch {
      toast.error("保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">ステップ3: ショッピングルール</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          AIへの指示を自由に記入できます。詳細なルール（除外食材、ブランド設定）は後から設定画面で追加できます。
        </p>

        <Textarea
          placeholder="例：有機野菜を優先してください。なるべく国産を選んでください。"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={4}
        />

        <div className="flex gap-3">
          <Button variant="outline" onClick={onBack}>← 戻る</Button>
          <Button onClick={handleSave} disabled={saving} className="flex-1">
            {saving ? "保存中..." : notes.trim() ? "保存して完了 →" : "スキップ →"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function CompleteStep({ onFinish }: { onFinish: () => void }) {
  // Mark setup as done
  if (typeof window !== "undefined") {
    localStorage.setItem("setup_completed", "true");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base text-center">セットアップ完了</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-center">
        <p className="text-sm text-muted-foreground">
          初期設定が完了しました。設定はいつでも変更できます。
        </p>
        <Button onClick={onFinish} className="w-full">
          買い物を始める →
        </Button>
      </CardContent>
    </Card>
  );
}
