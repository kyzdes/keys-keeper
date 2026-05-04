// keys-keeper admin client
(() => {
  const TOKEN = window.KK_TOKEN;

  async function api(path, opts = {}) {
    opts.headers = { ...(opts.headers || {}), 'Sec-Keys-Token': TOKEN };
    const r = await fetch(path, opts);
    if (!r.ok) throw new Error(`${path}: ${r.status}`);
    return r.json();
  }

  const TYPE_META = {
    api_key: { short: 'AP', color: 'var(--type-api)' },
    ssh_key: { short: 'SSH', color: 'var(--type-ssh)' },
    server:  { short: 'SV', color: 'var(--type-server)' },
    domain:  { short: 'DM', color: 'var(--type-domain)' },
    note:    { short: 'NT', color: 'var(--type-note)' },
  };

  const state = {
    entries: [],
    activeTags: new Set(),
    search: '',
  };

  function relTime(iso) {
    const t = new Date(iso).getTime();
    const ago = Math.max(0, Date.now() - t);
    const m = Math.floor(ago / 60000);
    if (m < 1) return 'just now';
    if (m < 60) return `${m} min ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h} hr ago`;
    const d = Math.floor(h / 24);
    return `${d} d ago`;
  }

  function el(tag, attrs = {}, ...children) {
    const e = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'class') e.className = v;
      else if (k === 'onclick') e.onclick = v;
      else e.setAttribute(k, v);
    });
    children.flat().forEach(c => e.append(c instanceof Node ? c : document.createTextNode(c ?? '')));
    return e;
  }

  function render() {
    const mount = document.getElementById('entries-mount');
    mount.innerHTML = '';
    const filtered = state.entries.filter(e => {
      if (state.search && !(`${e.name} ${(e.tags || []).join(' ')} ${e.note || ''}`.toLowerCase().includes(state.search.toLowerCase()))) {
        return false;
      }
      if (state.activeTags.size > 0 && !(e.tags || []).some(t => state.activeTags.has(t))) {
        return false;
      }
      return true;
    });
    if (filtered.length === 0) {
      mount.append(el('div', { class: 'empty', style: 'padding:40px;text-align:center;color:var(--text-3)' }, 'No matches'));
      return;
    }
    filtered.forEach(e => mount.append(rowEl(e)));
  }

  function rowEl(e) {
    const meta = TYPE_META[e.type] || { short: '?', color: 'var(--text-3)' };
    const row = el('div', { class: 'entry-row unified' });
    row.append(
      el('span', {
        class: 'type-icon',
        style: `background:${meta.color};width:22px;height:22px;font-size:10px;display:inline-flex;align-items:center;justify-content:center;border-radius:5px;color:var(--bg);font-weight:700`,
      }, meta.short),
      el('span', { class: 'type-label-mono' }, e.type),
      (() => {
        const c = el('div', { class: 'name-block' });
        const r1 = el('div', { class: 'row', style: 'gap:10px;flex-wrap:wrap' });
        r1.append(el('span', { class: 'name' }, e.name));
        const taglist = el('div', { class: 'tag-mini-list' });
        (e.tags || []).slice(0, 4).forEach(t => taglist.append(el('span', { class: 'tag-mini' }, t)));
        r1.append(taglist);
        c.append(r1);
        return c;
      })(),
      el('span', { class: 'note-preview', style: 'margin:0;max-width:100%' }, e.note || (e.fields?.host ? `${e.fields.user || ''}@${e.fields.host}` : '')),
      el('span', { class: 'last-access' }, e.updated_at ? relTime(e.updated_at) : ''),
      (() => {
        const a = el('div', { class: 'actions' });
        const copyBtn = el('button', {
          class: 'icon-btn',
          title: 'Copy to clipboard',
          onclick: (ev) => { ev.stopPropagation(); copy(e.id, e.name); },
        }, '📋');
        const editBtn = el('a', { class: 'icon-btn', href: `/entry/${encodeURIComponent(e.id)}`, title: 'Open' }, '↗');
        a.append(copyBtn, editBtn);
        return a;
      })(),
    );
    row.onclick = () => { location.href = `/entry/${encodeURIComponent(e.id)}`; };
    return row;
  }

  async function copy(id, name) {
    try {
      await api('/api/copy', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) });
      toast(`Copied ${name} · auto-clear in 30s`);
    } catch (ex) {
      toast(`Copy failed: ${ex.message}`, 'error');
    }
  }

  function toast(msg, kind = 'success') {
    const t = el('div', { class: 'app-toast' }, msg);
    if (kind === 'error') t.style.borderColor = 'var(--danger)';
    document.body.append(t);
    setTimeout(() => t.remove(), 3500);
  }

  function renderTagRail() {
    const rail = document.getElementById('tag-rail');
    if (!rail) return;
    const allTags = new Set();
    state.entries.forEach(e => (e.tags || []).forEach(t => allTags.add(t)));
    rail.querySelectorAll('.tag-chip').forEach(n => n.remove());
    [...allTags].sort().forEach(t => {
      const chip = el('span', {
        class: 'tag-chip' + (state.activeTags.has(t) ? ' active' : ''),
        onclick: () => {
          if (state.activeTags.has(t)) state.activeTags.delete(t);
          else state.activeTags.add(t);
          renderTagRail();
          render();
        },
      }, t);
      rail.append(chip);
    });
  }

  async function load() {
    const data = await api('/api/entries');
    state.entries = data.entries;
    renderTagRail();
    render();
  }

  document.getElementById('search').addEventListener('input', (e) => {
    state.search = e.target.value;
    render();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
      e.preventDefault();
      document.getElementById('search')?.focus();
    }
    if (e.key === 'Escape') {
      const s = document.getElementById('search');
      if (s) s.value = '';
      state.search = '';
      state.activeTags.clear();
      renderTagRail();
      render();
    }
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      paletteOpen();
    }
  });

  // -- command palette --
  const palette = {
    open: false,
    query: '',
    selectedIdx: 0,
    items: [],
  };

  async function paletteOpen() {
    palette.open = true;
    palette.query = '';
    palette.selectedIdx = 0;
    document.getElementById('cmdk-overlay').hidden = false;
    document.getElementById('cmdk-input').value = '';
    document.getElementById('cmdk-input').focus();
    if (state.entries.length === 0) {
      try {
        const r = await api('/api/entries');
        state.entries = r.entries;
      } catch {}
    }
    paletteRender();
  }
  function paletteClose() {
    palette.open = false;
    document.getElementById('cmdk-overlay').hidden = true;
  }
  function paletteRender() {
    const q = palette.query.toLowerCase();
    palette.items = state.entries
      .filter(e => !q || e.name.toLowerCase().includes(q) || (e.tags || []).some(t => t.toLowerCase().includes(q)))
      .slice(0, 20);
    if (palette.selectedIdx >= palette.items.length) palette.selectedIdx = Math.max(0, palette.items.length - 1);
    const r = document.getElementById('cmdk-results');
    r.innerHTML = '';
    palette.items.forEach((e, i) => {
      const meta = TYPE_META[e.type] || {};
      const row = el('div', {
        class: 'cmdk-row' + (i === palette.selectedIdx ? ' selected' : ''),
        onclick: () => { paletteClose(); location.href = `/entry/${encodeURIComponent(e.id)}`; },
      });
      row.append(
        el('span', { class: 'type-icon', style: `background:${meta.color};color:var(--bg);font-weight:700;display:inline-flex;align-items:center;justify-content:center;border-radius:4px` }, meta.short || '?'),
        el('span', { class: 'name', style: 'flex:1' }, e.name),
        el('span', { style: 'color:var(--text-3);font-size:11px' }, e.type),
      );
      r.append(row);
    });
  }

  document.getElementById('cmdk-input').addEventListener('input', (e) => {
    palette.query = e.target.value;
    palette.selectedIdx = 0;
    paletteRender();
  });
  document.getElementById('cmdk-input').addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); palette.selectedIdx = Math.min(palette.items.length - 1, palette.selectedIdx + 1); paletteRender(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); palette.selectedIdx = Math.max(0, palette.selectedIdx - 1); paletteRender(); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      const sel = palette.items[palette.selectedIdx];
      if (sel) { paletteClose(); location.href = `/entry/${encodeURIComponent(sel.id)}`; }
    }
    else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); paletteClose(); }
  });

  document.getElementById('cmdk-trigger')?.addEventListener('click', paletteOpen);

  setInterval(() => {
    fetch('/api/heartbeat', { method: 'POST', headers: { 'Sec-Keys-Token': TOKEN } });
  }, 60000);

  window.addEventListener('beforeunload', () => {
    navigator.sendBeacon('/api/shutdown');
  });

  load().catch(err => {
    document.getElementById('entries-mount').textContent = `Failed to load: ${err.message}`;
  });
})();
