() => {
  // Page snapshot for the browser worker. Evaluated as a function expression (no arguments).
  // Assigns data-bok-id="eN" to interactive elements; only ids created here are ever acted on.
  const MAX_ELEMENTS = 150, MAX_TEXT = 4000, MAX_NAME = 80, MAX_TEXT_EL = 80, MAX_VALUE = 80;
  document.querySelectorAll('[data-bok-id]').forEach(el => el.removeAttribute('data-bok-id'));

  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const clip = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s);
  const visible = el => {
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || st.visibility === 'collapse') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const inViewport = el => {
    const r = el.getBoundingClientRect();
    return r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth;
  };

  const SELECTOR = [
    'button', 'a[href]', 'input', 'textarea', 'select', '[contenteditable]:not([contenteditable=false])',
    '[role=button]', '[role=link]', '[role=tab]', '[role=menuitem]', '[role=checkbox]',
    '[role=textbox]', '[role=combobox]',
  ].join(',');
  const SKIP_INPUT = new Set(['hidden', 'range', 'color']);
  const CLICK_INPUT = new Set(['button', 'submit', 'reset', 'image', 'checkbox', 'radio']);

  const kindOf = el => {
    const tag = el.tagName.toLowerCase(), role = el.getAttribute('role');
    if (tag === 'input') {
      const t = (el.getAttribute('type') || 'text').toLowerCase();
      if (t === 'file') return 'upload';
      if (SKIP_INPUT.has(t)) return null;
      return CLICK_INPUT.has(t) ? 'click' : 'fill';
    }
    if (tag === 'select') return 'select';
    if (tag === 'textarea' || role === 'textbox' || role === 'combobox') return 'fill';
    if (el.isContentEditable && el.hasAttribute('contenteditable')) return 'fill';
    return 'click';
  };

  const roleOf = el => {
    const explicit = el.getAttribute('role');
    if (explicit) return explicit;
    const tag = el.tagName.toLowerCase();
    if (tag === 'a') return 'link';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'select') return 'combobox';
    if (tag === 'input') {
      const t = (el.getAttribute('type') || 'text').toLowerCase();
      if (t === 'file') return 'file';
      if (CLICK_INPUT.has(t)) return t === 'checkbox' || t === 'radio' ? t : 'button';
      return 'textbox';
    }
    if (el.hasAttribute('contenteditable')) return 'textbox';
    return tag;
  };

  const labelText = el => {
    const parts = [];
    if (el.labels) for (const l of el.labels) parts.push(clean(l.innerText || l.textContent));
    return parts.filter(Boolean).join(' ');
  };

  // Secrets: password/card/OTP-like inputs never expose their value (the snapshot goes to an external service).
  const SENSITIVE_AUTOCOMPLETE = /cc-|one-time-code|current-password|new-password/i;
  const SENSITIVE_NAME = /pass|mật khẩu|otp|cvv|cvc|card|thẻ|pin|token|secret/i;
  const isSensitive = el => {
    const tag = el.tagName.toLowerCase();
    const editable = el.hasAttribute('contenteditable') || el.getAttribute('role') === 'textbox';
    if (tag !== 'input' && tag !== 'textarea' && tag !== 'select' && !editable) return false;
    const type = (el.getAttribute('type') || 'text').toLowerCase();
    if (tag === 'input' && CLICK_INPUT.has(type)) return false;
    if (type === 'password') return true;
    if (SENSITIVE_AUTOCOMPLETE.test(el.getAttribute('autocomplete') || '')) return true;
    return SENSITIVE_NAME.test([el.getAttribute('name'), el.id, el.getAttribute('aria-label')].filter(Boolean).join(' '));
  };

  const nameOf = (el, kind) => {
    const aria = clean(el.getAttribute('aria-label'));
    if (aria) return aria;
    const by = el.getAttribute('aria-labelledby');
    if (by) {
      const t = clean(by.split(/\s+/).map(id => (document.getElementById(id) || {}).textContent || '').join(' '));
      if (t) return t;
    }
    const lab = labelText(el);
    if (lab) return lab;
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (tag === 'input' && ['button', 'submit', 'reset'].includes(type) && clean(el.value)) return clean(el.value);
    const ph = clean(el.getAttribute('placeholder'));
    if (kind === 'fill' && ph) return ph;
    if (kind !== 'upload' && !isSensitive(el)) {
      const inner = clean(el.innerText);
      if (inner) return inner;
    }
    const title = clean(el.getAttribute('title'));
    if (title) return title;
    if (kind === 'upload') {
      // Hidden file input: use the visible button/label next to it, else the visible container text.
      for (const sib of [el.previousElementSibling, el.nextElementSibling]) {
        if (sib && visible(sib) && /^(BUTTON|LABEL|A)$/.test(sib.tagName) && clean(sib.innerText)) return clean(sib.innerText);
      }
      let p = el.parentElement;
      while (p && !visible(p)) p = p.parentElement;
      if (p) return clean(p.innerText) || clean(p.getAttribute('aria-label')) || 'chọn tệp';
    }
    return ph || '';
  };

  // Same naming as the snapshot; the worker calls window.__bokName(el) right before a click (TOCTOU guard).
  const currentName = el => {
    const kind = kindOf(el);
    return clip(nameOf(el, kind || 'click'), MAX_NAME);
  };
  window.__bokName = currentName;
  // Visible text of an element, same cleaning/clipping as the snapshot 'text' field (click guard, L1).
  window.__bokText = el => clip(clean(el.innerText), MAX_TEXT_EL);

  const valueOf = el => {
    if (isSensitive(el)) return '';
    const tag = el.tagName.toLowerCase();
    if (tag === 'input') {
      const t = (el.getAttribute('type') || 'text').toLowerCase();
      if (t === 'checkbox' || t === 'radio') return el.checked ? 'đã chọn' : 'chưa chọn';
      if (t === 'file') return el.files && el.files.length ? Array.from(el.files).map(f => f.name).join(', ') : '';
      return clip(el.value || '', MAX_VALUE);
    }
    if (tag === 'textarea' || tag === 'select') return clip(el.value || '', MAX_VALUE);
    if (el.hasAttribute('contenteditable') || el.getAttribute('role') === 'textbox') return clip(clean(el.innerText), MAX_VALUE);
    if (el.getAttribute('aria-checked')) return el.getAttribute('aria-checked') === 'true' ? 'đã chọn' : 'chưa chọn';
    return '';
  };

  // File inputs are usually hidden: keep them when the container is visible (button, label or dropzone).
  const usable = (el, kind) => {
    if (visible(el)) return true;
    if (kind !== 'upload') return false;
    let p = el.parentElement;
    while (p && p !== document.body && !visible(p)) p = p.parentElement;
    return !!p && visible(p);
  };

  const seen = new Set();
  const items = [];
  for (const el of document.querySelectorAll(SELECTOR)) {
    if (seen.has(el)) continue;
    seen.add(el);
    const kind = kindOf(el);
    if (!kind || !usable(el, kind)) continue;
    items.push({ el, kind, front: visible(el) ? inViewport(el) : true });
  }
  const ordered = items.filter(i => i.front).concat(items.filter(i => !i.front)).slice(0, MAX_ELEMENTS);

  const elements = ordered.map((it, i) => {
    const { el, kind } = it;
    const id = 'e' + (i + 1);
    el.setAttribute('data-bok-id', id);
    const disabled = el.disabled === true || el.getAttribute('aria-disabled') === 'true';
    const sensitive = isSensitive(el);
    return {
      id, kind, role: roleOf(el), name: currentName(el), text: sensitive ? '' : clip(clean(el.innerText), MAX_TEXT_EL),
      value: valueOf(el), sensitive, placeholder: clean(el.getAttribute('placeholder')), disabled,
    };
  });

  const text = clip((document.body ? document.body.innerText : '').replace(/\n{3,}/g, '\n\n').trim(), MAX_TEXT);
  return { url: location.href, title: document.title, text, elements };
}
