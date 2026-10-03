/* Builder page: prompt -> generate -> "How I understood your request" panel. */
(function () {
  'use strict';
  var form = $('#prompt-form'), box = $('#prompt'), err = $('#prompt-error'), genBtn = $('#generate-btn');
  var result = $('#result'), meta = null, current = null, mandatory = [];

  function setCount() {
    var max = box.getAttribute('maxlength');
    $('#prompt-count').textContent = box.value.length + ' / ' + max;
  }
  box.addEventListener('input', setCount);
  setCount();

  $$('.example-chip').forEach(function (b) {
    b.addEventListener('click', function () { box.value = b.textContent; setCount(); box.focus(); });
  });
  box.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { form.requestSubmit(); }
  });

  api('GET', '/api/meta').then(function (r) {
    if (!r.ok) { showBanner(err, r.message); return; }
    meta = r.data;
    mandatory = meta.mandatory_sections;
    var sel = $('#u-type');
    meta.site_types.forEach(function (t) { sel.appendChild(el('option', { value: t.id, text: t.label })); });
  });

  function pct(x) { return Math.round(x * 100) + '%'; }
  function label(id) { var t = meta.site_types.filter(function (x) { return x.id === id; })[0]; return t ? t.label : id; }
  function pretty(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

  function render(payload) {
    current = payload;
    var req = payload.requirements, model = payload.project.model;
    result.hidden = false;
    $('#gen-time').textContent = 'Generated in ' + payload.timing_ms.toFixed(1) + ' ms';
    var low = $('#low-conf');
    low.hidden = !req.low_confidence;
    var ul = $('#low-conf-reasons');
    ul.textContent = '';
    (req.low_confidence_reasons || []).forEach(function (r) { ul.appendChild(el('li', { text: r })); });
    $('#u-type').value = req.site_type;
    var conf = req.confidence, thr = meta.confidence_threshold;
    var meter = $('#conf-meter');
    meter.setAttribute('aria-valuenow', String(Math.round(conf * 100)));
    meter.classList.toggle('low', conf < thr);
    $('#conf-fill').style.width = Math.round(conf * 100) + '%';
    $('#conf-mark').style.left = (thr * 100) + '%';
    $('#conf-text').textContent = 'Site-type confidence ' + pct(conf) + ' (low-confidence threshold ' + pct(thr) + ')';
    var others = Object.keys(req.type_scores).slice(1, 3).map(function (k) { return label(k) + ' ' + pct(req.type_scores[k]); });
    $('#type-scores').textContent = 'Next most likely: ' + others.join(', ');
    var secBox = $('#u-sections');
    secBox.textContent = '';
    meta.sections.forEach(function (s) {
      var fixed = mandatory.indexOf(s) >= 0;
      var cb = el('input', { type: 'checkbox', value: s, id: 'sec-' + s, checked: req.sections.indexOf(s) >= 0 || fixed, disabled: fixed });
      cb.checked = req.sections.indexOf(s) >= 0 || fixed;
      secBox.appendChild(el('label', { for: 'sec-' + s }, [cb, pretty(s)]));
    });
    var slots = req.slots, ms = model.slots;
    [['name', 'Site name'], ['tagline', 'Tagline'], ['email', 'Email'], ['phone', 'Phone'], ['location', 'Location']].forEach(function (p) {
      var inp = $('#s-' + p[0]);
      inp.value = slots[p[0]] || '';
      inp.placeholder = (p[0] === 'name' || p[0] === 'tagline') ? ('default: ' + ms[p[0]]) : 'not found';
    });
    var words = [];
    if (slots.colors.length) { words.push('Color words: ' + slots.colors.join(', ')); }
    if (slots.tones.length) { words.push('Tone words: ' + slots.tones.join(', ')); }
    $('#s-words').textContent = (words.join('. ') || 'No color or tone words found, so the default theme for this site type is used') +
      '. Theme chosen: ' + model.theme.palette + ' palette, ' + model.theme.font + ' font.';
    $('#open-editor').setAttribute('href', '/editor/' + payload.project.id);
    result.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var text = box.value.trim();
    if (!text) { result.hidden = true; current = null;
      showBanner(err, 'Please type a description of the website you want.'); box.focus(); return; }
    showBanner(err, '');
    setLoading(genBtn, true);
    api('POST', '/api/generate', { prompt: text }).then(function (r) {
      setLoading(genBtn, false);
      if (!r.ok) { result.hidden = true; current = null; showBanner(err, r.message); return; }
      render(r.data);
    });
  });

  $('#rebuild-btn').addEventListener('click', function () {
    if (!current) { return; }
    var btn = this;
    var overrides = {
      site_type: $('#u-type').value,
      sections: $$('#u-sections input').filter(function (c) { return c.checked; }).map(function (c) { return c.value; }),
      slots: { name: $('#s-name').value, tagline: $('#s-tagline').value, email: $('#s-email').value,
               phone: $('#s-phone').value, location: $('#s-location').value,
               colors: current.requirements.slots.colors, tones: current.requirements.slots.tones }
    };
    setLoading(btn, true);
    api('POST', '/api/projects/' + current.project.id + '/regenerate', { prompt: box.value.trim() || current.project.prompt, overrides: overrides }).then(function (r) {
      setLoading(btn, false);
      if (!r.ok) { toast(r.message, 'error'); return; }
      // after a manual correction the user's choice is the understanding: do not keep warning
      r.data.requirements.low_confidence = r.data.requirements.low_confidence && !(r.data.requirements.overridden || []).length;
      render(r.data);
      toast('Rebuilt with your changes.');
    });
  });
}());
