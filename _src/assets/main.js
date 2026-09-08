/* ==========================================================================
   Data Insights North West — site scripts
   Every block guards on the elements it needs, so this one file is safe to
   load on every page.
   ========================================================================== */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ------------------------------------------------------------ mobile nav */
  var toggle = document.getElementById('navtoggle');
  var links  = document.getElementById('navlinks');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    links.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        links.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && links.classList.contains('open')) {
        links.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
      }
    });
  }

  /* ------------------------------------------------- chart hover + tooltip
     Any element inside a .plot carrying data-tip becomes hoverable. The tip
     anchors to the element itself, or to data-anchor if the mark sits
     elsewhere (hit bands on a line chart anchor to their point marker). */
  document.querySelectorAll('.plot').forEach(function (plot) {
    var tip   = plot.querySelector('.tip');
    var cross = plot.querySelector('.crosshair');
    if (!tip) return;

    function hide() {
      tip.classList.remove('on');
      if (cross) cross.classList.remove('on');
    }

    plot.querySelectorAll('[data-tip]').forEach(function (t) {
      function show() {
        var sel    = t.getAttribute('data-anchor');
        var anchor = sel ? plot.querySelector(sel) : t;
        if (!anchor) return;

        tip.innerHTML = t.getAttribute('data-tip');
        tip.classList.add('on');

        var pr = plot.getBoundingClientRect();
        var ar = anchor.getBoundingClientRect();
        var x  = ar.left - pr.left + ar.width / 2;
        var y  = ar.top - pr.top - 8;

        // Keep the tip inside the plot box rather than clipping at the edge.
        var half = tip.offsetWidth / 2;
        x = Math.max(half + 2, Math.min(pr.width - half - 2, x));
        tip.style.left = x + 'px';
        tip.style.top  = Math.max(tip.offsetHeight, y) + 'px';

        var cx = t.getAttribute('data-cx');
        if (cross && cx) {
          cross.setAttribute('x1', cx);
          cross.setAttribute('x2', cx);
          cross.classList.add('on');
        }
      }
      t.addEventListener('mouseenter', show);
      t.addEventListener('mousemove', show);
      t.addEventListener('focus', show);
      t.addEventListener('mouseleave', hide);
      t.addEventListener('blur', hide);
    });

    plot.addEventListener('mouseleave', hide);
  });

  /* --------------------------------------------------- draw-in for line paths */
  if (!reduceMotion && 'IntersectionObserver' in window) {
    var lines = document.querySelectorAll('.series-line[data-draw]');
    if (lines.length) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          var el = en.target, len;
          try { len = el.getTotalLength(); } catch (e) { return; }
          el.style.strokeDasharray  = len;
          el.style.strokeDashoffset = len;
          el.style.transition = 'stroke-dashoffset 1.1s ease .1s';
          requestAnimationFrame(function () {
            requestAnimationFrame(function () { el.style.strokeDashoffset = 0; });
          });
          io.unobserve(el);
        });
      }, { threshold: 0.35 });
      lines.forEach(function (l) { io.observe(l); });
    }
  }

  /* ------------------------------------------------------- table-view toggle
     The relief mechanism for charts whose colours sit under 3:1 — the data is
     always reachable as a table, not only as colour. */
  document.querySelectorAll('[data-toggle]').forEach(function (btn) {
    var target = document.querySelector(btn.getAttribute('data-toggle'));
    if (!target) return;
    var showLabel = btn.getAttribute('data-label-show') || 'Show data table';
    var hideLabel = btn.getAttribute('data-label-hide') || 'Hide data table';
    btn.setAttribute('aria-expanded', target.hidden ? 'false' : 'true');
    btn.addEventListener('click', function () {
      target.hidden = !target.hidden;
      btn.textContent = target.hidden ? showLabel : hideLabel;
      btn.setAttribute('aria-expanded', target.hidden ? 'false' : 'true');
    });
  });

  /* ------------------------------------------------------ dashboard slicers
     Drives the sample Power BI canvas. Data lives in a JSON script block so
     the markup stays readable and the numbers stay in one place. */
  var dashData = document.getElementById('dash-data');
  if (dashData) {
    var DATA;
    try { DATA = JSON.parse(dashData.textContent); } catch (e) { DATA = null; }

    if (DATA) {
      var group = document.querySelector('.filters[data-slicer]');

      var fmt = {
        gbp: function (n) {
          if (n >= 1000000) return '£' + (n / 1000000).toFixed(2) + 'm';
          if (n >= 1000)    return '£' + Math.round(n / 1000) + 'k';
          return '£' + n.toLocaleString('en-GB');
        },
        gbp2: function (n) {
          return '£' + n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        },
        num: function (n) { return n.toLocaleString('en-GB'); },
        pct: function (n) { return n.toFixed(1) + '%'; }
      };

      // Round an axis maximum up to the next 1 / 2 / 2.5 / 5 / 10 x 10^n, so
      // the tick labels land on numbers a reader recognises.
      function niceMax(v) {
        if (v <= 0) return 1;
        var mag  = Math.pow(10, Math.floor(Math.log10(v)));
        var norm = v / mag;
        var step = [1, 2, 2.5, 5, 10].find(function (s) { return norm <= s; }) || 10;
        return step * mag;
      }

      function paint(key) {
        var d = DATA[key];
        if (!d) return;

        // KPI tiles
        Object.keys(d.kpis).forEach(function (id) {
          var tile = document.querySelector('[data-kpi="' + id + '"]');
          if (!tile) return;
          var k = d.kpis[id];
          var v = tile.querySelector('.v');
          var delta = tile.querySelector('.d');
          if (v) v.textContent = fmt[k.f] ? fmt[k.f](k.v) : k.v;
          if (delta) {
            var dir = k.d > 0 ? 'up' : (k.d < 0 ? 'down' : 'flat');
            var glyph = k.d > 0 ? '▲' : (k.d < 0 ? '▼' : '■');
            delta.className = 'd ' + dir;
            delta.textContent = glyph + ' ' + (k.d > 0 ? '+' : '') + k.d.toFixed(1) + '%';
          }
        });

        // Monthly bars. Filtering rescales the axis, so the TICK LABELS are
        // recomputed too — a fixed axis with changing bars would misstate the
        // magnitude of every filtered slice.
        var max = niceMax(Math.max.apply(null, d.months));

        // Plot geometry is fixed: y=118 is the baseline, y=14 the axis top.
        var yTop = 14, yZero = 118, span = yZero - yTop;
        [['dash-y2', max], ['dash-y1', max / 2], ['dash-y0', 0]].forEach(function (pair) {
          var el = document.getElementById(pair[0]);
          if (el) el.textContent = pair[1] === 0 ? '£0' : fmt.gbp(pair[1]);
        });

        document.querySelectorAll('[data-bar]').forEach(function (bar, i) {
          var val = d.months[i];
          if (val == null) return;
          var h = Math.max(2, (val / max) * span);
          bar.setAttribute('height', h.toFixed(1));
          bar.setAttribute('y', (yZero - h).toFixed(1));

          var hit = document.querySelector('[data-barhit="' + i + '"]');
          if (hit) hit.setAttribute('data-tip', '<b>' + d.labels[i] + '</b><br>' + fmt.gbp(val));

          var cell = document.querySelector('[data-cell="' + i + '"]');
          if (cell) cell.textContent = fmt.gbp(val);
        });

        // Category rows
        (d.categories || []).forEach(function (c, i) {
          var row = document.querySelector('[data-cat="' + i + '"]');
          if (!row) return;
          var nm = row.querySelector('.cat-name');
          var vl = row.querySelector('.cat-val');
          var fl = row.querySelector('.cat-fill');
          if (nm) nm.textContent = c.name;
          if (vl) vl.textContent = fmt.gbp(c.value);
          if (fl) fl.style.width = c.share + '%';
        });

        var stamp = document.querySelector('[data-scope]');
        if (stamp) stamp.textContent = d.scope;
      }

      if (group) {
        group.querySelectorAll('button[data-key]').forEach(function (b) {
          b.addEventListener('click', function () {
            group.querySelectorAll('button[data-key]').forEach(function (o) {
              o.setAttribute('aria-pressed', 'false');
            });
            b.setAttribute('aria-pressed', 'true');
            paint(b.getAttribute('data-key'));
          });
        });
      }
      paint('all');
    }
  }

  /* ------------------------------------------------------- ROI calculator */
  var calc = document.getElementById('calc');
  if (calc) {
    var inputs = {
      hours: document.getElementById('c-hours'),
      people: document.getElementById('c-people'),
      rate: document.getElementById('c-rate')
    };
    var outs = {
      hours: document.getElementById('o-hours'),
      people: document.getElementById('o-people'),
      rate: document.getElementById('o-rate'),
      annualCost: document.getElementById('o-annual-cost'),
      daysBack: document.getElementById('o-days'),
      annualHours: document.getElementById('o-annual-hours'),
      weekly: document.getElementById('o-weekly')
    };

    var gbp0 = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 });

    function recalc() {
      var h = +inputs.hours.value;
      var p = +inputs.people.value;
      var r = +inputs.rate.value;

      var weeklyHours = h * p;
      var annualHours = weeklyHours * 46;          // 46 working weeks
      var annualCost  = annualHours * r;
      var daysBack    = annualHours / 7.5;         // a 7.5-hour working day

      if (outs.hours)  outs.hours.textContent  = h + (h === 1 ? ' hour' : ' hours');
      if (outs.people) outs.people.textContent = p + (p === 1 ? ' person' : ' people');
      if (outs.rate)   outs.rate.textContent   = gbp0.format(r) + ' / hour';

      // Deliberately NOT showing a "payback period" against a retainer. At
      // realistic inputs that figure flatters the pitch or misleads, and an
      // analyst's own calculator has to be straight with the arithmetic.
      if (outs.annualCost)  outs.annualCost.textContent  = gbp0.format(annualCost);
      if (outs.daysBack)    outs.daysBack.textContent    = (Math.round(daysBack * 10) / 10).toLocaleString('en-GB');
      if (outs.annualHours) outs.annualHours.textContent = Math.round(annualHours).toLocaleString('en-GB');
      if (outs.weekly)      outs.weekly.textContent      = weeklyHours.toLocaleString('en-GB');
    }

    Object.keys(inputs).forEach(function (k) {
      if (inputs[k]) inputs[k].addEventListener('input', recalc);
    });
    recalc();
  }

  /* ---------------------------------------------------------- enquiry form */
  var form = document.getElementById('enquiry');
  if (form) {
    var status = document.getElementById('status');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = form.querySelector('button[type=submit]');
      var label = btn ? btn.textContent : '';
      if (btn) { btn.textContent = 'Sending…'; btn.disabled = true; }
      if (status) status.className = 'form-status';

      fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { Accept: 'application/json' }
      }).then(function (r) {
        if (r.ok) {
          form.reset();
          if (status) {
            status.innerHTML = '<strong>Thank you — your enquiry has been sent.</strong><br>' +
              'We\'ll be in touch within one working day. A confirmation has gone to your email address.';
            status.className = 'form-status ok';
            status.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' });
          }
        } else {
          throw new Error('bad response');
        }
      }).catch(function () {
        if (status) {
          status.innerHTML = 'Something went wrong sending that. Please email ' +
            '<a href="mailto:enquiries@datainsightsnorthwest.co.uk">enquiries@datainsightsnorthwest.co.uk</a> instead.';
          status.className = 'form-status err';
        }
      }).then(function () {
        if (btn) { btn.textContent = label; btn.disabled = false; }
      });
    });
  }
})();
