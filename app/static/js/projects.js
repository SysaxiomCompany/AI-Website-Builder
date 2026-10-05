/* Projects page: list, open, duplicate, download, delete. */
(function () {
  'use strict';
  var list = $('#project-list'), loading = $('#projects-loading'), empty = $('#projects-empty'), err = $('#projects-error');
  var dialog = $('#confirm-dialog');

  function load() {
    loading.hidden = false; list.hidden = true; empty.hidden = true; showBanner(err, '');
    api('GET', '/api/projects').then(function (r) {
      loading.hidden = true;
      if (!r.ok) {
        showBanner(err, r.message);
        err.appendChild(document.createTextNode(' '));
        err.appendChild(el('button', { class: 'btn btn-sm btn-ghost', type: 'button', onclick: load, text: 'Retry' }));
        return;
      }
      render(r.data.projects);
    });
  }

  function label(t) { return t.replace('_', ' '); }

  function render(items) {
    list.textContent = '';
    if (!items.length) { empty.hidden = false; list.hidden = true; return; }
    items.forEach(function (p) {
      var rating = p.rating ? ('Rated ' + p.rating + ' of 5') : 'Not rated';
      var card = el('li', { class: 'project-card' }, [
        el('h2', { text: p.name }),
        el('div', { class: 'project-meta' }, [
          el('span', { class: 'badge', text: label(p.site_type) }),
          el('span', { class: 'muted', text: 'Updated ' + formatDate(p.updated_at) }),
          el('span', { class: 'muted', text: rating })]),
        el('p', { class: 'project-prompt', text: p.prompt }),
        el('div', { class: 'actions' }, [
          el('a', { class: 'btn btn-sm', href: '/editor/' + p.id, text: 'Open' }),
          el('button', { class: 'btn btn-sm btn-ghost', type: 'button', text: 'Duplicate', onclick: function () { duplicate(p); } }),
          el('a', { class: 'btn btn-sm btn-ghost', href: '/api/projects/' + p.id + '/export', text: 'Download ZIP' }),
          el('button', { class: 'btn btn-sm btn-ghost', type: 'button', text: 'Delete', onclick: function () { remove(p); } })])
      ]);
      list.appendChild(card);
    });
    list.hidden = false;
  }

  function duplicate(p) {
    api('POST', '/api/projects/' + p.id + '/duplicate').then(function (r) {
      if (!r.ok) { toast(r.message, 'error'); return; }
      toast('Duplicated "' + p.name + '".');
      load();
    });
  }

  function remove(p) {
    $('#confirm-text').textContent = '"' + p.name + '" and its rating will be deleted from this computer. This cannot be undone.';
    var done = function () {
      dialog.removeEventListener('close', done);
      if (dialog.returnValue !== 'ok') { return; }
      api('DELETE', '/api/projects/' + p.id).then(function (r) {
        if (!r.ok) { toast(r.message, 'error'); return; }
        toast('Deleted.');
        load();
      });
    };
    dialog.addEventListener('close', done);
    dialog.returnValue = '';
    dialog.showModal();
  }

  load();
}());
