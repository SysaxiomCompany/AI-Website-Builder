/* Shared helpers: theme toggle, API wrapper, toasts, tiny DOM builder. No external requests. */
(function () {
  'use strict';
  window.$ = function (sel, root) { return (root || document).querySelector(sel); };
  window.$$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  /* el('div', {class:'x', onclick: fn}, 'text' | node | [children]) - text always via textContent (never innerHTML) */
  window.el = function (tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v === false || v === null || v === undefined) { return; }
      if (k.slice(0, 2) === 'on' && typeof v === 'function') { node.addEventListener(k.slice(2), v); }
      else if (k === 'class') { node.className = v; }
      else if (k === 'text') { node.textContent = v; }
      else { node.setAttribute(k, v === true ? '' : v); }
    });
    [].concat(children === undefined ? [] : children).forEach(function (c) {
      if (c === null || c === undefined || c === false) { return; }
      node.appendChild(typeof c === 'object' ? c : document.createTextNode(String(c)));
    });
    return node;
  };

  /* api(method, url, body) -> Promise<{ok, status, data}>; network failures become a readable error */
  window.api = function (method, url, body) {
    var opts = { method: method, headers: {} };
    if (body !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    return fetch(url, opts).then(function (res) {
      return res.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = { raw: text }; }
        if (!res.ok) {
          var msg = (data && data.error && data.error.message) || ('The server answered with an error (' + res.status + ').');
          return { ok: false, status: res.status, data: data, message: msg };
        }
        return { ok: true, status: res.status, data: data, raw: text };
      });
    }, function () {
      return { ok: false, status: 0, data: null, message: 'Cannot reach the local server. Is the app still running?' };
    });
  };

  window.toast = function (message, kind) {
    var box = document.getElementById('toasts');
    if (!box) { return; }
    var t = window.el('div', { class: 'toast' + (kind === 'error' ? ' error' : ''), text: message });
    box.appendChild(t);
    setTimeout(function () { t.remove(); }, 4200);
  };

  window.showBanner = function (node, message) {
    if (!node) { return; }
    node.textContent = message || '';
    node.hidden = !message;
  };

  window.setLoading = function (btn, on) {
    if (!btn) { return; }
    btn.classList.toggle('loading', !!on);
    btn.disabled = !!on;
  };

  window.formatDate = function (iso) {
    var d = new Date(iso);
    return isNaN(d) ? iso : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  };

  /* theme toggle (the initial theme is set by the inline script in <head>) */
  var btn = document.getElementById('theme-toggle');
  function sync() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (btn) { btn.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme'); }
  }
  if (btn) {
    btn.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('aiwb-theme', next); } catch (e) { /* storage may be blocked */ }
      sync();
    });
    sync();
  }
}());
