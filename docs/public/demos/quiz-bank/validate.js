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
