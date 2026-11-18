"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const C = require("../core.js");

function board() {
  const s = C.makeBoard("T", [
    { title: "A", items: [{ title: "a1" }, { title: "a2" }, { title: "a3" }] },
    { title: "B", items: [{ title: "b1" }] },
    { title: "C" },
  ]);
  return s;
}
const titles = (col) => col.items.map((i) => i.title);
const id = (s, colIdx, itemIdx) => s.columns[colIdx].items[itemIdx].id;

test("makeBoard trims, defaults and drops empty items", () => {
  const s = C.makeBoard("  ", [{ title: "  ", color: "nope", items: [{ title: " " }, { title: " x " }] }]);
  assert.equal(s.title, "Untitled board");
  assert.equal(s.columns[0].title, "Untitled");
  assert.equal(s.columns[0].color, C.PALETTE[0]);
  assert.deepEqual(titles(s.columns[0]), ["x"]);
});

test("addColumn appends or inserts at an index", () => {
  const s = board();
  C.addColumn(s, { title: "D" });
  C.addColumn(s, { title: "Z" }, 0);
  assert.deepEqual(s.columns.map((c) => c.title), ["Z", "A", "B", "C", "D"]);
});

test("updateColumn validates color and keeps title when blank", () => {
  const s = board();
  const col = s.columns[0];
  C.updateColumn(s, col.id, { title: "  ", color: "red", description: "d" });
  assert.equal(col.title, "A");
  assert.equal(col.color, C.PALETTE[0]);
  assert.equal(col.description, "d");
  C.updateColumn(s, col.id, { title: "New", color: "#ABCDEF" });
  assert.equal(col.title, "New");
  assert.equal(col.color, "#abcdef");
});

test("moveColumn uses post-removal index and reports no-ops", () => {
  const s = board();
  const [a, b, c] = s.columns.map((x) => x.id);
  assert.equal(C.moveColumn(s, a, 2), true);
  assert.deepEqual(s.columns.map((x) => x.id), [b, c, a]);
  assert.equal(C.moveColumn(s, a, 2), false);
  assert.equal(C.moveColumn(s, a, -5), true);
  assert.deepEqual(s.columns.map((x) => x.id), [a, b, c]);
  assert.equal(C.moveColumn(s, "missing", 0), false);
});

test("duplicateColumn copies items with fresh ids", () => {
  const s = board();
  const copy = C.duplicateColumn(s, s.columns[0].id);
  assert.equal(s.columns[1], copy);
  assert.deepEqual(titles(copy), ["a1", "a2", "a3"]);
  const ids = new Set(s.columns.flatMap((c) => c.items.map((i) => i.id)));
  assert.equal(ids.size, 7);
});

test("deleteColumn and clearColumn", () => {
  const s = board();
  assert.equal(C.clearColumn(s, s.columns[0].id), true);
  assert.equal(s.columns[0].items.length, 0);
  assert.equal(C.deleteColumn(s, s.columns[1].id).title, "B");
  assert.equal(s.columns.length, 2);
  assert.equal(C.deleteColumn(s, "nope"), null);
});

test("addItem rejects blank titles and unknown columns", () => {
  const s = board();
  assert.equal(C.addItem(s, s.columns[2].id, { title: "  " }), null);
  assert.equal(C.addItem(s, "nope", { title: "x" }), null);
  const item = C.addItem(s, s.columns[2].id, { title: "c1", tag: "t", note: "n" });
  assert.deepEqual(titles(s.columns[2]), ["c1"]);
  assert.equal(item.tag, "t");
  C.addItem(s, s.columns[2].id, { title: "first" }, 0);
  assert.deepEqual(titles(s.columns[2]), ["first", "c1"]);
});

test("updateItem and deleteItem", () => {
  const s = board();
  const itemId = id(s, 0, 0);
  C.updateItem(s, itemId, { title: "renamed", note: "n", tag: "x" });
  assert.deepEqual(C.findItem(s, itemId).item, { id: itemId, title: "renamed", note: "n", tag: "x" });
  C.updateItem(s, itemId, { title: "" });
  assert.equal(C.findItem(s, itemId).item.title, "renamed");
  assert.equal(C.deleteItem(s, itemId).title, "renamed");
  assert.equal(C.findItem(s, itemId), null);
  assert.equal(C.deleteItem(s, itemId), null);
});

test("moveItem within a column reorders using post-removal index", () => {
  const s = board();
  assert.equal(C.moveItem(s, id(s, 0, 0), s.columns[0].id, 2), true);
  assert.deepEqual(titles(s.columns[0]), ["a2", "a3", "a1"]);
  assert.equal(C.moveItem(s, id(s, 0, 2), s.columns[0].id, 2), false);
  assert.deepEqual(titles(s.columns[0]), ["a2", "a3", "a1"]);
  assert.equal(C.moveItem(s, id(s, 0, 2), s.columns[0].id, 0), true);
  assert.deepEqual(titles(s.columns[0]), ["a1", "a2", "a3"]);
});

test("moveItem across columns, including into an empty column and past the end", () => {
  const s = board();
  assert.equal(C.moveItem(s, id(s, 0, 1), s.columns[2].id, 0), true);
  assert.deepEqual(titles(s.columns[2]), ["a2"]);
  assert.deepEqual(titles(s.columns[0]), ["a1", "a3"]);
  assert.equal(C.moveItem(s, id(s, 0, 0), s.columns[1].id, 99), true);
  assert.deepEqual(titles(s.columns[1]), ["b1", "a1"]);
  assert.equal(C.moveItem(s, "missing", s.columns[1].id, 0), false);
  assert.equal(C.moveItem(s, id(s, 1, 0), "missing", 0), false);
  assert.equal(C.countItems(s), 4);
});

test("parseBulk strips list markers and blank lines", () => {
  const text = "- one\n* two\n\n  3. three\n4) four\n\u2022 five\nsix";
  assert.deepEqual(C.parseBulk(text), ["one", "two", "three", "four", "five", "six"]);
  assert.deepEqual(C.parseBulk("  \n "), []);
  assert.deepEqual(C.parseBulk("2024 roadmap"), ["2024 roadmap"]);
});

test("allTags is unique and sorted", () => {
  const s = board();
  C.updateItem(s, id(s, 0, 0), { tag: "b" });
  C.updateItem(s, id(s, 0, 1), { tag: "a" });
  C.updateItem(s, id(s, 0, 2), { tag: "b" });
  assert.deepEqual(C.allTags(s), ["a", "b"]);
});

test("toMarkdown renders columns, tags, notes and empty columns", () => {
  const s = board();
  C.updateItem(s, id(s, 0, 0), { tag: "Net", note: "line1\nline2" });
  C.updateColumn(s, s.columns[0].id, { description: "desc" });
  const md = C.toMarkdown(s);
  assert.match(md, /^# T\n/);
  assert.match(md, /## A \(3\)\n_desc_\n/);
  assert.match(md, /- \*\*a1\*\* `Net` \u2014 line1 line2/);
  assert.match(md, /## C \(0\)\n\n- \(none\)/);
});

test("normalize rejects junk and sanitizes imported data", () => {
  assert.throws(() => C.normalize(null));
  assert.throws(() => C.normalize({ columns: "x" }));
  const clean = C.normalize({
    title: "  Imported ",
    columns: [
      { id: "dup", title: "A", color: "javascript:alert(1)", items: [{ id: "x", title: "t1" }, { id: "x", title: "t2" }, { title: "" }, null] },
      { id: "dup", title: "B", items: "oops" },
      "bad",
    ],
  });
  assert.equal(clean.title, "Imported");
  assert.equal(clean.columns.length, 2);
  assert.equal(clean.columns[0].color, C.PALETTE[0]);
  assert.equal(new Set(clean.columns.map((c) => c.id)).size, 2);
  const itemIds = clean.columns[0].items.map((i) => i.id);
  assert.equal(itemIds.length, 2);
  assert.notEqual(itemIds[0], itemIds[1]);
  assert.deepEqual(clean.columns[1].items, []);
});

test("normalize round-trips a real board", () => {
  const s = C.templates.ciscoSE();
  assert.deepEqual(C.normalize(JSON.parse(JSON.stringify(s))), s);
});

test("history undo/redo with limit and redo invalidation", () => {
  const h = C.createHistory(2);
  assert.equal(h.undo("x"), null);
  h.record("s1");
  h.record("s2");
  h.record("s3");
  assert.equal(h.undo("s4"), "s3");
  assert.equal(h.undo("s3"), "s2");
  assert.equal(h.undo("s2"), null);
  assert.equal(h.redo("s2"), "s3");
  assert.equal(h.canRedo(), true);
  h.record("s5");
  assert.equal(h.canRedo(), false);
});

test("starter templates are valid and the SE template has core, nice-to-have and a pool", () => {
  for (const make of Object.values(C.templates)) C.normalize(make());
  const se = C.templates.ciscoSE();
  assert.deepEqual(se.columns.map((c) => c.title), ["Core Competencies", "Nice to Have", "To Sort"]);
  assert.ok(C.countItems(se) > 20);
  const ids = se.columns.flatMap((c) => [c.id, ...c.items.map((i) => i.id)]);
  assert.equal(new Set(ids).size, ids.length);
});
