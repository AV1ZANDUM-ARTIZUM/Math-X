(() => {
  const $ = s => document.querySelector(s);
  const url = $('#url'), homePage = $('#homePage'), viewerPage = $('#viewerPage');
  const frame = $('#viewer'), readerView = $('#readerView'), tabsEl = $('#tabs');
  const drawer = $('#drawer'), drawerContent = $('#drawerContent'), toastEl = $('#toast');
  const status = $('#status'), hint = $('#hint'), loading = $('#loading'), errorBox = $('#error');
  const homeSearch = $('#homeSearch');

  const read = (key, fallback) => { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } };
  let tabs = read('mx-tabs', [{ id: Date.now(), url: '', title: 'New Tab' }]);
  let active = Math.max(0, Math.min(read('mx-active', 0), tabs.length - 1));
  let history = read('mx-history', []);
  let bookmarks = read('mx-bookmarks', read('mx-favorites', []));
  let bookmarkFolder = read('mx-bookmark-folder', 'General');
  let searchEngine = read('mx-search-engine', 'https://www.google.com/search?q=');
  let zoom = Number(localStorage.getItem('mx-zoom') || 100);
  let dark = localStorage.getItem('mx-theme') !== 'light';
  let dragIndex = null;

  const engines = {
    'Google': 'https://www.google.com/search?q=',
    'Bing': 'https://www.bing.com/search?q=',
    'DuckDuckGo': 'https://duckduckgo.com/?q=',
    'Brave Search': 'https://search.brave.com/search?q='
  };

  function save() {
    localStorage.setItem('mx-tabs', JSON.stringify(tabs));
    localStorage.setItem('mx-active', String(active));
    localStorage.setItem('mx-history', JSON.stringify(history));
    localStorage.setItem('mx-bookmarks', JSON.stringify(bookmarks));
    localStorage.setItem('mx-bookmark-folder', bookmarkFolder);
    localStorage.setItem('mx-search-engine', searchEngine);
    localStorage.setItem('mx-zoom', String(zoom));
    localStorage.setItem('mx-theme', dark ? 'dark' : 'light');
  }

  function toast(message) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => toastEl.classList.remove('show'), 1800);
  }

  function normalize(value) {
    let v = String(value || '').trim();
    if (!v) return '';
    if (/^[a-z][a-z0-9+.-]*:\/\//i.test(v)) return /^https?:\/\//i.test(v) ? v : '';
    if (/^[^\s]+\.[^\s]+/.test(v)) return 'https://' + v;
    return searchEngine + encodeURIComponent(v);
  }

  function hostTitle(v) {
    try { return new URL(v).hostname.replace(/^www\./, '') || 'New Tab'; } catch { return 'New Tab'; }
  }

  function renderTabs() {
    tabsEl.innerHTML = '';
    tabs.forEach((tab, i) => {
      const b = document.createElement('button');
      b.className = 'tab' + (i === active ? ' active' : '');
      b.draggable = true;
      b.title = tab.url || 'New Tab';
      const label = document.createElement('span');
      label.textContent = '🌐 ' + (tab.title || 'New Tab');
      const x = document.createElement('span');
      x.className = 'x'; x.textContent = '×';
      b.append(label, x);
      b.onclick = e => { if (e.target === x) closeTab(i); else { active = i; save(); showTab(); } };
      b.ondragstart = () => { dragIndex = i; b.style.opacity = '.5'; };
      b.ondragend = () => { dragIndex = null; b.style.opacity = ''; };
      b.ondragover = e => e.preventDefault();
      b.ondrop = e => { e.preventDefault(); if (dragIndex === null || dragIndex === i) return; const moved = tabs.splice(dragIndex, 1)[0]; tabs.splice(i, 0, moved); active = tabs.indexOf(moved); save(); renderTabs(); showTab(); };
      tabsEl.appendChild(b);
    });
  }

  function showHome() {
    homePage.hidden = false; viewerPage.hidden = true; frame.src = 'about:blank'; readerView.hidden = true; errorBox.hidden = true;
    status.textContent = 'Ready'; hint.textContent = 'Start page';
  }

  function showTab() {
    renderTabs();
    const tab = tabs[active];
    if (!tab || !tab.url) { showHome(); return; }
    homePage.hidden = true; viewerPage.hidden = false; readerView.hidden = true; errorBox.hidden = true;
    url.value = tab.url; status.textContent = tab.title || hostTitle(tab.url); hint.textContent = 'Direct website view';
    loading.hidden = false;
    frame.hidden = false;
    frame.src = tab.url;
    applyZoom();
    save();
  }

  function openSite(value, saveHistory = true) {
    const target = normalize(value);
    if (!target) { toast('Only HTTP/HTTPS addresses are supported.'); return; }
    const old = tabs[active] || { id: Date.now() };
    tabs[active] = { ...old, url: target, title: hostTitle(target) };
    if (saveHistory && /^https?:/i.test(target)) history = [target, ...history.filter(x => x !== target)].slice(0, 100);
    save(); showTab();
  }

  function newTab(focus = true) {
    tabs.push({ id: Date.now(), url: '', title: 'New Tab' });
    active = tabs.length - 1; save(); renderTabs(); showTab();
    if (focus) setTimeout(() => url.focus(), 30);
  }

  function closeTab(i) {
    if (tabs.length === 1) { tabs[0] = { id: Date.now(), url: '', title: 'New Tab' }; active = 0; }
    else { tabs.splice(i, 1); if (active >= tabs.length) active = tabs.length - 1; if (i < active) active--; }
    save(); showTab();
  }

  function goSearch(value) { if (value) openSite(value); }

  function renderPreviews() {
    const bp = $('#bookmarkPreview'), hp = $('#historyPreview');
    if (bp) {
      bp.innerHTML = '';
      const items = bookmarks.slice(0, 4);
      if (!items.length) bp.textContent = 'No bookmarks yet.';
      items.forEach(b => addPreview(bp, b.title || hostTitle(b.url), () => openSite(b.url)));
    }
    if (hp) {
      hp.innerHTML = '';
      const items = history.slice(0, 4);
      if (!items.length) hp.textContent = 'No history yet.';
      items.forEach(v => addPreview(hp, hostTitle(v), () => openSite(v, false)));
    }
  }

  function addPreview(parent, text, action) {
    const b = document.createElement('button'); b.textContent = text; b.onclick = action; parent.appendChild(b);
  }

  function openDrawer(title, bodyBuilder) {
    drawerContent.innerHTML = '';
    const h = document.createElement('h2'); h.textContent = title; drawerContent.appendChild(h);
    bodyBuilder(drawerContent);
    drawer.classList.add('open');
  }

  function makeButton(text, fn) { const b = document.createElement('button'); b.textContent = text; b.onclick = fn; return b; }

  function showBookmarks() {
    openDrawer('⭐ Bookmarks', box => {
      const folders = [...new Set(bookmarks.map(b => b.folder || 'General'))];
      const select = document.createElement('select'); select.className = 'drawer-select';
      ['All', ...folders].forEach(f => { const o = document.createElement('option'); o.value = f; o.textContent = f; select.appendChild(o); });
      box.appendChild(select);
      const list = document.createElement('div'); box.appendChild(list);
      const render = () => { list.innerHTML = ''; const chosen = select.value; const items = bookmarks.filter(b => chosen === 'All' || (b.folder || 'General') === chosen); if (!items.length) { list.innerHTML = '<p class="empty">No bookmarks here yet.</p>'; return; } items.forEach((b, i) => { const item = document.createElement('div'); item.className = 'item'; item.innerHTML = `<strong>${escapeHtml(b.title || hostTitle(b.url))}</strong><small>${escapeHtml(b.folder || 'General')}</small>`; item.onclick = () => { openSite(b.url); drawer.classList.remove('open'); }; const del = makeButton('×', e => { e.stopPropagation(); bookmarks.splice(bookmarks.indexOf(b), 1); save(); renderPreviews(); render(); toast('Bookmark removed'); }); del.className = 'mini-delete'; item.appendChild(del); list.appendChild(item); }); };
      select.onchange = render; render();
      box.appendChild(makeButton('＋ Add current page', () => bookmarkCurrent()));
    });
  }

  function bookmarkCurrent() {
    const tab = tabs[active]; if (!tab?.url) { toast('Open a page first.'); return; }
    const existing = bookmarks.find(b => b.url === tab.url);
    if (existing) { bookmarks = bookmarks.filter(b => b.url !== tab.url); toast('Bookmark removed'); }
    else { const folder = prompt('Bookmark folder name:', bookmarkFolder || 'General') || 'General'; bookmarkFolder = folder; bookmarks.unshift({ url: tab.url, title: tab.title, folder }); bookmarks = bookmarks.slice(0, 100); toast('⭐ Bookmarked'); }
    save(); updateBookmarkButton(); renderPreviews();
  }

  function updateBookmarkButton() {
    const b = $('#bookmark'); if (!b) return;
    const is = !!tabs[active]?.url && bookmarks.some(x => x.url === tabs[active].url); b.textContent = is ? '★' : '☆'; b.title = is ? 'Remove bookmark' : 'Bookmark current page';
  }

  function showHistory() {
    openDrawer('🕘 History', box => {
      box.appendChild(makeButton('🧹 Clear history', () => { history = []; save(); renderPreviews(); showHistory(); toast('History cleared'); }));
      history.forEach(v => { const item = document.createElement('div'); item.className = 'item'; item.textContent = v; item.onclick = () => { openSite(v, false); drawer.classList.remove('open'); }; box.appendChild(item); });
      if (!history.length) { const p = document.createElement('p'); p.className = 'empty'; p.textContent = 'No history yet.'; box.appendChild(p); }
    });
  }

  function showSettings() {
    openDrawer('⚙ Settings', box => {
      const label = document.createElement('label'); label.textContent = 'Search engine';
      const select = document.createElement('select'); select.className = 'drawer-select';
      Object.entries(engines).forEach(([name, endpoint]) => { const o = document.createElement('option'); o.value = endpoint; o.textContent = name; if (endpoint === searchEngine) o.selected = true; select.appendChild(o); });
      select.onchange = () => { searchEngine = select.value; save(); toast('Search engine updated'); };
      box.append(label, select);
      const zoomRow = document.createElement('div'); zoomRow.className = 'settings-row';
      zoomRow.append(makeButton('−', () => setZoom(zoom - 10)), makeButton(`${zoom}%`, () => setZoom(100)), makeButton('+', () => setZoom(zoom + 10)));
      box.appendChild(document.createElement('hr')); box.appendChild(document.createTextNode('Page zoom')); box.appendChild(zoomRow);
      box.appendChild(makeButton(dark ? '☀️ Switch to light theme' : '🌙 Switch to dark theme', toggleTheme));
      box.appendChild(makeButton('⌨ Keyboard shortcuts', showShortcuts));
      box.appendChild(makeButton('🧹 Clear all local data', () => { if (!confirm('Clear tabs, bookmarks, history, and settings?')) return; localStorage.clear(); location.reload(); }));
      const note = document.createElement('p'); note.className = 'empty'; note.textContent = 'Your tabs, bookmarks and history stay in this browser. A static site cannot bypass CORS or iframe restrictions.'; box.appendChild(note);
    });
  }

  function showShortcuts() {
    openDrawer('⌨ Keyboard Shortcuts', box => {
      [['Ctrl/⌘ + L','Focus address bar'],['Ctrl/⌘ + T','New tab'],['Ctrl/⌘ + W','Close tab'],['Ctrl/⌘ + R','Reload page'],['Alt + ←','Back'],['Alt + →','Forward'],['Esc','Close panel'],['Ctrl/⌘ + +','Zoom in'],['Ctrl/⌘ + −','Zoom out']].forEach(([a,b]) => { const p = document.createElement('p'); p.innerHTML = `<kbd>${a}</kbd> <span>${b}</span>`; box.appendChild(p); });
    });
  }

  function toggleTheme() { dark = !dark; document.body.classList.toggle('light', !dark); save(); const t = $('#theme'); if (t) t.textContent = dark ? '☾' : '☀'; }
  function setZoom(value) { zoom = Math.max(60, Math.min(140, value)); save(); applyZoom(); toast(`Zoom ${zoom}%`); }
  function applyZoom() { if (!frame) return; frame.style.transform = `scale(${zoom / 100})`; frame.style.transformOrigin = 'top left'; frame.style.width = `${10000 / zoom}%`; frame.style.height = `${10000 / zoom}%`; }

  async function reader() {
    const target = tabs[active]?.url; if (!target) { toast('Open a page first.'); return; }
    if (!/^https?:/i.test(target)) return;
    loading.hidden = false; status.textContent = 'Reader mode'; hint.textContent = 'Fetching readable text…';
    try {
      const res = await fetch('https://r.jina.ai/' + target, { headers: { Accept: 'text/plain' } });
      if (!res.ok) throw new Error('Reader service returned ' + res.status);
      const text = await res.text();
      readerView.textContent = text.slice(0, 500000); readerView.hidden = false; frame.hidden = true; errorBox.hidden = true; loading.hidden = true; toast('📖 Reader mode ready');
    } catch (e) { loading.hidden = true; toast('Reader mode could not load this page.'); hint.textContent = 'Reader unavailable'; }
  }

  function clearPage() { const tab = tabs[active]; if (!tab) return; tabs[active] = { ...tab, url: '', title: 'New Tab' }; save(); showTab(); toast('Page cleared'); }

  function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  $('#go').onclick = () => goSearch(url.value);
  url.addEventListener('keydown', e => { if (e.key === 'Enter') goSearch(url.value); });
  homeSearch?.addEventListener('keydown', e => { if (e.key === 'Enter') goSearch(homeSearch.value); });
  $('#homeGo')?.addEventListener('click', () => goSearch(homeSearch.value));
  document.querySelectorAll('[data-url]').forEach(b => b.onclick = () => openSite(b.dataset.url));
  $('#newTab')?.addEventListener('click', () => newTab());
  $('#openTab')?.addEventListener('click', () => newTab());
  $('#bookmark')?.addEventListener('click', bookmarkCurrent);
  $('#settings')?.addEventListener('click', showSettings);
  $('#reader')?.addEventListener('click', reader); $('#reader2')?.addEventListener('click', reader);
  $('#clearPage')?.addEventListener('click', clearPage);
  $('#fullscreen')?.addEventListener('click', () => { (viewerPage.requestFullscreen ? viewerPage.requestFullscreen() : frame.requestFullscreen?.()).catch?.(() => {}); });
  $('#home')?.addEventListener('click', showHome);
  $('#reload')?.addEventListener('click', () => tabs[active]?.url && showTab());
  $('#back')?.addEventListener('click', () => { if (history.length > 1) { const current = tabs[active]?.url; const pos = history.indexOf(current); const previous = history[pos + 1] || history[1]; if (previous) openSite(previous, false); } });
  $('#forward')?.addEventListener('click', () => toast('Forward navigation is limited by browser history in static mode.'));
  $('#closeDrawer')?.addEventListener('click', () => drawer.classList.remove('open'));
  $('#errorOpen')?.addEventListener('click', () => tabs[active]?.url && window.open(tabs[active].url, '_blank', 'noopener'));

  frame?.addEventListener('load', () => { loading.hidden = true; if (tabs[active]?.url) { status.textContent = tabs[active].title || hostTitle(tabs[active].url); hint.textContent = 'Direct website view'; } });
  window.addEventListener('online', () => { const o=$('#online'); if(o){o.textContent='● Online';o.style.color='#7ee2a8';} });
  window.addEventListener('offline', () => { const o=$('#online'); if(o){o.textContent='● Offline';o.style.color='#e7b07a';} });

  document.addEventListener('keydown', e => {
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === 'l') { e.preventDefault(); url.focus(); url.select(); }
    else if (mod && e.key.toLowerCase() === 't') { e.preventDefault(); newTab(); }
    else if (mod && e.key.toLowerCase() === 'w') { e.preventDefault(); closeTab(active); }
    else if (mod && e.key.toLowerCase() === 'r') { e.preventDefault(); tabs[active]?.url && showTab(); }
    else if (mod && (e.key === '+' || e.key === '=')) { e.preventDefault(); setZoom(zoom + 10); }
    else if (mod && e.key === '-') { e.preventDefault(); setZoom(zoom - 10); }
    else if (e.key === 'Escape') drawer.classList.remove('open');
  });

  // Extra browser panels exposed through the settings button's long-click / right-click.
  $('#settings')?.addEventListener('contextmenu', e => { e.preventDefault(); showShortcuts(); });
  document.body.classList.toggle('light', !dark);
  const themeButton = $('#theme'); if (themeButton) { themeButton.textContent = dark ? '☾' : '☀'; themeButton.onclick = toggleTheme; }
  renderPreviews(); renderTabs(); showTab(); updateBookmarkButton(); applyZoom();
})();
