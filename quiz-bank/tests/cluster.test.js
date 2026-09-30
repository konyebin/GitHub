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
