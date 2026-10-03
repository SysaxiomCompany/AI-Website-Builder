/* Editor: edit text, show/hide and reorder sections, theme, regenerate; live preview in a sandboxed iframe. */
(function () {
  'use strict';
  var root = $('.editor'), pid = root.getAttribute('data-project-id');
  var state = { project: null, model: null, name: '', saved: '', meta: null, open: {}, seq: 0, timer: null, feedback: null };
  var errBox = $('#editor-error'), saveBtn = $('#save-btn'), frame = $('#preview'), loadingEl = $('#frame-loading');
  var ICONS = ['star', 'heart', 'bolt', 'shield', 'clock', 'check', 'book', 'camera'];
  var LONG = { text: 1, subheadline: 1, intro: 1, a: 1, quote: 1, paragraphs: 1 };

  function snapshot() { return JSON.stringify([state.name, state.model]); }
  function isDirty() { return state.model && snapshot() !== state.saved; }
  function refreshDirty() { $('#dirty-badge').hidden = !isDirty(); }
  function changed() { refreshDirty(); schedulePreview(); }
  function pretty(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function sectionLabel(t) {
    var map = { navbar: 'Navigation bar', hero: 'Hero', footer: 'Footer' };
    return map[t] || (state.model.nav_labels[t] ? pretty(t) + ' (' + state.model.nav_labels[t] + ')' : pretty(t));
  }
  function isFixedEnd(t) { return t === 'navbar' || t === 'footer'; }
  function isFixed(t) { return t === 'navbar' || t === 'hero' || t === 'footer'; }

  /* ---------- preview ---------- */
  function schedulePreview() { clearTimeout(state.timer); state.timer = setTimeout(renderPreview, 250); }
  function renderPreview() {
    var seq = ++state.seq;
    loadingEl.hidden = false;
    $('#preview-status').textContent = '';
    api('POST', '/api/preview', { model: state.model }).then(function (r) {
      if (seq !== state.seq) { return; }
      loadingEl.hidden = true;
      if (!r.ok) { $('#preview-status').textContent = 'Preview failed: ' + r.message; showBanner(errBox, 'Preview failed: ' + r.message); return; }
      showBanner(errBox, '');
      frame.srcdoc = r.raw;
    });
  }
  $$('.device-toggle button').forEach(function (b) {
    b.addEventListener('click', function () {
      $$('.device-toggle button').forEach(function (x) { x.setAttribute('aria-checked', x === b ? 'true' : 'false'); });
      $('#frame').setAttribute('data-device', b.getAttribute('data-w'));
    });
  });

  /* ---------- field editors (bound directly to the model objects) ---------- */
  var uid = 0;
  function textField(label, obj, key, long) {
    var id = 'f' + (++uid);
    var inp = el(long ? 'textarea' : 'input', long ? { id: id, rows: 3 } : { id: id, type: 'text' });
    inp.value = obj[key];
    inp.addEventListener('input', function () { obj[key] = inp.value; changed(); });
    return el('div', {}, [el('label', { for: id, text: label }), inp]);
  }
  function fieldsFor(obj, skip) {
    var out = [];
    Object.keys(obj).forEach(function (key) {
      var v = obj[key];
      if (skip && skip.indexOf(key) >= 0) { return; }
      var label = key === 'cta_label' ? 'Button label' : pretty(key.replace('_', ' '));
      if (key === 'icon') {
        var id = 'f' + (++uid), sel = el('select', { id: id }, ICONS.map(function (i) { return el('option', { value: i, text: pretty(i) }); }));
        sel.value = v;
        sel.addEventListener('change', function () { obj[key] = sel.value; changed(); });
        out.push(el('div', {}, [el('label', { for: id, text: 'Icon' }), sel]));
      } else if (key === 'cta_target') {
        var id2 = 'f' + (++uid), sel2 = el('select', { id: id2 }, state.model.sections.filter(function (s) { return !isFixed(s.type); }).map(function (s) { return el('option', { value: s.type, text: pretty(s.type) }); }));
        sel2.value = v;
        sel2.addEventListener('change', function () { obj[key] = sel2.value; changed(); });
        out.push(el('div', {}, [el('label', { for: id2, text: 'Button links to' }), sel2]));
      } else if (typeof v === 'boolean') {
        var cb = el('input', { type: 'checkbox' });
        cb.checked = v;
        cb.addEventListener('change', function () { obj[key] = cb.checked; changed(); });
        out.push(el('label', { class: 'check-row' }, [cb, 'Highlight this item']));
      } else if (typeof v === 'string') {
        out.push(textField(label, obj, key, !!LONG[key] || v.length > 70));
      } else if (Array.isArray(v)) {
        v.forEach(function (item, i) {
          if (typeof item === 'string') { out.push(textField(label + ' ' + (i + 1), v, i, true)); }
          else { out.push(el('div', { class: 'field-group' }, [el('p', { class: 'label-like', text: label + ' ' + (i + 1) })].concat(fieldsFor(item)))); }
        });
      }
    });
    return out;
  }

  /* ---------- sections pane ---------- */
  function detailsItem() {
    var key = '_details', open = !!state.open[key];
    var body = el('div', { class: 'section-body' }, fieldsFor(state.model.slots, ['colors', 'tones']));
    body.hidden = !open;
    var head = el('div', { class: 'section-head' }, [el('button', { class: 'name', type: 'button', 'aria-expanded': open ? 'true' : 'false', text: 'Site details (name, tagline, contact)', onclick: function () {
      state.open[key] = !state.open[key]; body.hidden = !state.open[key]; this.setAttribute('aria-expanded', String(!!state.open[key])); } })]);
    return el('li', { class: 'section-item' }, [head, body]);
  }
  function renderSections() {
    var list = $('#section-list');
    list.textContent = '';
    list.appendChild(detailsItem());
    var secs = state.model.sections, last = secs.length - 1;
    secs.forEach(function (s, i) {
      var fixed = isFixed(s.type), open = !!state.open[s.type];
      var body = el('div', { class: 'section-body' });
      if (s.type === 'navbar') { body.appendChild(el('p', { class: 'muted', text: 'The links are built from the visible sections. The site name comes from Site details.' })); }
      else { fieldsFor(s.content).forEach(function (n) { body.appendChild(n); }); }
      body.hidden = !open;
      var canUp = !isFixedEnd(s.type) && hasVisibleNeighbour(i, -1);
      var canDown = !isFixedEnd(s.type) && hasVisibleNeighbour(i, 1);
      var eye = el('button', { class: 'mini-btn', type: 'button', disabled: s.type === 'navbar' || s.type === 'hero' || s.type === 'footer',
        'aria-pressed': s.visible ? 'true' : 'false', 'aria-label': (s.visible ? 'Hide ' : 'Show ') + s.type + ' section', title: s.visible ? 'Hide section' : 'Show section',
        text: s.visible ? '◉' : '○', onclick: function () { s.visible = !s.visible; renderSections(); changed(); } });
      var item = el('li', { class: 'section-item' + (s.visible ? '' : ' hidden-section') }, [
        el('div', { class: 'section-head' }, [
          el('button', { class: 'name', type: 'button', 'aria-expanded': open ? 'true' : 'false', text: sectionLabel(s.type) + (s.visible ? '' : ' (hidden)'), onclick: function () {
            state.open[s.type] = !state.open[s.type]; body.hidden = !state.open[s.type]; this.setAttribute('aria-expanded', String(!!state.open[s.type])); } }),
          el('button', { class: 'mini-btn', type: 'button', disabled: !canUp, 'aria-label': 'Move ' + s.type + ' up', title: 'Move up', text: '↑', onclick: function () { move(i, -1); } }),
          el('button', { class: 'mini-btn', type: 'button', disabled: !canDown, 'aria-label': 'Move ' + s.type + ' down', title: 'Move down', text: '↓', onclick: function () { move(i, 1); } }),
          eye]),
        body]);
      list.appendChild(item);
    });
    var missing = state.meta.sections.filter(function (s) { return !isFixed(s) && !secs.some(function (x) { return x.type === s; }); });
    $('#addable').hidden = !missing.length;
    var al = $('#addable-list'); al.textContent = '';
    missing.forEach(function (s) { al.appendChild(el('button', { class: 'chip', type: 'button', text: '+ ' + pretty(s), onclick: function () { addSection(s); } })); });
  }
  function move(i, d) {
    /* swap with the nearest VISIBLE neighbour (skipping hidden ones), keeping navbar first and footer last */
    var secs = state.model.sections, j = i + d;
    while (j >= 1 && j <= secs.length - 2 && !secs[j].visible) { j += d; }
    if (j < 1 || j > secs.length - 2) { return; }
    var t = secs.splice(i, 1)[0];
    secs.splice(j, 0, t);
    renderSections(); changed();
  }
  function hasVisibleNeighbour(i, d) {
    var secs = state.model.sections, j = i + d;
    while (j >= 1 && j <= secs.length - 2) { if (secs[j].visible) { return true; } j += d; }
    return false;
  }
  function addSection(s) {
    api('POST', '/api/model/add-section', { model: state.model, section: s }).then(function (r) {
      if (!r.ok) { toast(r.message, 'error'); return; }
      state.model = r.data.model; state.open[s] = true;
      renderSections(); changed();
    });
  }

  /* ---------- theme pane ---------- */
  function renderTheme() {
    var box = $('#palette-list'); box.textContent = '';
    state.meta.palettes.forEach(function (p) {
      var on = state.model.theme.palette === p.id;
      box.appendChild(el('button', { class: 'swatch', type: 'button', role: 'radio', 'aria-checked': on ? 'true' : 'false', onclick: function () {
        state.model.theme.palette = p.id; renderTheme(); changed(); } }, [el('i', { style: 'background:' + p.swatch }), p.label]));
    });
    var sel = $('#font-select'); sel.textContent = '';
    state.meta.fonts.forEach(function (f) { sel.appendChild(el('option', { value: f.id, text: f.label })); });
    sel.value = state.model.theme.font;
  }
  $('#font-select').addEventListener('change', function () { state.model.theme.font = this.value; changed(); });

  /* ---------- prompt pane ---------- */
  function renderPrompt() {
    var req = state.model.requirements || {}, box = $('#understanding');
    box.textContent = '';
    if (req.site_type) {
      box.appendChild(el('p', { text: 'Understood as a ' + req.site_type.replace('_', ' ') + ' site (confidence ' + Math.round((req.confidence || 0) * 100) + '%) with sections: ' + (req.predicted_sections || []).join(', ') + '. Navigation bar, hero and footer are always added.' }));
    }
    var warn = $('#ed-low-conf');
    warn.hidden = !req.low_confidence;
    warn.textContent = req.low_confidence ? ('Low confidence when this site was generated: ' + (req.low_confidence_reasons || []).join(' ')) : '';
    $('#ed-prompt').value = state.project.prompt;
  }
  var dialog = $('#confirm-dialog');
  $('#regen-btn').addEventListener('click', function () {
    var btn = this, text = $('#ed-prompt').value.trim();
    if (!text) { toast('Please type a description first.', 'error'); return; }
    var done = function () {
      dialog.removeEventListener('close', done);
      if (dialog.returnValue !== 'ok') { return; }
      setLoading(btn, true);
      api('POST', '/api/projects/' + pid + '/regenerate', { prompt: text }).then(function (r) {
        setLoading(btn, false);
        if (!r.ok) { toast(r.message, 'error'); return; }
        adopt(r.data.project);
        if (r.data.requirements.low_confidence) { toast('Regenerated, but with low confidence: check the Prompt tab.', 'error'); } else { toast('Regenerated from the new prompt.'); }
      });
    };
    dialog.addEventListener('close', done);
    dialog.returnValue = '';
    dialog.showModal();
  });

  /* ---------- rating ---------- */
  var rating = 0;
  function renderStars() {
    var box = $('#stars'); box.textContent = '';
    for (var n = 1; n <= 5; n++) {
      (function (k) {
        box.appendChild(el('button', { class: 'star', type: 'button', role: 'radio', 'aria-checked': rating === k ? 'true' : 'false', 'aria-label': k + ' of 5', text: String(k), onclick: function () { rating = k; renderStars(); } }));
      }(n));
    }
  }
  $('#rate-btn').addEventListener('click', function () {
    if (!rating) { $('#rate-status').textContent = 'Choose a rating from 1 to 5 first.'; return; }
    api('POST', '/api/projects/' + pid + '/feedback', { rating: rating, comment: $('#rate-comment').value }).then(function (r) {
      $('#rate-status').textContent = r.ok ? 'Thank you. Your rating is saved on this computer.' : r.message;
    });
  });

  /* ---------- load / save / export ---------- */
  function adopt(project) {
    state.project = project;
    state.model = project.model;
    state.name = project.name;
    $('#project-name').value = project.name;
    state.saved = snapshot();
    renderSections(); renderTheme(); renderPrompt(); refreshDirty(); renderPreview();
  }
  $('#project-name').addEventListener('input', function () { state.name = this.value; refreshDirty(); });

  function save() {
    if (!state.name.trim()) { toast('The project name cannot be empty.', 'error'); return Promise.resolve(false); }
    setLoading(saveBtn, true);
    return api('PUT', '/api/projects/' + pid, { name: state.name, model: state.model }).then(function (r) {
      setLoading(saveBtn, false);
      if (!r.ok) { showBanner(errBox, 'Save failed: ' + r.message); return false; }
      showBanner(errBox, '');
      state.project = r.data.project; state.model = r.data.project.model; state.name = r.data.project.name;
      $('#project-name').value = state.name;
      state.saved = snapshot();
      renderSections(); renderTheme(); refreshDirty();
      toast('Saved.');
      return true;
    });
  }
  saveBtn.addEventListener('click', save);
  document.addEventListener('keydown', function (e) { if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); save(); } });
  $('#export-btn').addEventListener('click', function () {
    (isDirty() ? save() : Promise.resolve(true)).then(function (ok) { if (ok) { window.location.href = '/api/projects/' + pid + '/export'; } });
  });
  window.addEventListener('beforeunload', function (e) { if (isDirty()) { e.preventDefault(); e.returnValue = ''; } });

  /* ---------- tabs ---------- */
  $$('.side-tabs button').forEach(function (b) {
    b.addEventListener('click', function () {
      $$('.side-tabs button').forEach(function (x) { x.setAttribute('aria-selected', x === b ? 'true' : 'false'); });
      $$('.pane').forEach(function (p) { p.hidden = p.id !== b.getAttribute('data-pane'); });
    });
  });
  var grid = $('.editor-grid');
  grid.setAttribute('data-view', 'edit');
  function view(v) {
    grid.setAttribute('data-view', v);
    $('#tab-edit').setAttribute('aria-selected', String(v === 'edit'));
    $('#tab-preview').setAttribute('aria-selected', String(v === 'preview'));
  }
  $('#tab-edit').addEventListener('click', function () { view('edit'); });
  $('#tab-preview').addEventListener('click', function () { view('preview'); });

  /* ---------- start ---------- */
  renderStars();
  Promise.all([api('GET', '/api/meta'), api('GET', '/api/projects/' + pid)]).then(function (res) {
    if (!res[0].ok || !res[1].ok) { showBanner(errBox, (res[1].ok ? res[0] : res[1]).message); loadingEl.hidden = true; return; }
    state.meta = res[0].data;
    adopt(res[1].data.project);
    var fb = res[1].data.feedback;
    if (fb) { rating = fb.rating; $('#rate-comment').value = fb.comment; renderStars(); $('#rate-status').textContent = 'You rated this site ' + fb.rating + ' of 5.'; }
  });
}());
