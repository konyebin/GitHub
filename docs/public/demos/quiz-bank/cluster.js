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
