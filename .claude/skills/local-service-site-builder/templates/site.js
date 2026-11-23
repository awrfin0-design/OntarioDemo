/* Site behaviour: mobile menu, quote forms, pricing calculator. "__P__" = class prefix (set at build time). */
(function () {
  var P = '__P__';

  // ---- mobile menu ----
  var btn = document.querySelector('.' + P + '-menu-btn');
  var nav = document.querySelector('.' + P + '-nav');
  if (btn && nav) {
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') { nav.classList.remove('is-open'); btn.setAttribute('aria-expanded', 'false'); }
    });
  }

  // ---- forms ----
  document.querySelectorAll('form.' + P + '-form').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var note = form.querySelector('.' + P + '-form-note');
      var data = new FormData(form);
      if (data.get('company_website')) return; // honeypot
      if (!String(data.get('phone') || '').trim() && !String(data.get('email') || '').trim()) {
        note.className = P + '-form-note is-err';
        note.textContent = 'Please add a phone number or email so we can reach you.';
        return;
      }
      if (!String(data.get('name') || '').trim()) {
        note.className = P + '-form-note is-err';
        note.textContent = 'Please add your name.';
        return;
      }
      data.append('page', location.href);
      var endpoint = form.dataset.endpoint;
      var done = function () {
        if (form.dataset.thanks) { location.href = form.dataset.thanks; return; }
        note.className = P + '-form-note is-ok';
        note.textContent = 'Thanks! We have your request and will be in touch shortly.';
        form.reset();
      };
      if (!endpoint) {
        console.warn('Form endpoint not configured (site.json -> form.endpoint). Submission not sent.', Object.fromEntries(data));
        note.className = P + '-form-note is-err';
        note.textContent = 'This form is not connected yet. Please call us instead.';
        return;
      }
      var b = form.querySelector('button[type=submit]');
      b.disabled = true;
      fetch(endpoint, { method: 'POST', body: data, headers: { Accept: 'application/json' } })
        .then(function (r) { if (!r.ok) throw new Error(r.status); done(); })
        .catch(function () {
          note.className = P + '-form-note is-err';
          note.textContent = 'Sorry, something went wrong. Please call us instead.';
        })
        .finally(function () { b.disabled = false; });
    });
  });

  // ---- pricing calculator ----
  var cfgEl = document.getElementById(P + '-pricing');
  var root = document.querySelector('[data-calc]');
  if (!cfgEl || !root) return;
  var cfg = JSON.parse(cfgEl.textContent);
  var state = { service: cfg.services[0].slug, job: Object.keys(cfg.jobs)[0], timing: Object.keys(cfg.timing)[0], area: null };
  var areaRegion = {};
  cfg.regions.forEach(function (r) { r.areas.forEach(function (a) { areaRegion[a] = r; }); });

  function opt(group, value, label, note) {
    var id = P + '-c-' + group + '-' + value;
    return '<label class="' + P + '-opt" for="' + id + '"><input type="radio" name="' + P + '-' + group + '" id="' + id +
      '" value="' + value + '"><span>' + label + (note ? '<small>' + note + '</small>' : '') + '</span></label>';
  }
  function pct(f) { var p = Math.round((f - 1) * 100); return p === 0 ? 'No change' : (p > 0 ? '+' : '−') + Math.abs(p) + '%'; }
  var fmt = new Intl.NumberFormat(cfg.locale, { style: 'currency', currency: cfg.currency, maximumFractionDigits: 0 });
  function money(n) { return fmt.format(n); }
  function round(n) { return Math.round(n / cfg.roundTo) * cfg.roundTo; }

  root.querySelector('[data-calc-group=service]').innerHTML = cfg.services.map(function (s) { return opt('service', s.slug, s.name); }).join('');
  root.querySelector('[data-calc-group=job]').innerHTML = Object.keys(cfg.jobs).map(function (k) { return opt('job', k, cfg.jobs[k]); }).join('');
  root.querySelector('[data-calc-group=timing]').innerHTML = Object.keys(cfg.timing).map(function (k) {
    var t = cfg.timing[k]; return opt('timing', k, t.name, t.factor !== 1 ? pct(t.factor) : t.note || '');
  }).join('');
  var sel = root.querySelector('[data-calc-area]');
  sel.innerHTML = cfg.regions.map(function (r) {
    return '<optgroup label="' + r.name + '">' + r.areas.slice().sort().map(function (a) { return '<option>' + a + '</option>'; }).join('') + '</optgroup>';
  }).join('');
  state.area = sel.value;

  function calc() {
    var s = cfg.services.filter(function (x) { return x.slug === state.service; })[0];
    var base = s.jobs[state.job];
    if (!base) { // this service doesn't offer this job type: fall back to its first one
      state.job = Object.keys(s.jobs)[0]; base = s.jobs[state.job]; sync();
    }
    var r = areaRegion[state.area], t = cfg.timing[state.timing], f = r.factor * t.factor;
    return { s: s, base: base, r: r, t: t, low: round(base[0] * f), high: round(base[1] * f) };
  }
  function out(k, v) { root.querySelector('[data-out=' + k + ']').textContent = v; }
  function render() {
    var c = calc();
    out('title', c.s.name + ' · ' + cfg.jobs[state.job] + ' · ' + state.area);
    out('range', money(c.low) + ' – ' + money(c.high));
    out('tax', cfg.taxRate ? money(c.low * (1 + cfg.taxRate)) + ' – ' + money(c.high * (1 + cfg.taxRate)) + ' incl. ' + cfg.taxLabel : '');
    out('base', money(c.base[0]) + ' – ' + money(c.base[1]));
    out('region', c.r.name + ': ' + pct(c.r.factor));
    out('timing', c.t.name + ': ' + pct(c.t.factor));
    root.querySelectorAll('input[name=' + P + '-job]').forEach(function (i) { i.disabled = !c.s.jobs[i.value]; i.parentNode.style.opacity = c.s.jobs[i.value] ? '' : '.45'; });
  }
  function sync() {
    ['service', 'job', 'timing'].forEach(function (k) {
      var i = root.querySelector('input[name=' + P + '-' + k + '][value="' + state[k] + '"]'); if (i) i.checked = true;
    });
  }
  root.addEventListener('change', function (e) {
    var n = e.target.name;
    if (n === P + '-service') state.service = e.target.value;
    else if (n === P + '-job') state.job = e.target.value;
    else if (n === P + '-timing') state.timing = e.target.value;
    else if (e.target === sel) state.area = sel.value;
    render();
  });
  root.querySelector('[data-calc-book]').addEventListener('click', function (e) {
    var c = calc();
    var form = document.querySelector('form.' + P + '-form');
    if (!form) return;
    e.preventDefault();
    var msg = form.querySelector('textarea[name=message]');
    var svc = form.querySelector('select[name=service]');
    if (msg) msg.value = 'Estimate: ' + c.s.name + ', ' + cfg.jobs[state.job] + ', ' + state.area + ', ' + c.t.name + ' (' + money(c.low) + ' - ' + money(c.high) + ').';
    if (svc) svc.value = c.s.name;
    form.scrollIntoView({ behavior: 'smooth', block: 'center' });
    var first = form.querySelector('input[name=name]'); if (first) setTimeout(function () { first.focus(); }, 400);
  });
  sync();
  render();
})();
