import { clusterQuizzes } from "./cluster.js";
import { publishQuiz } from "./publish.js";
import { validateQuiz } from "./validate.js";

const topicsEl = document.querySelector("#topics");
const playerEl = document.querySelector("#player");
const form = document.querySelector("#add-quiz");
const questionFields = document.querySelector("#question-fields");
const statusEl = document.querySelector("#form-status");
const tokenInput = form.elements.token;

const PUBLISH = {
  owner: "konyebin",
  repo: "GitHub",
  branch: "main",
  path: "docs/public/demos/quiz-bank/quizzes.json",
};

let quizzes = [];

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
  if (topics.length === 0) {
    topicsEl.textContent = "No quizzes yet.";
    return;
  }
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

function showErrors(errors) {
  statusEl.replaceChildren();
  const list = document.createElement("ul");
  for (const message of errors) {
    const item = document.createElement("li");
    item.textContent = message;
    list.append(item);
  }
  statusEl.append(list);
}

function slugify(title) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function addChoiceRow(block, checked) {
  const rows = block.querySelector(".choice-fields");
  if (rows.children.length >= 6) return;
  const row = document.createElement("label");
  row.className = "choice-row";
  const radio = document.createElement("input");
  radio.type = "radio";
  radio.name = block.dataset.radio;
  radio.checked = checked;
  const text = document.createElement("input");
  text.type = "text";
  text.className = "choice-text";
  text.autocomplete = "off";
  row.append(radio, text);
  rows.append(row);
}

function addQuestionBlock() {
  const block = document.createElement("fieldset");
  block.dataset.radio = `correct-${questionFields.children.length}`;
  const legend = document.createElement("legend");
  legend.textContent = `Question ${questionFields.children.length + 1}`;
  const promptLabel = document.createElement("label");
  promptLabel.textContent = "Prompt ";
  const prompt = document.createElement("input");
  prompt.type = "text";
  prompt.className = "prompt";
  prompt.autocomplete = "off";
  promptLabel.append(prompt);
  const choices = document.createElement("div");
  choices.className = "choice-fields";
  const addChoice = document.createElement("button");
  addChoice.type = "button";
  addChoice.textContent = "Add choice";
  addChoice.addEventListener("click", () => addChoiceRow(block, false));
  block.append(legend, promptLabel, choices, addChoice);
  questionFields.append(block);
  addChoiceRow(block, true);
  addChoiceRow(block, false);
}

function readQuiz() {
  const title = form.elements.title.value.trim();
  const questions = [...questionFields.querySelectorAll("fieldset")].map((block) => {
    const choices = [...block.querySelectorAll(".choice-text")].map((input) => input.value);
    const radios = [...block.querySelectorAll('input[type="radio"]')];
    const answerIndex = radios.findIndex((radio) => radio.checked);
    return {
      prompt: block.querySelector(".prompt").value,
      choices,
      answerIndex,
    };
  });
  return {
    id: slugify(title),
    title,
    description: form.elements.description.value.trim(),
    questions,
  };
}

function remember(quiz) {
  if (!quizzes.some((item) => item.id === quiz.id)) quizzes.push(quiz);
  renderTopics(clusterQuizzes(quizzes));
}

form.addEventListener("submit", (event) => event.preventDefault());
document.querySelector("#add-question").addEventListener("click", addQuestionBlock);
addQuestionBlock();

document.querySelector("#preview").addEventListener("click", () => {
  const validated = validateQuiz(readQuiz());
  if (!validated.ok) {
    showErrors(validated.errors);
    return;
  }
  if (quizzes.some((item) => item.id === validated.quiz.id)) {
    showErrors(["A quiz with that id is already on the site."]);
    return;
  }
  remember(validated.quiz);
  statusEl.textContent = "Preview added in this tab. Publish to keep it on the site.";
});

document.querySelector("#publish").addEventListener("click", async () => {
  const validated = validateQuiz(readQuiz());
  const token = tokenInput.value;
  tokenInput.value = "";
  if (!validated.ok) {
    showErrors(validated.errors);
    return;
  }
  try {
    await publishQuiz({ ...PUBLISH, token, quiz: validated.quiz });
    remember(validated.quiz);
    statusEl.replaceChildren();
    statusEl.append("Committed to main. The live page updates when Deploy docs to GitHub Pages finishes. ");
    const link = document.createElement("a");
    link.href = "https://github.com/konyebin/GitHub/actions";
    link.textContent = "View the workflow";
    link.rel = "noopener noreferrer";
    statusEl.append(link);
  } catch (error) {
    if (error.status === 401 || error.status === 403) {
      statusEl.textContent = "That token cannot write to this repository.";
    } else if (error.status === 409) {
      statusEl.textContent = "The bank changed while saving. Reload and publish again.";
    } else {
      statusEl.textContent = error.message || "GitHub did not accept the quiz.";
    }
  }
});

try {
  const response = await fetch("./quizzes.json", { cache: "no-store" });
  if (!response.ok) throw new Error("load failed");
  const loaded = await response.json();
  if (!Array.isArray(loaded)) throw new Error("bank is not a list");
  quizzes = loaded;
  renderTopics(clusterQuizzes(quizzes));
} catch {
  showLoadError();
}
