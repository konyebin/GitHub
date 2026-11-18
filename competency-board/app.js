(function () {
  "use strict";

  const C = window.BoardCore;
  const STORAGE_KEY = "se-competency-board:v1";
  const THEME_KEY = "se-competency-board:theme";
  const DRAG_THRESHOLD = 5;

  const $ = (sel) => document.querySelector(sel);
  const boardEl = $("#board");
  const titleInput = $("#board-title");
  const statsEl = $("#board-stats");
  const searchInput = $("#search");
  const undoBtn = $("#undo");
  const redoBtn = $("#redo");
  const toastEl = $("#toast");

  const history = C.createHistory(100);
  let state = loadState();
  let query = "";
  let drag = null;
  let pendingFocus = null;
  let toastTimer = null;
  let activeMenu = null;

  /* ---------- persistence ---------- */

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return C.normalize(JSON.parse(raw));
    } catch (err) {
      console.warn("Could not restore saved board; starting fresh.", err);
    }
    return C.templates.ciscoSE();
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (err) {
      showToast("Browser storage is unavailable; use Export to keep your work.");
    }
  }

  // Every user-visible change goes through here so undo/redo, saving and rendering stay in lockstep.
  function commit(mutate, opts) {
    const before = JSON.stringify(state);
    mutate(state);
    if (JSON.stringify(state) === before) {
      render();
      return false;
    }
    history.record(before);
    persist();
    render();
    if (opts && opts.toast) showToast(opts.toast, true);
    return true;
  }

  function undo() {
    const prev = history.undo(JSON.stringify(state));
    if (prev == null) return;
    state = JSON.parse(prev);
    persist();
    render();
  }

  function redo() {
    const next = history.redo(JSON.stringify(state));
    if (next == null) return;
    state = JSON.parse(next);
    persist();
    render();
  }

  /* ---------- tiny DOM helpers ---------- */

  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value == null || value === false) continue;
      if (key === "class") el.className = value;
      else if (key === "dataset") Object.assign(el.dataset, value);
      else if (key.startsWith("on")) el.addEventListener(key.slice(2).toLowerCase(), value);
      else el.setAttribute(key, value === true ? "" : value);
    }
    for (const kid of kids.flat()) {
      if (kid == null || kid === false) continue;
      el.append(kid.nodeType ? kid : document.createTextNode(kid));
    }
    return el;
  }

  const ICONS = {
    edit: "M3 17.25V21h3.75L17.8 9.94l-3.75-3.75L3 17.25ZM20.7 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83Z",
    trash: "M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12ZM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4Z",
    more: "M6 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm6 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm6 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z",
  };

  function iconButton(icon, label, onClick, extraClass) {
    const btn = h("button", { class: "icon-btn " + (extraClass || ""), type: "button", title: label, "aria-label": label });
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", ICONS[icon]);
    svg.append(path);
    btn.append(svg);
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      onClick(btn, e);
    });
    return btn;
  }

  function tagHue(tag) {
    let hash = 0;
    for (const ch of tag.toLowerCase()) hash = (hash * 31 + ch.charCodeAt(0)) % 360;
    return hash;
  }

  /* ---------- rendering ---------- */

  function render() {
    if (document.activeElement !== titleInput) titleInput.value = state.title;
    document.title = state.title + " | Competency Board";

    boardEl.replaceChildren(...state.columns.map(renderColumn), renderAddColumn());

    const items = C.countItems(state);
    statsEl.textContent =
      state.columns.length + (state.columns.length === 1 ? " column" : " columns") + " \u00b7 " + items + (items === 1 ? " item" : " items");
    undoBtn.disabled = !history.canUndo();
    redoBtn.disabled = !history.canRedo();
    applyFilter();

    if (pendingFocus) {
      const target = pendingFocus;
      pendingFocus = null;
      const el = typeof target === "function" ? target() : null;
      if (el) {
        el.focus({ preventScroll: true });
        el.scrollIntoView({ block: "nearest", inline: "nearest" });
      }
    }
  }

  function renderColumn(column) {
    const el = h("section", { class: "column", role: "listitem", dataset: { id: column.id }, "aria-label": column.title });
    el.style.setProperty("--col-color", column.color);

    const titleField = h("input", {
      class: "col-title",
      value: column.title,
      maxlength: C.LIMITS.columnTitle,
      "aria-label": "Column title",
      spellcheck: "false",
    });
    titleField.addEventListener("keydown", (e) => {
      if (e.key === "Enter") titleField.blur();
      if (e.key === "Escape") {
        titleField.value = column.title;
        titleField.blur();
      }
    });
    titleField.addEventListener("change", () => {
      const value = titleField.value.trim();
      if (!value) titleField.value = column.title;
      else commit((s) => C.updateColumn(s, column.id, { title: value }));
    });

    const header = h(
      "div",
      { class: "col-header" },
      h("span", { class: "grip", "aria-hidden": "true", title: "Drag to reorder column" }),
      h("div", { class: "col-head-main" }, titleField, column.description && h("p", { class: "col-desc" }, column.description)),
      h("span", { class: "count", title: column.items.length + " items" }, String(column.items.length)),
      iconButton("more", "Column options", (btn) => openColumnMenu(btn, column.id))
    );
    header.addEventListener("pointerdown", (e) => onPointerDown(e, "column", el, column.id));

    const list = h("div", { class: "cards", role: "list", "aria-label": column.title + " items" }, column.items.map((item) => renderCard(item)));

    const input = h("textarea", {
      rows: "1",
      placeholder: "Add item\u2026",
      maxlength: "2000",
      "aria-label": "Add item to " + column.title,
    });
    const submit = () => {
      const titles = C.parseBulk(input.value);
      if (!titles.length) return;
      pendingFocus = () => boardEl.querySelector('.column[data-id="' + column.id + '"] .add-item textarea');
      commit((s) => titles.forEach((title) => C.addItem(s, column.id, { title })));
      const added = list.lastElementChild;
      if (added) added.scrollIntoView({ block: "nearest" });
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        submit();
      }
    });
    input.addEventListener("input", () => autosize(input));
    const addBtn = h("button", { class: "btn", type: "button", title: "Add item", "aria-label": "Add item" }, "+");
    addBtn.addEventListener("click", submit);

    el.append(header, list, h("div", { class: "add-item" }, input, addBtn));
    return el;
  }

  function autosize(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 140) + "px";
  }

  function renderCard(item) {
    const el = h(
      "article",
      { class: "card", role: "listitem", tabindex: "0", dataset: { id: item.id }, "aria-label": item.title },
      h("span", { class: "grip", "aria-hidden": "true", title: "Drag to move" }),
      h(
        "div",
        { class: "card-body" },
        h("div", { class: "card-title" }, item.title),
        item.note && h("div", { class: "card-note" }, item.note),
        item.tag && h("span", { class: "tag", style: "--tag-hue:" + tagHue(item.tag) }, item.tag)
      ),
      h(
        "div",
        { class: "card-actions" },
        iconButton("edit", "Edit item", () => openItemDialog(item.id)),
        iconButton("trash", "Delete item", () => removeItem(item.id), "danger")
      )
    );
    el.addEventListener("pointerdown", (e) => onPointerDown(e, "card", el, item.id));
    el.addEventListener("dblclick", (e) => {
      if (!e.target.closest("button")) openItemDialog(item.id);
    });
    el.addEventListener("keydown", (e) => onCardKey(e, item.id));
    return el;
  }

  function renderAddColumn() {
    const input = h("input", { type: "text", placeholder: "Add column\u2026", maxlength: C.LIMITS.columnTitle, "aria-label": "New column title" });
    const submit = () => {
      const title = input.value.trim();
      if (!title) return;
      pendingFocus = () => {
        const field = boardEl.querySelector(".add-column input");
        boardEl.scrollLeft = boardEl.scrollWidth;
        return field;
      };
      const color = C.PALETTE[state.columns.length % C.PALETTE.length];
      commit((s) => C.addColumn(s, { title, color }));
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") submit();
    });
    const btn = h("button", { class: "btn primary", type: "button" }, "Add");
    btn.addEventListener("click", submit);
    return h("div", { class: "add-column" }, input, btn);
  }

  function applyFilter() {
    const q = query.trim().toLowerCase();
    for (const card of boardEl.querySelectorAll(".card")) {
      if (!q) {
        card.classList.remove("filtered-out", "match");
        continue;
      }
      const found = C.findItem(state, card.dataset.id);
      const text = found ? (found.item.title + " " + found.item.note + " " + found.item.tag).toLowerCase() : "";
      const hit = text.includes(q);
      card.classList.toggle("filtered-out", !hit);
      card.classList.toggle("match", hit);
    }
  }

  /* ---------- actions ---------- */

  function removeItem(itemId) {
    const found = C.findItem(state, itemId);
    if (!found) return;
    commit((s) => C.deleteItem(s, itemId), { toast: "Deleted \u201c" + found.item.title + "\u201d" });
  }

  function removeColumn(columnId) {
    const column = C.findColumn(state, columnId);
    if (!column) return;
    const n = column.items.length;
    if (n && !window.confirm('Delete column "' + column.title + '" and its ' + n + (n === 1 ? " item?" : " items?") + " You can undo this.")) return;
    commit((s) => C.deleteColumn(s, columnId), { toast: "Deleted column \u201c" + column.title + "\u201d" });
  }

  function openColumnMenu(anchor, columnId) {
    const index = state.columns.findIndex((c) => c.id === columnId);
    openMenu(anchor, [
      { label: "Edit title, description & color\u2026", action: () => openColumnDialog(columnId) },
      { label: "Move left", disabled: index === 0, action: () => commit((s) => C.moveColumn(s, columnId, index - 1)) },
      { label: "Move right", disabled: index === state.columns.length - 1, action: () => commit((s) => C.moveColumn(s, columnId, index + 1)) },
      { label: "Duplicate column", action: () => commit((s) => C.duplicateColumn(s, columnId)) },
      "-",
      {
        label: "Clear all items",
        danger: true,
        action: () => commit((s) => C.clearColumn(s, columnId), { toast: "Cleared column" }),
      },
      { label: "Delete column", danger: true, action: () => removeColumn(columnId) },
    ]);
  }

  /* ---------- menus ---------- */

  function closeMenu() {
    if (!activeMenu) return;
    activeMenu.menu.remove();
    const { anchor } = activeMenu;
    activeMenu = null;
    if (anchor && anchor.isConnected) anchor.focus({ preventScroll: true });
  }

  function openMenu(anchor, entries) {
    closeMenu();
    const menu = h(
      "div",
      { class: "menu", role: "menu" },
      entries.map((entry) =>
        entry === "-"
          ? h("hr")
          : h(
              "button",
              {
                class: "menu-item" + (entry.danger ? " danger" : ""),
                type: "button",
                role: "menuitem",
                disabled: entry.disabled,
                onClick: () => {
                  activeMenu.anchor = null;
                  closeMenu();
                  entry.action();
                },
              },
              entry.label
            )
      )
    );
    document.body.append(menu);
    const a = anchor.getBoundingClientRect();
    const m = menu.getBoundingClientRect();
    menu.style.left = Math.max(8, Math.min(a.left, window.innerWidth - m.width - 8)) + "px";
    menu.style.top = Math.max(8, Math.min(a.bottom + 4, window.innerHeight - m.height - 8)) + "px";
    activeMenu = { menu, anchor };
    const first = menu.querySelector("button:not(:disabled)");
    if (first) first.focus();
  }

  document.addEventListener("pointerdown", (e) => {
    if (activeMenu && !activeMenu.menu.contains(e.target)) {
      activeMenu.anchor = null;
      closeMenu();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (!activeMenu) return;
    const buttons = [...activeMenu.menu.querySelectorAll("button:not(:disabled)")];
    const i = buttons.indexOf(document.activeElement);
    if (e.key === "Escape") {
      e.preventDefault();
      closeMenu();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      buttons[(i + 1) % buttons.length].focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      buttons[(i - 1 + buttons.length) % buttons.length].focus();
    }
  });

  /* ---------- dialogs ---------- */

  function wireDialog(dialog) {
    dialog.addEventListener("click", (e) => {
      if (e.target === dialog) dialog.close();
      if (e.target.closest("[data-close]")) dialog.close();
    });
  }
  const itemDialog = $("#item-dialog");
  const columnDialog = $("#column-dialog");
  const helpDialog = $("#help-dialog");
  [itemDialog, columnDialog, helpDialog].forEach(wireDialog);

  let editingItemId = null;
  const itemForm = $("#item-form");

  function openItemDialog(itemId) {
    const found = C.findItem(state, itemId);
    if (!found) return;
    editingItemId = itemId;
    itemForm.elements.title.value = found.item.title;
    itemForm.note.value = found.item.note;
    itemForm.tag.value = found.item.tag;
    $("#tag-list").replaceChildren(...C.allTags(state).map((t) => h("option", { value: t })));
    itemForm.column.replaceChildren(
      ...state.columns.map((c) => h("option", { value: c.id, selected: c.id === found.column.id }, c.title))
    );
    itemDialog.showModal();
    itemForm.elements.title.select();
  }

  itemForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const id = editingItemId;
    const fields = { title: itemForm.elements.title.value, note: itemForm.note.value, tag: itemForm.tag.value };
    const destId = itemForm.column.value;
    itemDialog.close();
    pendingFocus = () => boardEl.querySelector('.card[data-id="' + id + '"]');
    commit((s) => {
      C.updateItem(s, id, fields);
      const found = C.findItem(s, id);
      if (found && found.column.id !== destId) C.moveItem(s, id, destId, Number.MAX_SAFE_INTEGER);
    });
  });

  $("#item-delete").addEventListener("click", () => {
    const id = editingItemId;
    itemDialog.close();
    removeItem(id);
  });

  let editingColumnId = null;
  let chosenColor = C.PALETTE[0];
  const columnForm = $("#column-form");
  const swatchesEl = $("#swatches");

  function renderSwatches() {
    const custom = h("input", { type: "color", value: chosenColor, "aria-label": "Custom color", title: "Custom color" });
    custom.addEventListener("input", () => {
      chosenColor = custom.value;
      renderSwatches();
    });
    swatchesEl.replaceChildren(
      ...C.PALETTE.map((color) => {
        const btn = h("button", {
          type: "button",
          class: "swatch",
          role: "radio",
          "aria-checked": String(color === chosenColor),
          "aria-label": color,
          title: color,
        });
        btn.style.setProperty("--swatch", color);
        btn.addEventListener("click", () => {
          chosenColor = color;
          renderSwatches();
        });
        return btn;
      }),
      custom
    );
  }

  function openColumnDialog(columnId) {
    const column = C.findColumn(state, columnId);
    if (!column) return;
    editingColumnId = columnId;
    chosenColor = column.color;
    columnForm.elements.title.value = column.title;
    columnForm.description.value = column.description;
    renderSwatches();
    columnDialog.showModal();
    columnForm.elements.title.select();
  }

  columnForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const id = editingColumnId;
    const patch = { title: columnForm.elements.title.value, description: columnForm.description.value, color: chosenColor };
    columnDialog.close();
    commit((s) => C.updateColumn(s, id, patch));
  });

  /* ---------- toast ---------- */

  function showToast(message, withUndo) {
    clearTimeout(toastTimer);
    toastEl.replaceChildren(h("span", {}, message));
    if (withUndo) {
      toastEl.append(
        h("button", { type: "button", onClick: () => { hideToast(); undo(); } }, "Undo")
      );
    }
    toastEl.hidden = false;
    toastTimer = setTimeout(hideToast, 6000);
  }

  function hideToast() {
    toastEl.hidden = true;
  }

  /* ---------- drag and drop (pointer events: mouse, touch and pen) ---------- */

  function onPointerDown(e, kind, el, id) {
    if (drag) return;
    if (e.pointerType === "mouse" && e.button !== 0) return;
    if (e.target.closest("button, input, textarea, select, a")) return;
    // Touch scrolling must keep working, so touch drags start only from the grip handle.
    if (e.pointerType !== "mouse" && !e.target.closest(".grip")) return;
    e.stopPropagation();
    drag = { kind, el, id, pointerId: e.pointerId, startX: e.clientX, startY: e.clientY, x: e.clientX, y: e.clientY, active: false, raf: 0 };
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerCancel);
    window.addEventListener("keydown", onDragKey, true);
  }

  function onPointerMove(e) {
    if (!drag || e.pointerId !== drag.pointerId) return;
    drag.x = e.clientX;
    drag.y = e.clientY;
    if (!drag.active) {
      if (Math.hypot(drag.x - drag.startX, drag.y - drag.startY) < DRAG_THRESHOLD) return;
      activateDrag();
    }
    e.preventDefault();
    positionGhost();
    updatePlaceholder();
  }

  function activateDrag() {
    drag.active = true;
    const rect = drag.el.getBoundingClientRect();
    drag.offsetX = drag.startX - rect.left;
    drag.offsetY = drag.startY - rect.top;
    const ghost = drag.el.cloneNode(true);
    ghost.classList.add("ghost", drag.kind === "card" ? "card-ghost" : "column-ghost");
    ghost.removeAttribute("tabindex");
    ghost.removeAttribute("role");
    ghost.style.width = rect.width + "px";
    ghost.style.height = drag.kind === "column" ? Math.min(rect.height, 260) + "px" : "auto";
    ghost.style.overflow = "hidden";
    if (drag.kind === "column") ghost.style.setProperty("--col-color", drag.el.style.getPropertyValue("--col-color"));
    document.body.append(ghost);
    drag.ghost = ghost;
    drag.el.classList.add("dragging");
    document.body.classList.add("is-dragging");
    if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur();
    drag.raf = requestAnimationFrame(autoScrollTick);
  }

  function positionGhost() {
    const x = drag.x - drag.offsetX;
    const y = drag.y - drag.offsetY;
    drag.ghost.style.transform = "translate(" + x + "px," + y + "px) rotate(1.5deg)";
  }

  function updatePlaceholder() {
    if (drag.kind === "card") placeCard();
    else placeColumn();
  }

  function columnUnderPointer() {
    const columns = [...boardEl.querySelectorAll(":scope > .column")];
    const pad = 8;
    return columns.find((c) => {
      const r = c.getBoundingClientRect();
      return drag.x >= r.left - pad && drag.x <= r.right + pad;
    });
  }

  function placeCard() {
    const columnEl = columnUnderPointer();
    for (const c of boardEl.querySelectorAll(".column.drop-target")) if (c !== columnEl) c.classList.remove("drop-target");
    if (!columnEl) return;
    columnEl.classList.add("drop-target");
    const list = columnEl.querySelector(".cards");
    const siblings = [...list.children].filter((c) => c !== drag.el && c.classList.contains("card") && !c.classList.contains("filtered-out"));
    const before = siblings.find((c) => {
      const r = c.getBoundingClientRect();
      return drag.y < r.top + r.height / 2;
    });
    if (before) {
      if (drag.el.nextElementSibling !== before) list.insertBefore(drag.el, before);
    } else if (drag.el.parentElement !== list || list.lastElementChild !== drag.el) {
      list.append(drag.el);
    }
  }

  function placeColumn() {
    const siblings = [...boardEl.querySelectorAll(":scope > .column")].filter((c) => c !== drag.el);
    const before = siblings.find((c) => {
      const r = c.getBoundingClientRect();
      return drag.x < r.left + r.width / 2;
    });
    const anchor = before || boardEl.querySelector(":scope > .add-column");
    if (drag.el.nextElementSibling !== anchor) boardEl.insertBefore(drag.el, anchor);
  }

  function autoScrollTick() {
    if (!drag || !drag.active) return;
    const edge = 70;
    const speed = (depth) => Math.min(20, 4 + depth / 4);
    const box = boardEl.getBoundingClientRect();
    let moved = false;
    if (drag.x < box.left + edge) {
      boardEl.scrollLeft -= speed(box.left + edge - drag.x);
      moved = true;
    } else if (drag.x > box.right - edge) {
      boardEl.scrollLeft += speed(drag.x - (box.right - edge));
      moved = true;
    }
    if (drag.kind === "card") {
      const list = drag.el.parentElement;
      const r = list.getBoundingClientRect();
      if (drag.y < r.top + 40) {
        list.scrollTop -= speed(r.top + 40 - drag.y);
        moved = true;
      } else if (drag.y > r.bottom - 40) {
        list.scrollTop += speed(drag.y - (r.bottom - 40));
        moved = true;
      }
    }
    if (moved) updatePlaceholder();
    drag.raf = requestAnimationFrame(autoScrollTick);
  }

  function endDrag() {
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", onPointerUp);
    window.removeEventListener("pointercancel", onPointerCancel);
    window.removeEventListener("keydown", onDragKey, true);
    if (drag && drag.raf) cancelAnimationFrame(drag.raf);
    if (drag && drag.ghost) drag.ghost.remove();
    document.body.classList.remove("is-dragging");
    for (const c of boardEl.querySelectorAll(".drop-target")) c.classList.remove("drop-target");
  }

  function onPointerUp(e) {
    if (!drag || e.pointerId !== drag.pointerId) return;
    const finished = drag;
    // Read the placeholder's final position before the DOM is torn down.
    let apply = null;
    if (finished.active) {
      if (finished.kind === "card") {
        const list = finished.el.parentElement;
        const columnId = list.closest(".column").dataset.id;
        const index = [...list.children].filter((c) => c.classList.contains("card")).indexOf(finished.el);
        apply = (s) => C.moveItem(s, finished.id, columnId, index);
      } else {
        const index = [...boardEl.querySelectorAll(":scope > .column")].indexOf(finished.el);
        apply = (s) => C.moveColumn(s, finished.id, index);
      }
    }
    endDrag();
    drag = null;
    if (apply) {
      pendingFocus = finished.kind === "card" ? () => boardEl.querySelector('.card[data-id="' + finished.id + '"]') : null;
      commit(apply);
    }
  }

  function cancelDrag() {
    const wasActive = drag && drag.active;
    endDrag();
    drag = null;
    if (wasActive) render();
  }

  function onPointerCancel(e) {
    if (drag && e.pointerId === drag.pointerId) cancelDrag();
  }

  function onDragKey(e) {
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      cancelDrag();
    }
  }

  /* ---------- keyboard on cards ---------- */

  function onCardKey(e, itemId) {
    if (e.target !== e.currentTarget) return;
    const found = C.findItem(state, itemId);
    if (!found) return;
    const { column, index } = found;
    const colIndex = state.columns.indexOf(column);
    const focusCard = (id) => () => boardEl.querySelector('.card[data-id="' + id + '"]');

    if (e.altKey && e.key.startsWith("Arrow")) {
      e.preventDefault();
      let destCol = column;
      let destIndex = index;
      if (e.key === "ArrowUp") destIndex = index - 1;
      else if (e.key === "ArrowDown") destIndex = index + 1;
      else {
        destCol = state.columns[colIndex + (e.key === "ArrowLeft" ? -1 : 1)];
        if (!destCol) return;
        destIndex = Math.min(index, destCol.items.length);
      }
      if (destCol === column && (destIndex < 0 || destIndex >= column.items.length)) return;
      pendingFocus = focusCard(itemId);
      commit((s) => C.moveItem(s, itemId, destCol.id, destIndex));
      return;
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const cards = [...e.currentTarget.parentElement.querySelectorAll(".card:not(.filtered-out)")];
      const next = cards[cards.indexOf(e.currentTarget) + (e.key === "ArrowDown" ? 1 : -1)];
      if (next) next.focus();
    } else if (e.key === "Enter" || e.key === "F2") {
      e.preventDefault();
      openItemDialog(itemId);
    } else if (e.key === "Delete" || e.key === "Backspace") {
      e.preventDefault();
      const cards = [...e.currentTarget.parentElement.querySelectorAll(".card")];
      const neighbor = cards[cards.indexOf(e.currentTarget) + 1] || cards[cards.indexOf(e.currentTarget) - 1];
      if (neighbor) pendingFocus = focusCard(neighbor.dataset.id);
      removeItem(itemId);
    }
  }

  /* ---------- toolbar ---------- */

  titleInput.addEventListener("change", () => {
    const value = titleInput.value.trim();
    if (!value) titleInput.value = state.title;
    else commit((s) => (s.title = value.slice(0, C.LIMITS.boardTitle)));
  });
  titleInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") titleInput.blur();
  });

  searchInput.addEventListener("input", () => {
    query = searchInput.value;
    applyFilter();
  });
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      searchInput.value = "";
      query = "";
      applyFilter();
      searchInput.blur();
    }
  });

  undoBtn.addEventListener("click", undo);
  redoBtn.addEventListener("click", redo);
  $("#help").addEventListener("click", () => helpDialog.showModal());

  function applyTemplate(key, label) {
    if (C.countItems(state) && !window.confirm("Replace the current board with the \u201c" + label + "\u201d template? You can undo this.")) return;
    const fresh = C.templates[key]();
    commit((s) => {
      s.title = fresh.title;
      s.columns = fresh.columns;
    });
  }

  $("#templates-btn").addEventListener("click", (e) =>
    openMenu(e.currentTarget, [
      { label: "Cisco SE starter (Core / Nice to Have / To Sort)", action: () => applyTemplate("ciscoSE", "Cisco SE starter") },
      { label: "Blank: Core vs Nice to Have", action: () => applyTemplate("coreVsNice", "Core vs Nice to Have") },
      { label: "Empty board", action: () => applyTemplate("empty", "Empty board") },
    ])
  );

  function download(filename, text, type) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const a = h("a", { href: url, download: filename });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const fileSlug = () => (state.title || "board").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "board";

  $("#export-btn").addEventListener("click", (e) =>
    openMenu(e.currentTarget, [
      { label: "Download JSON (backup)", action: () => download(fileSlug() + ".json", JSON.stringify(state, null, 2), "application/json") },
      { label: "Download Markdown", action: () => download(fileSlug() + ".md", C.toMarkdown(state), "text/markdown") },
      {
        label: "Copy Markdown",
        action: () => {
          const md = C.toMarkdown(state);
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(md).then(
              () => showToast("Markdown copied to clipboard"),
              () => download(fileSlug() + ".md", md, "text/markdown")
            );
          } else download(fileSlug() + ".md", md, "text/markdown");
        },
      },
    ])
  );

  const importFile = $("#import-file");
  $("#import-btn").addEventListener("click", () => importFile.click());
  importFile.addEventListener("change", async () => {
    const file = importFile.files[0];
    importFile.value = "";
    if (!file) return;
    try {
      const imported = C.normalize(JSON.parse(await file.text()));
      if (C.countItems(state) && !window.confirm("Replace the current board with \u201c" + imported.title + "\u201d? You can undo this.")) return;
      commit((s) => {
        s.title = imported.title;
        s.columns = imported.columns;
      });
      showToast("Imported \u201c" + imported.title + "\u201d", true);
    } catch (err) {
      showToast("Import failed: " + err.message);
    }
  });

  /* ---------- theme ---------- */

  function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (err) {
      /* theme just won't persist */
    }
  }
  const storedTheme = (() => {
    try {
      return localStorage.getItem(THEME_KEY);
    } catch (err) {
      return null;
    }
  })();
  setTheme(storedTheme || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  $("#theme").addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));

  /* ---------- global shortcuts ---------- */

  document.addEventListener("keydown", (e) => {
    const typing = e.target.closest && e.target.closest("input, textarea, select, [contenteditable]");
    const mod = e.ctrlKey || e.metaKey;
    if (mod && !typing && e.key.toLowerCase() === "z") {
      e.preventDefault();
      if (e.shiftKey) redo();
      else undo();
    } else if (mod && !typing && e.key.toLowerCase() === "y") {
      e.preventDefault();
      redo();
    } else if (!typing && !mod && e.key === "/") {
      e.preventDefault();
      searchInput.focus();
    } else if (!typing && !mod && e.key === "?") {
      e.preventDefault();
      helpDialog.showModal();
    }
  });

  window.addEventListener("storage", (e) => {
    if (e.key === STORAGE_KEY && !drag) {
      try {
        state = C.normalize(JSON.parse(e.newValue));
        render();
      } catch (err) {
        /* ignore malformed external writes */
      }
    }
  });

  persist();
  render();
})();
