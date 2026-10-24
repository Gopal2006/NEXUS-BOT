/**
 * NEXUS BOT — Web Control Dashboard Client Logic
 * Handles real-time telemetry, WebSocket streaming, Discord embed simulation,
 * guild state synchronization, RBAC authentication & Admin Panel command.
 */

// ── Application State ────────────────────────────────────────────────────────
const state = {
  online: false,
  guilds: [],
  activeGuildId: null,
  activeGuild: null,
  ws: null,
  wsConnected: false,
  terminalFilter: 'ALL',
  terminalLogs: [],
  dmMode: 'user', // 'user' or 'role'
  authToken: localStorage.getItem('nexus_token') || null,
  currentUser: null,
};

// ── Central API Fetch Wrapper with Auth Injection & 401 Handling ─────────────
async function apiFetch(url, options = {}) {
  options.headers = options.headers || {};
  if (state.authToken) {
    options.headers['Authorization'] = `Bearer ${state.authToken}`;
  }
  options.credentials = 'same-origin';

  try {
    const res = await fetch(url, options);
    if (res.status === 401) {
      // Session expired, invalidated, or unauthenticated
      state.authToken = null;
      state.currentUser = null;
      localStorage.removeItem('nexus_token');
      updateAuthUI(null);
      showLoginModal('Session expired or unauthorized. Please authenticate.');
      throw new Error('Unauthorized');
    }
    return res;
  } catch (err) {
    throw err;
  }
}

// ── Initialization ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initTabs();
  initColorPickers();
  initLivePreview();
  initTerminal();
  initEventHandlers();

  // Public status heartbeat
  fetchStatus();
  setInterval(fetchStatus, 6000);

  // Authenticate user session
  const isAuthenticated = await checkAuth();
  if (isAuthenticated) {
    fetchGuilds();
    initWebSocket();
  }
});

// ── Toast Notification System ────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : type === 'warning' ? '⚠' : 'ℹ'}</span>
    <span class="toast-msg">${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ── Tab Navigation ───────────────────────────────────────────────────────────
function initTabs() {
  const tabButtons = document.querySelectorAll('.nav-tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');
      switchTab(targetId);
    });
  });
}

function switchTab(tabId) {
  // STRICT SECURITY GATE: Only authorized Admins can view or switch to Admin Panel / Non-Prefix tools!
  if (tabId === 'tab-admin' || tabId === 'tab-nonprefix') {
    if (!state.currentUser || !state.currentUser.is_admin) {
      showToast('Unauthorized: Administrator access required', 'error');
      return;
    }
  }

  document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

  const activeBtn = document.querySelector(`.nav-tab-btn[data-tab="${tabId  }"]`);
  const activePane = document.getElementById(tabId);

  if (activeBtn) activeBtn.classList.add('active');
  if (activePane) activePane.classList.add('active');

  // Trigger tab-specific refresh
  if (tabId === 'tab-admin') loadAdminData();
  if (tabId === 'tab-giveaways') fetchGiveaways();
  if (tabId === 'tab-tickets') fetchTickets();
  if (tabId === 'tab-moderation' && state.activeGuildId) fetchWarns(state.activeGuildId);
  if (tabId === 'tab-nonprefix') fetchNonPrefix();
}


// ── Data Fetching: Status & Metrics ──────────────────────────────────────────
async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) throw new Error('API Error');
    const data = await res.json();

    state.online = data.online;

    // Update Status Pill
    const pill = document.getElementById('bot-status-pill');
    const label = document.getElementById('bot-status-text');
    const pingBadge = document.getElementById('bot-ping-badge');
    const avatarStatus = document.getElementById('bot-avatar-status');

    if (data.online) {
      pill.className = 'status-pill status-online';
      label.textContent = 'Online';
      if (data.ping_ms !== null) {
        pingBadge.textContent = `${data.ping_ms} ms`;
        pingBadge.classList.remove('hidden');
        document.getElementById('stat-ping').textContent = `${data.ping_ms} ms`;
      }
      if (avatarStatus) avatarStatus.style.background = 'var(--green)';
    } else {
      pill.className = 'status-pill status-offline';
      label.textContent = 'Bot Offline';
      pingBadge.classList.add('hidden');
      document.getElementById('stat-ping').textContent = '--';
      if (avatarStatus) avatarStatus.style.background = 'var(--red)';
    }

    // Top & Overview metrics
    if (data.bot_user) {
      document.getElementById('bot-name-label').textContent = data.bot_user.name;
      if (data.bot_user.avatar_url) {
        document.getElementById('bot-avatar-img').src = data.bot_user.avatar_url;
        document.getElementById('sim-avatar').src = data.bot_user.avatar_url;
      }
      document.getElementById('sim-bot-name').textContent = data.bot_user.name;
    }

    document.getElementById('stat-guilds').textContent = data.guild_count || 0;
    document.getElementById('stat-users').textContent = data.user_count ? data.user_count.toLocaleString() : '0';
    document.getElementById('kpi-uptime-badge').textContent = `Uptime: ${data.uptime}`;

    if (data.db_stats) {
      document.getElementById('stat-giveaways').textContent = data.db_stats.active_giveaways || 0;
      document.getElementById('stat-tickets').textContent = data.db_stats.open_tickets || 0;
      document.getElementById('stat-warns').textContent = data.db_stats.total_warns || 0;
    }

    if (data.activity && data.activity.name) {
      document.getElementById('current-presence-badge').textContent = `${data.activity.type}: ${data.activity.name}`;
    } else {
      document.getElementById('current-presence-badge').textContent = `Status: ${data.status || 'Standard'}`;
    }

  } catch (err) {
    const pill = document.getElementById('bot-status-pill');
    pill.className = 'status-pill status-offline';
    document.getElementById('bot-status-text').textContent = 'Server Unreachable';
  }
}

// ── Data Fetching: Guilds ────────────────────────────────────────────────────
async function fetchGuilds() {
  try {
    const res = await apiFetch('/api/guilds');
    if (!res.ok) throw new Error('Failed to load guilds');
    const data = await res.json();
    state.guilds = data.guilds || [];

    renderServerDropdown();
    renderOverviewServerGrid();

    if (state.guilds.length > 0 && !state.activeGuildId) {
      setActiveGuild(state.guilds[0].id);
    }
  } catch (err) {
    console.error('fetchGuilds error:', err);
  }
}

function renderServerDropdown() {
  const select = document.getElementById('server-select');
  select.innerHTML = '';

  if (state.guilds.length === 0) {
    select.innerHTML = '<option value="">No servers joined</option>';
    return;
  }

  state.guilds.forEach(g => {
    const opt = document.createElement('option');
    opt.value = g.id;
    opt.textContent = `${g.name} (${g.member_count} members)`;
    select.appendChild(opt);
  });

  select.value = state.activeGuildId || state.guilds[0].id;
}

function renderOverviewServerGrid() {
  const container = document.getElementById('overview-server-grid');
  const countBadge = document.getElementById('server-count-badge');
  countBadge.textContent = `${state.guilds.length} Servers`;

  if (state.guilds.length === 0) {
    container.innerHTML = '<div class="empty-state">No Discord servers connected yet. Invite Nexus to your server!</div>';
    return;
  }

  container.innerHTML = '';
  state.guilds.forEach(g => {
    const card = document.createElement('div');
    card.className = 'server-card-item';
    const iconHtml = g.icon
      ? `<img src="${g.icon}" class="server-card-icon" alt="${g.name}">`
      : `<div class="server-card-icon-fallback">${g.name.substring(0, 2).toUpperCase()}</div>`;

    card.innerHTML = `
      ${iconHtml}
      <div class="server-card-details">
        <div class="server-card-name">${escapeHtml(g.name)}</div>
        <div class="server-card-sub">${g.member_count} Members · ${g.channels.length} Channels</div>
      </div>
      <button class="btn btn-secondary btn-sm" onclick="selectAndConfigureServer('${g.id}')">Configure</button>
    `;
    container.appendChild(card);
  });
}

function selectAndConfigureServer(guildId) {
  setActiveGuild(guildId);
  switchTab('tab-config');
}

function setActiveGuild(guildId) {
  state.activeGuildId = guildId;
  state.activeGuild = state.guilds.find(g => g.id === guildId) || null;

  const select = document.getElementById('server-select');
  if (select && select.value !== guildId) {
    select.value = guildId;
  }

  if (state.activeGuild) {
    document.getElementById('config-server-name').textContent = state.activeGuild.name;
    document.getElementById('sim-footer-text').textContent = state.activeGuild.name;

    // Populate all channel & role pickers
    populateGuildPickers(state.activeGuild);
    // Fetch and populate configuration
    fetchGuildConfig(guildId);
  }
}

function populateGuildPickers(guild) {
  const textChannels = guild.channels.filter(c => c.type === 'text');
  const roles = guild.roles;
  const members = guild.members || [];

  // Helper to fill channel select
  const fillSelect = (selectId, items, defaultText = 'Disabled / Not Set') => {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    const currVal = sel.value;
    sel.innerHTML = `<option value="">${defaultText}</option>`;
    items.forEach(it => {
      const opt = document.createElement('option');
      opt.value = it.id;
      opt.textContent = `#${it.name}`;
      sel.appendChild(opt);
    });
    if (currVal) sel.value = currVal;
  };

  // Roles select helper
  const fillRoleSelect = (selectId, defaultText = 'No Role Assigned') => {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    const currVal = sel.value;
    sel.innerHTML = `<option value="">${defaultText}</option>`;
    roles.forEach(r => {
      const opt = document.createElement('option');
      opt.value = r.id;
      opt.textContent = `@${r.name}`;
      sel.appendChild(opt);
    });
    if (currVal) sel.value = currVal;
  };

  // Channels
  fillSelect('cfg-welcome-ch', textChannels);
  fillSelect('cfg-leave-ch', textChannels);
  fillSelect('cfg-mod-log', textChannels);
  fillSelect('cfg-server-log', textChannels);
  fillSelect('cfg-activity-log', textChannels);
  fillSelect('cfg-cmd-log', textChannels);

  fillSelect('mod-channel-select', textChannels, 'Select a channel...');
  fillSelect('ann-channel-select', textChannels, 'Select target channel...');
  fillSelect('gw-channel-select', textChannels, 'Select channel...');
  fillSelect('poll-channel-select', textChannels, 'Select target channel...');
  fillSelect('ticket-channel-select', textChannels, 'Select channel...');

  // Roles
  fillRoleSelect('cfg-bot-role', 'No Role Assigned (Owner Only)');
  fillRoleSelect('cfg-ticket-role', 'No Role Assigned');
  fillRoleSelect('gw-role-select', 'Everyone (No role restriction)');
  fillRoleSelect('dm-role-select', 'Select target role...');

  // Members picker for Moderation & DM
  const fillMemberSelect = (selectId) => {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    sel.innerHTML = '<option value="">Select a member...</option>';
    members.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = `${m.displayName || m.name} (@${m.name})`;
      sel.appendChild(opt);
    });
  };

  fillMemberSelect('mod-member-select');
  fillMemberSelect('dm-member-select');
}

async function fetchGuildConfig(guildId) {
  try {
    const res = await apiFetch(`/api/guild/${guildId}/config`);
    if (!res.ok) throw new Error('Failed to load config');
    const cfg = await res.json();

    // Map fields
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val || '';
    };

    setVal('cfg-bot-role', cfg.bot_role_id);
    setVal('cfg-ticket-role', cfg.ticket_role_id);
    setVal('cfg-welcome-ch', cfg.welcome_ch);
    setVal('cfg-leave-ch', cfg.leave_ch);
    setVal('cfg-mod-log', cfg.mod_log_ch || cfg.log_ch);
    setVal('cfg-server-log', cfg.server_log_ch);
    setVal('cfg-activity-log', cfg.activity_log_ch);
    setVal('cfg-cmd-log', cfg.cmd_log_ch);

    if (cfg.welcome_msg) setVal('cfg-welcome-msg', cfg.welcome_msg);
    if (cfg.leave_msg) setVal('cfg-leave-msg', cfg.leave_msg);

    updateWelcomePreview();
  } catch (err) {
    console.error('fetchGuildConfig error:', err);
  }
}

// ── Live Discord Message Embed Simulation ────────────────────────────────────
function initColorPickers() {
  const palette = document.getElementById('ann-color-palette');
  if (!palette) return;

  const colorMap = {
    blurple: '#5865F2',
    green: '#57F287',
    gold: '#FEE75C',
    red: '#ED4245',
    purple: '#9B59B6',
    cyan: '#1ABC9C',
    fuchsia: '#EB459E',
    dark: '#2B2D31'
  };

  palette.querySelectorAll('.color-swatch').forEach(swatch => {
    swatch.addEventListener('click', () => {
      palette.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('active'));
      swatch.classList.add('active');
      const colorKey = swatch.getAttribute('data-color');
      document.getElementById('ann-color-val').value = colorKey;

      // Update Live Preview border color
      const hex = colorMap[colorKey] || '#5865F2';
      document.getElementById('sim-embed').style.borderLeftColor = hex;
    });
  });
}

function initLivePreview() {
  const titleInput = document.getElementById('ann-title-input');
  const contentInput = document.getElementById('ann-content-input');
  const bannerInput = document.getElementById('ann-banner-url');
  const thumbInput = document.getElementById('ann-thumb-url');
  const buttonInput = document.getElementById('ann-button-input');
  const pingSelect = document.getElementById('ann-ping-select');

  const updatePreview = () => {
    const title = titleInput.value.trim();
    const content = contentInput.value.trim();
    const banner = bannerInput.value.trim();
    const thumb = thumbInput.value.trim();
    const button = buttonInput.value.trim();
    const ping = pingSelect.value;

    // Title
    const titleEl = document.getElementById('sim-title');
    titleEl.textContent = title || 'Announcement Title';
    titleEl.style.display = title ? 'block' : 'none';

    // Content
    const descEl = document.getElementById('sim-desc');
    descEl.textContent = content || 'Announcement description will appear here.';

    // Banner
    const bannerWrap = document.getElementById('sim-banner-wrap');
    const bannerImg = document.getElementById('sim-banner-img');
    if (banner) {
      bannerImg.src = banner;
      bannerWrap.classList.remove('hidden');
    } else {
      bannerWrap.classList.add('hidden');
    }

    // Thumbnail
    const thumbWrap = document.getElementById('sim-thumb-wrap');
    const thumbImg = document.getElementById('sim-thumb-img');
    if (thumb) {
      thumbImg.src = thumb;
      thumbWrap.classList.remove('hidden');
    } else {
      thumbWrap.classList.add('hidden');
    }

    // Button
    const btnWrap = document.getElementById('sim-button-wrap');
    const btnLabel = document.getElementById('sim-button-label');
    if (button) {
      const parts = button.split('|');
      btnLabel.textContent = parts[0].trim() || 'Action';
      btnWrap.classList.remove('hidden');
    } else {
      btnWrap.classList.add('hidden');
    }

    // Ping
    const pingEl = document.getElementById('sim-ping-preview');
    if (ping === 'everyone') {
      pingEl.textContent = '@everyone';
      pingEl.classList.remove('hidden');
    } else if (ping === 'here') {
      pingEl.textContent = '@here';
      pingEl.classList.remove('hidden');
    } else {
      pingEl.classList.add('hidden');
    }
  };

  [titleInput, contentInput, bannerInput, thumbInput, buttonInput].forEach(el => {
    if (el) el.addEventListener('input', updatePreview);
  });
  if (pingSelect) pingSelect.addEventListener('change', updatePreview);

  // DM preview listeners
  const dmTitle = document.getElementById('dm-title-input');
  const dmContent = document.getElementById('dm-content-input');
  const updateDmPreview = () => {
    const simDmTitle = document.getElementById('sim-dm-title');
    const simDmDesc = document.getElementById('sim-dm-desc');
    if (simDmTitle && dmTitle) simDmTitle.textContent = dmTitle.value || 'Direct Notice';
    if (simDmDesc && dmContent) simDmDesc.textContent = dmContent.value || 'Direct message text...';
  };
  if (dmTitle) dmTitle.addEventListener('input', updateDmPreview);
  if (dmContent) dmContent.addEventListener('input', updateDmPreview);

  // Welcome message preview listener
  const welcomeInput = document.getElementById('cfg-welcome-msg');
  if (welcomeInput) {
    welcomeInput.addEventListener('input', updateWelcomePreview);
  }
}

function updateWelcomePreview() {
  const input = document.getElementById('cfg-welcome-msg');
  const preview = document.getElementById('welcome-live-preview');
  if (!input || !preview) return;

  const serverName = state.activeGuild ? state.activeGuild.name : 'Nexus Hub';
  const text = input.value
    .replace(/{mention}/g, '@NewMember')
    .replace(/{name}/g, 'NewMember')
    .replace(/{guild}/g, serverName);

  preview.textContent = text;
}

function insertPlaceholder(inputId, placeholder) {
  const el = document.getElementById(inputId);
  if (!el) return;
  const start = el.selectionStart || el.value.length;
  const end = el.selectionEnd || el.value.length;
  el.value = el.value.substring(0, start) + placeholder + el.value.substring(end);
  el.focus();
  el.selectionStart = el.selectionEnd = start + placeholder.length;
  updateWelcomePreview();
}

// ── Event Handlers & Submissions ─────────────────────────────────────────────
function initEventHandlers() {
  // Server selector change listener (attached once)
  const serverSelect = document.getElementById('server-select');
  if (serverSelect) {
    serverSelect.addEventListener('change', (e) => {
      if (e.target.value) {
        setActiveGuild(e.target.value);
      }
    });
  }

  // Refresh button in top-nav
  const refreshBtn = document.getElementById('btn-refresh');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      fetchStatus();
      if (state.currentUser) {
        fetchGuilds();
        if (state.activeGuildId) {
          fetchGuildConfig(state.activeGuildId);
          fetchWarns(state.activeGuildId);
        }
      }
      showToast('Live telemetry refreshed!', 'info');
    });
  }

  // Auth: Logout Button
  const logoutBtn = document.getElementById('btn-logout');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }

  // Auth: Login Form
  const loginForm = document.getElementById('form-login');
  if (loginForm) {
    loginForm.addEventListener('submit', handleLoginSubmit);
  }

  // Admin Panel: Open Add User Modal
  const openAddAdminBtn = document.getElementById('btn-open-add-admin');
  if (openAddAdminBtn) {
    openAddAdminBtn.addEventListener('click', () => openModal('modal-add-admin'));
  }

  // Admin Panel: Add User Form
  const addAdminForm = document.getElementById('form-add-admin');
  if (addAdminForm) {
    addAdminForm.addEventListener('submit', handleAddAdminSubmit);
  }

  // Admin Panel: Reset Passcode Form
  const resetPassForm = document.getElementById('form-reset-passcode');
  if (resetPassForm) {
    resetPassForm.addEventListener('submit', handleResetPasscodeSubmit);
  }

  // Admin Panel: Refresh Buttons
  const refreshUsersBtn = document.getElementById('btn-refresh-admin-users');
  if (refreshUsersBtn) {
    refreshUsersBtn.addEventListener('click', loadAdminUsers);
  }

  const refreshSessionsBtn = document.getElementById('btn-refresh-admin-sessions');
  if (refreshSessionsBtn) {
    refreshSessionsBtn.addEventListener('click', loadAdminSessions);
  }

  const refreshAuditBtn = document.getElementById('btn-refresh-audit-logs');
  if (refreshAuditBtn) {
    refreshAuditBtn.addEventListener('click', loadAdminAuditLogs);
  }

  const auditFilter = document.getElementById('audit-filter-action');
  if (auditFilter) {
    auditFilter.addEventListener('change', loadAdminAuditLogs);
  }

  // Dead refresh buttons now fully wired!
  const refreshWarnsBtn = document.getElementById('btn-refresh-warns');
  if (refreshWarnsBtn) {
    refreshWarnsBtn.addEventListener('click', () => {
      if (state.activeGuildId) fetchWarns(state.activeGuildId);
      else showToast('Please select a server first', 'warning');
    });
  }

  const refreshGwBtn = document.getElementById('btn-refresh-giveaways');
  if (refreshGwBtn) {
    refreshGwBtn.addEventListener('click', fetchGiveaways);
  }

  const refreshTicketsBtn = document.getElementById('btn-refresh-tickets');
  if (refreshTicketsBtn) {
    refreshTicketsBtn.addEventListener('click', fetchTickets);
  }

  // Quick Presence form
  const presenceForm = document.getElementById('form-quick-presence');
  if (presenceForm) {
    presenceForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      await submitPresence(
        document.getElementById('presence-status-select').value,
        document.getElementById('presence-activity-select').value,
        document.getElementById('presence-text-input').value
      );
    });
  }

  // Presence Modal
  const openModalBtn = document.getElementById('btn-presence-modal');
  if (openModalBtn) {
    openModalBtn.addEventListener('click', () => openModal('modal-presence'));
  }

  const modalSavePresence = document.getElementById('btn-modal-save-presence');
  if (modalSavePresence) {
    modalSavePresence.addEventListener('click', async () => {
      await submitPresence(
        document.getElementById('modal-status-select').value,
        document.getElementById('modal-activity-type').value,
        document.getElementById('modal-activity-name').value
      );
      closeModal('modal-presence');
    });
  }

  // Server Config Save
  const configForm = document.getElementById('form-server-config');
  if (configForm) {
    configForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!state.activeGuildId) {
        showToast('Please select a server first', 'warning');
        return;
      }

      const payload = {
        bot_role_id: document.getElementById('cfg-bot-role').value || null,
        ticket_role_id: document.getElementById('cfg-ticket-role').value || null,
        welcome_ch: document.getElementById('cfg-welcome-ch').value || null,
        leave_ch: document.getElementById('cfg-leave-ch').value || null,
        mod_log_ch: document.getElementById('cfg-mod-log').value || null,
        server_log_ch: document.getElementById('cfg-server-log').value || null,
        activity_log_ch: document.getElementById('cfg-activity-log').value || null,
        cmd_log_ch: document.getElementById('cfg-cmd-log').value || null,
        welcome_msg: document.getElementById('cfg-welcome-msg').value,
        leave_msg: document.getElementById('cfg-leave-msg').value,
      };

      try {
        const res = await apiFetch(`/api/guild/${state.activeGuildId}/config`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
          showToast('Server configuration saved successfully!', 'success');
        } else {
          showToast(`Save failed: ${data.error}`, 'error');
        }
      } catch (err) {
        showToast(`Request failed: ${err.message}`, 'error');
      }
    });
  }

  // Auto-Setup Audit Logs (/setupbot)
  const setupBotBtn = document.getElementById('btn-run-setupbot');
  if (setupBotBtn) {
    setupBotBtn.addEventListener('click', async () => {
      if (!state.activeGuildId) return showToast('Please select a server first', 'warning');
      if (!confirm('Auto-create "📁 NEXUS LOGS" category and private audit channels in this server?')) return;

      setupBotBtn.disabled = true;
      setupBotBtn.textContent = 'Setting up...';
      try {
        const res = await apiFetch(`/api/guild/${state.activeGuildId}/setup`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showToast('Audit log channels created & configured!', 'success');
          await fetchGuilds();
          fetchGuildConfig(state.activeGuildId);
        } else {
          showToast(`Setup failed: ${data.error}`, 'error');
        }
      } catch (err) {
        showToast(`Setup error: ${err.message}`, 'error');
      } finally {
        setupBotBtn.disabled = false;
        setupBotBtn.textContent = 'Auto-Setup Audit Logs';
      }
    });
  }

  // Moderation: Warn
  const warnBtn = document.getElementById('btn-mod-warn');
  if (warnBtn) {
    warnBtn.addEventListener('click', async () => {
      if (!state.activeGuildId) return showToast('Please select a server first', 'warning');
      const userId = getTargetUserId();
      const reason = document.getElementById('mod-reason-input').value.trim();
      if (!userId) return showToast('Please select or enter a target user ID', 'warning');
      if (!reason) return showToast('Reason is strictly required', 'warning');

      try {
        const res = await apiFetch('/api/moderation/warn', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ guild_id: state.activeGuildId, user_id: userId, reason })
        });
        const d = await res.json();
        if (d.success) {
          showToast('Warning successfully recorded and logged', 'success');
          fetchWarns(state.activeGuildId);
        } else showToast(d.error, 'error');
      } catch (err) { showToast(err.message, 'error'); }
    });
  }

  // Moderation: Kick
  const kickBtn = document.getElementById('btn-mod-kick');
  if (kickBtn) {
    kickBtn.addEventListener('click', async () => {
      if (!state.activeGuildId) return showToast('Please select a server first', 'warning');
      const userId = getTargetUserId();
      const reason = document.getElementById('mod-reason-input').value.trim();
      if (!userId) return showToast('Select or enter target user', 'warning');
      if (!confirm(`Are you sure you want to kick member ${userId}?`)) return;

      try {
        const res = await apiFetch('/api/moderation/kick', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ guild_id: state.activeGuildId, user_id: userId, reason })
        });
        const d = await res.json();
        if (d.success) showToast('Member kicked successfully', 'success');
        else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }

  // Moderation: Ban
  const banBtn = document.getElementById('btn-mod-ban');
  if (banBtn) {
    banBtn.addEventListener('click', async () => {
      if (!state.activeGuildId) return showToast('Please select a server first', 'warning');
      const userId = getTargetUserId();
      const reason = document.getElementById('mod-reason-input').value.trim();
      if (!userId) return showToast('Select or enter target user', 'warning');
      if (!confirm(`Are you sure you want to permanently BAN user ${userId}?`)) return;

      try {
        const res = await apiFetch('/api/moderation/ban', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ guild_id: state.activeGuildId, user_id: userId, reason, delete_days: 1 })
        });
        const d = await res.json();
        if (d.success) showToast('User banned successfully', 'success');
        else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }

  // Moderation: Timeout / Mute
  const timeoutBtn = document.getElementById('btn-mod-timeout');
  if (timeoutBtn) {
    timeoutBtn.addEventListener('click', async () => {
      if (!state.activeGuildId) return showToast('Please select a server first', 'warning');
      const userId = getTargetUserId();
      const duration = parseInt(document.getElementById('mod-timeout-duration').value);
      const reason = document.getElementById('mod-reason-input').value.trim();
      if (!userId) return showToast('Select target member', 'warning');

      try {
        const res = await apiFetch('/api/moderation/mute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ guild_id: state.activeGuildId, user_id: userId, duration, reason })
        });
        const d = await res.json();
        if (d.success) showToast('Timeout applied successfully', 'success');
        else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }

  // Moderation: Remove Timeout
  const untimeoutBtn = document.getElementById('btn-mod-untimeout');
  if (untimeoutBtn) {
    untimeoutBtn.addEventListener('click', async () => {
      if (!state.activeGuildId) return showToast('Please select a server first', 'warning');
      const userId = getTargetUserId();
      if (!userId) return showToast('Select target member', 'warning');

      try {
        const res = await apiFetch('/api/moderation/unmute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ guild_id: state.activeGuildId, user_id: userId })
        });
        const d = await res.json();
        if (d.success) showToast('Timeout removed successfully', 'success');
        else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }

  // Moderation: Unban
  const unbanBtn = document.getElementById('btn-mod-unban');
  if (unbanBtn) {
    unbanBtn.addEventListener('click', async () => {
      if (!state.activeGuildId) return showToast('Please select a server first', 'warning');
      const userId = document.getElementById('mod-unban-userid').value.trim();
      if (!userId) return showToast('Enter user ID to unban', 'warning');

      try {
        const res = await apiFetch('/api/moderation/unban', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ guild_id: state.activeGuildId, user_id: userId })
        });
        const d = await res.json();
        if (d.success) showToast('User unbanned successfully', 'success');
        else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }

  // Moderation: Lock & Unlock
  const lockBtn = document.getElementById('btn-channel-lock');
  const unlockBtn = document.getElementById('btn-channel-unlock');
  if (lockBtn) {
    lockBtn.addEventListener('click', () => handleChannelLock(true));
  }
  if (unlockBtn) {
    unlockBtn.addEventListener('click', () => handleChannelLock(false));
  }

  // Moderation: Slowmode
  const slowmodeSlider = document.getElementById('mod-slowmode-slider');
  const slowmodeDisplay = document.getElementById('slowmode-display');
  if (slowmodeSlider) {
    slowmodeSlider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      slowmodeDisplay.textContent = val === 0 ? '0s (Off)' : val < 60 ? `${val}s` : `${Math.floor(val / 60)}m`;
    });
  }
  const applySlowmodeBtn = document.getElementById('btn-apply-slowmode');
  if (applySlowmodeBtn) {
    applySlowmodeBtn.addEventListener('click', async () => {
      const channelId = document.getElementById('mod-channel-select').value;
      const seconds = parseInt(document.getElementById('mod-slowmode-slider').value);
      if (!channelId) return showToast('Select a channel first', 'warning');

      try {
        const res = await apiFetch('/api/moderation/slowmode', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ channel_id: channelId, seconds })
        });
        const d = await res.json();
        if (d.success) showToast(`Slowmode set to ${seconds}s`, 'success');
        else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }

  // Moderation: Purge
  const purgeBtn = document.getElementById('btn-channel-purge');
  if (purgeBtn) {
    purgeBtn.addEventListener('click', async () => {
      const channelId = document.getElementById('mod-channel-select').value;
      const amount = parseInt(document.getElementById('mod-purge-count').value);
      if (!channelId) return showToast('Select a channel first', 'warning');
      if (!confirm(`Purge ${amount} recent messages from this channel?`)) return;

      try {
        const res = await apiFetch('/api/moderation/purge', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ channel_id: channelId, amount })
        });
        const d = await res.json();
        if (d.success) showToast(`Purged ${d.count} messages!`, 'success');
        else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }

  // Announcements: Dispatch
  const dispatchAnnounceBtn = document.getElementById('btn-dispatch-announcement');
  if (dispatchAnnounceBtn) {
    dispatchAnnounceBtn.addEventListener('click', async () => {
      const channelId = document.getElementById('ann-channel-select').value;
      if (!channelId) return showToast('Please select a target channel', 'warning');

      const payload = {
        channel_id: channelId,
        type: 'embed',
        ping: document.getElementById('ann-ping-select').value,
        title: document.getElementById('ann-title-input').value,
        content: document.getElementById('ann-content-input').value,
        color: document.getElementById('ann-color-val').value,
        banner_url: document.getElementById('ann-banner-url').value,
        thumbnail_url: document.getElementById('ann-thumb-url').value,
        button: document.getElementById('ann-button-input').value,
      };

      try {
        const res = await apiFetch('/api/announce', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const d = await res.json();
        if (d.success) showToast('Announcement published successfully to Discord!', 'success');
        else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }

  // Direct Message: Dispatch
  const dispatchDmBtn = document.getElementById('btn-dispatch-dm');
  if (dispatchDmBtn) {
    dispatchDmBtn.addEventListener('click', async () => {
      if (!state.activeGuildId) return showToast('Select an active server', 'warning');

      let targetId = null;
      if (state.dmMode === 'user') {
        targetId = document.getElementById('dm-manual-userid').value.trim() || document.getElementById('dm-member-select').value;
      } else {
        targetId = document.getElementById('dm-role-select').value;
      }

      if (!targetId) return showToast('Please select or specify a recipient', 'warning');

      const payload = {
        target_type: state.dmMode,
        guild_id: state.activeGuildId,
        target_id: targetId,
        title: document.getElementById('dm-title-input').value,
        content: document.getElementById('dm-content-input').value,
        button: document.getElementById('dm-button-input').value,
      };

      try {
        const res = await apiFetch('/api/dm', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const d = await res.json();
        if (d.success) showToast(`DM dispatched! (Delivered: ${d.sent}, Failed: ${d.failed})`, 'success');
        else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }

  // Giveaways: Create
  const createGwBtn = document.getElementById('btn-create-giveaway');
  if (createGwBtn) {
    createGwBtn.addEventListener('click', async () => {
      const channelId = document.getElementById('gw-channel-select').value;
      const prize = document.getElementById('gw-prize-input').value.trim();
      const winners = document.getElementById('gw-winners-count').value;
      const duration = document.getElementById('gw-duration-input').value.trim();
      const reqRole = document.getElementById('gw-role-select').value;

      if (!channelId) return showToast('Select a channel', 'warning');
      if (!prize) return showToast('Prize name cannot be empty', 'warning');

      try {
        const res = await apiFetch('/api/giveaways/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            guild_id: state.activeGuildId,
            channel_id: channelId,
            prize,
            winners,
            duration,
            required_roles: reqRole || null
          })
        });
        const d = await res.json();
        if (d.success) {
          showToast('Giveaway launched on Discord!', 'success');
          fetchGiveaways();
        } else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }

  // Polls: Create
  const deployPollBtn = document.getElementById('btn-deploy-poll');
  if (deployPollBtn) {
    deployPollBtn.addEventListener('click', async () => {
      const channelId = document.getElementById('poll-channel-select').value;
      const question = document.getElementById('poll-question-input').value.trim();
      const duration = parseInt(document.getElementById('poll-duration-input').value);
      const optInputs = document.querySelectorAll('.poll-opt-input');
      const options = Array.from(optInputs).map(i => i.value.trim()).filter(Boolean);

      if (!channelId) return showToast('Select a channel', 'warning');
      if (!question) return showToast('Question is required', 'warning');
      if (options.length < 2) return showToast('Provide at least 2 options', 'warning');

      try {
        const res = await apiFetch('/api/polls/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ channel_id: channelId, question, options, duration })
        });
        const d = await res.json();
        if (d.success) showToast('Interactive poll deployed!', 'success');
        else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }

  // Tickets: Deploy Panel
  const deployTicketBtn = document.getElementById('btn-deploy-ticket-panel');
  if (deployTicketBtn) {
    deployTicketBtn.addEventListener('click', async () => {
      if (!state.activeGuildId) return showToast('Select an active server first', 'warning');
      const channelId = document.getElementById('ticket-channel-select').value;
      if (!channelId) return showToast('Select channel', 'warning');

      try {
        const res = await apiFetch('/api/tickets/setup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            guild_id: state.activeGuildId,
            channel_id: channelId,
            title: document.getElementById('ticket-panel-title').value,
            description: document.getElementById('ticket-panel-desc').value,
            button_label: document.getElementById('ticket-panel-btn-label').value,
          })
        });
        const d = await res.json();
        if (d.success) showToast('Support ticket panel deployed!', 'success');
        else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }

  // Non-Prefix: Add
  const addNonPrefixBtn = document.getElementById('btn-add-nonprefix');
  if (addNonPrefixBtn) {
    addNonPrefixBtn.addEventListener('click', async () => {
      const userId = document.getElementById('nonprefix-userid').value.trim();
      if (!userId) return showToast('Enter user ID', 'warning');

      try {
        const res = await apiFetch('/api/non_prefix', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'add', user_id: userId })
        });
        const d = await res.json();
        if (d.success) {
          showToast('Non-prefix access granted!', 'success');
          document.getElementById('nonprefix-userid').value = '';
          fetchNonPrefix();
        } else showToast(d.error, 'error');
      } catch (e) { showToast(e.message, 'error'); }
    });
  }
}

function getTargetUserId() {
  const manual = document.getElementById('mod-custom-userid').value.trim();
  if (manual) return manual;
  return document.getElementById('mod-member-select').value;
}

async function handleChannelLock(lock) {
  const channelId = document.getElementById('mod-channel-select').value;
  if (!channelId) return showToast('Please select a channel first', 'warning');

  try {
    const res = await apiFetch('/api/moderation/lock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel_id: channelId, lock })
    });
    const d = await res.json();
    if (d.success) showToast(`Channel ${lock ? 'Locked' : 'Unlocked'} successfully`, 'success');
    else showToast(d.error, 'error');
  } catch (e) { showToast(e.message, 'error'); }
}

async function submitPresence(status, activityType, activityName) {
  try {
    const res = await apiFetch('/api/bot/presence', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status,
        activity_type: activityType,
        activity_name: activityName
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast('Bot presence updated!', 'success');
      fetchStatus();
    } else {
      showToast(data.error || 'Failed to update presence', 'error');
    }
  } catch (err) {
    showToast(`Presence error: ${err.message}`, 'error');
  }
}

// ── Data Tables & Sub-Views ──────────────────────────────────────────────────
async function fetchWarns(guildId) {
  const tbody = document.getElementById('warns-table-body');
  if (!tbody) return;

  try {
    const res = await apiFetch(`/api/moderation/${guildId}/warns`);
    const warns = await res.json();
    if (warns.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center">No active warnings on record for this server.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    warns.forEach(w => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>#${w.id}</td>
        <td><code>${w.user_id}</code></td>
        <td><code>${w.mod_id}</code></td>
        <td>${escapeHtml(w.reason || 'None')}</td>
        <td>${w.date}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="clearWarnsForUser('${w.user_id}')">Clear Warns</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('fetchWarns error:', err);
  }
}

async function clearWarnsForUser(userId) {
  if (!confirm(`Clear all warnings for user ${userId}?`)) return;
  try {
    const res = await apiFetch('/api/moderation/clearwarns', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ guild_id: state.activeGuildId, user_id: userId })
    });
    const d = await res.json();
    if (d.success) {
      showToast('Warnings cleared', 'success');
      fetchWarns(state.activeGuildId);
    }
  } catch (e) { showToast(e.message, 'error'); }
}

async function fetchGiveaways() {
  const container = document.getElementById('giveaways-list-container');
  if (!container) return;

  try {
    const res = await apiFetch('/api/giveaways');
    const list = await res.json();
    if (list.length === 0) {
      container.innerHTML = '<div class="empty-state">No giveaways currently in database.</div>';
      return;
    }

    container.innerHTML = '';
    list.forEach(gw => {
      const div = document.createElement('div');
      div.className = 'item-row-card';
      const statusBadge = gw.ended
        ? '<span class="badge badge-neutral">Ended</span>'
        : '<span class="badge badge-success">Active</span>';

      div.innerHTML = `
        <div>
          <div class="item-info-title">🎉 ${escapeHtml(gw.prize)}</div>
          <div class="item-info-meta">
            <span>Winners: ${gw.winners}</span>
            <span>Channel: #${gw.channel_id}</span>
            ${statusBadge}
          </div>
        </div>
        <div class="item-actions">
          ${!gw.ended ? `<button class="btn btn-danger btn-sm" onclick="forceEndGiveaway('${gw.id}')">Force End</button>` : ''}
        </div>
      `;
      container.appendChild(div);
    });
  } catch (e) { console.error('fetchGiveaways error:', e); }
}

async function forceEndGiveaway(id) {
  try {
    const res = await apiFetch('/api/giveaways/end', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    const d = await res.json();
    if (d.success) {
      showToast('Giveaway ended and winner chosen!', 'success');
      fetchGiveaways();
    }
  } catch (e) { showToast(e.message, 'error'); }
}

async function fetchTickets() {
  const container = document.getElementById('tickets-list-container');
  if (!container) return;

  try {
    const res = await apiFetch('/api/tickets');
    const tickets = await res.json();
    if (tickets.length === 0) {
      container.innerHTML = '<div class="empty-state">No tickets open currently.</div>';
      return;
    }

    container.innerHTML = '';
    tickets.forEach(t => {
      const div = document.createElement('div');
      div.className = 'item-row-card';
      div.innerHTML = `
        <div>
          <div class="item-info-title">Ticket #${t.id} · User: <code>${t.user_id}</code></div>
          <div class="item-info-meta">
            <span>Channel ID: ${t.channel_id}</span>
            <span class="badge ${t.status === 'open' ? 'badge-success' : 'badge-neutral'}">${t.status}</span>
          </div>
        </div>
        <div class="item-actions">
          ${t.status === 'open' ? `<button class="btn btn-danger btn-sm" onclick="closeTicket('${t.channel_id}')">Close & Delete</button>` : ''}
        </div>
      `;
      container.appendChild(div);
    });
  } catch (e) { console.error('fetchTickets error:', e); }
}

async function closeTicket(channelId) {
  if (!confirm('Close this ticket and delete channel?')) return;
  try {
    const res = await apiFetch('/api/tickets/close', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel_id: channelId })
    });
    const d = await res.json();
    if (d.success) {
      showToast('Ticket closed', 'success');
      fetchTickets();
    }
  } catch (e) { showToast(e.message, 'error'); }
}

async function fetchNonPrefix() {
  const tbody = document.getElementById('nonprefix-tbody');
  if (!tbody) return;

  try {
    const res = await apiFetch('/api/non_prefix');
    const users = await res.json();
    if (users.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" class="text-center">No non-prefix users configured.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    users.forEach(u => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><code>${u.user_id}</code></td>
        <td>${escapeHtml(u.name)}</td>
        <td>${u.added_at}</td>
        <td>
          <button class="btn btn-danger btn-sm" onclick="removeNonPrefix('${u.user_id}')">Revoke</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error('fetchNonPrefix error:', e); }
}

async function removeNonPrefix(userId) {
  try {
    const res = await apiFetch('/api/non_prefix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'remove', user_id: userId })
    });
    const d = await res.json();
    if (d.success) {
      showToast('Access revoked', 'info');
      fetchNonPrefix();
    }
  } catch (e) { showToast(e.message, 'error'); }
}

// ── DM Mode Toggle ───────────────────────────────────────────────────────────
function setDmMode(mode) {
  state.dmMode = mode;
  document.getElementById('dm-mode-user').classList.toggle('active', mode === 'user');
  document.getElementById('dm-mode-role').classList.toggle('active', mode === 'role');

  document.getElementById('dm-user-field').classList.toggle('hidden', mode !== 'user');
  document.getElementById('dm-role-field').classList.toggle('hidden', mode !== 'role');
}

// ── Poll Options Helper ──────────────────────────────────────────────────────
function addPollOption() {
  const container = document.getElementById('poll-options-container');
  const count = container.children.length + 1;
  if (count > 10) return showToast('Maximum 10 options allowed', 'warning');

  const row = document.createElement('div');
  row.className = 'poll-option-row';
  row.innerHTML = `
    <span class="option-num">${count}</span>
    <input type="text" class="form-input poll-opt-input" placeholder="Option ${count}">
  `;
  container.appendChild(row);
}

function applyPollTemplate(tmpl) {
  const container = document.getElementById('poll-options-container');
  if (tmpl === 'yesno') {
    container.innerHTML = `
      <div class="poll-option-row">
        <span class="option-num">1</span>
        <input type="text" class="form-input poll-opt-input" value="Yes / Agree 👍">
      </div>
      <div class="poll-option-row">
        <span class="option-num">2</span>
        <input type="text" class="form-input poll-opt-input" value="No / Disagree 👎">
      </div>
    `;
  }
}

// ── Live Terminal Console & WebSockets ───────────────────────────────────────
function initTerminal() {
  const filterPills = document.querySelectorAll('.filter-pill');
  filterPills.forEach(p => {
    p.addEventListener('click', () => {
      filterPills.forEach(f => f.classList.remove('active'));
      p.classList.add('active');
      state.terminalFilter = p.getAttribute('data-level');
      renderTerminal();
    });
  });

  const searchInput = document.getElementById('terminal-search');
  if (searchInput) {
    searchInput.addEventListener('input', renderTerminal);
  }

  const clearBtn = document.getElementById('btn-clear-terminal');
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      state.terminalLogs = [];
      renderTerminal();
    });
  }
}

function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const tokenParam = state.authToken ? `?token=${encodeURIComponent(state.authToken)}` : '';
  const wsUrl = `${protocol}//${window.location.host}/ws${tokenParam}`;

  try {
    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
      state.wsConnected = true;
      appendTerminalLog({
        timestamp: new Date().toLocaleTimeString(),
        level: 'INFO',
        logger: 'WebSocket',
        message: 'Connected to live Nexus log stream'
      });
    };

    

    state.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'history' && Array.isArray(msg.data)) {
          state.terminalLogs = msg.data;
          renderTerminal();
        } else if (msg.type === 'log') {
          state.terminalLogs.push(msg.data);
          if (state.terminalLogs.length > 500) state.terminalLogs.shift();
          renderTerminal();
        }
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };

    state.ws.onclose = () => {
      state.wsConnected = false;
      // Reconnect if authenticated
      if (state.authToken) {
        setTimeout(initWebSocket, 4000);
      }
    };
  } catch (err) {
    console.warn('WebSocket connection not supported or failed:', err);
  }
}

function appendTerminalLog(log) {
  state.terminalLogs.push(log);
  renderTerminal();
}

function renderTerminal() {
  const screen = document.getElementById('terminal-screen');
  if (!screen) return;

  const searchQuery = (document.getElementById('terminal-search')?.value || '').toLowerCase();
  const filterLevel = state.terminalFilter;

  const filtered = state.terminalLogs.filter(item => {
    if (filterLevel !== 'ALL' && item.level !== filterLevel) return false;
    if (searchQuery) {
      const text = `${item.logger} ${item.message}`.toLowerCase();
      if (!text.includes(searchQuery)) return false;
    }
    return true;
  });

  screen.innerHTML = '';
  filtered.forEach(log => {
    const line = document.createElement('div');
    const lvlClass = log.level === 'ERROR' ? 'log-lvl-error' : log.level === 'WARNING' ? 'log-lvl-warning' : 'log-lvl-info';
    line.className = 'log-line';
    line.innerHTML = `
      <span class="log-ts">[${log.timestamp || '00:00:00'}]</span>
      <span class="${lvlClass}">[${log.level}]</span>
      <span class="log-logger">${escapeHtml(log.logger)}:</span>
      <span class="log-msg">${escapeHtml(log.message)}</span>
    `;
    screen.appendChild(line);
  });

  const autoscroll = document.getElementById('terminal-autoscroll')?.checked;
  if (autoscroll) {
    screen.scrollTop = screen.scrollHeight;
  }
}

// ── Modal Utilities ──────────────────────────────────────────────────────────
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('hidden');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('hidden');
}

// ── General Utilities ────────────────────────────────────────────────────────
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ── Authentication & RBAC Access Control ─────────────────────────────────────
async function checkAuth() {
  state.authToken = localStorage.getItem('nexus_token');
  try {
    const res = await fetch('/api/auth/me', {
      headers: state.authToken ? { 'Authorization': `Bearer ${state.authToken}` } : {},
      credentials: 'same-origin'
    });

    if (res.ok) {
      const data = await res.json();
      if (data.authenticated && data.user) {
        state.currentUser = data.user;
        updateAuthUI(data.user);
        closeModal('modal-login');
        return true;
      }
    }
  } catch (err) {
    console.warn('checkAuth error:', err);
  }

  // Not authenticated
  state.currentUser = null;
  state.authToken = null;
  localStorage.removeItem('nexus_token');
  updateAuthUI(null);
  showLoginModal();
  return false;
}

function updateAuthUI(user) {
  const badge = document.getElementById('user-badge');
  const adminBtn = document.getElementById('tab-btn-admin');

  if (user) {
    if (badge) {
      badge.classList.remove('hidden');
      const letterEl = document.getElementById('user-avatar-letter');
      const nameEl = document.getElementById('user-display-name');
      const roleEl = document.getElementById('user-role-badge');
      if (letterEl) letterEl.textContent = (user.name || 'U').charAt(0).toUpperCase();
      if (nameEl) nameEl.textContent = user.name || user.user_id;
      if (roleEl) {
        roleEl.textContent = (user.role || 'operator').toUpperCase();
        roleEl.className = `user-role-badge role-${user.role}`;
      }
    }

    // STRICT OWNER/ADMIN VISIBILITY REQUIREMENT:
    // Only verified Administrators / Owner can see the Admin Panel and Non-Prefix tab buttons!
    if (adminBtn) {
      if (user.is_admin) {
        adminBtn.style.display = 'flex';
      } else {
        adminBtn.style.display = 'none';
        const adminPane = document.getElementById('tab-admin');
        if (adminPane && adminPane.classList.contains('active')) {
          switchTab('tab-overview');
        }
      }
    }
    const nonprefixBtn = document.getElementById('tab-btn-nonprefix');
    if (nonprefixBtn) {
      if (user.is_admin) {
        nonprefixBtn.style.display = 'flex';
      } else {
        nonprefixBtn.style.display = 'none';
        const nonprefixPane = document.getElementById('tab-nonprefix');
        if (nonprefixPane && nonprefixPane.classList.contains('active')) {
          switchTab('tab-overview');
        }
      }
    }
  } else {
    if (badge) badge.classList.add('hidden');
    if (adminBtn) adminBtn.style.display = 'none';
    const nonprefixBtn = document.getElementById('tab-btn-nonprefix');
    if (nonprefixBtn) nonprefixBtn.style.display = 'none';
    const adminPane = document.getElementById('tab-admin');
    if (adminPane && adminPane.classList.contains('active')) {
      switchTab('tab-overview');
    }
    const nonprefixPane = document.getElementById('tab-nonprefix');
    if (nonprefixPane && nonprefixPane.classList.contains('active')) {
      switchTab('tab-overview');
    }
  }
}

function showLoginModal(errMessage = '') {
  openModal('modal-login');
  const errDiv = document.getElementById('login-error');
  if (errDiv) {
    if (errMessage) {
      errDiv.textContent = errMessage;
      errDiv.classList.remove('hidden');
    } else {
      errDiv.textContent = '';
      errDiv.classList.add('hidden');
    }
  }
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const userId = document.getElementById('login-user-id').value.trim();
  const passcode = document.getElementById('login-passcode').value.trim();
  const btn = document.getElementById('btn-submit-login');
  const errDiv = document.getElementById('login-error');

  if (!userId || !passcode) {
    if (errDiv) {
      errDiv.textContent = 'Please enter both Discord User ID and Passcode.';
      errDiv.classList.remove('hidden');
    }
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Verifying identity...';
  if (errDiv) errDiv.classList.add('hidden');

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ user_id: userId, passcode: passcode })
    });
    const data = await res.json();
    if (data.success && data.token) {
      state.authToken = data.token;
      state.currentUser = data.user;
      localStorage.setItem('nexus_token', data.token);
      updateAuthUI(data.user);
      closeModal('modal-login');
      showToast(`Welcome back, ${data.user.name}!`, 'success');

      // Initialize live subsystems
      fetchGuilds();
      initWebSocket();
    } else {
      if (errDiv) {
        errDiv.textContent = data.error || 'Authentication failed. Please verify credentials.';
        errDiv.classList.remove('hidden');
      }
    }
  } catch (err) {
    if (errDiv) {
      errDiv.textContent = `Connection error: ${err.message}`;
      errDiv.classList.remove('hidden');
    }
  } finally {
    btn.disabled = false;
    btn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
      Authenticate & Enter
    `;
  }
}

async function handleLogout() {
  if (!confirm('Are you sure you want to sign out of the control center?')) return;
  try {
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: state.authToken ? { 'Authorization': `Bearer ${state.authToken}` } : {},
      credentials: 'same-origin'
    });
  } catch (e) {
    console.warn('Logout API error:', e);
  }
  state.authToken = null;
  state.currentUser = null;
  localStorage.removeItem('nexus_token');
  updateAuthUI(null);
  if (state.ws) {
    state.ws.close();
  }
  showToast('Signed out successfully.', 'info');
  showLoginModal();
}

// ── Admin Panel Subsystem (Strictly Owner & Admins) ───────────────────────────
async function loadAdminData() {
  if (!state.currentUser || !state.currentUser.is_admin) return;
  await Promise.all([
    loadAdminUsers(),
    loadAdminSessions(),
    loadAdminAuditLogs()
  ]);
}

async function loadAdminUsers() {
  const tbody = document.getElementById('admin-users-tbody');
  if (!tbody) return;

  try {
    const res = await apiFetch('/api/admin/users');
    const data = await res.json();
    const users = Array.isArray(data) ? data : (data.users || []);

    const countBadge = document.getElementById('admin-kpi-users');
    if (countBadge) countBadge.textContent = users.length;

    if (users.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center">No authorized personnel registered.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    users.forEach(u => {
      const tr = document.createElement('tr');
      const isOwner = u.role === 'owner';
      const roleBadgeClass = u.role === 'owner' ? 'badge-owner' : u.role === 'admin' ? 'badge-admin' : 'badge-operator';
      const statusBadge = u.is_active
        ? '<span class="badge badge-success">Active</span>'
        : '<span class="badge badge-danger">Disabled</span>';

      let actionsHtml = '';
      if (isOwner) {
        actionsHtml = '<span class="text-muted text-xs">Primary Owner</span>';
      } else {
        const toggleLabel = u.is_active ? 'Disable' : 'Enable';
        const toggleClass = u.is_active ? 'btn-secondary' : 'btn-success';
        actionsHtml = `
          <div class="flex-align-center gap-2">
            <button class="btn ${toggleClass} btn-xs" onclick="toggleAdminUser('${u.user_id}', ${u.is_active ? 0 : 1})">${toggleLabel}</button>
            <button class="btn btn-secondary btn-xs" onclick="openResetPasscodeModal('${u.user_id}', '${escapeHtml(u.name)}')">Reset Passcode</button>
            <button class="btn btn-danger btn-xs" onclick="deleteAdminUser('${u.user_id}', '${escapeHtml(u.name)}')">Delete</button>
          </div>
        `;
      }

      tr.innerHTML = `
        <td>
          <div class="flex-align-center gap-2">
            <span class="user-avatar-sm">${escapeHtml(u.name).charAt(0).toUpperCase()}</span>
            <strong>${escapeHtml(u.name)}</strong>
          </div>
        </td>
        <td><code>${u.user_id}</code></td>
        <td><span class="role-tag-badge ${roleBadgeClass}">${u.role.toUpperCase()}</span></td>
        <td>${escapeHtml(u.added_by || 'System')}</td>
        <td>${statusBadge}</td>
        <td>${actionsHtml}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('loadAdminUsers error:', err);
  }
}

async function handleAddAdminSubmit(e) {
  e.preventDefault();
  const userId = document.getElementById('admin-new-id').value.trim();
  const name = document.getElementById('admin-new-name').value.trim();
  const role = document.getElementById('admin-new-role').value;
  const passcode = document.getElementById('admin-new-passcode').value.trim();
  const saveBtn = document.getElementById('btn-save-new-admin');

  if (!userId || !name || !passcode) {
    return showToast('All fields are required', 'warning');
  }

  saveBtn.disabled = true;
  saveBtn.textContent = 'Authorizing...';

  try {
    const res = await apiFetch('/api/admin/users/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, name, role, passcode })
    });
    const d = await res.json();
    if (d.success) {
      showToast(`User ${name} authorized as ${role.toUpperCase()}!`, 'success');
      document.getElementById('form-add-admin').reset();
      closeModal('modal-add-admin');
      loadAdminUsers();
      loadAdminAuditLogs();
    } else {
      showToast(d.error || 'Failed to add user', 'error');
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Authorize User';
  }
}

async function toggleAdminUser(userId, enable) {
  const actionText = enable ? 'enable' : 'disable';
  if (!confirm(`Are you sure you want to ${actionText} access for user ${userId}?`)) return;

  try {
    const res = await apiFetch('/api/admin/users/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, is_active: Boolean(enable) })
    });
    const d = await res.json();
    if (d.success) {
      showToast(`User access ${actionText}d`, 'success');
      loadAdminUsers();
      loadAdminSessions();
      loadAdminAuditLogs();
    } else {
      showToast(d.error || 'Failed to update user', 'error');
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

async function deleteAdminUser(userId, name) {
  if (!confirm(`Permanently remove operator ${name} (${userId})? This will revoke all sessions and access immediately.`)) return;

  try {
    const res = await apiFetch('/api/admin/users/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId })
    });
    const d = await res.json();
    if (d.success) {
      showToast(`Operator ${name} removed`, 'info');
      loadAdminUsers();
      loadAdminSessions();
      loadAdminAuditLogs();
    } else {
      showToast(d.error || 'Failed to delete user', 'error');
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

function openResetPasscodeModal(userId, name) {
  document.getElementById('reset-target-user-id').value = userId;
  document.getElementById('reset-target-user-info').textContent = `Resetting passcode for ${name} (${userId}).`;
  document.getElementById('admin-reset-new-passcode').value = '';
  openModal('modal-reset-passcode');
}

async function handleResetPasscodeSubmit(e) {
  e.preventDefault();
  const userId = document.getElementById('reset-target-user-id').value;
  const newPasscode = document.getElementById('admin-reset-new-passcode').value.trim();
  const btn = document.getElementById('btn-save-reset-passcode');

  if (!newPasscode) return showToast('Please enter a new passcode', 'warning');

  btn.disabled = true;
  btn.textContent = 'Updating...';

  try {
    const res = await apiFetch('/api/admin/users/reset-passcode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, passcode: newPasscode })
    });
    const d = await res.json();
    if (d.success) {
      showToast('Passcode updated and active sessions revoked', 'success');
      closeModal('modal-reset-passcode');
      loadAdminSessions();
      loadAdminAuditLogs();
    } else {
      showToast(d.error || 'Failed to reset passcode', 'error');
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Update Passcode';
  }
}

async function loadAdminSessions() {
  const tbody = document.getElementById('admin-sessions-tbody');
  if (!tbody) return;

  try {
    const res = await apiFetch('/api/admin/sessions');
    const data = await res.json();
    const sessions = Array.isArray(data) ? data : (data.sessions || []);

    const countBadge = document.getElementById('admin-kpi-sessions');
    if (countBadge) countBadge.textContent = sessions.length;

    if (sessions.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center">No active sessions tracked.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    sessions.forEach(s => {
      const tr = document.createElement('tr');
      const roleBadgeClass = s.role === 'owner' ? 'badge-owner' : s.role === 'admin' ? 'badge-admin' : 'badge-operator';
      tr.innerHTML = `
        <td><strong>${escapeHtml(s.name)}</strong></td>
        <td><code>${s.user_id}</code></td>
        <td><span class="role-tag-badge ${roleBadgeClass}">${(s.role || '').toUpperCase()}</span></td>
        <td><code>${escapeHtml(s.ip_address || 'Unknown')}</code></td>
        <td class="text-xs text-muted" title="${escapeHtml(s.user_agent || '')}">${escapeHtml((s.user_agent || 'Unknown').substring(0, 32))}...</td>
        <td>${s.last_active || '-'}</td>
        <td>
          <button class="btn btn-danger btn-xs" onclick="terminateSession('${s.token_hash}')">Revoke Session</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('loadAdminSessions error:', err);
  }
}

async function terminateSession(tokenHash) {
  if (!confirm('Revoke and terminate this active session immediately? The user will be signed out.')) return;

  try {
    const res = await apiFetch('/api/admin/sessions/terminate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token_hash: tokenHash })
    });
    const d = await res.json();
    if (d.success) {
      showToast('Session terminated', 'info');
      loadAdminSessions();
      loadAdminAuditLogs();
    } else {
      showToast(d.error || 'Failed to terminate session', 'error');
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

async function loadAdminAuditLogs() {
  const tbody = document.getElementById('admin-audit-tbody');
  if (!tbody) return;

  const actionFilter = document.getElementById('audit-filter-action')?.value || '';
  const url = actionFilter
    ? `/api/admin/audit_logs?action=${encodeURIComponent(actionFilter)}&limit=100`
    : '/api/admin/audit_logs?limit=100';

  try {
    const res = await apiFetch(url);
    const data = await res.json();
    const logs = Array.isArray(data) ? data : (data.logs || []);

    const countBadge = document.getElementById('admin-kpi-audits');
    if (countBadge) countBadge.textContent = logs.length;

    if (logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center">No security audit logs recorded yet.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    logs.forEach(log => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="text-xs text-muted whitespace-nowrap">${log.timestamp}</td>
        <td>
          <div>
            <strong>${escapeHtml(log.user_name || 'System')}</strong>
            <span class="text-xs text-muted"><code>${log.user_id || '-'}</code></span>
          </div>
        </td>
        <td><span class="action-pill-code">${escapeHtml(log.action)}</span></td>
        <td><code>${escapeHtml(log.guild_id || log.target_id || '-')}</code></td>
        <td class="text-xs">${escapeHtml(log.details || '-')}</td>
        <td><code class="text-xs">${escapeHtml(log.ip_address || '-')}</code></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('loadAdminAuditLogs error:', err);
  }
}
