"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { UserPlus, User, Bot, ShieldAlert, Sparkles } from "lucide-react";
import { RoleSelect, Role } from "@/components/RoleSelect";
import { Toast } from "@/components/Toast";
import { PageHeader } from "@/components/ui/PageHeader";
import { MasterCard } from "@/components/ui/MasterCard";
import { FeatureRow } from "@/components/ui/FeatureRow";
import { GlassCard } from "@/components/ui/GlassCard";
import { StickySaveBar } from "@/components/ui/StickySaveBar";

export default function AutorolePage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [roles, setRoles] = useState<Role[]>([]);
  const [autorole, setAutorole] = useState<any>({ human_role_id: null, bot_role_id: null });
  const [initialAutorole, setInitialAutorole] = useState<any>({ human_role_id: null, bot_role_id: null });
  const [masterEnabled, setMasterEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [arRes, rolesRes] = await Promise.all([
          fetch(`/api/backend/guilds/${guildId}/autorole`),
          fetch(`/api/backend/guilds/${guildId}/roles`),
        ]);

        if (arRes.ok) {
          const data = await arRes.json();
          const parsed = {
            human_role_id: data.human_role_id ? String(data.human_role_id) : null,
            bot_role_id: data.bot_role_id ? String(data.bot_role_id) : null,
          };
          setAutorole(parsed);
          setInitialAutorole(parsed);
          setMasterEnabled(Boolean(parsed.human_role_id || parsed.bot_role_id));
        }

        if (rolesRes.ok) {
          setRoles(await rolesRes.json());
        }
      } catch {
        setToast({ type: "error", message: "Failed to load autorole configuration" });
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [guildId]);

  const hasChanges = JSON.stringify(autorole) !== JSON.stringify(initialAutorole);

  const handleSave = async () => {
    try {
      setSaving(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/autorole`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(autorole),
      });

      if (!res.ok) {
        throw new Error("Failed to save autorole settings");
      }

      setInitialAutorole(autorole);
      setToast({ type: "success", message: "Autorole settings updated successfully" });
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to update autorole" });
    } finally {
      setSaving(false);
    }
  };

  const handleDiscard = () => {
    setAutorole(initialAutorole);
  };

  const handleMasterToggle = (enabled: boolean) => {
    setMasterEnabled(enabled);
    if (!enabled) {
      setAutorole({ human_role_id: null, bot_role_id: null });
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-16 glass rounded-2xl w-72" />
        <div className="h-72 glass-strong rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-28">
      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}

      {/* Page Header */}
      <PageHeader
        icon={<UserPlus className="w-5 h-5 text-[var(--ice-silver)]" />}
        title="Autorole"
        description="Automatically grant designated roles to new members and bot applications upon server arrival."
      />

      {/* Master Card Pattern with Feature Rows & Side Info Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Master Card + Feature Rows (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          <MasterCard
            label="AUTOROLE SETTINGS"
            title="Automated Role Assignment"
            description="Manage auto-assigned roles for new members and bot applications. When toggled off, auto-role assignment is paused."
            enabled={masterEnabled}
            onToggle={handleMasterToggle}
          >
            {/* Feature Row 1: Human Member Role */}
            <FeatureRow
              icon={<User className="w-4 h-4 text-[var(--ice-silver)]" />}
              title="Human Member Role"
              description="Assigned instantly to newly verified human accounts."
              badge={autorole.human_role_id ? "active" : "off"}
              badgeLabel={autorole.human_role_id ? "Active" : "Unset"}
              defaultExpanded={true}
            >
              <div className="space-y-2">
                <RoleSelect
                  label="Assigned Human Role"
                  description="Human members receive this role immediately on join."
                  roles={roles}
                  value={autorole.human_role_id}
                  onChange={(val) => setAutorole({ ...autorole, human_role_id: val })}
                  placeholder="Select a role for new humans..."
                />
              </div>
            </FeatureRow>

            {/* Feature Row 2: Bot Application Role */}
            <FeatureRow
              icon={<Bot className="w-4 h-4 text-[var(--ice-silver)]" />}
              title="Bot Integration Role"
              description="Separate automated bots with an isolated service role."
              badge={autorole.bot_role_id ? "active" : "off"}
              badgeLabel={autorole.bot_role_id ? "Active" : "Unset"}
              defaultExpanded={Boolean(autorole.bot_role_id)}
            >
              <div className="space-y-2">
                <RoleSelect
                  label="Assigned Bot Role"
                  description="Bot accounts receive this role on arrival."
                  roles={roles}
                  value={autorole.bot_role_id}
                  onChange={(val) => setAutorole({ ...autorole, bot_role_id: val })}
                  placeholder="Select a role for bot integrations..."
                />
              </div>
            </FeatureRow>
          </MasterCard>
        </div>

        {/* Right Column: Side Info Card (~300px / 4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <GlassCard variant="soft" className="p-5 space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono tracking-wider uppercase text-[var(--ice-silver)] font-semibold">
              <ShieldAlert className="w-4 h-4 text-[var(--warning)] shrink-0" />
              <span>Role Hierarchy Rule</span>
            </div>
            <p className="text-[13px] text-[var(--text-muted)] leading-relaxed">
              In Discord, a bot cannot assign a role positioned higher than its own highest role. Ensure the <strong>NEXUS</strong> bot role is placed higher than your chosen autoroles in <em>Server Settings &gt; Roles</em>.
            </p>
          </GlassCard>

          <GlassCard variant="soft" className="p-5 space-y-2">
            <div className="text-xs font-mono tracking-wider uppercase text-[var(--hint)] font-semibold">
              Safety Verification
            </div>
            <p className="text-[12px] text-[var(--text-muted)] leading-relaxed">
              Never select roles with Administrator or Manage Server permissions as an autorole.
            </p>
          </GlassCard>
        </div>
      </div>

      {/* Sticky Bottom Save Bar */}
      <StickySaveBar
        show={hasChanges}
        isSaving={saving}
        onSave={handleSave}
        onDiscard={handleDiscard}
        saveLabel="Save configuration"
        message="Careful — you have unsaved autorole modifications"
      />
    </div>
  );
}
