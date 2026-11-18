/*
 * Pure board state logic: no DOM access, so it runs in the browser and under `node --test`.
 * All mutators change the passed-in state in place; the UI snapshots state around them for undo.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.BoardCore = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const SCHEMA_VERSION = 1;
  const LIMITS = { title: 200, note: 2000, tag: 40, columnTitle: 80, description: 240, boardTitle: 120 };

  const PALETTE = [
    "#049fd9", // blue
    "#2ea36b", // green
    "#e8a317", // amber
    "#ef7b2b", // orange
    "#d6455d", // red
    "#7a5af8", // purple
    "#14a8a0", // teal
    "#667085", // slate
  ];
  const COLOR_RE = /^#[0-9a-f]{6}$/i;

  let counter = 0;
  function uid(prefix) {
    counter += 1;
    return (
      (prefix || "id") + "_" + Date.now().toString(36) + counter.toString(36) + Math.random().toString(36).slice(2, 7)
    );
  }

  function clip(value, max) {
    return String(value == null ? "" : value).trim().slice(0, max);
  }

  function clamp(n, lo, hi) {
    return Math.max(lo, Math.min(hi, n));
  }

  function makeItem(fields) {
    return {
      id: uid("i"),
      title: clip(fields.title, LIMITS.title),
      note: clip(fields.note, LIMITS.note),
      tag: clip(fields.tag, LIMITS.tag),
    };
  }

  function makeColumn(fields) {
    return {
      id: uid("c"),
      title: clip(fields.title, LIMITS.columnTitle) || "Untitled",
      description: clip(fields.description, LIMITS.description),
      color: COLOR_RE.test(fields.color || "") ? fields.color.toLowerCase() : PALETTE[0],
      items: (fields.items || []).map(makeItem).filter((i) => i.title),
    };
  }

  function makeBoard(title, columns) {
    return { version: SCHEMA_VERSION, title: clip(title, LIMITS.boardTitle) || "Untitled board", columns: columns.map(makeColumn) };
  }

  /* ---------- lookups ---------- */

  function findColumn(state, columnId) {
    return state.columns.find((c) => c.id === columnId) || null;
  }

  function findItem(state, itemId) {
    for (const column of state.columns) {
      const index = column.items.findIndex((i) => i.id === itemId);
      if (index !== -1) return { column, index, item: column.items[index] };
    }
    return null;
  }

  function allTags(state) {
    const tags = new Set();
    for (const column of state.columns) for (const item of column.items) if (item.tag) tags.add(item.tag);
    return [...tags].sort((a, b) => a.localeCompare(b));
  }

  function countItems(state) {
    return state.columns.reduce((n, c) => n + c.items.length, 0);
  }

  /* ---------- columns ---------- */

  function addColumn(state, fields, index) {
    const column = makeColumn(fields);
    const at = index == null ? state.columns.length : clamp(index, 0, state.columns.length);
    state.columns.splice(at, 0, column);
    return column;
  }

  function updateColumn(state, columnId, patch) {
    const column = findColumn(state, columnId);
    if (!column) return false;
    if ("title" in patch) column.title = clip(patch.title, LIMITS.columnTitle) || column.title;
    if ("description" in patch) column.description = clip(patch.description, LIMITS.description);
    if ("color" in patch && COLOR_RE.test(patch.color)) column.color = patch.color.toLowerCase();
    return true;
  }

  function deleteColumn(state, columnId) {
    const index = state.columns.findIndex((c) => c.id === columnId);
    if (index === -1) return null;
    return state.columns.splice(index, 1)[0];
  }

  // toIndex is the position in the column list once the column has been lifted out.
  function moveColumn(state, columnId, toIndex) {
    const from = state.columns.findIndex((c) => c.id === columnId);
    if (from === -1) return false;
    const [column] = state.columns.splice(from, 1);
    const to = clamp(toIndex, 0, state.columns.length);
    state.columns.splice(to, 0, column);
    return from !== to;
  }

  function duplicateColumn(state, columnId) {
    const index = state.columns.findIndex((c) => c.id === columnId);
    if (index === -1) return null;
    const source = state.columns[index];
    const copy = makeColumn({
      title: source.title + " (copy)",
      description: source.description,
      color: source.color,
      items: source.items,
    });
    state.columns.splice(index + 1, 0, copy);
    return copy;
  }

  function clearColumn(state, columnId) {
    const column = findColumn(state, columnId);
    if (!column) return false;
    column.items = [];
    return true;
  }

  /* ---------- items ---------- */

  function addItem(state, columnId, fields, index) {
    const column = findColumn(state, columnId);
    if (!column) return null;
    const item = makeItem(fields);
    if (!item.title) return null;
    const at = index == null ? column.items.length : clamp(index, 0, column.items.length);
    column.items.splice(at, 0, item);
    return item;
  }

  function updateItem(state, itemId, patch) {
    const found = findItem(state, itemId);
    if (!found) return false;
    const { item } = found;
    if ("title" in patch) item.title = clip(patch.title, LIMITS.title) || item.title;
    if ("note" in patch) item.note = clip(patch.note, LIMITS.note);
    if ("tag" in patch) item.tag = clip(patch.tag, LIMITS.tag);
    return true;
  }

  function deleteItem(state, itemId) {
    const found = findItem(state, itemId);
    if (!found) return null;
    return found.column.items.splice(found.index, 1)[0];
  }

  // toIndex is the position in the destination list once the item has been lifted out,
  // which is what the UI computes from the placeholder's position among its sibling cards.
  function moveItem(state, itemId, toColumnId, toIndex) {
    const found = findItem(state, itemId);
    const dest = findColumn(state, toColumnId);
    if (!found || !dest) return false;
    const [item] = found.column.items.splice(found.index, 1);
    const to = clamp(toIndex, 0, dest.items.length);
    dest.items.splice(to, 0, item);
    return !(found.column === dest && found.index === to);
  }

  /* ---------- text helpers ---------- */

  // One item per non-empty line; strips list markers so pasted bullets/numbering come through clean.
  function parseBulk(text) {
    return String(text || "")
      .split(/\r?\n/)
      .map((line) => line.replace(/^\s*(?:[-*\u2022]|\d+[.)])\s+/, "").trim())
      .filter(Boolean);
  }

  function toMarkdown(state) {
    const out = ["# " + state.title, ""];
    for (const column of state.columns) {
      out.push("## " + column.title + " (" + column.items.length + ")");
      if (column.description) out.push("_" + column.description + "_");
      out.push("");
      if (!column.items.length) out.push("- (none)");
      for (const item of column.items) {
        let line = "- **" + item.title + "**";
        if (item.tag) line += " `" + item.tag + "`";
        if (item.note) line += " \u2014 " + item.note.replace(/\s*\n\s*/g, " ");
        out.push(line);
      }
      out.push("");
    }
    return out.join("\n").replace(/\n{3,}/g, "\n\n").trimEnd() + "\n";
  }

  /* ---------- import / validation ---------- */

  // Accepts untrusted JSON (file import, localStorage) and returns a clean, de-duplicated board or throws.
  function normalize(data) {
    if (!data || typeof data !== "object" || !Array.isArray(data.columns)) {
      throw new Error("Not a valid board file: expected an object with a \"columns\" array.");
    }
    const seen = new Set();
    const claim = (id, prefix) => {
      const wanted = typeof id === "string" && id && id.length <= 80 ? id : "";
      const final = wanted && !seen.has(wanted) ? wanted : uid(prefix);
      seen.add(final);
      return final;
    };
    const columns = data.columns
      .filter((c) => c && typeof c === "object")
      .map((c) => {
        const column = makeColumn({ title: c.title, description: c.description, color: c.color });
        column.id = claim(c.id, "c");
        const items = Array.isArray(c.items) ? c.items : [];
        column.items = items
          .filter((i) => i && typeof i === "object")
          .map((i) => {
            const item = makeItem(i);
            item.id = claim(i.id, "i");
            return item;
          })
          .filter((i) => i.title);
        return column;
      });
    return { version: SCHEMA_VERSION, title: clip(data.title, LIMITS.boardTitle) || "Untitled board", columns };
  }

  /* ---------- undo / redo ---------- */

  // Stores serialized snapshots so later mutation of live state can never corrupt history.
  function createHistory(limit) {
    const max = limit || 100;
    const undoStack = [];
    const redoStack = [];
    return {
      record(snapshot) {
        undoStack.push(snapshot);
        if (undoStack.length > max) undoStack.shift();
        redoStack.length = 0;
      },
      undo(current) {
        if (!undoStack.length) return null;
        redoStack.push(current);
        return undoStack.pop();
      },
      redo(current) {
        if (!redoStack.length) return null;
        undoStack.push(current);
        return redoStack.pop();
      },
      canUndo: () => undoStack.length > 0,
      canRedo: () => redoStack.length > 0,
    };
  }

  /* ---------- starter templates ---------- */

  const templates = {
    ciscoSE() {
      const sort = (title, tag, note) => ({ title, tag, note });
      return makeBoard("Cisco SE Competency Map", [
        {
          title: "Core Competencies",
          description: "Must-haves: an SE can't be effective without these",
          color: "#2ea36b",
          items: [
            sort("Discovery & requirements gathering", "Presales", "Uncover business outcomes, not just feature checklists"),
            sort("Network fundamentals (L2/L3, routing, switching)", "Networking", ""),
            sort("Solution design & architecture", "Presales", "Turn requirements into a validated design"),
            sort("Whiteboarding & technical storytelling", "Presales", ""),
            sort("Demos & proof of value", "Presales", ""),
          ],
        },
        {
          title: "Nice to Have",
          description: "Differentiators: valuable, can be learned on the job",
          color: "#e8a317",
          items: [
            sort("Python scripting", "Automation", ""),
            sort("Public cloud networking (AWS / Azure / GCP)", "Cloud", ""),
            sort("Competitive positioning", "Presales", ""),
          ],
        },
        {
          title: "To Sort",
          description: "Drag each into Core or Nice to Have",
          color: "#667085",
          items: [
            sort("SD-WAN design", "Networking", ""),
            sort("Campus automation & assurance (Catalyst Center)", "Networking", ""),
            sort("Meraki cloud-managed networking", "Networking", ""),
            sort("Data center fabrics (ACI / Nexus)", "Data Center", ""),
            sort("Secure Access / SASE", "Security", ""),
            sort("Next-gen firewall (Secure Firewall)", "Security", ""),
            sort("Zero trust & identity (Duo, ISE)", "Security", ""),
            sort("Webex Calling & collaboration", "Collaboration", ""),
            sort("Contact center", "Collaboration", ""),
            sort("Observability (ThousandEyes)", "Observability", ""),
            sort("Network automation (APIs, Ansible, Terraform)", "Automation", ""),
            sort("AI & AIOps fluency", "Emerging", ""),
            sort("Hands-on troubleshooting", "Networking", ""),
            sort("Licensing, BOM & pricing", "Presales", ""),
            sort("Objection handling & negotiation", "Presales", ""),
            sort("Executive presence", "Presales", ""),
            sort("Partner & channel collaboration", "Presales", ""),
            sort("CCNP / CCIE-level certification", "Certification", ""),
          ],
        },
      ]);
    },
    coreVsNice() {
      return makeBoard("Core vs Nice to Have", [
        { title: "Core Competencies", description: "Must-haves", color: "#2ea36b" },
        { title: "Nice to Have", description: "Differentiators", color: "#e8a317" },
      ]);
    },
    empty() {
      return makeBoard("Untitled board", []);
    },
  };

  return {
    SCHEMA_VERSION,
    LIMITS,
    PALETTE,
    COLOR_RE,
    uid,
    makeBoard,
    findColumn,
    findItem,
    allTags,
    countItems,
    addColumn,
    updateColumn,
    deleteColumn,
    moveColumn,
    duplicateColumn,
    clearColumn,
    addItem,
    updateItem,
    deleteItem,
    moveItem,
    parseBulk,
    toMarkdown,
    normalize,
    createHistory,
    templates,
  };
});
