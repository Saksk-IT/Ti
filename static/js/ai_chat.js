(function () {
  'use strict';

  const state = {
    sessions: [],
    messages: [],
    models: [],
    defaultModel: '',
    currentSessionId: 0,
    streaming: false,
    filter: ''
  };

  const els = {};

  function $(id) {
    return document.getElementById(id);
  }

  function initEls() {
    els.shell = document.querySelector('.ai-chat-shell');
    els.sidebar = $('aiChatSidebar');
    els.overlay = $('aiChatOverlay');
    els.mobileMenu = $('aiChatMobileMenu');
    els.newSession = $('aiNewSessionBtn');
    els.search = $('aiSessionSearch');
    els.list = $('aiSessionList');
    els.title = $('aiCurrentTitle');
    els.meta = $('aiCurrentMeta');
    els.model = $('aiModelSelect');
    els.rename = $('aiRenameBtn');
    els.delete = $('aiDeleteBtn');
    els.pane = $('aiMessagePane');
    els.empty = $('aiEmptyState');
    els.status = $('aiStatus');
    els.form = $('aiComposerForm');
    els.input = $('aiComposer');
    els.send = $('aiSendBtn');
  }

  async function apiJson(url, options) {
    const opts = Object.assign({ credentials: 'include' }, options || {});
    opts.headers = new Headers(opts.headers || {});
    if (!opts.headers.has('Content-Type') && opts.body) {
      opts.headers.set('Content-Type', 'application/json');
    }
    if (!opts.headers.has('X-Requested-With')) {
      opts.headers.set('X-Requested-With', 'XMLHttpRequest');
    }
    const res = await fetch(url, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.status === 'error') {
      throw new Error(data.message || '请求失败');
    }
    return data;
  }

  function setStatus(text, type) {
    if (!els.status) return;
    els.status.textContent = text || '';
    els.status.className = 'ai-status' + (type ? ' ' + type : '');
  }

  function escapeHtml(text) {
    return String(text == null ? '' : text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function sanitizeMarkdownUrl(url) {
    const raw = String(url || '').trim();
    if (!/^https?:\/\//i.test(raw)) return '';
    try {
      const parsed = new URL(raw);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return '';
      return parsed.href;
    } catch (err) {
      return '';
    }
  }

  function renderStrongMarkdown(text) {
    const value = String(text || '');
    const strongRe = /\*\*([\s\S]+?)\*\*/g;
    let html = '';
    let lastIndex = 0;
    let match;
    while ((match = strongRe.exec(value)) !== null) {
      html += escapeHtml(value.slice(lastIndex, match.index));
      html += `<strong>${escapeHtml(match[1])}</strong>`;
      lastIndex = match.index + match[0].length;
    }
    html += escapeHtml(value.slice(lastIndex));
    return html;
  }

  function renderInlineText(text) {
    const value = String(text || '');
    const linkRe = /\[([^\]\n]+)\]\(([^()\s]+)\)/g;
    let html = '';
    let lastIndex = 0;
    let match;
    while ((match = linkRe.exec(value)) !== null) {
      html += renderStrongMarkdown(value.slice(lastIndex, match.index));
      const href = sanitizeMarkdownUrl(match[2]);
      if (href) {
        html += `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${renderStrongMarkdown(match[1])}</a>`;
      } else {
        html += renderStrongMarkdown(match[0]);
      }
      lastIndex = match.index + match[0].length;
    }
    html += renderStrongMarkdown(value.slice(lastIndex));
    return html;
  }

  function renderInlineMarkdown(text) {
    const value = String(text || '');
    const codeRe = /`([^`\n]+)`/g;
    let html = '';
    let lastIndex = 0;
    let match;
    while ((match = codeRe.exec(value)) !== null) {
      html += renderInlineText(value.slice(lastIndex, match.index));
      html += `<code>${escapeHtml(match[1])}</code>`;
      lastIndex = match.index + match[0].length;
    }
    html += renderInlineText(value.slice(lastIndex));
    return html;
  }

  function renderParagraph(lines) {
    return `<p>${renderInlineMarkdown(lines.join('\n')).replace(/\n/g, '<br>')}</p>`;
  }

  function isTableDivider(line) {
    return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line || '');
  }

  function splitTableRow(line) {
    return String(line || '')
      .replace(/^\s*\|/, '')
      .replace(/\|\s*$/, '')
      .split('|')
      .map(cell => cell.trim());
  }

  function renderTable(lines) {
    const headers = splitTableRow(lines[0] || '');
    const rows = lines.slice(2).map(splitTableRow);
    const headHtml = headers.map(cell => `<th>${renderInlineMarkdown(cell)}</th>`).join('');
    const bodyHtml = rows.map(row => (
      `<tr>${headers.map((_, idx) => `<td>${renderInlineMarkdown(row[idx] || '')}</td>`).join('')}</tr>`
    )).join('');
    return `<div class="ai-md-table-wrap"><table><thead><tr>${headHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`;
  }

  function isMarkdownBlockStart(line, nextLine) {
    const text = String(line || '');
    return /^```\s*([A-Za-z0-9_-]+)?\s*$/.test(text) ||
      /^#{1,3}\s+/.test(text) ||
      /^>\s?/.test(text) ||
      /^\s*[-*]\s+/.test(text) ||
      /^\s*\d+[.)]\s+/.test(text) ||
      (text.includes('|') && isTableDivider(nextLine || ''));
  }

  function renderMarkdown(markdown) {
    const lines = String(markdown || '').replace(/\r\n?/g, '\n').split('\n');
    const html = [];
    let index = 0;

    while (index < lines.length) {
      const line = lines[index];
      if (!line.trim()) {
        index += 1;
        continue;
      }

      const fence = line.match(/^```\s*([A-Za-z0-9_-]+)?\s*$/);
      if (fence) {
        const codeLines = [];
        index += 1;
        while (index < lines.length && !/^```\s*$/.test(lines[index])) {
          codeLines.push(lines[index]);
          index += 1;
        }
        if (index < lines.length) index += 1;
        const lang = fence[1] ? ` class="language-${escapeHtml(fence[1])}"` : '';
        html.push(`<pre><code${lang}>${escapeHtml(codeLines.join('\n'))}</code></pre>`);
        continue;
      }

      const heading = line.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        const level = heading[1].length;
        html.push(`<h${level}>${renderInlineMarkdown(heading[2].trim())}</h${level}>`);
        index += 1;
        continue;
      }

      if (line.includes('|') && isTableDivider(lines[index + 1] || '')) {
        const tableLines = [line, lines[index + 1]];
        index += 2;
        while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
          tableLines.push(lines[index]);
          index += 1;
        }
        html.push(renderTable(tableLines));
        continue;
      }

      if (/^>\s?/.test(line)) {
        const quoteLines = [];
        while (index < lines.length && /^>\s?/.test(lines[index])) {
          quoteLines.push(lines[index].replace(/^>\s?/, ''));
          index += 1;
        }
        html.push(`<blockquote>${renderInlineMarkdown(quoteLines.join('\n')).replace(/\n/g, '<br>')}</blockquote>`);
        continue;
      }

      if (/^\s*[-*]\s+/.test(line)) {
        const items = [];
        while (index < lines.length && /^\s*[-*]\s+/.test(lines[index])) {
          items.push(lines[index].replace(/^\s*[-*]\s+/, ''));
          index += 1;
        }
        html.push(`<ul>${items.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul>`);
        continue;
      }

      if (/^\s*\d+[.)]\s+/.test(line)) {
        const items = [];
        while (index < lines.length && /^\s*\d+[.)]\s+/.test(lines[index])) {
          items.push(lines[index].replace(/^\s*\d+[.)]\s+/, ''));
          index += 1;
        }
        html.push(`<ol>${items.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ol>`);
        continue;
      }

      const paragraph = [];
      while (
        index < lines.length &&
        lines[index].trim() &&
        !isMarkdownBlockStart(lines[index], lines[index + 1])
      ) {
        paragraph.push(lines[index]);
        index += 1;
      }
      if (!paragraph.length) {
        paragraph.push(lines[index]);
        index += 1;
      }
      html.push(renderParagraph(paragraph));
    }

    return html.join('');
  }

  function formatTime(value) {
    if (!value) return '';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '';
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    if (sameDay) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
  }

  function currentSession() {
    return state.sessions.find(item => Number(item.id) === Number(state.currentSessionId)) || null;
  }

  function selectedModel() {
    return els.model && els.model.value ? els.model.value : state.defaultModel;
  }

  function renderModels() {
    if (!els.model) return;
    const html = state.models.map(item => {
      const label = item.label || item.id;
      const selected = item.id === state.defaultModel ? ' selected' : '';
      return `<option value="${escapeHtml(item.id)}"${selected}>${escapeHtml(label)}</option>`;
    }).join('');
    els.model.innerHTML = html || '<option value="">暂无可用模型</option>';
  }

  function renderSessions() {
    if (!els.list) return;
    const keyword = state.filter.trim().toLowerCase();
    const rows = state.sessions.filter(item => {
      if (!keyword) return true;
      return String(item.title || '').toLowerCase().includes(keyword) ||
        String(item.model || '').toLowerCase().includes(keyword);
    });

    if (!rows.length) {
      els.list.innerHTML = '<div class="ai-session-empty">暂无会话</div>';
      return;
    }

    els.list.innerHTML = rows.map(item => {
      const active = Number(item.id) === Number(state.currentSessionId) ? ' active' : '';
      return `
        <button class="ai-session-item${active}" type="button" data-session-id="${item.id}">
          <span class="ai-session-title">${escapeHtml(item.title || '新的 AI 会话')}</span>
          <span class="ai-session-meta">
            <span>${escapeHtml(item.model || '')}</span>
            <span>${escapeHtml(formatTime(item.updated_at))}</span>
          </span>
        </button>
      `;
    }).join('');
  }

  function renderHeader() {
    const session = currentSession();
    if (session) {
      els.title.textContent = session.title || '新的 AI 会话';
      els.meta.textContent = `${session.provider || 'AI'} · ${session.model || selectedModel() || '未选择模型'}`;
      if (els.model && session.model) els.model.value = session.model;
      els.rename.disabled = false;
      els.delete.disabled = false;
    } else {
      els.title.textContent = '新的 AI 会话';
      els.meta.textContent = '选择模型后开始提问';
      els.rename.disabled = true;
      els.delete.disabled = true;
    }
  }

  function messageRoleText(role) {
    if (role === 'user') return '我';
    if (role === 'assistant') return 'AI';
    return role || '消息';
  }

  function renderMessage(message) {
    const role = message.role === 'user' ? 'user' : 'assistant';
    const failed = message.status === 'failed' ? ' failed' : '';
    const content = message.content || '';
    const contentHtml = role === 'assistant' ? renderMarkdown(content) : escapeHtml(content);
    const contentClass = role === 'assistant' ? ' ai-message-markdown' : ' ai-message-plain';
    const status = message.status === 'streaming'
      ? '<div class="ai-message-status">正在回复...</div>'
      : message.status === 'failed'
        ? '<div class="ai-message-status">回复失败，可重新发送。</div>'
        : '';
    const avatar = role === 'user' ? '我' : 'AI';
    return `
      <article class="ai-message-row ${role}" data-message-id="${message.id || ''}">
        ${role === 'assistant' ? `<div class="ai-avatar">${avatar}</div>` : ''}
        <div class="ai-message${failed}">
          <div class="ai-message-role">${messageRoleText(message.role)}</div>
          <div class="ai-message-content${contentClass}">${contentHtml}</div>
          ${status}
        </div>
        ${role === 'user' ? `<div class="ai-avatar">${avatar}</div>` : ''}
      </article>
    `;
  }

  function renderMessages() {
    if (!els.pane) return;
    const messageHtml = state.messages.map(renderMessage).join('');
    els.empty.style.display = state.messages.length ? 'none' : 'grid';
    const emptyHtml = els.empty.outerHTML;
    els.pane.innerHTML = emptyHtml + messageHtml;
    els.empty = $('aiEmptyState');
    bindPromptButtons();
    scrollToBottom();
  }

  function scrollToBottom() {
    if (!els.pane) return;
    requestAnimationFrame(() => {
      els.pane.scrollTop = els.pane.scrollHeight;
    });
  }

  async function loadModels() {
    const data = await apiJson('/api/ai-chat/models');
    const payload = data.data || {};
    state.models = Array.isArray(payload.models) ? payload.models : [];
    state.defaultModel = payload.default_model || (state.models[0] && state.models[0].id) || '';
    renderModels();
  }

  async function loadSessions(selectFirst) {
    const data = await apiJson('/api/ai-chat/sessions');
    const payload = data.data || {};
    state.sessions = Array.isArray(payload.sessions) ? payload.sessions : [];
    if (selectFirst && !state.currentSessionId && state.sessions.length) {
      state.currentSessionId = state.sessions[0].id;
      await loadMessages(state.currentSessionId);
    }
    renderSessions();
    renderHeader();
  }

  async function loadMessages(sessionId) {
    if (!sessionId) {
      state.messages = [];
      renderMessages();
      return;
    }
    const data = await apiJson(`/api/ai-chat/sessions/${sessionId}/messages`);
    const payload = data.data || {};
    state.messages = Array.isArray(payload.messages) ? payload.messages : [];
    renderMessages();
  }

  async function createSession(title) {
    const data = await apiJson('/api/ai-chat/sessions', {
      method: 'POST',
      body: JSON.stringify({
        title: title || '新的 AI 会话',
        model: selectedModel()
      })
    });
    const session = data.data && data.data.session;
    if (session) {
      state.sessions = [session].concat(state.sessions.filter(item => Number(item.id) !== Number(session.id)));
      state.currentSessionId = session.id;
      state.messages = [];
      renderSessions();
      renderHeader();
      renderMessages();
      closeDrawer();
    }
    return session;
  }

  function upsertSession(session) {
    if (!session) return;
    state.sessions = [session].concat(state.sessions.filter(item => Number(item.id) !== Number(session.id)));
    renderSessions();
    renderHeader();
  }

  async function ensureSession(prompt) {
    const session = currentSession();
    if (session) return session;
    return createSession(prompt ? prompt.slice(0, 60) : '新的 AI 会话');
  }

  async function selectSession(sessionId) {
    if (state.streaming) return;
    state.currentSessionId = Number(sessionId || 0);
    renderSessions();
    renderHeader();
    await loadMessages(state.currentSessionId);
    closeDrawer();
  }

  function appendMessage(message) {
    if (!message) return;
    const id = Number(message.id || 0);
    if (id) {
      const idx = state.messages.findIndex(item => Number(item.id) === id);
      if (idx >= 0) {
        state.messages = state.messages.map(item => Number(item.id) === id ? Object.assign({}, item, message) : item);
      } else {
        state.messages = state.messages.concat([message]);
      }
    } else {
      state.messages = state.messages.concat([message]);
    }
    renderMessages();
  }

  function appendDelta(messageId, text) {
    const id = Number(messageId || 0);
    state.messages = state.messages.map(item => {
      if (Number(item.id) !== id) return item;
      return Object.assign({}, item, {
        content: String(item.content || '') + String(text || ''),
        status: 'streaming'
      });
    });
    renderMessages();
  }

  function updateMessage(message) {
    if (!message) return;
    const id = Number(message.id || 0);
    state.messages = state.messages.map(item => Number(item.id) === id ? Object.assign({}, item, message) : item);
    renderMessages();
  }

  function parseSseBuffer(buffer, onEvent) {
    const parts = buffer.split('\n\n');
    const rest = parts.pop() || '';
    parts.forEach(block => {
      let eventName = 'message';
      const dataLines = [];
      block.split('\n').forEach(line => {
        if (line.startsWith('event:')) eventName = line.slice(6).trim();
        if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
      });
      if (!dataLines.length) return;
      try {
        onEvent(eventName, JSON.parse(dataLines.join('\n')));
      } catch (err) {
        console.warn('AI stream parse failed', err);
      }
    });
    return rest;
  }

  async function sendPrompt(prompt) {
    const text = String(prompt || '').trim();
    if (!text || state.streaming) return;

    const session = await ensureSession(text);
    if (!session) return;

    state.streaming = true;
    els.send.disabled = true;
    els.input.disabled = true;
    setStatus('AI 正在思考...');

    try {
      const res = await fetch(`/api/ai-chat/sessions/${session.id}/messages/stream`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ content: text, model: selectedModel() })
      });

      if (!res.ok || !res.body) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.message || 'AI 回复失败');
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let done = false;
      while (!done) {
        const chunk = await reader.read();
        done = chunk.done;
        buffer += decoder.decode(chunk.value || new Uint8Array(), { stream: !done });
        buffer = parseSseBuffer(buffer, (eventName, data) => {
          if (eventName === 'meta') {
            upsertSession(data.session);
            appendMessage(data.user_message);
            appendMessage(data.assistant_message);
          } else if (eventName === 'delta') {
            appendDelta(data.message_id, data.text);
          } else if (eventName === 'done') {
            updateMessage(data.message);
            upsertSession(data.session);
            setStatus('');
          } else if (eventName === 'error') {
            setStatus(data.message || 'AI 回复失败，请稍后重试。', 'error');
            state.messages = state.messages.map(item => {
              if (Number(item.id) !== Number(data.message_id)) return item;
              return Object.assign({}, item, { status: 'failed' });
            });
            renderMessages();
          }
        });
      }
    } catch (err) {
      setStatus(err.message || 'AI 回复失败，请稍后重试。', 'error');
    } finally {
      state.streaming = false;
      els.send.disabled = false;
      els.input.disabled = false;
      els.input.value = '';
      resizeInput();
      els.input.focus();
      await loadSessions(false).catch(() => {});
    }
  }

  function resizeInput() {
    if (!els.input) return;
    els.input.style.height = 'auto';
    els.input.style.height = Math.min(180, Math.max(38, els.input.scrollHeight)) + 'px';
  }

  async function renameCurrentSession() {
    const session = currentSession();
    if (!session) return;
    const title = await appPrompt('输入新的会话标题', session.title || '新的 AI 会话');
    if (title === null) return;
    const clean = title.trim();
    if (!clean) {
      setStatus('会话标题不能为空', 'error');
      return;
    }
    try {
      const data = await apiJson(`/api/ai-chat/sessions/${session.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ title: clean })
      });
      upsertSession(data.data && data.data.session);
      setStatus('会话已重命名');
    } catch (err) {
      setStatus(err.message || '重命名失败', 'error');
    }
  }

  async function deleteCurrentSession() {
    const session = currentSession();
    if (!session || state.streaming) return;
    if (!(await appConfirm('删除这个 AI 会话？'))) return;
    try {
      await apiJson(`/api/ai-chat/sessions/${session.id}`, { method: 'DELETE' });
      state.sessions = state.sessions.filter(item => Number(item.id) !== Number(session.id));
      state.currentSessionId = state.sessions[0] ? state.sessions[0].id : 0;
      await loadMessages(state.currentSessionId);
      renderSessions();
      renderHeader();
      setStatus('会话已删除');
    } catch (err) {
      setStatus(err.message || '删除失败', 'error');
    }
  }

  async function changeSessionModel() {
    const session = currentSession();
    if (!session || state.streaming) return;
    try {
      const data = await apiJson(`/api/ai-chat/sessions/${session.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ model: selectedModel() })
      });
      upsertSession(data.data && data.data.session);
      setStatus('模型已切换');
    } catch (err) {
      setStatus(err.message || '模型切换失败', 'error');
    }
  }

  function openDrawer() {
    if (els.shell) els.shell.classList.add('drawer-open');
  }

  function closeDrawer() {
    if (els.shell) els.shell.classList.remove('drawer-open');
  }

  function bindPromptButtons() {
    document.querySelectorAll('.ai-prompt-grid button[data-prompt]').forEach(btn => {
      btn.addEventListener('click', () => {
        els.input.value = btn.getAttribute('data-prompt') || '';
        resizeInput();
        els.input.focus();
      });
    });
  }

  function bindEvents() {
    els.newSession.addEventListener('click', () => {
      createSession('新的 AI 会话').catch(err => setStatus(err.message || '新建失败', 'error'));
    });
    els.list.addEventListener('click', event => {
      const item = event.target.closest('.ai-session-item');
      if (!item) return;
      selectSession(item.getAttribute('data-session-id')).catch(err => setStatus(err.message || '加载会话失败', 'error'));
    });
    els.search.addEventListener('input', () => {
      state.filter = els.search.value || '';
      renderSessions();
    });
    els.model.addEventListener('change', changeSessionModel);
    els.rename.addEventListener('click', renameCurrentSession);
    els.delete.addEventListener('click', deleteCurrentSession);
    els.form.addEventListener('submit', event => {
      event.preventDefault();
      sendPrompt(els.input.value).catch(err => setStatus(err.message || '发送失败', 'error'));
    });
    els.input.addEventListener('input', resizeInput);
    els.input.addEventListener('keydown', event => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        els.form.requestSubmit();
      }
    });
    if (els.mobileMenu) els.mobileMenu.addEventListener('click', openDrawer);
    if (els.overlay) els.overlay.addEventListener('click', closeDrawer);
  }

  async function boot() {
    initEls();
    bindEvents();
    renderMessages();
    try {
      await loadModels();
      await loadSessions(true);
    } catch (err) {
      setStatus(err.message || 'AI 聊天加载失败', 'error');
    }
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
