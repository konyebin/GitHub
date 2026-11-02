/*
 * Browser end-to-end check of drag and drop, persistence, and keyboard flows.
 * Needs playwright-core and a Chrome binary:
 *   npm i --no-save playwright-core && CHROME_PATH=/path/to/chrome node tests/e2e.js
 */
"use strict";
const assert = require("node:assert/strict");
const path = require("node:path");
const { chromium } = require("playwright-core");

const URL = "file://" + path.resolve(__dirname, "..", "index.html");
const SHOTS = process.env.SHOT_DIR || "";

async function snapshot(page) {
  return page.evaluate(() => JSON.parse(localStorage.getItem("se-competency-board:v1")));
}
const titles = (board, name) => board.columns.find((c) => c.title === name).items.map((i) => i.title);
const colTitles = (board) => board.columns.map((c) => c.title);

async function dragTo(page, source, target, { dx = 0, dy = 0, steps = 12 } = {}) {
  await source.scrollIntoViewIfNeeded();
  const s = await source.boundingBox();
  const t = await target.boundingBox();
  await page.mouse.move(s.x + s.width / 2, s.y + s.height / 2);
  await page.mouse.down();
  await page.mouse.move(s.x + s.width / 2 + 8, s.y + s.height / 2 + 8, { steps: 3 });
  await page.mouse.move(t.x + t.width / 2 + dx, t.y + t.height / 2 + dy, { steps });
  await page.mouse.up();
}

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || "/usr/local/bin/google-chrome",
    args: ["--no-sandbox"],
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 860 } });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("dialog", (d) => d.accept());

  await page.goto(URL);
  await page.waitForSelector(".column");
  if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "01-initial.png") });

  const col = (name) => page.locator(".column", { has: page.locator(`input.col-title[value="${name}"]`) });
  const card = (text) => page.locator(".card", { hasText: text }).first();

  // 1. Starter template renders three columns
  let board = await snapshot(page);
  assert.deepEqual(colTitles(board), ["Core Competencies", "Nice to Have", "To Sort"]);

  // 2. Drag a card from To Sort into Core Competencies (lands at the bottom)
  await dragTo(page, card("SD-WAN design"), col("Core Competencies").locator(".cards"), { dy: 300 });
  board = await snapshot(page);
  assert.equal(titles(board, "Core Competencies").at(-1), "SD-WAN design");
  assert.ok(!titles(board, "To Sort").includes("SD-WAN design"));

  // 3. Drag a card to the top of another column
  await dragTo(page, card("Meraki cloud-managed networking"), card("Python scripting"), { dy: -20 });
  board = await snapshot(page);
  assert.equal(titles(board, "Nice to Have")[0], "Meraki cloud-managed networking");

  // 4. Reorder within the same column
  const before = titles(board, "Core Competencies");
  await dragTo(page, card(before[0]), card(before[2]), { dy: 10 });
  board = await snapshot(page);
  assert.deepEqual(titles(board, "Core Competencies").slice(0, 3), [before[1], before[2], before[0]]);

  // 5. Add a column dynamically and drag a card into the empty column
  await page.fill(".add-column input", "Stretch Goals");
  await page.press(".add-column input", "Enter");
  board = await snapshot(page);
  assert.deepEqual(colTitles(board), ["Core Competencies", "Nice to Have", "To Sort", "Stretch Goals"]);
  await page.evaluate(() => (document.querySelector("#board").scrollLeft = 9999));
  await dragTo(page, card("Secure Access / SASE"), col("Stretch Goals").locator(".cards"));
  board = await snapshot(page);
  assert.deepEqual(titles(board, "Stretch Goals"), ["Secure Access / SASE"]);

  // 6. Add items by typing, and bulk-add by multi-line paste
  const input = col("Stretch Goals").locator(".add-item textarea");
  await input.fill("Solo item");
  await input.press("Enter");
  await page.locator(".column .add-item textarea").nth(3).fill("- first\n2. second\n\n* third");
  await page.locator(".column .add-item textarea").nth(3).press("Enter");
  board = await snapshot(page);
  assert.deepEqual(titles(board, "Stretch Goals"), ["Secure Access / SASE", "Solo item", "first", "second", "third"]);
  assert.equal(await page.evaluate(() => document.activeElement.tagName), "TEXTAREA", "focus stays in add box for rapid entry");

  // 7. Reorder columns by dragging a header
  await page.evaluate(() => (document.querySelector("#board").scrollLeft = 0));
  await dragTo(page, col("Stretch Goals").locator(".col-header .grip"), col("Core Competencies").locator(".col-header"), { dx: -100, dy: 0 });
  board = await snapshot(page);
  assert.deepEqual(colTitles(board), ["Stretch Goals", "Core Competencies", "Nice to Have", "To Sort"]);

  // 8. Rename a column inline
  const nice = col("Nice to Have").locator("input.col-title");
  await nice.fill("Nice-to-Haves");
  await nice.press("Enter");
  assert.ok(colTitles(await snapshot(page)).includes("Nice-to-Haves"));

  // 9. Edit an item via dialog: notes, tag and move to another column
  await card("Hands-on troubleshooting").dblclick();
  await page.fill("#item-form [name=note]", "Packet captures and CLI fluency");
  await page.fill("#item-form [name=tag]", "Hands-on");
  await page.selectOption("#item-form [name=column]", { label: "Core Competencies" });
  await page.click("#item-form button[type=submit]");
  board = await snapshot(page);
  const moved = board.columns.find((c) => c.title === "Core Competencies").items.at(-1);
  assert.deepEqual([moved.title, moved.note, moved.tag], ["Hands-on troubleshooting", "Packet captures and CLI fluency", "Hands-on"]);

  // 10. Keyboard move: Alt+Right moves the focused card one column over
  await card("Hands-on troubleshooting").focus();
  await page.keyboard.press("Alt+ArrowRight");
  board = await snapshot(page);
  assert.ok(titles(board, "Nice-to-Haves").includes("Hands-on troubleshooting"));

  // 11. Persistence across reload
  await page.reload();
  await page.waitForSelector(".column");
  assert.deepEqual(await snapshot(page), board);
  assert.equal(await page.locator(".column").count(), 4);

  // 12. Delete with undo / redo
  const countBefore = (await snapshot(page)).columns.flatMap((c) => c.items).length;
  await card("Solo item").hover();
  await card("Solo item").getByRole("button", { name: "Delete item" }).click();
  assert.equal((await snapshot(page)).columns.flatMap((c) => c.items).length, countBefore - 1);
  await page.click("#toast button");
  assert.equal((await snapshot(page)).columns.flatMap((c) => c.items).length, countBefore);
  await page.click("#redo");
  assert.equal((await snapshot(page)).columns.flatMap((c) => c.items).length, countBefore - 1);
  await page.click("#undo");

  // 13. Escape cancels an in-flight drag
  const pre = await snapshot(page);
  const s = await card("Python scripting").boundingBox();
  await page.mouse.move(s.x + 40, s.y + 10);
  await page.mouse.down();
  await page.mouse.move(s.x + 400, s.y + 200, { steps: 8 });
  assert.equal(await page.locator(".ghost").count(), 1);
  await page.keyboard.press("Escape");
  await page.mouse.up();
  assert.equal(await page.locator(".ghost").count(), 0);
  assert.deepEqual(await snapshot(page), pre);

  // 14. Filter
  await page.fill("#search", "sd-wan");
  assert.equal(await page.locator(".card:not(.filtered-out)").count(), 1);
  await page.fill("#search", "");

  // 15. Column menu: delete column (undoable) and color dialog
  await col("Stretch Goals").getByRole("button", { name: "Column options" }).click();
  await page.getByRole("menuitem", { name: /Edit title/ }).click();
  await page.locator("#swatches .swatch").nth(5).click();
  await page.click("#column-form button[type=submit]");
  assert.equal((await snapshot(page)).columns.find((c) => c.title === "Stretch Goals").color, "#7a5af8");

  // 16. Export markdown and JSON round-trip import
  const [dl] = await Promise.all([page.waitForEvent("download"), (async () => {
    await page.click("#export-btn");
    await page.getByRole("menuitem", { name: "Download JSON (backup)" }).click();
  })()]);
  const file = path.join(require("node:os").tmpdir(), "board-export.json");
  await dl.saveAs(file);
  await page.click("#templates-btn");
  await page.getByRole("menuitem", { name: "Empty board" }).click();
  assert.equal(await page.locator(".column").count(), 0);
  await page.setInputFiles("#import-file", file);
  await page.waitForSelector(".column");
  assert.equal(await page.locator(".column").count(), 4);

  // 17. Dark theme + screenshot
  await page.click("#theme");
  if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "02-dark.png") });

  assert.deepEqual(errors, [], "no console or page errors");

  // 18. Touch: grip-initiated drag works with touch pointers
  const touch = await browser.newContext({ viewport: { width: 420, height: 800 }, hasTouch: true, isMobile: true });
  const tp = await touch.newPage();
  await tp.goto(URL);
  await tp.waitForSelector(".column");
  const cdp = await touch.newCDPSession(tp);
  const from = await tp.locator(".card .grip").first().boundingBox();
  const to = await tp.locator(".column").nth(1).locator(".cards").boundingBox();
  const fx = from.x + from.width / 2;
  const fy = from.y + from.height / 2;
  const tx = to.x + to.width / 2;
  const ty = to.y + 20;
  const firstTitle = await tp.locator(".card .card-title").first().textContent();
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: fx, y: fy }] });
  for (let i = 1; i <= 10; i++) {
    await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: fx + ((tx - fx) * i) / 10, y: fy + ((ty - fy) * i) / 10 }] });
  }
  await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  const tb = await tp.evaluate(() => JSON.parse(localStorage.getItem("se-competency-board:v1")));
  assert.equal(titles(tb, "Nice to Have")[0], firstTitle, "touch drag moved card to the next column");
  if (SHOTS) await tp.screenshot({ path: path.join(SHOTS, "03-mobile.png") });

  await browser.close();
  console.log("e2e: all checks passed");
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
