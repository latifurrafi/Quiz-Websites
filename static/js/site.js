/* ==========================================================================
   Shared site behaviour: preloader, nav, scroll reveal, counters, starfield
   ========================================================================== */
(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ------------------------------------------------------------ preloader */
  function preloader() {
    var el = document.querySelector("[data-preloader]");
    if (!el) return;
    var hide = function () {
      el.classList.add("is-done");
      document.body.classList.add("is-ready");
      window.setTimeout(function () {
        el.remove();
      }, 800);
    };
    if (document.readyState === "complete") {
      window.setTimeout(hide, reduced ? 0 : 450);
    } else {
      window.addEventListener("load", function () {
        window.setTimeout(hide, reduced ? 0 : 450);
      });
    }
    // Never let a stalled asset trap the visitor behind the loader.
    window.setTimeout(hide, 4000);
  }

  /* ------------------------------------------------------- sticky navbar */
  function stickyNav() {
    var nav = document.querySelector("[data-nav]");
    if (!nav) return;
    var apply = function () {
      nav.classList.toggle("is-stuck", window.scrollY > 24);
    };
    apply();
    window.addEventListener("scroll", apply, { passive: true });
  }

  /* ----------------------------------------------------- scroll progress */
  function scrollProgress() {
    var bar = document.querySelector("[data-scroll-progress]");
    if (!bar) return;
    var tick = function () {
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var ratio = max > 0 ? window.scrollY / max : 0;
      bar.style.transform = "scaleX(" + Math.min(1, Math.max(0, ratio)) + ")";
    };
    tick();
    window.addEventListener("scroll", tick, { passive: true });
    window.addEventListener("resize", tick, { passive: true });
  }

  /* ------------------------------------------------------- reveal on view */
  function reveals() {
    var items = document.querySelectorAll("[data-reveal], .split");
    if (!items.length) return;

    if (reduced || !("IntersectionObserver" in window)) {
      items.forEach(function (el) {
        el.classList.add("is-visible");
      });
      return;
    }

    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );

    items.forEach(function (el) {
      io.observe(el);
    });
  }

  /* ---------------------------------------------- split headline into words */
  function splitHeadlines() {
    document.querySelectorAll(".split").forEach(function (el) {
      if (el.dataset.split === "done") return;
      var delay = 0;

      var walk = function (node) {
        var kids = Array.prototype.slice.call(node.childNodes);
        kids.forEach(function (child) {
          if (child.nodeType === 3) {
            var frag = document.createDocumentFragment();
            child.textContent.split(/(\s+)/).forEach(function (chunk) {
              if (!chunk) return;
              if (/^\s+$/.test(chunk)) {
                frag.appendChild(document.createTextNode(chunk));
                return;
              }
              var outer = document.createElement("span");
              outer.className = "split__word";
              var inner = document.createElement("span");
              inner.textContent = chunk;
              inner.style.setProperty("--word-delay", delay + "ms");
              delay += 55;
              outer.appendChild(inner);
              frag.appendChild(outer);
            });
            node.replaceChild(frag, child);
          } else if (child.nodeType === 1 && !child.classList.contains("split__word")) {
            walk(child);
          }
        });
      };

      walk(el);
      el.dataset.split = "done";
    });
  }

  /* ------------------------------------------------------------- counters */
  function counters() {
    var nodes = document.querySelectorAll("[data-count]");
    if (!nodes.length) return;

    var run = function (el) {
      var target = parseFloat(el.dataset.count) || 0;
      var suffix = el.dataset.countSuffix || "";
      var duration = reduced ? 0 : 1500;
      var start = performance.now();

      var frame = function (now) {
        var p = duration ? Math.min(1, (now - start) / duration) : 1;
        var eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target * eased) + suffix;
        if (p < 1) requestAnimationFrame(frame);
      };
      requestAnimationFrame(frame);
    };

    if (!("IntersectionObserver" in window)) {
      nodes.forEach(run);
      return;
    }

    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          run(entry.target);
          io.unobserve(entry.target);
        });
      },
      { threshold: 0.5 }
    );
    nodes.forEach(function (el) {
      io.observe(el);
    });
  }

  /* ------------------------------------------------------------ starfield */
  function starfield() {
    var canvas = document.querySelector("[data-starfield]");
    if (!canvas || reduced) return;

    var ctx = canvas.getContext("2d");
    var stars = [];
    var w = 0;
    var h = 0;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var pointer = { x: -999, y: -999 };
    var raf = null;

    var COLORS = ["#4fc8ea", "#a88be8", "#f2ece0"];

    var seed = function () {
      var area = w * h;
      var count = Math.min(150, Math.max(40, Math.round(area / 14000)));
      stars = [];
      for (var i = 0; i < count; i++) {
        stars.push({
          x: Math.random() * w,
          y: Math.random() * h,
          r: Math.random() * 1.5 + 0.4,
          vx: (Math.random() - 0.5) * 0.14,
          vy: (Math.random() - 0.5) * 0.14,
          a: Math.random() * 0.5 + 0.2,
          tw: Math.random() * 0.02 + 0.004,
          c: COLORS[Math.floor(Math.random() * COLORS.length)]
        });
      }
    };

    var resize = function () {
      var rect = canvas.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      seed();
    };

    var draw = function () {
      ctx.clearRect(0, 0, w, h);

      for (var i = 0; i < stars.length; i++) {
        var s = stars[i];
        s.x += s.vx;
        s.y += s.vy;
        if (s.x < 0) s.x = w;
        if (s.x > w) s.x = 0;
        if (s.y < 0) s.y = h;
        if (s.y > h) s.y = 0;

        s.a += s.tw;
        if (s.a > 0.75 || s.a < 0.15) s.tw *= -1;

        ctx.globalAlpha = s.a;
        ctx.fillStyle = s.c;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fill();
      }

      // Thread a faint line between neighbours, and brighten near the cursor.
      for (var a = 0; a < stars.length; a++) {
        for (var b = a + 1; b < stars.length; b++) {
          var dx = stars[a].x - stars[b].x;
          var dy = stars[a].y - stars[b].y;
          var d2 = dx * dx + dy * dy;
          if (d2 > 16900) continue;
          var alpha = (1 - Math.sqrt(d2) / 130) * 0.16;

          var mx = (stars[a].x + stars[b].x) / 2;
          var my = (stars[a].y + stars[b].y) / 2;
          var pd = Math.hypot(mx - pointer.x, my - pointer.y);
          if (pd < 160) alpha += (1 - pd / 160) * 0.3;

          ctx.globalAlpha = alpha;
          ctx.strokeStyle = "#4fc8ea";
          ctx.lineWidth = 0.6;
          ctx.beginPath();
          ctx.moveTo(stars[a].x, stars[a].y);
          ctx.lineTo(stars[b].x, stars[b].y);
          ctx.stroke();
        }
      }

      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(draw);
    };

    var onPointer = function (e) {
      var rect = canvas.getBoundingClientRect();
      pointer.x = e.clientX - rect.left;
      pointer.y = e.clientY - rect.top;
    };

    resize();
    draw();

    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("pointermove", onPointer, { passive: true });
    window.addEventListener("pointerleave", function () {
      pointer.x = pointer.y = -999;
    });

    // Stop burning frames when the canvas scrolls out of view.
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting && raf === null) {
            raf = requestAnimationFrame(draw);
          } else if (!entry.isIntersecting && raf !== null) {
            cancelAnimationFrame(raf);
            raf = null;
          }
        });
      }).observe(canvas);
    }
  }

  /* -------------------------------------------------------- marquee clone */
  function marquees() {
    document.querySelectorAll("[data-marquee]").forEach(function (el) {
      var track = el.querySelector(".marquee__track");
      if (!track || track.dataset.cloned === "yes") return;
      var copy = track.cloneNode(true);
      copy.setAttribute("aria-hidden", "true");
      el.appendChild(copy);
      track.dataset.cloned = "yes";
    });
  }

  /* ------------------------------------------------------------- parallax */
  function parallax() {
    var nodes = document.querySelectorAll("[data-parallax]");
    if (!nodes.length || reduced) return;
    var tick = function () {
      var y = window.scrollY;
      nodes.forEach(function (el) {
        var speed = parseFloat(el.dataset.parallax) || 0.1;
        el.style.transform = "translate3d(0," + (y * speed).toFixed(2) + "px,0)";
      });
    };
    tick();
    window.addEventListener("scroll", tick, { passive: true });
  }

  /* ----------------------------------------------------------------- init */
  function init() {
    splitHeadlines();
    preloader();
    stickyNav();
    scrollProgress();
    reveals();
    counters();
    starfield();
    marquees();
    parallax();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
