// Background function (name ends in -background): Netlify answers 202 right away
// and lets this run for up to 15 minutes. It re-checks the payment itself, so a
// direct call without a paid session does nothing.
import { paidSession, store } from "./lib/common.mjs";
import { BREAKDOWN_PROMPT, BREAKDOWN_SCHEMA } from "./lib/prompt.mjs";

const MODEL = process.env.GEMINI_MODEL || "gemini-4-hydrogen";
const MAX_SECONDS = Number(process.env.BREAKDOWN_MAX_SECONDS || 600); // analyse at most the first 10 minutes

export default async (req) => {
  let sessionId = null;
  try { sessionId = (await req.json()).session_id; } catch {}
  const paid = await paidSession(sessionId).catch(() => null);
  if (!paid) return;

  const db = store();
  const rec = (await db.get(paid.id, { type: "json" })) || {};
  if (rec.status === "done") return;
  const save = (patch) => db.setJSON(paid.id, { ...rec, ...patch, updated: Date.now() });

  try {
    const key = process.env.GEMINI_API_KEY;
    if (!key) throw new Error("GEMINI_API_KEY is not set");
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-goog-api-key": key },
      body: JSON.stringify({
        contents: [{
          role: "user",
          parts: [
            { file_data: { file_uri: paid.youtube.url, mime_type: "video/*" }, video_metadata: { end_offset: `${MAX_SECONDS}s` } },
            { text: BREAKDOWN_PROMPT },
          ],
        }],
        generationConfig: { responseMimeType: "application/json", responseSchema: BREAKDOWN_SCHEMA, temperature: 0.4 },
      }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j?.error?.message || `Gemini ${r.status}`);
    const text = j?.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("") || "";
    const result = JSON.parse(text);
    if (!result?.boothmate_prompts?.length) throw new Error("Empty breakdown");
    await save({ status: "done", result, error: null, finished: Date.now() });
  } catch (e) {
    console.error("breakdown failed", paid.id, e);
    await save({ status: "error", error: friendly(e) });
  }
};

function friendly(e) {
  const m = String(e?.message || e);
  if (/private|unavailable|not found|permission/i.test(m)) return "Gemini couldn't open this video. It may be private or blocked in some countries.";
  if (/quota|rate|429|resource/i.test(m)) return "Our analyser is busy right now. Try again in a minute.";
  return "Something went wrong while breaking down this beat. Try again.";
}
