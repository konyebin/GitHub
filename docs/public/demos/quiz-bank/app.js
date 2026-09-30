import { clusterQuizzes } from "./cluster.js";

const topicsEl = document.querySelector("#topics");

function showLoadError() {
  topicsEl.textContent = "The quiz bank could not be loaded.";
}

function renderTopics(topics) {
  topicsEl.replaceChildren();
  for (const topic of topics) {
    const item = document.createElement("li");
    item.className = "topic-card";

    const heading = document.createElement("h2");
    heading.textContent = topic.title;

    const count = document.createElement("p");
    count.className = "quiz-count";
    const noun = topic.quizzes.length === 1 ? "quiz" : "quizzes";
    count.textContent = `${topic.quizzes.length} ${noun}`;

    const list = document.createElement("ul");
    for (const quiz of topic.quizzes) {
      const quizItem = document.createElement("li");
      quizItem.textContent = quiz.title;
      list.append(quizItem);
    }

    item.append(heading, count, list);
    topicsEl.append(item);
  }
}

try {
  const response = await fetch("./quizzes.json", { cache: "no-store" });
  if (!response.ok) throw new Error("load failed");
  const quizzes = await response.json();
  if (!Array.isArray(quizzes)) throw new Error("bank is not a list");
  renderTopics(clusterQuizzes(quizzes));
} catch {
  showLoadError();
}
