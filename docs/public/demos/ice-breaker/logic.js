/* Team ice breaker rules. No network, no secrets — names stay in the browser. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.IceLogic = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const SEAT_COUNT = 5;
  const SPOTLIGHT_SECONDS = 45;

  function sanitizeName(value) {
    return String(value == null ? "" : value)
      .replace(/[\u0000-\u001F\u007F]/g, "")
      .slice(0, 40);
  }

  function displayName(name, index) {
    const clean = sanitizeName(name).trim();
    return clean || "Person " + (index + 1);
  }

  function uniqueLabel(seats, index) {
    const label = displayName(seats[index].name, index);
    const key = label.toLowerCase();
    const duplicate = seats.some(function (seat, other) {
      return other !== index && displayName(seat.name, other).toLowerCase() === key;
    });
    return duplicate ? label + " (seat " + (index + 1) + ")" : label;
  }

  function presentIndices(seats) {
    const indices = [];
    for (let i = 0; i < seats.length; i += 1) {
      if (seats[i].here) indices.push(i);
    }
    return indices;
  }

  function shuffle(items, random) {
    const arr = items.slice();
    for (let i = arr.length - 1; i > 0; i -= 1) {
      const j = Math.floor(random() * (i + 1));
      const tmp = arr[i];
      arr[i] = arr[j];
      arr[j] = tmp;
    }
    return arr;
  }

  function randomUnit() {
    const buf = new Uint32Array(1);
    crypto.getRandomValues(buf);
    return buf[0] / 4294967296;
  }

  function makeGroups(indices) {
    if (!indices.length) return [];
    if (indices.length === 1) return [indices.slice()];
    const groups = [];
    for (let i = 0; i < indices.length; i += 2) {
      groups.push(indices.slice(i, i + 2));
    }
    const last = groups[groups.length - 1];
    if (last.length === 1 && groups.length > 1) {
      groups[groups.length - 2].push(last[0]);
      groups.pop();
    }
    return groups;
  }

  function syncOrder(order, present) {
    const presentSet = new Set(present);
    const next = order.filter(function (index) {
      return presentSet.has(index);
    });
    for (let i = 0; i < present.length; i += 1) {
      if (next.indexOf(present[i]) === -1) next.push(present[i]);
    }
    return next;
  }

  function remaining(order, doneList, present) {
    const done = new Set(doneList);
    const presentSet = new Set(present);
    return syncOrder(order, present).filter(function (index) {
      return presentSet.has(index) && !done.has(index);
    });
  }

  function passTurn(order, index, remainingCount) {
    if (remainingCount < 2) return order.slice();
    const at = order.indexOf(index);
    if (at < 0) return order.slice();
    const next = order.slice();
    next.splice(at, 1);
    next.push(index);
    return next;
  }

  function pickPrompt(length, current, random) {
    if (length <= 1) return 0;
    let next = current;
    for (let i = 0; i < 6; i += 1) {
      next = Math.floor(random() * length);
      if (next !== current) return next;
    }
    return (current + 1) % length;
  }

  function assignGroupPrompts(groupCount, promptCount, random) {
    if (!groupCount || !promptCount) return [];
    const bag = shuffle(
      Array.from({ length: promptCount }, function (_, i) {
        return i;
      }),
      random
    );
    const assigned = [];
    for (let i = 0; i < groupCount; i += 1) {
      assigned.push(bag[i % bag.length]);
    }
    return assigned;
  }

  function attendanceLine(hereCount, total) {
    const away = total - hereCount;
    if (hereCount <= 0) return "Nobody is checked in.";
    if (hereCount === total) return "All " + total + " are on the call.";
    const verb = hereCount === 1 ? "is" : "are";
    const awayWord = away === 1 ? "person sits" : "people sit";
    return hereCount + " of " + total + " " + verb + " on the call. " + away + " " + awayWord + " this one out.";
  }

  function loadSeats(raw) {
    const blank = function () {
      const seats = [];
      for (let i = 0; i < SEAT_COUNT; i += 1) seats.push({ name: "", here: true });
      return seats;
    };
    if (!raw || !Array.isArray(raw.seats) || raw.seats.length !== SEAT_COUNT) return blank();
    return raw.seats.map(function (seat) {
      return {
        name: sanitizeName(seat && seat.name),
        here: Boolean(seat && seat.here),
      };
    });
  }

  function usablePrompts(prompts, people) {
    const count = Math.max(people, 1);
    const filtered = prompts.filter(function (prompt) {
      return (prompt.min || 1) <= count;
    });
    return filtered.length ? filtered : prompts.slice();
  }

  return {
    SEAT_COUNT: SEAT_COUNT,
    SPOTLIGHT_SECONDS: SPOTLIGHT_SECONDS,
    sanitizeName: sanitizeName,
    displayName: displayName,
    uniqueLabel: uniqueLabel,
    presentIndices: presentIndices,
    shuffle: shuffle,
    randomUnit: randomUnit,
    makeGroups: makeGroups,
    syncOrder: syncOrder,
    remaining: remaining,
    passTurn: passTurn,
    pickPrompt: pickPrompt,
    assignGroupPrompts: assignGroupPrompts,
    attendanceLine: attendanceLine,
    loadSeats: loadSeats,
    usablePrompts: usablePrompts,
  };
});
