/* ==========================================================================
   Result screen: score ring, count-up, confetti, answer review accordion
   ========================================================================== */
(function () {
  "use strict";

  var root = document.querySelector("[data-result]");
  if (!root) return;

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var score = parseInt(root.dataset.score, 10) || 0;
  var total = parseInt(root.dataset.total, 10) || 0;
  var pct = parseInt(root.dataset.pct, 10) || 0;
  var passed = root.dataset.passed === "1";

  /* ----------------------------------------------------------- score ring */
  function ring() {
    var bar = root.querySelector("[data-ring-bar]");
    var num = root.querySelector("[data-ring-score]");
    if (!bar) return;

    var r = bar.r.baseVal.value;
    var circ = 2 * Math.PI * r;
    bar.style.strokeDasharray = circ;
    bar.style.strokeDashoffset = circ;

    var fill = function () {
      bar.style.strokeDashoffset = circ * (1 - pct / 100);
    };

    if (reduced) {
      fill();
      if (num) num.firstChild.textContent = String(score);
      return;
    }

    window.setTimeout(fill, 250);

    if (num) {
      var duration = 1600;
      var start = performance.now();
      var step = function (now) {
        var p = Math.min(1, (now - start) / duration);
        var eased = 1 - Math.pow(1 - p, 3);
        num.firstChild.textContent = String(Math.round(score * eased));
        if (p < 1) requestAnimationFrame(step);
      };
      window.setTimeout(function () {
        requestAnimationFrame(step);
      }, 250);
    }
  }

  /* ------------------------------------------------------------- confetti */
  function confetti() {
    if (reduced || !passed) return;

    var canvas = document.querySelector("[data-confetti]");
    if (!canvas) return;

    var ctx = canvas.getContext("2d");
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = window.innerWidth;
    var h = window.innerHeight;

    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    var COLORS = ["#4fc8ea", "#8fe4f7", "#a88be8", "#7b5ec4", "#f2ece0"];
    var pieces = [];
    var count = pct === 100 ? 160 : 110;

    for (var i = 0; i < count; i++) {
      pieces.push({
        x: w / 2 + (Math.random() - 0.5) * w * 0.5,
        y: -20 - Math.random() * h * 0.4,
        w: Math.random() * 8 + 4,
        h: Math.random() * 5 + 3,
        vx: (Math.random() - 0.5) * 2.4,
        vy: Math.random() * 2.6 + 1.8,
        rot: Math.random() * Math.PI * 2,
        vr: (Math.random() - 0.5) * 0.22,
        c: COLORS[Math.floor(Math.random() * COLORS.length)],
        life: 1
      });
    }

    var started = performance.now();

    var frame = function (now) {
      ctx.clearRect(0, 0, w, h);
      var elapsed = now - started;
      var alive = false;

      for (var i = 0; i < pieces.length; i++) {
        var p = pieces[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.045;
        p.vx *= 0.995;
        p.rot += p.vr;
        if (elapsed > 2600) p.life -= 0.015;

        if (p.y < h + 40 && p.life > 0) alive = true;

        ctx.save();
        ctx.globalAlpha = Math.max(0, p.life);
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.fillStyle = p.c;
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
      }

      if (alive) {
        requestAnimationFrame(frame);
      } else {
        ctx.clearRect(0, 0, w, h);
        canvas.remove();
      }
    };

    window.setTimeout(function () {
      requestAnimationFrame(frame);
    }, 450);
  }

  /* -------------------------------------------------------------- review */
  function review() {
    var items = root.querySelectorAll("[data-review-item]");
    if (!items.length) return;

    items.forEach(function (item) {
      var toggle = item.querySelector("[data-review-toggle]");
      var panel = item.querySelector("[data-review-panel]");
      if (!toggle || !panel) return;

      toggle.addEventListener("click", function () {
        var open = item.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        panel.setAttribute("aria-hidden", open ? "false" : "true");
      });
    });

    // Open the first thing they got wrong — that's what they came to see.
    var firstWrong = root.querySelector('[data-review-item][data-correct="0"]');
    if (firstWrong) {
      var t = firstWrong.querySelector("[data-review-toggle]");
      if (t) t.click();
    }
  }

  /* --------------------------------------------------------- expand / all */
  function expandAll() {
    var btn = root.querySelector("[data-expand-all]");
    if (!btn) return;

    btn.addEventListener("click", function () {
      var items = root.querySelectorAll("[data-review-item]");
      var anyClosed = Array.prototype.some.call(items, function (i) {
        return !i.classList.contains("is-open");
      });

      items.forEach(function (item) {
        var toggle = item.querySelector("[data-review-toggle]");
        var panel = item.querySelector("[data-review-panel]");
        item.classList.toggle("is-open", anyClosed);
        if (toggle) toggle.setAttribute("aria-expanded", anyClosed ? "true" : "false");
        if (panel) panel.setAttribute("aria-hidden", anyClosed ? "false" : "true");
      });

      btn.textContent = anyClosed ? "Collapse all" : "Expand all";
    });
  }

  ring();
  confetti();
  review();
  expandAll();
})();
