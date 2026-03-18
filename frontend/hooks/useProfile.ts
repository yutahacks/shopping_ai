"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { HouseholdProfile } from "@/lib/types";

export function useProfile() {
  const [profile, setProfile] = useState<HouseholdProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.profile
      .get()
      .then(setProfile)
      .catch(() => setProfile({ members: [] }))
      .finally(() => setLoading(false));
  }, []);

  const saveProfile = useCallback(async (updated: HouseholdProfile) => {
    setSaving(true);
    try {
      const result = await api.profile.update(updated);
      setProfile(result);
      return result;
    } catch {
      return null;
    } finally {
      setSaving(false);
    }
  }, []);

  return { profile, loading, saving, saveProfile };
}
