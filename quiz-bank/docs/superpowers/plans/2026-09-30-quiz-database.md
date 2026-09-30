# Quiz Database Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a quiz bank on the existing GitHub Pages site where adding a quiz commits it into the site, and every page load groups similar quizzes into topics, giving a quiz that matches nothing a topic of its own.

**Architecture:** Quizzes live in one public JSON file under `docs/public/demos/quiz-bank/`. The page fetches that file on load and clusters it in the browser with Jaccard similarity. An Add form validates a new multiple-choice quiz and, when the author supplies a fine-grained GitHub token, commits the updated JSON to `main` through the Contents API. The existing Deploy docs workflow then publishes the file. Topics are never stored; they are recomputed from the bank on each load so a newly published quiz joins or starts a topic without a second data model.

**Tech Stack:** Static HTML, CSS, and ES modules. Node.js built-in test runner (`node --test`) for the pure modules. Existing VitePress GitHub Pages site (`base: "/GitHub/"`). No new Pages workflow, no backend, no npm dependency for the quiz app.

## Global Constraints

- Hosted path is `docs/public/demos/quiz-bank/`. Live URL is `https://konyebin.github.io/GitHub/demos/quiz-bank/index.html`.
- One Pages site only. Do not add a second workflow. Deploys happen from `main` via `.github/workflows/deploy-docs.yml`.
- Relative asset paths only inside the demo folder.
- Never hardcode a GitHub token, client secret, or any credential. The token is typed into the Add form, held in a page-memory variable, and never written to source, `localStorage`, `sessionStorage`, logs, or the quiz JSON.
- Render quiz text with `textContent` (or `createElement`). Do not assign user or quiz strings to `innerHTML`.
- The public site must not contain customer data, PII, or secrets inside quiz text.
- Clustering threshold is `0.22` Jaccard, exported as `SIMILARITY_THRESHOLD`.
- Quiz ids match `/^[a-z0-9]+(?:-[a-z0-9]+)*$/`.

---

## Approaches

| Approach | What it does | Why it loses |
|----------|----------------|--------------|
| **A. Load-time clustering + Contents API publish (this plan)** | Page groups quizzes every load. Add commits `quizzes.json` to `main`. | Needs a token with contents write to publish. Preview still works without one. |
| B. Cluster during the VitePress build | Topics are frozen into HTML in CI. | Contradicts "when the page is being loaded". A new quiz would not form a topic until a custom build step. |
| C. Author picks a topic in the JSON | No similarity code. | Contradicts automatic topics and the rule that an unmatched quiz gets its own topic. |

A is the plan because the grouping requirement is a view-time rule and the publish requirement is "the quiz is added to the GitHub site."

## File structure

| File | Responsibility |
|------|----------------|
| `docs/public/demos/quiz-bank/validate.js` | Parse and reject a quiz object. |
| `docs/public/demos/quiz-bank/cluster.js` | Tokenize, score, and assign topics. |
| `docs/public/demos/quiz-bank/publish.js` | Read/write `quizzes.json` through the GitHub Contents API. |
| `docs/public/demos/quiz-bank/app.js` | Load, render topics, play a quiz, submit the add form. |
| `docs/public/demos/quiz-bank/index.html` | Shell: topic list, player, add form. |
| `docs/public/demos/quiz-bank/style.css` | Layout. |
| `docs/public/demos/quiz-bank/quizzes.json` | The database. Array of quizzes. |
| `quiz-bank/tests/validate.test.js` | Schema tests. |
| `quiz-bank/tests/cluster.test.js` | Grouping and singleton tests. |
| `quiz-bank/tests/publish.test.js` | Request-shape tests with a fake `fetch`. |
| `docs/projects/quiz-bank.md` | Project page with the live link. |
| `docs/.vitepress/config.ts` | Sidebar entry. |

`validate.js`, `cluster.js`, and `publish.js` stay free of DOM so Node can import them.

## Data model

```json
{
  "id": "ospf-areas",
  "title": "OSPF areas",
  "description": "How OSPF splits a network into areas.",
  "questions": [
    {
      "prompt": "Which area must exist in every OSPF domain?",
      "choices": ["Area 0", "Area 1", "The NSSA", "A stub area"],
      "answerIndex": 0
    }
  ]
}
```

`quizzes.json` is a JSON array of those objects. Topic objects exist only in memory:

```js
{
  id: "topic-ospf-areas",
  title: "OSPF areas",
  singleton: true,
  quizzes: [/* quiz objects */]
}
```

A grouped topic sets `singleton` to `false` and replaces `title` with up to four shared words. A singleton topic keeps the quiz title verbatim.

## Data flow

1. `index.html` loads. `app.js` fetches `quizzes.json` (cache-bust with the response's freshness; use `cache: "no-store"`).
2. `clusterQuizzes` sorts by `id`, then walks the list. Each quiz joins the existing topic with the highest Jaccard score when that score is at least `0.22`. Otherwise it starts a topic named after itself.
3. The page lists topics. Opening a topic lists its quizzes. Opening a quiz walks questions and shows a score at the end.
4. Add form builds a quiz, runs `validateQuiz`, and shows it in the current tab immediately (in-memory only).
5. Publish reads `docs/public/demos/quiz-bank/quizzes.json` from `konyebin/GitHub` on `main`, appends the quiz, and `PUT`s the file back with the blob `sha`. The existing workflow deploys `main`. The author reloads after that workflow finishes and the new quiz is in whatever topic the clusterer assigns.

## Error handling

- Missing or invalid `quizzes.json`: show "The quiz bank could not be loaded." and still show the Add form.
- Validation failure: list the messages next to the form. Do not call GitHub.
- GitHub 401/403: "That token cannot write to this repository."
- GitHub 409 or a sha mismatch: refetch once and retry the `PUT` a single time. If it fails again, show "The bank changed while saving. Reload and publish again."
- Duplicate id: validation error, no write.
- Empty bank: topic list says "No quizzes yet." The first published quiz becomes a topic named with its title.

## Clustering rule (locked)

Tokens are lowercase words of length greater than 2 from `title`, `description`, and every question `prompt`, with this stop list removed: `a an the of and or to in for on with is are was were what which how does do quiz about from that this your you`.

Score is Jaccard over the two token sets. A quiz compares itself to each topic centroid. The centroid is the union of member tokens. Ties go to the topic whose `id` sorts first. After a join, recompute the centroid and the shared-word title.

Shared-word title: words present in every member, excluding the stop list, sorted by how many times they occur across members, then alphabetically, capped at four, title-cased. If the intersection is empty, use the first quiz's title plus " and related".

---

### Task 1: Quiz validation

**Files:**
- Create: `docs/public/demos/quiz-bank/validate.js`
- Test: `quiz-bank/tests/validate.test.js`

**Interfaces:**
- Consumes: nothing
- Produces: `validateQuiz(value) -> { ok: true, quiz } | { ok: false, errors: string[] }`

- [ ] **Step 1: Write the failing test**

```js
import assert from "node:assert/strict";
import test from "node:test";
import { validateQuiz } from "../../docs/public/demos/quiz-bank/validate.js";

const good = {
  id: "ospf-areas",
  title: "OSPF areas",
  description: "Areas.",
  questions: [
    { prompt: "Backbone?", choices: ["Area 0", "Area 1"], answerIndex: 0 },
  ],
};

test("accepts a minimal quiz", () => {
  const result = validateQuiz(good);
  assert.equal(result.ok, true);
  assert.equal(result.quiz.id, "ospf-areas");
});

test("rejects a bad id, short choice list, and out-of-range answer", () => {
  const result = validateQuiz({
    id: "OSPF Areas",
    title: "",
    questions: [{ prompt: "", choices: ["only"], answerIndex: 3 }],
  });
  assert.equal(result.ok, false);
  assert.ok(result.errors.length >= 3);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test quiz-bank/tests/validate.test.js`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `validate.js`.

- [ ] **Step 3: Write minimal implementation**

```js
const ID_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export function validateQuiz(value) {
  const errors = [];
  if (!value || typeof value !== "object") {
    return { ok: false, errors: ["Quiz must be an object."] };
  }
  if (typeof value.id !== "string" || !ID_RE.test(value.id)) {
    errors.push("Id must be lowercase words separated by hyphens.");
  }
  if (typeof value.title !== "string" || value.title.trim().length < 1 || value.title.length > 120) {
    errors.push("Title must be 1 to 120 characters.");
  }
  const description = typeof value.description === "string" ? value.description.trim() : "";
  if (value.description != null && typeof value.description !== "string") {
    errors.push("Description must be text.");
  }
  if (!Array.isArray(value.questions) || value.questions.length < 1 || value.questions.length > 40) {
    errors.push("A quiz needs 1 to 40 questions.");
  }
  const questions = [];
  if (Array.isArray(value.questions)) {
    value.questions.forEach((question, index) => {
      const prompt = question && typeof question.prompt === "string" ? question.prompt.trim() : "";
      if (!prompt) errors.push(`Question ${index + 1} needs a prompt.`);
      const choices = Array.isArray(question?.choices)
        ? question.choices.map((choice) => (typeof choice === "string" ? choice.trim() : ""))
        : [];
      if (choices.length < 2 || choices.length > 6 || choices.some((choice) => !choice)) {
        errors.push(`Question ${index + 1} needs 2 to 6 non-empty choices.`);
      }
      const answerIndex = question?.answerIndex;
      if (!Number.isInteger(answerIndex) || answerIndex < 0 || answerIndex >= choices.length) {
        errors.push(`Question ${index + 1} has an answer outside its choices.`);
      }
      questions.push({ prompt, choices, answerIndex });
    });
  }
  if (errors.length) return { ok: false, errors };
  return {
    ok: true,
    quiz: {
      id: value.id,
      title: value.title.trim(),
      description,
      questions,
    },
  };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test quiz-bank/tests/validate.test.js`

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add docs/public/demos/quiz-bank/validate.js quiz-bank/tests/validate.test.js
git commit -m "Add quiz JSON validation."
```

---

### Task 2: Load-time topics

**Files:**
- Create: `docs/public/demos/quiz-bank/cluster.js`
- Test: `quiz-bank/tests/cluster.test.js`

**Interfaces:**
- Consumes: quiz objects from `validateQuiz`
- Produces: `SIMILARITY_THRESHOLD`, `clusterQuizzes(quizzes) -> Topic[]` where each topic is `{ id, title, singleton, quizzes }`

- [ ] **Step 1: Write the failing test**

```js
import assert from "node:assert/strict";
import test from "node:test";
import { SIMILARITY_THRESHOLD, clusterQuizzes } from "../../docs/public/demos/quiz-bank/cluster.js";

const ospf = {
  id: "ospf-areas",
  title: "OSPF routing areas",
  description: "OSPF routing protocol router area prefix neighbor.",
  questions: [{ prompt: "Which routing protocol uses a backbone area?", choices: ["OSPF"], answerIndex: 0 }],
};
const bgp = {
  id: "bgp-peers",
  title: "BGP routing peers",
  description: "BGP routing protocol router prefix neighbor sessions.",
  questions: [{ prompt: "What does a routing protocol peer advertise?", choices: ["Prefixes"], answerIndex: 0 }],
};
const python = {
  id: "python-lists",
  title: "Python lists",
  description: "Python list methods.",
  questions: [{ prompt: "Which method adds to a Python list?", choices: ["append"], answerIndex: 0 }],
};

test("groups similar quizzes and isolates an unrelated one", () => {
  const topics = clusterQuizzes([python, bgp, ospf]);
  const networking = topics.find((topic) => topic.quizzes.some((quiz) => quiz.id === "ospf-areas"));
  const alone = topics.find((topic) => topic.quizzes.some((quiz) => quiz.id === "python-lists"));
  assert.equal(SIMILARITY_THRESHOLD, 0.22);
  assert.equal(networking.singleton, false);
  assert.deepEqual(networking.quizzes.map((quiz) => quiz.id).sort(), ["bgp-peers", "ospf-areas"]);
  assert.equal(alone.singleton, true);
  assert.equal(alone.title, "Python lists");
  assert.equal(alone.id, "topic-python-lists");
});

test("a single quiz is its own topic", () => {
  const [topic] = clusterQuizzes([python]);
  assert.equal(topic.singleton, true);
  assert.equal(topic.title, "Python lists");
});

test("the same bank always yields the same topics", () => {
  const left = clusterQuizzes([python, ospf, bgp]);
  const right = clusterQuizzes([bgp, python, ospf]);
  assert.deepEqual(left.map((topic) => topic.id), right.map((topic) => topic.id));
});
```

These fixtures are already above the line: the OSPF and BGP bags share `routing`, `protocol`, `router`, `prefix`, and `neighbor` (Jaccard 0.33). The Python bag shares none of those words. Do not lower `SIMILARITY_THRESHOLD` if a later fixture fails to group; change that fixture's wording.

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test quiz-bank/tests/cluster.test.js`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `cluster.js`.

- [ ] **Step 3: Write minimal implementation**

```js
export const SIMILARITY_THRESHOLD = 0.22;

const STOP = new Set(
  "a an the of and or to in for on with is are was were what which how does do quiz about from that this your you"
    .split(" "),
);

function bag(quiz) {
  const text = [quiz.title, quiz.description || "", ...quiz.questions.map((q) => q.prompt)].join(" ");
  return new Set(
    text
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((word) => word.length > 2 && !STOP.has(word)),
  );
}

function jaccard(left, right) {
  let inter = 0;
  for (const word of left) if (right.has(word)) inter += 1;
  const union = left.size + right.size - inter;
  return union === 0 ? 0 : inter / union;
}

function titleCase(word) {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

function sharedTitle(quizzes) {
  const counts = new Map();
  const bags = quizzes.map(bag);
  for (const words of bags) {
    for (const word of words) counts.set(word, (counts.get(word) || 0) + 1);
  }
  const shared = [...counts.entries()]
    .filter(([, count]) => count === quizzes.length)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 4)
    .map(([word]) => titleCase(word));
  if (shared.length) return shared.join(" ");
  return `${quizzes[0].title} and related`;
}

export function clusterQuizzes(quizzes) {
  const ordered = [...quizzes].sort((a, b) => a.id.localeCompare(b.id));
  const topics = [];
  for (const quiz of ordered) {
    const words = bag(quiz);
    let best = null;
    let bestScore = 0;
    for (const topic of topics) {
      const score = jaccard(words, topic.centroid);
      if (score > bestScore || (score === bestScore && best && topic.id < best.id)) {
        best = topic;
        bestScore = score;
      }
    }
    if (best && bestScore >= SIMILARITY_THRESHOLD) {
      best.quizzes.push(quiz);
      best.quizzes.sort((a, b) => a.id.localeCompare(b.id));
      best.centroid = new Set(best.quizzes.flatMap((item) => [...bag(item)]));
      best.title = sharedTitle(best.quizzes);
      best.singleton = false;
    } else {
      topics.push({
        id: `topic-${quiz.id}`,
        title: quiz.title,
        singleton: true,
        quizzes: [quiz],
        centroid: words,
      });
    }
  }
  return topics
    .map(({ centroid, ...topic }) => topic)
    .sort((a, b) => a.title.localeCompare(b.title) || a.id.localeCompare(b.id));
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test quiz-bank/tests/cluster.test.js`

Expected: PASS, 3 tests. Leave `SIMILARITY_THRESHOLD` at `0.22`.

- [ ] **Step 5: Commit**

```bash
git add docs/public/demos/quiz-bank/cluster.js quiz-bank/tests/cluster.test.js
git commit -m "Cluster similar quizzes into topics on load."
```

---

### Task 3: Seed bank and topic page

**Files:**
- Create: `docs/public/demos/quiz-bank/quizzes.json`
- Create: `docs/public/demos/quiz-bank/index.html`
- Create: `docs/public/demos/quiz-bank/style.css`
- Create: `docs/public/demos/quiz-bank/app.js`
- Modify: `docs/.vitepress/config.ts` sidebar Projects items
- Create: `docs/projects/quiz-bank.md`

**Interfaces:**
- Consumes: `clusterQuizzes` from `cluster.js`
- Produces: a page that renders one card per topic and lists member quiz titles. No player and no add form yet.

Seed four quizzes in `quizzes.json`: `ospf-areas` and `bgp-peers` with shared words `routing`, `router`, `protocol`, `prefix`, and `neighbor`; `python-lists` with only Python list language; `tudor-monarchs` with only Tudor history language. Expected topics on first paint: one grouped routing topic, plus singleton topics titled `Python lists` and `Tudor monarchs`.

- [ ] **Step 1: Write the seed bank**

Write this array to `docs/public/demos/quiz-bank/quizzes.json`:

```json
[
  {
    "id": "ospf-areas",
    "title": "OSPF routing areas",
    "description": "OSPF routing protocol router area prefix neighbor.",
    "questions": [
      {
        "prompt": "Which routing protocol uses a backbone area?",
        "choices": ["OSPF", "RIP", "Static"],
        "answerIndex": 0
      },
      {
        "prompt": "What is the OSPF backbone area number?",
        "choices": ["0", "1", "51"],
        "answerIndex": 0
      }
    ]
  },
  {
    "id": "bgp-peers",
    "title": "BGP routing peers",
    "description": "BGP routing protocol router prefix neighbor sessions.",
    "questions": [
      {
        "prompt": "What does a routing protocol peer advertise?",
        "choices": ["Prefixes", "Passwords", "VLANs"],
        "answerIndex": 0
      },
      {
        "prompt": "Which protocol forms a neighbor session between routers?",
        "choices": ["BGP", "NTP", "SMTP"],
        "answerIndex": 0
      }
    ]
  },
  {
    "id": "python-lists",
    "title": "Python lists",
    "description": "Python list methods.",
    "questions": [
      {
        "prompt": "Which method adds to a Python list?",
        "choices": ["append", "commit", "compile"],
        "answerIndex": 0
      },
      {
        "prompt": "What does a Python list store?",
        "choices": ["Ordered items", "Only numbers", "Only keys"],
        "answerIndex": 0
      }
    ]
  },
  {
    "id": "tudor-monarchs",
    "title": "Tudor monarchs",
    "description": "Tudor kings and queens of England.",
    "questions": [
      {
        "prompt": "Who was the first Tudor monarch?",
        "choices": ["Henry VII", "Henry VIII", "Elizabeth I"],
        "answerIndex": 0
      },
      {
        "prompt": "Which Tudor queen ruled after Mary I?",
        "choices": ["Elizabeth I", "Anne", "Victoria"],
        "answerIndex": 0
      }
    ]
  }
]
```

- [ ] **Step 2: Write the page shell**

`index.html` has a heading "Quiz bank", an empty `<ul id="topics">`, and `<script type="module" src="./app.js"></script>`. `style.css` sets a max-width column, a topic card, and a muted line for the quiz count. `app.js` fetches `./quizzes.json` with `cache: "no-store"`, calls `clusterQuizzes`, and for each topic creates an `li` whose heading is the topic title and whose body is a list of quiz titles set with `textContent`. On fetch or JSON failure, set the list's text to `The quiz bank could not be loaded.`

- [ ] **Step 3: Link it from the docs site**

Add `{ text: "Quiz bank", link: "/projects/quiz-bank" }` to the Projects sidebar in `docs/.vitepress/config.ts`.

`docs/projects/quiz-bank.md`:

```md
# Quiz bank

[Open the quiz bank](https://konyebin.github.io/GitHub/demos/quiz-bank/index.html)

Static multiple-choice quizzes. The page groups similar quizzes into topics each time it loads. A quiz that matches nothing becomes its own topic.
```

- [ ] **Step 4: Verify in a browser**

From `docs/public/demos/quiz-bank/`, serve the folder (`python3 -m http.server 8765`) and open `http://127.0.0.1:8765/`. Confirm three topics: a routing group containing both networking quizzes, `Python lists` alone, and `Tudor monarchs` alone. Stop the server when done.

- [ ] **Step 5: Commit**

```bash
git add docs/public/demos/quiz-bank/quizzes.json docs/public/demos/quiz-bank/index.html \
  docs/public/demos/quiz-bank/style.css docs/public/demos/quiz-bank/app.js \
  docs/.vitepress/config.ts docs/projects/quiz-bank.md
git commit -m "Show quiz topics computed when the page loads."
```

---

### Task 4: Play a quiz

**Files:**
- Modify: `docs/public/demos/quiz-bank/index.html`
- Modify: `docs/public/demos/quiz-bank/app.js`
- Modify: `docs/public/demos/quiz-bank/style.css`

**Interfaces:**
- Consumes: topic list from Task 3
- Produces: `startQuiz(quiz)` in `app.js`, which renders one question at a time and a final score line `{correct} of {total}`

- [ ] **Step 1: Add a player region**

In `index.html`, add `<section id="player" hidden></section>` after the topic list. Each quiz title in a topic becomes a button. Activating it unhides `#player`.

- [ ] **Step 2: Implement the player**

`startQuiz` clears `#player`, shows the title, the current prompt, and one button per choice. Choosing records the index, advances, and on the last question replaces the body with `textContent` `{n} of {total}`. A "Back to topics" button hides the player. All strings go through `textContent`.

- [ ] **Step 3: Verify in the browser**

Serve the folder again. Open `Python lists`, answer both questions, and confirm the score matches the `answerIndex` values in `quizzes.json`. Confirm the other two singleton and grouped quizzes open the same way. Reload and confirm topics are unchanged.

- [ ] **Step 4: Commit**

```bash
git add docs/public/demos/quiz-bank/index.html docs/public/demos/quiz-bank/app.js \
  docs/public/demos/quiz-bank/style.css
git commit -m "Play a quiz from its topic."
```

---

### Task 5: Publish a quiz onto the site

**Files:**
- Create: `docs/public/demos/quiz-bank/publish.js`
- Test: `quiz-bank/tests/publish.test.js`
- Modify: `docs/public/demos/quiz-bank/index.html`
- Modify: `docs/public/demos/quiz-bank/app.js`

**Interfaces:**
- Consumes: `validateQuiz`
- Produces: `publishQuiz({ token, owner, repo, branch, path, quiz, fetchImpl }) -> Promise<{ contentSha: string }>`

`owner` is `konyebin`, `repo` is `GitHub`, `branch` is `main`, `path` is `docs/public/demos/quiz-bank/quizzes.json`.

- [ ] **Step 1: Write the failing test**

```js
import assert from "node:assert/strict";
import test from "node:test";
import { publishQuiz } from "../../docs/public/demos/quiz-bank/publish.js";

test("appends a quiz and puts the file with the current sha", async () => {
  const calls = [];
  const bank = [{ id: "python-lists", title: "Python lists", description: "", questions: [] }];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options });
    if (!options.method || options.method === "GET") {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          sha: "abc",
          content: Buffer.from(JSON.stringify(bank)).toString("base64"),
        }),
      };
    }
    return { ok: true, status: 200, json: async () => ({ content: { sha: "def" } }) };
  };
  const quiz = {
    id: "tudor-monarchs",
    title: "Tudor monarchs",
    description: "",
    questions: [{ prompt: "First Tudor king?", choices: ["Henry VII", "Henry VIII"], answerIndex: 0 }],
  };
  const result = await publishQuiz({
    token: "example-token",
    owner: "konyebin",
    repo: "GitHub",
    branch: "main",
    path: "docs/public/demos/quiz-bank/quizzes.json",
    quiz,
    fetchImpl,
  });
  assert.equal(result.contentSha, "def");
  const put = calls[1];
  assert.equal(put.options.method, "PUT");
  assert.equal(put.options.headers.Authorization, "Bearer example-token");
  const body = JSON.parse(put.options.body);
  assert.equal(body.sha, "abc");
  const written = JSON.parse(Buffer.from(body.content, "base64").toString("utf8"));
  assert.deepEqual(written.map((item) => item.id), ["python-lists", "tudor-monarchs"]);
});
```

The test token string exists only inside the test. Do not copy it into app source.

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test quiz-bank/tests/publish.test.js`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `publish.js`.

- [ ] **Step 3: Write minimal implementation**

```js
import { validateQuiz } from "./validate.js";

function contentsUrl(owner, repo, path) {
  return `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
}

function encodeBase64(text) {
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function decodeBase64(value) {
  const binary = atob(value.replace(/\s/g, ""));
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

export async function publishQuiz({ token, owner, repo, branch, path, quiz, fetchImpl = fetch }) {
  const validated = validateQuiz(quiz);
  if (!validated.ok) {
    const error = new Error(validated.errors.join(" "));
    error.code = "invalid-quiz";
    throw error;
  }
  if (typeof token !== "string" || token.length < 10) {
    const error = new Error("A GitHub token is required to publish.");
    error.code = "missing-token";
    throw error;
  }
  const url = `${contentsUrl(owner, repo, path)}?ref=${encodeURIComponent(branch)}`;
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
  };
  const current = await fetchImpl(url, { headers });
  if (!current.ok) {
    const error = new Error("The quiz bank could not be read.");
    error.code = "read-failed";
    error.status = current.status;
    throw error;
  }
  const payload = await current.json();
  const bank = JSON.parse(decodeBase64(payload.content));
  if (!Array.isArray(bank)) throw new Error("Quiz bank is not a list.");
  if (bank.some((item) => item.id === validated.quiz.id)) {
    const error = new Error("A quiz with that id is already on the site.");
    error.code = "duplicate-id";
    throw error;
  }
  bank.push(validated.quiz);
  const put = await fetchImpl(contentsUrl(owner, repo, path), {
    method: "PUT",
    headers,
    body: JSON.stringify({
      message: `Add quiz ${validated.quiz.id}`,
      content: encodeBase64(`${JSON.stringify(bank, null, 2)}\n`),
      sha: payload.sha,
      branch,
    }),
  });
  if (!put.ok) {
    const error = new Error("GitHub did not accept the quiz.");
    error.code = "write-failed";
    error.status = put.status;
    throw error;
  }
  const written = await put.json();
  return { contentSha: written.content.sha };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test quiz-bank/tests/publish.test.js`

Expected: PASS, 1 test.

- [ ] **Step 5: Add the form**

Add a form with fields: title, description, questions (one prompt plus choices, a radio for the correct choice, and a button to add another question), and a password input labeled "GitHub token". Buttons: "Preview" and "Publish to GitHub Pages".

Preview runs `validateQuiz`, appends the quiz to the in-memory list, reruns `clusterQuizzes`, and re-renders. It does not call `fetch` except the original bank load. The preview disappears on reload, which is correct: only a published file is on the site.

Publish calls `publishQuiz` with the token from the password field. On success, show "Committed to main. The live page updates when Deploy docs to GitHub Pages finishes." and a link to `https://github.com/konyebin/GitHub/actions`. On status 401 or 403, show "That token cannot write to this repository." Clear the password field after a success or a failure. Never log the token.

- [ ] **Step 6: Verify preview without a token**

Serve the folder. Add a quiz whose prompts repeat `python list append`. Preview it and confirm it lands in the Python topic. Reload and confirm it is gone. Do not exercise a real token in this task.

- [ ] **Step 7: Commit**

```bash
git add docs/public/demos/quiz-bank/publish.js quiz-bank/tests/publish.test.js \
  docs/public/demos/quiz-bank/index.html docs/public/demos/quiz-bank/app.js
git commit -m "Publish a new quiz onto the GitHub Pages bank."
```

---

### Task 6: End-to-end check

**Files:** none new.

- [ ] **Step 1: Run the module tests**

Run: `node --test quiz-bank/tests/*.test.js`

Expected: all tests PASS.

- [ ] **Step 2: Browser pass**

Serve `docs/public/demos/quiz-bank/`. Confirm the seed topics, play one grouped quiz and one singleton through to a score, preview a matching quiz into an existing topic, and preview an unrelated quiz into a new topic named with its title. Confirm a blank title does not render a topic and shows a validation message.

- [ ] **Step 3: Commit only if a fixture or copy fix was required**

```bash
git add docs/public/demos/quiz-bank quiz-bank/tests docs/projects/quiz-bank.md docs/.vitepress/config.ts
git commit -m "Fix quiz bank grouping fixtures."
```

Skip the commit when Step 1 and Step 2 already pass on the Task 5 tree.

---

## Spec coverage

| Requirement | Task |
|-------------|------|
| Quiz database on GitHub Pages | Task 3, existing `deploy-docs.yml` |
| Adding a quiz adds it to the site | Task 5 Contents API commit to `main` |
| On load, view quizzes and create topics when they are similar | Task 2 and Task 3 |
| A quiz that fits no topic gets its own | Task 2 singleton branch, asserted with `python-lists` |
| No hardcoded credentials | Token only as a function argument and a password field |

## Out of scope

Accounts, saved scores, images, essay questions, editing or deleting a published quiz, and a second GitHub Pages workflow.
