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
