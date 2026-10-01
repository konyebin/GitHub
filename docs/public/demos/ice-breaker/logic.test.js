import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const sandbox = { crypto: globalThis.crypto, Uint32Array };
vm.createContext(sandbox);
vm.runInContext(readFileSync(new URL("./logic.js", import.meta.url), "utf8"), sandbox);
const ice = sandbox.IceLogic;

function rng(seed) {
  let state = seed >>> 0;
  return function () {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

test("empty names fall back to seat numbers and control characters are stripped", function () {
  assert.equal(ice.displayName("  ", 0), "Person 1");
  assert.equal(ice.displayName("Sam\n", 2), "Sam");
  assert.equal(ice.sanitizeName("x".repeat(80)).length, 40);
});

test("duplicate names stay distinguishable", function () {
  const seats = [
    { name: "Sam", here: true },
    { name: "Sam", here: true },
  ];
  assert.equal(ice.uniqueLabel(seats, 0), "Sam (seat 1)");
  assert.equal(ice.uniqueLabel(seats, 1), "Sam (seat 2)");
});

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

test("groups never leave a person alone when someone else is here", function () {
  assert.deepEqual(plain(ice.makeGroups([])), []);
  assert.deepEqual(plain(ice.makeGroups([0])), [[0]]);
  assert.deepEqual(plain(ice.makeGroups([0, 1])), [[0, 1]]);
  assert.deepEqual(plain(ice.makeGroups([0, 1, 2])), [[0, 1, 2]]);
  assert.deepEqual(plain(ice.makeGroups([0, 1, 2, 3])), [
    [0, 1],
    [2, 3],
  ]);
  const five = plain(ice.makeGroups([0, 1, 2, 3, 4]));
  assert.equal(five.length, 2);
  assert.equal(five[0].length, 2);
  assert.equal(five[1].length, 3);
  assert.equal(new Set(five.flat()).size, 5);
});

test("late joins are appended and people who left drop out of the order", function () {
  assert.deepEqual(ice.syncOrder([0, 1, 2], [0, 2, 4]), [0, 2, 4]);
  assert.deepEqual(ice.remaining([0, 1, 2, 4], [0], [0, 2, 4]), [2, 4]);
});

test("pass sends the current person to the end unless they are the only one left", function () {
  assert.deepEqual(ice.passTurn([0, 1, 2], 0, 3), [1, 2, 0]);
  assert.deepEqual(ice.passTurn([2], 2, 1), [2]);
});

test("a new prompt is different from the one on screen", function () {
  const random = rng(7);
  for (let i = 0; i < 20; i += 1) {
    assert.notEqual(ice.pickPrompt(5, 2, random), 2);
  }
  assert.equal(ice.pickPrompt(1, 0, random), 0);
});

test("attendance copy matches whoever is actually here", function () {
  assert.equal(ice.attendanceLine(0, 5), "Nobody is checked in.");
  assert.equal(ice.attendanceLine(1, 5), "1 of 5 is on the call. 4 people sit this one out.");
  assert.equal(ice.attendanceLine(3, 5), "3 of 5 are on the call. 2 people sit this one out.");
  assert.equal(ice.attendanceLine(4, 5), "4 of 5 are on the call. 1 person sits this one out.");
  assert.equal(ice.attendanceLine(5, 5), "All 5 are on the call.");
});

test("saved roster must be five seats", function () {
  const fresh = ice.loadSeats(null);
  assert.equal(fresh.length, 5);
  assert.equal(fresh.every(function (seat) { return seat.here; }), true);
  const loaded = ice.loadSeats({
    seats: [
      { name: "A\n", here: false },
      { name: "B", here: true },
      { name: "C", here: 1 },
      { name: "D", here: 0 },
      { name: "E", here: true },
    ],
  });
  assert.equal(loaded[0].name, "A");
  assert.equal(loaded[0].here, false);
  assert.equal(loaded[3].here, false);
  assert.equal(ice.loadSeats({ seats: [{ name: "only one" }] }).length, 5);
});

test("prompts that need a second person drop out for a solo call", function () {
  const prompts = [
    { text: "solo", min: 1 },
    { text: "needs two", min: 2 },
  ];
  assert.deepEqual(
    ice.usablePrompts(prompts, 1).map(function (prompt) { return prompt.text; }),
    ["solo"]
  );
  assert.equal(ice.usablePrompts(prompts, 3).length, 2);
});
