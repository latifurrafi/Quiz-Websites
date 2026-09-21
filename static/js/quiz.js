/* ==========================================================================
   The quiz runner.
   Questions arrive without the answer key — scoring happens on the server.
   ========================================================================== */
(function () {
  "use strict";

  var root = document.querySelector("[data-quiz]");
  if (!root) return;

  var dataEl = document.getElementById("quiz-data");
  var questions = [];
  try {
    questions = JSON.parse(dataEl.textContent) || [];
  } catch (err) {
    questions = [];
  }
  if (!questions.length) return;

  var cfg = {
    seconds: parseInt(root.dataset.seconds, 10) || 0,
    submitUrl: root.dataset.submitUrl,
    resultUrl: root.dataset.resultUrl,
    csrf: root.dataset.csrf
  };

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var LETTERS = ["A", "B", "C", "D", "E", "F"];

  /* ------------------------------------------------------------- elements */
  var el = {
    card: root.querySelector("[data-card]"),
    index: root.querySelector("[data-index]"),
    text: root.querySelector("[data-question]"),
    options: root.querySelector("[data-options]"),
    next: root.querySelector("[data-next]"),
    nextLabel: root.querySelector("[data-next-label]"),
    progress: document.querySelector("[data-progress]"),
    counter: document.querySelector("[data-counter]"),
    dots: document.querySelector("[data-dots]"),
    timer: document.querySelector("[data-timer]"),
    timerBar: document.querySelector("[data-timer-bar]"),
    timerNum: document.querySelector("[data-timer-num]"),
    sending: document.querySelector("[data-sending]"),
    sendingError: document.querySelector("[data-sending-error]")
  };

  /* ---------------------------------------------------------------- state */
  var current = 0;
  var answers = {};
  var locked = false;
  var submitted = false;
  var ticker = null;
  var remaining = 0;

  var CIRC = 2 * Math.PI * 24; // timer ring radius is 24
  if (el.timerBar) {
    el.timerBar.style.strokeDasharray = CIRC;
    el.timerBar.style.strokeDashoffset = 0;
  }

  /* ----------------------------------------------------------------- dots */
  function buildDots() {
    if (!el.dots) return;
    var frag = document.createDocumentFragment();
    questions.forEach(function (_, i) {
      var dot = document.createElement("span");
      dot.className = "qdot";
      dot.dataset.dot = String(i);
      frag.appendChild(dot);
    });
    el.dots.appendChild(frag);
  }

  function paintDots() {
    if (!el.dots) return;
    el.dots.querySelectorAll(".qdot").forEach(function (dot, i) {
      dot.classList.toggle("is-answered", answers[questions[i].id] != null);
      dot.classList.toggle("is-current", i === current);
    });
  }

  /* ---------------------------------------------------------------- timer */
  function stopTimer() {
    if (ticker) {
      clearInterval(ticker);
      ticker = null;
    }
  }

  function paintTimer() {
    if (!el.timer) return;
    el.timerNum.textContent = remaining;
    var ratio = cfg.seconds ? remaining / cfg.seconds : 1;
    el.timerBar.style.strokeDashoffset = CIRC * (1 - ratio);
    el.timer.classList.toggle("is-low", remaining <= Math.ceil(cfg.seconds * 0.4) && remaining > 5);
    el.timer.classList.toggle("is-critical", remaining <= 5);
  }

  function startTimer() {
    stopTimer();
    if (!cfg.seconds || !el.timer) return;
    remaining = cfg.seconds;
    paintTimer();
    ticker = window.setInterval(function () {
      remaining -= 1;
      paintTimer();
      if (remaining <= 0) {
        stopTimer();
        advance(); // out of time — move on, answered or not
      }
    }, 1000);
  }

  /* ------------------------------------------------------------- rendering */
  function render() {
    var q = questions[current];
    var picked = answers[q.id];

    el.index.textContent = "Question " + (current + 1);
    el.text.textContent = q.text;
    el.options.innerHTML = "";

    q.choices.forEach(function (choice, i) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "qopt";
      btn.dataset.choice = String(choice.id);
      btn.setAttribute("aria-pressed", picked === choice.id ? "true" : "false");
      if (picked === choice.id) btn.classList.add("is-picked");

      var key = document.createElement("span");
      key.className = "qopt__key";
      key.textContent = LETTERS[i] || String(i + 1);

      var text = document.createElement("span");
      text.className = "qopt__text";
      text.textContent = choice.text;

      var tick = document.createElement("span");
      tick.className = "qopt__tick";
      tick.innerHTML =
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
        'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<polyline points="20 6 9 17 4 12"/></svg>';

      btn.append(key, text, tick);
      btn.addEventListener("click", function () {
        pick(choice.id);
      });
      el.options.appendChild(btn);
    });

    var last = current === questions.length - 1;
    el.nextLabel.textContent = last ? "Finish quiz" : "Next question";
    el.next.disabled = picked == null;

    if (el.counter) {
      el.counter.innerHTML =
        "<b>" + String(current + 1).padStart(2, "0") + "</b><span> / " +
        String(questions.length).padStart(2, "0") + "</span>";
    }
    if (el.progress) {
      el.progress.style.width = ((current / questions.length) * 100).toFixed(2) + "%";
    }

    paintDots();
    startTimer();
  }

  /* ------------------------------------------------------------- choosing */
  function pick(choiceId) {
    if (locked) return;
    var q = questions[current];
    answers[q.id] = choiceId;

    el.options.querySelectorAll(".qopt").forEach(function (btn) {
      var isIt = btn.dataset.choice === String(choiceId);
      btn.classList.toggle("is-picked", isIt);
      btn.setAttribute("aria-pressed", isIt ? "true" : "false");
    });

    el.next.disabled = false;
    paintDots();
  }

  /* -------------------------------------------------------------- advance */
  function advance() {
    if (locked) return;

    if (current >= questions.length - 1) {
      send();
      return;
    }

    locked = true;
    stopTimer();

    var go = function () {
      current += 1;
      render();
      el.card.classList.remove("is-leaving");
      el.card.classList.add("is-entering");
      window.setTimeout(function () {
        el.card.classList.remove("is-entering");
        locked = false;
      }, 500);
    };

    if (reduced) {
      go();
      return;
    }

    el.card.classList.add("is-leaving");
    window.setTimeout(go, 340);
  }

  /* --------------------------------------------------------------- submit */
  function send() {
    if (submitted) return;
    submitted = true;
    locked = true;
    stopTimer();

    if (el.progress) el.progress.style.width = "100%";
    if (el.sending) el.sending.classList.add("is-on");
    if (el.sendingError) el.sendingError.textContent = "";

    fetch(cfg.submitUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": cfg.csrf,
        "X-Requested-With": "XMLHttpRequest"
      },
      credentials: "same-origin",
      body: JSON.stringify({ answers: answers })
    })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        window.removeEventListener("beforeunload", warnOnLeave);
        window.location.href = data.redirect || cfg.resultUrl;
      })
      .catch(function () {
        submitted = false;
        locked = false;
        if (el.sendingError) {
          el.sendingError.textContent =
            "We couldn't send your answers. Check your connection and try again.";
        }
        if (el.sending) {
          var retry = el.sending.querySelector("[data-retry]");
          if (retry) retry.hidden = false;
        }
      });
  }

  /* ------------------------------------------------------------- keyboard */
  function onKey(e) {
    if (locked || e.metaKey || e.ctrlKey || e.altKey) return;
    var tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea") return;

    var q = questions[current];
    var key = e.key.toUpperCase();

    var byLetter = LETTERS.indexOf(key);
    var byNumber = /^[1-9]$/.test(e.key) ? parseInt(e.key, 10) - 1 : -1;
    var idx = byLetter > -1 ? byLetter : byNumber;

    if (idx > -1 && q.choices[idx]) {
      e.preventDefault();
      pick(q.choices[idx].id);
      return;
    }

    if ((e.key === "Enter" || e.key === " ") && answers[q.id] != null) {
      e.preventDefault();
      advance();
    }
  }

  /* ---------------------------------------------------- leaving mid-quiz */
  function warnOnLeave(e) {
    if (submitted) return;
    e.preventDefault();
    e.returnValue = "";
    return "";
  }

  /* ------------------------------------------------------------------ go */
  buildDots();
  render();

  el.next.addEventListener("click", advance);
  document.addEventListener("keydown", onKey);
  window.addEventListener("beforeunload", warnOnLeave);

  var retryBtn = document.querySelector("[data-retry]");
  if (retryBtn) {
    retryBtn.addEventListener("click", function () {
      retryBtn.hidden = true;
      send();
    });
  }

  // Pausing is not the point of a timed quiz, but don't punish a tab switch
  // that the browser itself throttled — resync from wall clock instead.
  var hiddenAt = null;
  document.addEventListener("visibilitychange", function () {
    if (!cfg.seconds) return;
    if (document.hidden) {
      hiddenAt = Date.now();
    } else if (hiddenAt) {
      var away = Math.round((Date.now() - hiddenAt) / 1000);
      hiddenAt = null;
      if (away > 0 && ticker) {
        remaining = Math.max(0, remaining - away);
        paintTimer();
        if (remaining <= 0) {
          stopTimer();
          advance();
        }
      }
    }
  });
})();
