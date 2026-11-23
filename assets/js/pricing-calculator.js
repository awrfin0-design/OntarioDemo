/*
 * Service Pricing Calculator (homepage section #pricing)
 * ------------------------------------------------------
 * EDIT YOUR PRICES HERE. All amounts are CAD, before tax.
 *
 *  - PRICING.services[service].jobs[job] = [low, high] base price range.
 *  - PRICING.regions[region].factor multiplies the base range (1.10 = +10%).
 *  - PRICING.timing[option].factor multiplies the result again.
 *  - PRICING.taxRate is used for the "with HST" line.
 *
 * The figures below are placeholder estimates. Replace them with your real prices
 * before going live.
 */
var PRICING = {
  taxRate: 0.13,
  roundTo: 5,
  services: {
    'gas-fireplace': {
      name: 'Gas Fireplace', img: '_site/gas/sections/features-3/img/gas-fireplace-2.webp',
      jobs: { repair: [175, 450], maintenance: [149, 229], installation: [2800, 6500] }
    },
    furnace: {
      name: 'Furnace', img: '_site/gas/sections/features-3/img/furnace-2.webp',
      jobs: { repair: [200, 650], maintenance: [129, 199], installation: [4500, 8500] }
    },
    'pool-heater': {
      name: 'Pool Heater', img: '_site/gas/sections/features-3/img/pool-heater-2.webp',
      jobs: { repair: [225, 700], maintenance: [175, 275], installation: [3500, 6500] }
    },
    hvac: {
      name: 'HVAC', img: '_site/gas/sections/features-3/img/hvac-2.webp',
      jobs: { repair: [200, 700], maintenance: [139, 229], installation: [6500, 14000] }
    },
    'air-conditioner': {
      name: 'Air Conditioner', img: '_site/gas/sections/features-3/img/air-conditioner-2.webp',
      jobs: { repair: [200, 650], maintenance: [129, 199], installation: [4200, 8000] }
    },
    'tankless-heater': {
      name: 'Tankless Heater', img: '_site/gas/sections/features-3/img/tankless-heater-2.webp',
      jobs: { repair: [200, 600], maintenance: [179, 279], installation: [3200, 5800] }
    }
  },
  jobs: {
    repair: 'Repair',
    maintenance: 'Maintenance / Tune-Up',
    installation: 'New Installation'
  },
  timing: {
    standard: { name: 'Scheduled', note: 'Book a time that works for you', factor: 1.00 },
    sameday: { name: 'Same-Day', note: 'A technician today', factor: 1.15 },
    emergency: { name: 'Emergency', note: 'Priority dispatch', factor: 1.30 }
  },
  regions: {
    toronto: { name: 'Toronto', factor: 1.10,
      cities: ['Toronto', 'North York', 'Scarborough', 'Etobicoke', 'East York'] },
    york: { name: 'York Region', factor: 1.08,
      cities: ['Markham', 'Vaughan', 'Richmond Hill', 'Thornhill', 'Unionville', 'Newmarket', 'Aurora', 'King City',
        'Nobleton', 'Schomberg', 'East Gwillimbury', 'Whitchurch-Stouffville', 'Georgina', 'Keswick', 'Sutton'] },
    peelHalton: { name: 'Peel & Halton', factor: 1.07,
      cities: ['Mississauga', 'Brampton', 'Caledon', 'Bolton', 'Oakville', 'Burlington', 'Milton', 'Halton Hills',
        'Georgetown', 'Acton'] },
    ottawa: { name: 'Ottawa', factor: 1.05, cities: ['Ottawa'] },
    durham: { name: 'Durham Region', factor: 1.03,
      cities: ['Ajax', 'Pickering', 'Whitby', 'Oshawa', 'Brooklin', 'Clarington', 'Courtice', 'Bowmanville', 'Newcastle',
        'Orono', 'Enniskillen', 'Mitchell Corners', 'Tyrone', 'Uxbridge', 'Scugog'] },
    simcoe: { name: 'Simcoe & Dufferin', factor: 1.02,
      cities: ['Barrie', 'Innisfil', 'Bradford', 'New Tecumseth', 'Tottenham', 'Angus', 'Adjala-Tosorontio', 'Springwater',
        'Oro-Medonte', 'Orillia', 'Midland', 'Collingwood', 'Wasaga Beach', 'Orangeville', 'Mono'] },
    hamiltonNiagara: { name: 'Hamilton & Niagara', factor: 1.00,
      cities: ['Hamilton', 'Grimsby', 'Lincoln', 'Smithville', 'St. Catharines', 'Niagara Falls', 'Niagara-on-the-Lake',
        'Thorold', 'Welland', 'Pelham', 'Port Colborne', 'Fort Erie'] },
    waterloo: { name: 'Waterloo, Wellington & Brant', factor: 1.00,
      cities: ['Kitchener', 'Waterloo', 'Cambridge', 'Guelph', 'Puslinch', 'Erin', 'Ayr', 'Brantford', 'Burford'] },
    southwest: { name: 'London & Southwestern Ontario', factor: 0.95,
      cities: ['London', 'Arva', 'Ilderton', 'Komoka', 'Kilworth', 'Delaware', 'Dorchester', 'Thamesford', 'Thorndale',
        'Lucan', 'Strathroy', 'Mount Brydges', 'Ailsa Craig', 'Parkhill', 'Glencoe', 'Dutton', 'Shedden', 'St. Thomas',
        'Port Stanley', 'Aylmer', 'Ingersoll', 'Woodstock', 'Norwich', 'Tillsonburg', 'Stratford', 'St. Marys', 'Mitchell',
        'Exeter', 'Hensall'] }
  }
};

(function () {
  var root = document.getElementById('pricing');
  if (!root) return;

  var state = { service: 'furnace', job: 'repair', city: 'Toronto', timing: 'standard' };
  var cityRegion = {};
  Object.keys(PRICING.regions).forEach(function (key) {
    PRICING.regions[key].cities.forEach(function (c) { cityRegion[c] = key; });
  });

  function money(n) { return '$' + Math.round(n).toLocaleString('en-CA'); }
  function round(n) { var r = PRICING.roundTo || 1; return Math.round(n / r) * r; }
  function pct(f) {
    var p = Math.round((f - 1) * 100);
    return p === 0 ? 'No change' : (p > 0 ? '+' : '−') + Math.abs(p) + '%';
  }
  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (html != null) e.innerHTML = html;
    return e;
  }

  // ---- Build the option controls ----
  var svcWrap = root.querySelector('[data-pc="services"]');
  Object.keys(PRICING.services).forEach(function (key) {
    var s = PRICING.services[key];
    var id = 'pc-svc-' + key;
    var label = el('label', { 'class': 'pc-svc', 'for': id });
    label.appendChild(el('input', { type: 'radio', name: 'pc-service', id: id, value: key }));
    label.appendChild(el('span', { 'class': 'pc-svc-img' }, '<img alt="" loading="lazy" src="' + s.img + '">'));
    label.appendChild(el('span', { 'class': 'pc-svc-name' }, s.name));
    svcWrap.appendChild(label);
  });

  function segment(wrapSel, name, items, getNote) {
    var wrap = root.querySelector(wrapSel);
    Object.keys(items).forEach(function (key) {
      var id = 'pc-' + name + '-' + key;
      var label = el('label', { 'class': 'pc-seg', 'for': id });
      label.appendChild(el('input', { type: 'radio', name: 'pc-' + name, id: id, value: key }));
      var text = typeof items[key] === 'string' ? items[key] : items[key].name;
      var note = getNote ? getNote(key) : '';
      label.appendChild(el('span', { 'class': 'pc-seg-text' },
        '<strong>' + text + '</strong>' + (note ? '<small>' + note + '</small>' : '')));
      wrap.appendChild(label);
    });
  }
  segment('[data-pc="jobs"]', 'job', PRICING.jobs);
  segment('[data-pc="timing"]', 'timing', PRICING.timing, function (k) {
    var t = PRICING.timing[k];
    return t.note + (t.factor !== 1 ? ' · ' + pct(t.factor) : '');
  });

  var citySel = root.querySelector('#pc-city');
  Object.keys(PRICING.regions).forEach(function (key) {
    var r = PRICING.regions[key];
    var group = el('optgroup', { label: r.name });
    r.cities.slice().sort().forEach(function (c) {
      var o = el('option', { value: c }); o.textContent = c; group.appendChild(o);
    });
    citySel.appendChild(group);
  });

  // The site's theme turns every <select> into a "nice-select" widget, which drops the
  // region groups. Keep the native dropdown for the city field.
  function keepNativeSelect() {
    var next = citySel.nextElementSibling;
    if (next && next.classList.contains('nice-select')) {
      if (window.jQuery && window.jQuery.fn.niceSelect) window.jQuery(citySel).niceSelect('destroy');
      else next.parentNode.removeChild(next);
    }
    citySel.style.display = 'block';
  }
  new MutationObserver(keepNativeSelect).observe(citySel.parentNode, { childList: true });
  document.addEventListener('DOMContentLoaded', keepNativeSelect);
  window.addEventListener('load', keepNativeSelect);

  // ---- Calculation ----
  function calc() {
    var svc = PRICING.services[state.service];
    var base = svc.jobs[state.job];
    var region = PRICING.regions[cityRegion[state.city]];
    var timing = PRICING.timing[state.timing];
    var f = region.factor * timing.factor;
    return {
      svc: svc, base: base, region: region, timing: timing,
      low: round(base[0] * f), high: round(base[1] * f)
    };
  }

  var out = {
    title: root.querySelector('[data-pc-out="title"]'),
    range: root.querySelector('[data-pc-out="range"]'),
    tax: root.querySelector('[data-pc-out="tax"]'),
    base: root.querySelector('[data-pc-out="base"]'),
    regionName: root.querySelector('[data-pc-out="region-name"]'),
    region: root.querySelector('[data-pc-out="region"]'),
    timingName: root.querySelector('[data-pc-out="timing-name"]'),
    timing: root.querySelector('[data-pc-out="timing"]')
  };

  function render() {
    var r = calc();
    out.title.textContent = r.svc.name + ' ' + PRICING.jobs[state.job] + ' in ' + state.city;
    out.range.textContent = money(r.low) + ' – ' + money(r.high);
    out.tax.textContent = money(r.low * (1 + PRICING.taxRate)) + ' – ' + money(r.high * (1 + PRICING.taxRate)) +
      ' with ' + Math.round(PRICING.taxRate * 100) + '% HST';
    out.base.textContent = money(r.base[0]) + ' – ' + money(r.base[1]);
    out.regionName.textContent = r.region.name;
    out.region.textContent = pct(r.region.factor);
    out.timingName.textContent = r.timing.name + ' service';
    out.timing.textContent = pct(r.timing.factor);
  }

  function sync() {
    ['service', 'job', 'timing'].forEach(function (k) {
      var input = root.querySelector('input[name="pc-' + k + '"][value="' + state[k] + '"]');
      if (input) input.checked = true;
    });
    citySel.value = state.city;
  }

  root.addEventListener('change', function (e) {
    var t = e.target;
    if (t.name === 'pc-service') state.service = t.value;
    else if (t.name === 'pc-job') state.job = t.value;
    else if (t.name === 'pc-timing') state.timing = t.value;
    else if (t.id === 'pc-city') state.city = t.value;
    render();
  });

  // ---- Book with this estimate: opens the site's quote pop-up, pre-filled ----
  root.querySelector('[data-pc="book"]').addEventListener('click', function (e) {
    var r = calc();
    var summary = 'Estimate request: ' + r.svc.name + ' ' + PRICING.jobs[state.job].toLowerCase() +
      ' in ' + state.city + ' (' + r.timing.name.toLowerCase() + '). Estimated ' + money(r.low) + ' - ' + money(r.high) + ' + HST.';
    if (typeof window.showQuoteModal === 'function') {
      e.preventDefault();
      window.showQuoteModal('Pricing Calculator');
      var modal = document.getElementById('quote-modal');
      var msg = modal && modal.querySelector('textarea[name="message"]');
      if (msg) msg.value = summary;
    }
  });

  sync();
  render();
})();
