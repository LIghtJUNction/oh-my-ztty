(() => {
  'use strict';
  const root = document.documentElement;
  const actionStatus = document.getElementById('action-status');
  const themeButton = document.querySelector('.theme-toggle');
  const themeMeta = document.querySelector('meta[name="theme-color"]');
  function syncThemeButton() {
    const light = root.dataset.theme === 'light';
    const label = light ? 'Switch to dark theme' : 'Switch to light theme';
    if (themeButton) { themeButton.setAttribute('aria-label', label); themeButton.title = label; }
    if (themeMeta) themeMeta.content = light ? '#faf8f4' : '#141210';
  }
  if (themeButton) {
    themeButton.hidden = false;
    themeButton.addEventListener('click', () => {
      const next = root.dataset.theme === 'light' ? 'dark' : 'light';
      root.dataset.theme = next;
      try { localStorage.setItem('omztty-docs-theme', next); } catch (error) {}
      syncThemeButton();
    });
  }
  syncThemeButton();
  document.querySelectorAll('.copy-button[data-copy]').forEach((button) => {
    button.hidden = false;
    let reset;
    button.addEventListener('click', async () => {
      const block = document.getElementById(button.dataset.copy);
      if (!block) return;
      const code = block.querySelector('code') || block;
      try {
        if (!navigator.clipboard) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(code.textContent);
        button.textContent = 'Copied';
        button.dataset.state = 'copied';
        if (actionStatus) actionStatus.textContent = 'Code copied to clipboard.';
        clearTimeout(reset);
        reset = setTimeout(() => { button.textContent = 'Copy'; delete button.dataset.state; }, 1800);
      } catch (error) {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(code);
        selection.removeAllRanges();
        selection.addRange(range);
        if (actionStatus) actionStatus.textContent = 'Code selected. Use your browser copy command.';
      }
    });
  });
  const headings = Array.from(document.querySelectorAll('.prose h2[id], .prose h3[id]'));
  const tocLinks = Array.from(document.querySelectorAll('.toc-list a[href^="#"]'));
  function markHeading(id) {
    tocLinks.forEach((link) => {
      if (decodeURIComponent(link.hash.slice(1)) === id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  if (headings.length) {
    markHeading(headings[0].id);
    let scheduled = false;
    const updateOutline = () => {
      scheduled = false;
      let active = headings[0];
      for (const heading of headings) {
        if (heading.getBoundingClientRect().top <= 150) active = heading;
        else break;
      }
      markHeading(active.id);
    };
    const scheduleOutline = () => {
      if (!scheduled) { scheduled = true; requestAnimationFrame(updateOutline); }
    };
    window.addEventListener('scroll', scheduleOutline, { passive: true });
    window.addEventListener('resize', scheduleOutline, { passive: true });
    updateOutline();
  }
  const dialog = document.getElementById('search-dialog');
  const input = document.getElementById('search-input');
  const results = document.getElementById('search-results');
  const searchStatus = document.getElementById('search-status');
  const triggers = Array.from(document.querySelectorAll('[data-search-open]'));
  if (!dialog || !input || !results || !searchStatus || typeof dialog.showModal !== 'function') return;
  let indexPromise;
  let index;
  let debounce;
  let opener;
  const base = new URL(document.body.dataset.root || './', document.baseURI);
  const normalize = (value) => String(value || '').normalize('NFKC').toLowerCase();
  const shortcut = /mac|iphone|ipad/i.test(navigator.platform) ? '⌘ K' : 'Ctrl K';
  document.querySelectorAll('.search-shortcut').forEach((label) => { label.textContent = shortcut; });
  function loadIndex() {
    if (index) return Promise.resolve(index);
    if (!indexPromise) {
      indexPromise = fetch(document.body.dataset.searchIndex, { credentials: 'same-origin' })
        .then((response) => {
          if (!response.ok) throw new Error('Search unavailable');
          return response.json();
        })
        .then((data) => {
          if (!Array.isArray(data)) throw new Error('Invalid search index');
          index = data.map((page) => ({
            ...page,
            normalizedTitle: normalize(page.title),
            normalizedHeadings: normalize((page.headings || []).map((h) => h.text).join(' ')),
            normalizedDescription: normalize(page.description),
            normalizedText: normalize(page.text)
          }));
          return index;
        }).catch((error) => { indexPromise = null; throw error; });
    }
    return indexPromise;
  }
  function excerpt(page, query) {
    const text = String(page.text || page.description || '').replace(/\s+/g, ' ');
    if (!query) return String(page.description || '').slice(0, 170);
    const term = query.split(/\s+/)[0];
    const found = normalize(text).indexOf(term);
    const start = Math.max(0, found - 50);
    return (start ? '…' : '') + text.slice(start, start + 180) + (text.length > start + 180 ? '…' : '');
  }
  function render(list, query) {
    results.replaceChildren();
    for (const page of list) {
      const url = new URL(page.url, base);
      if (url.origin !== location.origin || !url.pathname.startsWith(base.pathname)) continue;
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.className = 'search-result';
      link.href = url.href;
      const title = document.createElement('span');
      title.className = 'search-result-title';
      title.textContent = page.title;
      const description = document.createElement('span');
      description.className = 'search-result-excerpt';
      description.textContent = excerpt(page, query);
      link.append(title, description);
      item.append(link);
      results.append(item);
    }
    if (!query) searchStatus.textContent = 'Start here, or type to search all documentation.';
    else if (!results.children.length) searchStatus.textContent = 'No pages match “' + input.value.trim() + '”. Try a command or a shorter phrase.';
    else searchStatus.textContent = results.children.length + (results.children.length === 1 ? ' page found' : ' pages found');
  }
  async function search() {
    const query = normalize(input.value.trim());
    try {
      const pages = await loadIndex();
      if (query !== normalize(input.value.trim())) return;
      if (!query) {
        const recommended = pages.filter((p) => ['Installation', 'Configuration', 'Plugins', 'AI integration'].includes(p.title));
        render(recommended.length ? recommended.slice(0, 4) : pages.slice(0, 4), '');
        return;
      }
      const terms = query.split(/\s+/).filter(Boolean);
      const matches = pages.map((page) => {
        let score = 0;
        for (const term of terms) {
          if (page.normalizedTitle.includes(term)) score += 12;
          else if (page.normalizedHeadings.includes(term)) score += 7;
          else if (page.normalizedDescription.includes(term)) score += 4;
          else if (page.normalizedText.includes(term)) score += 1;
          else return { page, score: 0 };
        }
        return { page, score };
      }).filter((entry) => entry.score > 0).sort((a, b) => b.score - a.score);
      render(matches.slice(0, 8).map((entry) => entry.page), query);
    } catch (error) {
      results.replaceChildren();
      searchStatus.textContent = 'Search is unavailable. You can still browse every page from the menu.';
    }
  }
  function openSearch(trigger) {
    if (dialog.open) return;
    opener = trigger || document.activeElement;
    dialog.showModal();
    input.focus();
    searchStatus.textContent = 'Loading documentation…';
    search();
  }
  function closeSearch() { if (dialog.open) dialog.close(); }
  triggers.forEach((trigger) => {
    trigger.hidden = false;
    trigger.addEventListener('click', () => openSearch(trigger));
  });
  document.querySelectorAll('[data-search-close]').forEach((button) => button.addEventListener('click', closeSearch));
  dialog.addEventListener('close', () => {
    clearTimeout(debounce);
    if (opener && typeof opener.focus === 'function') opener.focus();
  });
  dialog.addEventListener('click', (event) => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeSearch();
  });
  input.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = setTimeout(search, 110);
  });
  input.addEventListener('keydown', (event) => {
    const first = results.querySelector('a');
    if (event.key === 'ArrowDown' && first) { event.preventDefault(); first.focus(); }
    if (event.key === 'Enter' && first) { event.preventDefault(); first.click(); }
  });
  results.addEventListener('keydown', (event) => {
    if (!['ArrowDown', 'ArrowUp'].includes(event.key)) return;
    const links = Array.from(results.querySelectorAll('a'));
    const current = links.indexOf(document.activeElement);
    if (current < 0) return;
    event.preventDefault();
    const next = current + (event.key === 'ArrowDown' ? 1 : -1);
    if (next < 0) input.focus();
    else if (next < links.length) links[next].focus();
  });
  document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k' && !event.altKey) {
      event.preventDefault();
      if (dialog.open) closeSearch();
      else openSearch(document.activeElement);
    }
  });
})();
