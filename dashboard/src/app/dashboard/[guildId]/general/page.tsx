"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ChannelSelect, Channel } from "@/components/ChannelSelect";
import { RoleSelect, Role } from "@/components/RoleSelect";
import { Toast } from "@/components/Toast";
import { CardSkeleton } from "@/components/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { MasterCard } from "@/components/ui/MasterCard";
import { FeatureRow } from "@/components/ui/FeatureRow";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { StickySaveBar } from "@/components/ui/StickySaveBar";
import {
  Crown,
  Shield,
  Ticket,
  Lock,
  Unlock,
  FileText,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Trash2,
} from "lucide-react";

export default function GeneralSettingsPage() {
  const params = useParams();
  const guildId = params.guildId as string;

  const [channels, setChannels] = useState<Channel[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [settings, setSettings] = useState<any>({});
  const [initialSettings, setInitialSettings] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Action loaders
  const [botRoleLoading, setBotRoleLoading] = useState(false);
  const [ticketRoleLoading, setTicketRoleLoading] = useState(false);
  const [lockdownLoading, setLockdownLoading] = useState(false);
  const [setupBotLoading, setSetupBotLoading] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Controlled role selects
  const [selectedBotRoleId, setSelectedBotRoleId] = useState<string | null>(null);
  const [selectedTicketRoleId, setSelectedTicketRoleId] = useState<string | null>(null);
  const [lockdownReason, setLockdownReason] = useState("Emergency lockdown initiated via Dashboard");

  const loadData = async () => {
    try {
      setLoading(true);
      const [chRes, roRes, setRes] = await Promise.all([
        fetch(`/api/backend/guilds/${guildId}/channels`),
        fetch(`/api/backend/guilds/${guildId}/roles`),
        fetch(`/api/backend/guilds/${guildId}/settings`),
      ]);

      if (chRes.ok) setChannels(await chRes.json());
      if (roRes.ok) setRoles(await roRes.json());
      if (setRes.ok) {
        const data = await setRes.json();
        setSettings(data);
        setInitialSettings(data);
        setSelectedBotRoleId(data.bot_role_id || null);
        setSelectedTicketRoleId(data.ticket_role_id || null);
      }
    } catch {
      setToast({ type: "error", message: "Failed to load guild settings" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [guildId]);

  const hasChanges =
    settings.server_log_ch !== initialSettings.server_log_ch ||
    settings.mod_log_ch !== initialSettings.mod_log_ch ||
    settings.activity_log_ch !== initialSettings.activity_log_ch ||
    settings.cmd_log_ch !== initialSettings.cmd_log_ch;

  const handleSave = async () => {
    try {
      setSaving(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          server_log_ch: settings.server_log_ch || null,
          mod_log_ch: settings.mod_log_ch || null,
          activity_log_ch: settings.activity_log_ch || null,
          cmd_log_ch: settings.cmd_log_ch || null,
        }),
      });

      const resData = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(resData.detail || resData.error || "Failed to save settings");
      }

      setInitialSettings(settings);
      setToast({ type: "success", message: "Audit log channels saved successfully!" });
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to update settings" });
    } finally {
      setSaving(false);
    }
  };

  const handleSetBotRole = async () => {
    if (!selectedBotRoleId) {
      setToast({ type: "error", message: "Please select a role to assign as Bot-Role" });
      return;
    }

    try {
      setBotRoleLoading(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/settings/bot-role`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role_id: selectedBotRoleId }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to assign Bot-Role");
      }

      setSettings((prev: any) => ({
        ...prev,
        bot_role_id: data.bot_role_id,
        bot_role_name: data.bot_role_name,
        bot_role_color: data.bot_role_color,
        bot_role_members_count: data.bot_role_members_count,
      }));
      setInitialSettings((prev: any) => ({
        ...prev,
        bot_role_id: data.bot_role_id,
        bot_role_name: data.bot_role_name,
        bot_role_color: data.bot_role_color,
        bot_role_members_count: data.bot_role_members_count,
      }));

      setToast({
        type: "success",
        message: `Bot-Role successfully configured to @${data.bot_role_name}!`,
      });
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to set Bot-Role" });
    } finally {
      setBotRoleLoading(false);
    }
  };

  const handleRemoveBotRole = async () => {
    const confirm = window.confirm(
      "Are you sure you want to remove the Bot-Role? Only the Server Owner will be able to manage the bot until a new role is set."
    );
    if (!confirm) return;

    try {
      setBotRoleLoading(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/settings/remove-bot-role`, {
        method: "POST",
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to remove Bot-Role");
      }

      setSettings((prev: any) => ({
        ...prev,
        bot_role_id: null,
        bot_role_name: null,
        bot_role_color: null,
        bot_role_members_count: 0,
      }));
      setInitialSettings((prev: any) => ({
        ...prev,
        bot_role_id: null,
        bot_role_name: null,
        bot_role_color: null,
        bot_role_members_count: 0,
      }));
      setSelectedBotRoleId(null);

      setToast({
        type: "success",
        message: "Bot-Role removed successfully. Bot access is now restricted to Server Owner.",
      });
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to remove Bot-Role" });
    } finally {
      setBotRoleLoading(false);
    }
  };

  const handleSetTicketRole = async () => {
    if (!selectedTicketRoleId) {
      setToast({ type: "error", message: "Please select a role to assign as Ticket Support Staff" });
      return;
    }

    try {
      setTicketRoleLoading(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/settings/ticket-role`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role_id: selectedTicketRoleId }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to assign Ticket Support Role");
      }

      setSettings((prev: any) => ({
        ...prev,
        ticket_role_id: data.ticket_role_id,
        ticket_role_name: data.ticket_role_name,
        ticket_role_color: data.ticket_role_color,
        ticket_role_members_count: data.ticket_role_members_count,
      }));
      setInitialSettings((prev: any) => ({
        ...prev,
        ticket_role_id: data.ticket_role_id,
        ticket_role_name: data.ticket_role_name,
        ticket_role_color: data.ticket_role_color,
        ticket_role_members_count: data.ticket_role_members_count,
      }));

      setToast({
        type: "success",
        message: `Ticket Staff Role successfully assigned to @${data.ticket_role_name}!`,
      });
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to set Ticket Staff Role" });
    } finally {
      setTicketRoleLoading(false);
    }
  };

  const handleRemoveTicketRole = async () => {
    const confirm = window.confirm(
      "Are you sure you want to remove the Ticket Support Staff Role? Only the Server Owner and Bot-Role holders will have access to tickets until a new role is configured."
    );
    if (!confirm) return;

    try {
      setTicketRoleLoading(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/settings/remove-ticket-role`, {
        method: "POST",
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to remove Ticket Staff Role");
      }

      setSettings((prev: any) => ({
        ...prev,
        ticket_role_id: null,
        ticket_role_name: null,
        ticket_role_color: null,
        ticket_role_members_count: 0,
      }));
      setInitialSettings((prev: any) => ({
        ...prev,
        ticket_role_id: null,
        ticket_role_name: null,
        ticket_role_color: null,
        ticket_role_members_count: 0,
      }));
      setSelectedTicketRoleId(null);

      setToast({
        type: "success",
        message: "Ticket Support Staff Role cleared successfully.",
      });
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to remove Ticket Staff Role" });
    } finally {
      setTicketRoleLoading(false);
    }
  };

  const handleLockdown = async () => {
    const confirm = window.confirm(
      "Are you sure you want to trigger an Emergency Lockdown across all channels? This will prevent @everyone from sending messages."
    );
    if (!confirm) return;

    try {
      setLockdownLoading(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/settings/lockdown`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scope: "all", reason: lockdownReason }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to trigger lockdown");
      }

      setToast({
        type: "success",
        message: `Emergency Lockdown Active: Locked down ${data.channels_locked} text channel(s)!`,
      });
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to trigger lockdown" });
    } finally {
      setLockdownLoading(false);
    }
  };

  const handleUnlockdown = async () => {
    try {
      setLockdownLoading(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/settings/unlockdown`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scope: "all" }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to lift lockdown");
      }

      setToast({
        type: "success",
        message: `Lockdown Lifted: Restored permissions across ${data.channels_unlocked} text channel(s)!`,
      });
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to lift lockdown" });
    } finally {
      setLockdownLoading(false);
    }
  };

  const handleSetupBot = async () => {
    try {
      setSetupBotLoading(true);
      const res = await fetch(`/api/backend/guilds/${guildId}/settings/setupbot`, {
        method: "POST",
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Failed to auto-provision channels");
      }
      setToast({
        type: "success",
        message: "Successfully auto-provisioned NEXUS LOGS and bound all 4 audit channels!",
      });
      loadData();
    } catch (err: any) {
      setToast({ type: "error", message: err.message || "Failed to execute /setupbot" });
    } finally {
      setSetupBotLoading(false);
    }
  };

  const handleReset = () => {
    setSettings(initialSettings);
  };

  if (loading) {
    return (
      <div className="space-y-6 pb-24">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  const isServerOwner = settings.is_server_owner ?? false;
  const currentBotRole = roles.find((r) => r.id === settings.bot_role_id);
  const activeBotRoleName = currentBotRole?.name || settings.bot_role_name;

  const currentTicketRole = roles.find((r) => r.id === settings.ticket_role_id);
  const activeTicketRoleName = currentTicketRole?.name || settings.ticket_role_name;

  return (
    <div className="space-y-8 animate-in fade-in duration-200 pb-28 font-sans">
      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}

      {/* Page Header */}
      <PageHeader
        icon={<Crown className="w-5 h-5 text-[var(--ice-silver)]" />}
        title="Settings & Administration"
        description="Configure server owner exclusive controls, bot roles, ticket staff permissions, and audit logs."
      />

      {/* Master Section 1: Bot-Role & Staff Isolation */}
      <MasterCard
        label="ACCESS CONTROL"
        title="Bot-Role & Permissions"
        description="Designate a dedicated Discord role that grants staff members access to configure bot settings. Server Owner always holds root authority."
        badge={
          settings.bot_role_id ? (
            <StatusBadge status="active" label={`@${activeBotRoleName}`} />
          ) : (
            <StatusBadge status="warning" label="Owner Only" />
          )
        }
      >
        <div className="space-y-4">
          {/* Feature Row 1: Bot Role */}
          <FeatureRow
            icon={<Shield className="w-5 h-5" />}
            title="Designate Bot Management Role"
            description="Members with this role can run bot management commands and access this dashboard."
            badge={
              settings.bot_role_id ? (
                <StatusBadge status="active" label="Enforced" />
              ) : (
                <StatusBadge status="off" label="Unset" />
              )
            }
          >
            <div className="space-y-4 pt-2">
              <RoleSelect
                roles={roles}
                value={selectedBotRoleId || ""}
                onChange={(val) => setSelectedBotRoleId(val || null)}
                placeholder="Select a role to designate as Bot-Role..."
              />
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleSetBotRole}
                  disabled={botRoleLoading || !selectedBotRoleId || selectedBotRoleId === settings.bot_role_id}
                  className="px-4 py-2.5 rounded-xl bg-[var(--ice-silver)] text-[var(--ink)] font-mono text-xs font-semibold uppercase tracking-wider hover:opacity-90 transition-all disabled:opacity-40 cursor-pointer shadow-sm"
                >
                  {botRoleLoading ? "Updating..." : "Save Bot-Role"}
                </button>
                {settings.bot_role_id && (
                  <button
                    type="button"
                    onClick={handleRemoveBotRole}
                    disabled={botRoleLoading}
                    className="px-4 py-2.5 rounded-xl glass-soft border border-[var(--error)]/30 text-[var(--error)] hover:bg-[var(--error)]/10 font-mono text-xs font-semibold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-1.5"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Clear Role</span>
                  </button>
                )}
              </div>
            </div>
          </FeatureRow>

          {/* Feature Row 2: Ticket Support Staff Role */}
          <FeatureRow
            icon={<Ticket className="w-5 h-5" />}
            title="Ticket Support Staff Role"
            description="Role permitted to view, respond to, and close user support tickets."
            badge={
              settings.ticket_role_id ? (
                <StatusBadge status="active" label={`@${activeTicketRoleName}`} />
              ) : (
                <StatusBadge status="off" label="Unset" />
              )
            }
          >
            <div className="space-y-4 pt-2">
              <RoleSelect
                roles={roles}
                value={selectedTicketRoleId || ""}
                onChange={(val) => setSelectedTicketRoleId(val || null)}
                placeholder="Select support staff role..."
              />
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleSetTicketRole}
                  disabled={ticketRoleLoading || !selectedTicketRoleId || selectedTicketRoleId === settings.ticket_role_id}
                  className="px-4 py-2.5 rounded-xl bg-[var(--ice-silver)] text-[var(--ink)] font-mono text-xs font-semibold uppercase tracking-wider hover:opacity-90 transition-all disabled:opacity-40 cursor-pointer shadow-sm"
                >
                  {ticketRoleLoading ? "Updating..." : "Save Ticket Role"}
                </button>
                {settings.ticket_role_id && (
                  <button
                    type="button"
                    onClick={handleRemoveTicketRole}
                    disabled={ticketRoleLoading}
                    className="px-4 py-2.5 rounded-xl glass-soft border border-[var(--error)]/30 text-[var(--error)] hover:bg-[var(--error)]/10 font-mono text-xs font-semibold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-1.5"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Clear Role</span>
                  </button>
                )}
              </div>
            </div>
          </FeatureRow>
        </div>
      </MasterCard>

      {/* Master Section 2: Emergency Lockdown */}
      <MasterCard
        label="EMERGENCY CONTROLS"
        title="Emergency Server Lockdown"
        description="Immediately revoke message sending permissions for @everyone across all standard text channels in the server."
      >
        <div className="space-y-4">
          <div>
            <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
              Lockdown Reason
            </label>
            <input
              type="text"
              value={lockdownReason}
              onChange={(e) => setLockdownReason(e.target.value)}
              placeholder="e.g. Server raid in progress, temporary containment active..."
              className="w-full h-11 px-3.5 glass-soft border border-[var(--glass-border)] rounded-xl text-sm text-[var(--ice-silver)] focus:outline-none focus:border-[var(--ice-silver)]/50 transition-colors"
            />
            <p className="text-[12px] text-[var(--text-muted)] mt-1.5">
              This reason will be recorded in the server's audit logs and broadcast to members.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              type="button"
              onClick={handleLockdown}
              disabled={lockdownLoading}
              className="px-5 py-2.5 rounded-xl glass-soft border border-[var(--warning)]/40 text-[var(--warning)] hover:bg-[var(--warning)]/10 font-mono text-xs font-bold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-2 shadow-sm"
            >
              <Lock className="w-4 h-4" />
              <span>{lockdownLoading ? "Processing..." : "Trigger Emergency Lockdown"}</span>
            </button>
            <button
              type="button"
              onClick={handleUnlockdown}
              disabled={lockdownLoading}
              className="px-5 py-2.5 rounded-xl bg-[var(--ice-silver)] text-[var(--ink)] font-mono text-xs font-bold uppercase tracking-wider hover:opacity-90 transition-all cursor-pointer flex items-center gap-2 shadow-sm"
            >
              <Unlock className="w-4 h-4" />
              <span>{lockdownLoading ? "Processing..." : "Lift Lockdown"}</span>
            </button>
          </div>
        </div>
      </MasterCard>

      {/* Master Section 3: Audit Log Routing */}
      <MasterCard
        label="LOG ROUTING"
        title="4-Channel Audit Log Binding"
        description="Route distinct event categories to individual Discord channels for monitoring and moderation."
        badge={
          <button
            type="button"
            onClick={handleSetupBot}
            disabled={setupBotLoading}
            className="px-3.5 py-1.5 rounded-xl glass-soft border border-[var(--ice-silver)]/20 hover:border-[var(--ice-silver)]/50 text-[var(--ice-silver)] font-mono text-[11px] font-semibold tracking-wider uppercase transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5 text-[var(--hint)]" />
            <span>{setupBotLoading ? "Provisioning..." : "1-Click /setupbot"}</span>
          </button>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
          {/* Channel 1: Server Log */}
          <div>
            <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
              Server Log Channel
            </label>
            <ChannelSelect
              channels={channels}
              value={settings.server_log_ch || ""}
              onChange={(val) => setSettings({ ...settings, server_log_ch: val || null })}
              placeholder="Select server log channel..."
            />
            <p className="text-[12px] text-[var(--text-muted)] mt-1.5">
              Role changes, channel updates, invites, and vanity changes.
            </p>
          </div>

          {/* Channel 2: Mod Log */}
          <div>
            <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
              Moderation Log Channel
            </label>
            <ChannelSelect
              channels={channels}
              value={settings.mod_log_ch || ""}
              onChange={(val) => setSettings({ ...settings, mod_log_ch: val || null })}
              placeholder="Select moderation log channel..."
            />
            <p className="text-[12px] text-[var(--text-muted)] mt-1.5">
              Warn, mute, kick, ban, unban, and case notes.
            </p>
          </div>

          {/* Channel 3: Activity Log */}
          <div>
            <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
              Activity Log Channel
            </label>
            <ChannelSelect
              channels={channels}
              value={settings.activity_log_ch || ""}
              onChange={(val) => setSettings({ ...settings, activity_log_ch: val || null })}
              placeholder="Select activity log channel..."
            />
            <p className="text-[12px] text-[var(--text-muted)] mt-1.5">
              Member joins, leaves, voice states, and avatar changes.
            </p>
          </div>

          {/* Channel 4: Command Log */}
          <div>
            <label className="text-[13px] font-medium text-[var(--ice-silver)] block mb-1.5">
              Command Execution Log Channel
            </label>
            <ChannelSelect
              channels={channels}
              value={settings.cmd_log_ch || ""}
              onChange={(val) => setSettings({ ...settings, cmd_log_ch: val || null })}
              placeholder="Select command log channel..."
            />
            <p className="text-[12px] text-[var(--text-muted)] mt-1.5">
              Slash command execution history and dashboard audit triggers.
            </p>
          </div>
        </div>
      </MasterCard>

      {/* Sticky Save Bar */}
      <StickySaveBar
        hasChanges={hasChanges}
        loading={saving}
        onSave={handleSave}
        onDiscard={handleReset}
      />
    </div>
  );
}
