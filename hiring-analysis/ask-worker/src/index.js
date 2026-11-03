import { buildMessages, corsHeaders, extractAnswer, parseRequest } from "./logic.js";

const json = (data, status, headers) =>
  new Response(JSON.stringify(data), { status, headers: { ...headers, "content-type": "application/json" } });

export default {
  async fetch(request, env) {
    const origin = request.headers.get("origin");
    const cors = corsHeaders(origin, env.ALLOWED_ORIGIN);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "POST") return json({ error: "Use POST." }, 405, cors);
    if (cors["access-control-allow-origin"] === "null") return json({ error: "Origin not allowed." }, 403, cors);

    const { success } = await env.LIMITER.limit({ key: origin });
    if (!success) return json({ error: "Too many questions. Wait a minute and try again." }, 429, cors);

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "Body must be JSON." }, 400, cors);
    }
    const parsed = parseRequest(body);
    if (parsed.error) return json({ error: parsed.error }, 400, cors);

    try {
      const out = await env.AI.run(env.MODEL, {
        messages: buildMessages(parsed.question, parsed.context),
        max_tokens: 700,
        temperature: 0.2,
        chat_template_kwargs: { enable_thinking: false }
      });
      const answer = extractAnswer(out);
      if (!answer) return json({ error: "The model returned no answer." }, 502, cors);
      return json({ answer }, 200, cors);
    } catch (err) {
      console.error(JSON.stringify({ msg: "ai_run_failed", error: String(err) }));
      return json({ error: "The AI service is unavailable right now." }, 502, cors);
    }
  }
};
