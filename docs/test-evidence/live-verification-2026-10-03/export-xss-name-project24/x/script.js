/* Fixed script template: mobile menu toggle. Identical for every generated site. */
(function () {
  var toggle = document.querySelector('.nav-toggle');
  var links = document.getElementById('nav-links');
  if (!toggle || !links) { return; }
  function setOpen(open) {
    links.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  toggle.addEventListener('click', function () { setOpen(!links.classList.contains('open')); });
  links.addEventListener('click', function (event) {
    if (event.target && event.target.tagName === 'A') { setOpen(false); }
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') { setOpen(false); }
  });
}());
