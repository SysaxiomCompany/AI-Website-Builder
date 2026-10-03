/* About the AI: shows only measured values read from /api/ml/info, /api/eval and /api/feedback/summary. */
(function () {
  'use strict';
  var err = $('#about-error');
  function pct(x, d) { return (x * 100).toFixed(d === undefined ? 1 : d) + '%'; }
  function num(x, d) { return Number(x).toFixed(d === undefined ? 3 : d); }
  function pretty(s) { return s.replace('_', ' '); }

  function stat(value, name, note) {
    return el('div', { class: 'stat' }, [el('div', { class: 'value', text: value }), el('div', { class: 'name', text: name }),
      note ? el('div', { class: 'note', text: note }) : null]);
  }
  function fill(sel, rows) { var t = $(sel); t.textContent = ''; rows.forEach(function (r) { t.appendChild(r); }); }
  function row(cells, tag) { return el('tr', {}, cells.map(function (c) { return el(tag || 'td', { text: c }); })); }

  Promise.all([api('GET', '/api/ml/info'), api('GET', '/api/eval'), api('GET', '/api/feedback/summary')]).then(function (res) {
    var info = res[0], ev = res[1], fb = res[2];
    if (!info.ok) { showBanner(err, info.message); $('#stat-grid').textContent = ''; return; }
    var m = info.data.metrics, evd = ev.ok ? ev.data : null;
    if (!ev.ok) { showBanner(err, 'Evaluation results are not available: ' + ev.message); }

    var test = m.test, cv = m.site_type.cv, scv = m.sections.cv;
    var grid = $('#stat-grid');
    grid.textContent = '';
    grid.appendChild(stat(pct(test.site_type.accuracy), 'Site-type accuracy, held-out test', 'macro F1 ' + num(test.site_type.macro_f1) + ', n = ' + test.n));
    grid.appendChild(stat(num(test.sections.micro_f1), 'Section micro F1, held-out test', 'exact-set match ' + pct(test.sections.exact_set_match)));
    if (evd) {
      grid.appendChild(stat(pct(evd.site_type.accuracy), 'Site-type accuracy, unseen wording', 'eval prompts, n = ' + evd.n + ', section micro F1 ' + num(evd.sections.micro_f1)));
      var g = evd.generation_time;
      grid.appendChild(stat(g.mean_ms.toFixed(1) + ' ms', 'Mean generation time', '95th percentile ' + g.p95_ms.toFixed(1) + ' ms over ' + g.n + ' prompts'));
    }
    var rated = fb.ok && fb.data.count > 0;
    grid.appendChild(stat(rated ? fb.data.average.toFixed(2) + ' / 5' : 'No ratings yet', 'Average user rating', rated ? 'from ' + fb.data.count + ' rating' + (fb.data.count === 1 ? '' : 's') + ' saved on this computer' : 'Rate a generated site in the editor'));
    grid.appendChild(stat(num(m.confidence.threshold, 2), 'Low-confidence threshold', 'chosen on the validation split'));

    // score table
    var head = $('#score-table thead'); head.textContent = '';
    head.appendChild(row(['Measure', '5-fold CV on train (mean ± std)', 'Held-out test split', evd ? 'Eval prompts (unseen wording)' : 'Eval prompts'], 'th'));
    var body = $('#score-table tbody'); body.textContent = '';
    function pm(mean, std) { return num(mean) + ' ± ' + num(std); }
    var E = evd || { site_type: null, sections: null };
    [['Site type: accuracy', pm(cv.accuracy_mean, cv.accuracy_std), num(test.site_type.accuracy), E.site_type ? num(E.site_type.accuracy) : 'n/a'],
     ['Site type: macro F1', pm(cv.macro_f1_mean, cv.macro_f1_std), num(test.site_type.macro_f1), E.site_type ? num(E.site_type.macro_f1) : 'n/a'],
     ['Sections: micro F1', pm(scv.micro_f1_mean, scv.micro_f1_std), num(test.sections.micro_f1), E.sections ? num(E.sections.micro_f1) : 'n/a'],
     ['Sections: macro F1', pm(scv.macro_f1_mean, scv.macro_f1_std), num(test.sections.macro_f1), E.sections ? num(E.sections.macro_f1) : 'n/a'],
     ['Sections: exact-set match', pm(scv.exact_match_mean, scv.exact_match_std), num(test.sections.exact_set_match), E.sections ? num(E.sections.exact_set_match) : 'n/a']
    ].forEach(function (r) { body.appendChild(row(r)); });
    $('#score-note').textContent = 'Sections are scored on the ' + test.sections.scored_labels.length + ' learnable sections (' + test.sections.scored_labels.join(', ') +
      '); navigation bar, hero and footer are always added by a rule. Held-out test n = ' + test.n + (evd ? ', eval prompts n = ' + evd.n + ' (of which ' + evd.hard_subset.n + ' hand-labelled harder prompts: site-type accuracy ' + num(evd.hard_subset.site_type_accuracy) + ')' : '') +
      '. Cross-validation uses the training split only (n = ' + cv.n + ', k = ' + cv.k + ').';

    // per-section table
    var sb = $('#section-table tbody'); sb.textContent = '';
    test.sections.scored_labels.forEach(function (s) {
      var p = test.sections.per_section[s];
      sb.appendChild(row([s, num(m.sections.thresholds[s], 2), num(p.precision), num(p.recall), num(p.f1), String(p.support)]));
    });

    // confusion matrix
    var cmh = $('#cm-table thead'); cmh.textContent = '';
    cmh.appendChild(row(['true \\ predicted'].concat(test.site_type.labels.map(pretty)), 'th'));
    var cmb = $('#cm-table tbody'); cmb.textContent = '';
    test.site_type.confusion_matrix.forEach(function (r, i) {
      var tr = el('tr', {}, [el('th', { text: pretty(test.site_type.labels[i]) })]);
      r.forEach(function (v, j) { tr.appendChild(el('td', { class: i === j ? 'diag' : '', text: String(v) })); });
      cmb.appendChild(tr);
    });

    // low-confidence
    var c = m.confidence;
    $('#conf-rule').textContent = 'Rule: ' + c.rule + '. Threshold ' + num(c.threshold, 4) + ' (' + c.threshold_choice + ').';
    var cl = $('#conf-list'); cl.textContent = '';
    cl.appendChild(el('li', { text: 'Flagged on the held-out test split: ' + pct(test.low_confidence.flagged_rate) + ' (' + test.low_confidence.flagged + ' of ' + test.n + ')' }));
    if (evd) {
      var lc = evd.low_confidence;
      cl.appendChild(el('li', { text: 'Flagged on the eval prompts: ' + pct(lc.flagged_rate) + ' (' + lc.flagged + ' of ' + evd.n + '); of the ' + lc.misclassified + ' eval prompts with a wrong site type, ' + lc.flagged_among_misclassified + ' were flagged and ' + lc.flagged_among_correct + ' correctly classified prompts were flagged too' }));
      var o = evd.ood_probe;
      var kinds = Object.keys(o.by_kind).map(function (k) { return k + ' ' + o.by_kind[k].flagged + '/' + o.by_kind[k].n; }).join(', ');
      cl.appendChild(el('li', { text: 'Unrelated, nonsense, very short and non-English probes flagged: ' + o.flagged + ' of ' + o.n + ' (' + kinds + ')' }));
      if (o.not_flagged.length) {
        cl.appendChild(el('li', { text: 'Not flagged: ' + o.not_flagged.map(function (r) { return '"' + r.text + '"'; }).join('; ') }));
      }
    }

    // time and ratings
    var tl = $('#time-list'); tl.textContent = '';
    if (evd) {
      var gt = evd.generation_time;
      tl.appendChild(el('li', { text: 'Mean ' + gt.mean_ms.toFixed(1) + ' ms, median ' + gt.median_ms.toFixed(1) + ' ms, 95th percentile ' + gt.p95_ms.toFixed(1) + ' ms, maximum ' + gt.max_ms.toFixed(1) + ' ms over ' + gt.n + ' evaluation prompts.' }));
      tl.appendChild(el('li', { text: 'Measured: ' + gt.scope + '. Machine: ' + gt.machine + '.' }));
    } else { tl.appendChild(el('li', { text: 'Generation time is not available until the evaluation has been run.' })); }
    var rb = $('#rating-box'); rb.textContent = '';
    if (rated) {
      var d = fb.data.distribution;
      rb.appendChild(el('p', { text: 'Average user rating ' + fb.data.average.toFixed(2) + ' out of 5 from ' + fb.data.count + ' rating' + (fb.data.count === 1 ? '' : 's') + ' (1: ' + d['1'] + ', 2: ' + d['2'] + ', 3: ' + d['3'] + ', 4: ' + d['4'] + ', 5: ' + d['5'] + '). Ratings are collected only in this app on this computer, usually from a handful of testers, so treat the average with caution.' }));
    } else {
      rb.appendChild(el('p', { text: 'No ratings have been saved yet. Open a generated site in the editor and use the Rate tab.' }));
    }

    // scope
    var ll = $('#learned-list'); ll.textContent = '';
    ll.appendChild(el('li', { text: 'Site-type classifier: TF-IDF features and ' + m.site_type.selection.name + ' (selected on validation data); chooses one of ' + info.data.site_types.length + ' site types.' }));
    ll.appendChild(el('li', { text: 'Section predictor: the same features with one-vs-rest ' + m.sections.selection.name + ' and one threshold per section chosen on validation data; scores ' + test.sections.scored_labels.length + ' learnable sections.' }));
    ll.appendChild(el('li', { text: 'Trained with the team\'s own pipeline (fixed seed ' + m.seed + ') on ' + m.data.train + ' training, ' + m.data.val + ' validation and ' + m.data.test + ' test prompts written by the team.' }));
    $('#type-list').textContent = info.data.site_types.map(pretty).join(', ');
    var sc = $('#section-chips'); sc.textContent = info.data.sections.join(', ') + ' (always present: ' + info.data.mandatory_sections.join(', ') + ')';
    $('#model-card').textContent = info.data.model_card;
  });
}());
