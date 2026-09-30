(function () {
  const ice = window.IceLogic;
  const STORAGE_KEY = "ice-breaker-roster-v1";

  const PROMPTS = {
    spotlight: [
      { text: "A small win from the last few days.", min: 1 },
      { text: "Something you're looking forward to this week.", min: 1 },
      { text: "A shortcut or habit that actually saves you time.", min: 1 },
      { text: "Something you learned recently that surprised you.", min: 1 },
      { text: "If this week had a headline, what would it be?", min: 1 },
      { text: "A question you've been meaning to ask this team.", min: 2 },
      { text: "What would make the rest of today easier?", min: 1 },
      { text: "A song, show, or meal you've had on repeat.", min: 1 },
      { text: "One thing on your plate that others might not see.", min: 1 },
      { text: "A decision you're glad you made lately.", min: 1 },
      { text: "Something that went smoother than you expected.", min: 1 },
      { text: "A tiny ritual that helps you start the day.", min: 1 },
      { text: "If you could hand off one chore this week, what would it be?", min: 1 },
      { text: "What are you curious about right now?", min: 1 },
      { text: "Name a constraint you're working inside. You don't have to solve it.", min: 1 },
      { text: "A tool you wish the whole team used.", min: 2 },
      { text: "A specific thank-you for someone else on this call.", min: 2 },
    ],
    pairs: [
      { text: "Find one thing you both did this week that wasn't on a calendar.", min: 2 },
      { text: "Each share a question you've been sitting on.", min: 2 },
      { text: "Trade one thing you're confident about and one thing you're unsure about.", min: 2 },
      { text: "Describe this week as a weather report, then compare forecasts.", min: 2 },
      { text: "Each name a decision you're glad you made recently.", min: 2 },
      { text: "What's one way the next meeting could be shorter?", min: 2 },
      { text: "Each pick a word for the work right now, and say why.", min: 2 },
      { text: "Share a small annoyance and a small delight from this week.", min: 2 },
    ],
    "one-word": [
      { text: "One word for this week.", min: 1 },
      { text: "One word for the work in front of you.", min: 1 },
      { text: "One word you'd put on the team fridge.", min: 1 },
      { text: "One word for how the last meeting felt.", min: 1 },
      { text: "One word you want more of this week.", min: 1 },
      { text: "One word for the team today.", min: 2 },
    ],
  };

  const MODE_HELP = {
    spotlight: "Each person who's here gets one prompt. Pass if they stepped away for a second.",
    pairs: "Whoever is here is split into pairs. An odd person joins a trio instead of sitting alone.",
    "one-word": "A fixed order, one word each. Useful when the call is short.",
  };

  const state = {
    screen: "roster",
    mode: "spotlight",
    seats: loadSeats(),
    order: [],
    done: [],
    promptIndex: { spotlight: 0, pairs: 0, "one-word": 0 },
    groups: [],
    groupPrompts: [],
    groupDone: [],
    groupKey: "",
    timerLeft: ice.SPOTLIGHT_SECONDS,
    timerRunning: false,
    timerId: null,
    roundStarted: false,
  };

  const screenRoster = document.getElementById("screen-roster");
  const screenPlay = document.getElementById("screen-play");
  const rosterEl = document.getElementById("roster");
  const summaryEl = document.getElementById("roster-summary");
  const startBtn = document.getElementById("start");
  const startOverBtn = document.getElementById("start-over");
  const backBtn = document.getElementById("back");
  const attendanceEl = document.getElementById("attendance");
  const chipsEl = document.getElementById("chips");
  const stageEl = document.getElementById("stage");
  const orderEl = document.getElementById("order");
  const actionsEl = document.getElementById("actions");
  const modeHelpEl = document.getElementById("mode-help");
  const passNoteEl = document.getElementById("pass-note");
  const layoutEl = document.querySelector(".layout");

  function el(tag, props, children) {
    const node = document.createElement(tag);
    Object.keys(props || {}).forEach(function (key) {
      const value = props[key];
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (value != null && value !== false) node.setAttribute(key, String(value));
    });
    (children || []).forEach(function (child) {
      if (child) node.append(child);
    });
    return node;
  }

  function loadSeats() {
    try {
      return ice.loadSeats(JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"));
    } catch (err) {
      return ice.loadSeats(null);
    }
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ seats: state.seats }));
    } catch (err) {
      /* private mode or blocked storage — the round still works */
    }
  }

  function present() {
    return ice.presentIndices(state.seats);
  }

  function label(index) {
    return ice.uniqueLabel(state.seats, index);
  }

  function pool(mode) {
    return ice.usablePrompts(PROMPTS[mode], present().length);
  }

  function promptText(mode) {
    const prompts = pool(mode);
    const index = state.promptIndex[mode] % prompts.length;
    return prompts[index].text;
  }

  function stopTimer() {
    if (state.timerId) clearInterval(state.timerId);
    state.timerId = null;
    state.timerRunning = false;
  }

  function startTimer() {
    stopTimer();
    state.timerLeft = ice.SPOTLIGHT_SECONDS;
    state.timerRunning = true;
    state.timerId = setInterval(function () {
      state.timerLeft -= 1;
      if (state.timerLeft <= 0) {
        state.timerLeft = 0;
        stopTimer();
      }
      paintTimer();
    }, 1000);
  }

  function paintTimer() {
    const labelNode = document.getElementById("timer-label");
    const bar = document.getElementById("timer-bar");
    if (!labelNode || !bar) return;
    const left = Math.max(state.timerLeft, 0);
    labelNode.textContent = left === 0 ? "Time" : left + "s left";
    bar.style.width = (left / ice.SPOTLIGHT_SECONDS) * 100 + "%";
  }

  function beginRound() {
    const people = present();
    state.order = ice.shuffle(people, ice.randomUnit);
    state.done = [];
    state.groupKey = "";
    regroup();
    state.roundStarted = true;
    state.promptIndex.spotlight = Math.floor(ice.randomUnit() * pool("spotlight").length);
    state.promptIndex["one-word"] = Math.floor(ice.randomUnit() * pool("one-word").length);
    if (state.mode === "spotlight") startTimer();
    else stopTimer();
  }

  function queue() {
    return ice.remaining(state.order, state.done, present());
  }

  function show(screen) {
    state.screen = screen;
    screenRoster.hidden = screen !== "roster";
    screenPlay.hidden = screen !== "play";
    if (screen === "roster") updateRosterSummary();
    else {
      if (state.mode === "spotlight" && queue().length) startTimer();
      renderPlay();
    }
  }

  function updateRosterSummary() {
    const count = present().length;
    let line = ice.attendanceLine(count, ice.SEAT_COUNT);
    if (count === 1) line += " Spotlight and one word work solo. Pairs needs two.";
    summaryEl.textContent = line;
    startBtn.disabled = count === 0;
    const returning = state.roundStarted && count > 0;
    startBtn.textContent = returning ? "Return to this round" : "Start round";
    startBtn.dataset.action = returning ? "return" : "start";
    startOverBtn.hidden = !returning;
  }

  function buildRoster() {
    rosterEl.replaceChildren();
    state.seats.forEach(function (seat, index) {
      const checkId = "seat-" + index;
      const checkbox = el("input", { type: "checkbox", id: checkId });
      checkbox.checked = seat.here;
      checkbox.addEventListener("change", function () {
        state.seats[index].here = checkbox.checked;
        save();
        updateRosterSummary();
      });
      const name = el("input", {
        type: "text",
        maxlength: "40",
        "aria-label": "Name for seat " + (index + 1),
        placeholder: "Person " + (index + 1),
      });
      name.value = seat.name;
      name.addEventListener("input", function () {
        state.seats[index].name = ice.sanitizeName(name.value);
        if (name.value !== state.seats[index].name) name.value = state.seats[index].name;
        save();
      });
      const row = el("div", { class: "seat" }, [
        el("label", {}, [checkbox, document.createTextNode("Here")]),
        name,
      ]);
      rosterEl.append(row);
    });
    updateRosterSummary();
  }

  function renderChips() {
    chipsEl.replaceChildren();
    state.seats.forEach(function (seat, index) {
      const chip = el("button", {
        type: "button",
        class: "chip",
        "aria-pressed": seat.here ? "true" : "false",
      });
      chip.textContent = label(index);
      chip.addEventListener("click", function () {
        state.seats[index].here = !state.seats[index].here;
        const box = document.getElementById("seat-" + index);
        if (box) box.checked = state.seats[index].here;
        save();
        passNoteEl.textContent = "";
        renderPlay();
      });
      chipsEl.append(chip);
    });
  }

  function regroup() {
    const people = present();
    state.groups = ice.makeGroups(ice.shuffle(people, ice.randomUnit));
    state.groupPrompts = ice.assignGroupPrompts(state.groups.length, Math.max(pool("pairs").length, 1), ice.randomUnit);
    state.groupDone = state.groups.map(function () { return false; });
    state.groupKey = people.join(",");
  }

  function ensureGroups() {
    if (present().join(",") !== state.groupKey) regroup();
  }

  function setMode(mode) {
    if (state.mode === mode) return;
    state.mode = mode;
    document.querySelectorAll(".modes button").forEach(function (button) {
      button.setAttribute("aria-selected", button.getAttribute("data-mode") === mode ? "true" : "false");
    });
    if (mode === "spotlight" && queue().length) startTimer();
    else stopTimer();
    passNoteEl.textContent = "";
    renderPlay();
  }

  function renderOrder(items) {
    orderEl.replaceChildren();
    items.forEach(function (item) {
      const li = el("li");
      if (item.current) li.setAttribute("aria-current", "step");
      li.append(document.createTextNode(item.name));
      if (item.done) {
        const mark = el("span", { class: "mark", text: "Done" });
        li.append(mark);
      }
      orderEl.append(li);
    });
  }

  function renderSpotlight(doneWord) {
    const people = queue();
    const spoken = ice.syncOrder(state.order, present());
    layoutEl.classList.toggle("layout--solo", false);
    orderEl.hidden = false;
    if (!present().length) {
      emptyStage();
      return;
    }
    if (!people.length) {
      stageEl.replaceChildren(
        el("p", { class: "kicker", text: "Round done" }),
        el("h3", { class: "who", text: "Everyone here has gone." }),
        el("p", { class: "prompt", text: "Start another round with this group, or check in someone who just joined." })
      );
      renderOrder(spoken.map(function (index) {
        return { name: label(index), done: true, current: false };
      }));
      actionsEl.replaceChildren(action("Another round", "primary", function () { beginRound(); renderPlay(); }));
      return;
    }
    const current = people[0];
    const upcoming = people.slice(1, 3).map(label);
    stageEl.replaceChildren(
      el("p", { class: "kicker", text: doneWord ? "One word" : "Up now" }),
      el("h3", { class: "who", text: label(current) }),
      el("p", { class: "prompt", text: promptText(state.mode) })
    );
    if (upcoming.length) {
      stageEl.append(el("p", { class: "then", text: "Then " + upcoming.join(", then ") + "." }));
    }
    if (!doneWord) {
      const timer = el("div", { class: "timer" }, [
        el("div", { class: "timer-row" }, [
          el("span", { text: "Keep it short" }),
          el("span", { id: "timer-label", text: state.timerLeft + "s left" }),
        ]),
        el("div", { class: "bar" }, [el("span", { id: "timer-bar" })]),
      ]);
      stageEl.append(timer);
      paintTimer();
    }
    renderOrder(spoken.map(function (index) {
      return {
        name: label(index),
        done: state.done.indexOf(index) !== -1,
        current: index === current,
      };
    }));
    const buttons = [
      action(doneWord ? "Next word" : "Next person", "primary", advance),
      action("Another prompt", "ghost", function () {
        const prompts = pool(state.mode);
        state.promptIndex[state.mode] = ice.pickPrompt(
          prompts.length,
          state.promptIndex[state.mode] % prompts.length,
          ice.randomUnit
        );
        renderPlay();
      }),
    ];
    if (people.length > 1) {
      buttons.splice(1, 0, action("Pass", "ghost", function () {
        state.order = ice.passTurn(state.order, current, people.length);
        passNoteEl.textContent = label(current) + " will go later this round.";
        if (!doneWord) startTimer();
        renderPlay();
      }));
    }
    buttons.push(action("New round", "ghost", function () { beginRound(); renderPlay(); }));
    actionsEl.replaceChildren.apply(actionsEl, buttons);
  }

  function renderPairs() {
    layoutEl.classList.add("layout--solo");
    orderEl.hidden = true;
    ensureGroups();
    const people = present();
    if (people.length < 2) {
      stageEl.replaceChildren(
        el("p", { class: "kicker", text: "Pairs" }),
        el("h3", { class: "who", text: people.length === 1 ? "Need one more person." : "Nobody is checked in." }),
        el("p", { class: "prompt", text: "Check in whoever just joined, or switch to Spotlight." })
      );
      actionsEl.replaceChildren(action("Use Spotlight", "primary", function () { setMode("spotlight"); }));
      return;
    }
    const prompts = pool("pairs");
    const wrap = el("div", { class: "groups" });
    state.groups.forEach(function (group, groupIndex) {
      const names = group.map(label).join("  ·  ");
      const kind = group.length === 3 ? "Trio" : group.length === 2 ? "Pair" : "Solo";
      const prompt = prompts[state.groupPrompts[groupIndex] % prompts.length].text;
      const shared = el("button", {
        type: "button",
        class: "shared",
        "aria-pressed": state.groupDone[groupIndex] ? "true" : "false",
      });
      shared.textContent = state.groupDone[groupIndex] ? "Shared" : "We shared";
      shared.addEventListener("click", function () {
        state.groupDone[groupIndex] = !state.groupDone[groupIndex];
        renderPlay();
      });
      wrap.append(el("article", { class: "group" }, [
        el("p", { class: "kicker", text: kind }),
        el("h3", { text: names }),
        el("p", { class: "prompt", text: prompt }),
        shared,
      ]));
    });
    stageEl.replaceChildren(wrap);
    actionsEl.replaceChildren(action("Reshuffle groups", "primary", function () {
      regroup();
      renderPlay();
    }));
  }

  function emptyStage() {
    stageEl.replaceChildren(
      el("p", { class: "kicker", text: "Nobody's here" }),
      el("h3", { class: "who", text: "Check in at least one person." })
    );
    orderEl.replaceChildren();
    actionsEl.replaceChildren();
  }

  function advance() {
    const people = queue();
    if (!people.length) return;
    state.done.push(people[0]);
    passNoteEl.textContent = "";
    if (state.mode === "spotlight" && queue().length) startTimer();
    else stopTimer();
    renderPlay();
  }

  function action(text, className, onClick) {
    const button = el("button", { type: "button", class: className, text: text });
    button.addEventListener("click", onClick);
    return button;
  }

  function renderPlay() {
    const count = present().length;
    attendanceEl.textContent = ice.attendanceLine(count, ice.SEAT_COUNT);
    modeHelpEl.textContent = MODE_HELP[state.mode];
    renderChips();
    if (state.mode === "pairs") renderPairs();
    else renderSpotlight(state.mode === "one-word");
  }

  startBtn.addEventListener("click", function () {
    if (!present().length) return;
    if (startBtn.dataset.action === "return") {
      show("play");
      return;
    }
    beginRound();
    show("play");
  });

  startOverBtn.addEventListener("click", function () {
    beginRound();
    show("play");
  });

  backBtn.addEventListener("click", function () {
    stopTimer();
    show("roster");
  });

  document.querySelectorAll(".modes button").forEach(function (button) {
    button.addEventListener("click", function () {
      setMode(button.getAttribute("data-mode"));
    });
  });

  document.addEventListener("keydown", function (event) {
    if (state.screen !== "play") return;
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
    if (event.key === "n" || event.key === "N") {
      if (state.mode !== "pairs") advance();
    }
  });

  buildRoster();
  show("roster");
})();
