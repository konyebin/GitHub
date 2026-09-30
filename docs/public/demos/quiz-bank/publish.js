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
  const readUrl = `${contentsUrl(owner, repo, path)}?ref=${encodeURIComponent(branch)}`;
  const writeUrl = contentsUrl(owner, repo, path);
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
  };

  let lastStatus = 0;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const current = await fetchImpl(readUrl, { headers });
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
    const put = await fetchImpl(writeUrl, {
      method: "PUT",
      headers,
      body: JSON.stringify({
        message: `Add quiz ${validated.quiz.id}`,
        content: encodeBase64(`${JSON.stringify(bank, null, 2)}\n`),
        sha: payload.sha,
        branch,
      }),
    });
    if (put.ok) {
      const written = await put.json();
      return { contentSha: written.content.sha };
    }
    lastStatus = put.status;
    if (put.status !== 409) break;
  }
  const error = new Error(
    lastStatus === 409
      ? "The bank changed while saving. Reload and publish again."
      : "GitHub did not accept the quiz.",
  );
  error.code = "write-failed";
  error.status = lastStatus;
  throw error;
}
