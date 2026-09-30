import { clusterQuizzes } from "./cluster.js";

const topicsEl = document.querySelector("#topics");
const playerEl = document.querySelector("#player");

function showLoadError() {
  topicsEl.textContent = "The quiz bank could not be loaded.";
}

function hidePlayer() {
  playerEl.hidden = true;
  playerEl.replaceChildren();
}

function backButton() {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "back";
  button.textContent = "Back to topics";
  button.addEventListener("click", hidePlayer);
  return button;
}

function startQuiz(quiz) {
  playerEl.hidden = false;
  let index = 0;
  let correct = 0;

  function showQuestion() {
    const question = quiz.questions[index];
    playerEl.replaceChildren();

    const title = document.createElement("h2");
    title.textContent = quiz.title;

    const prompt = document.createElement("p");
    prompt.textContent = question.prompt;

    const choices = document.createElement("div");
    choices.className = "choices";
    question.choices.forEach((choice, choiceIndex) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "choice";
      button.textContent = choice;
      button.addEventListener("click", () => {
        if (choiceIndex === question.answerIndex) correct += 1;
        index += 1;
        if (index >= quiz.questions.length) showScore();
        else showQuestion();
      });
      choices.append(button);
    });

    playerEl.append(title, prompt, choices, backButton());
  }

  function showScore() {
    playerEl.replaceChildren();
    const title = document.createElement("h2");
    title.textContent = quiz.title;
    const score = document.createElement("p");
    score.className = "score";
    score.textContent = `${correct} of ${quiz.questions.length}`;
    playerEl.append(title, score, backButton());
  }

  showQuestion();
}

function renderTopics(topics) {
  topicsEl.replaceChildren();
  hidePlayer();
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
      const button = document.createElement("button");
      button.type = "button";
      button.className = "quiz-open";
      button.textContent = quiz.title;
      button.addEventListener("click", () => startQuiz(quiz));
      quizItem.append(button);
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
