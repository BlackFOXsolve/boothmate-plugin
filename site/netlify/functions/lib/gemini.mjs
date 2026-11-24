// Calls Gemini on a YouTube video with a JSON schema and returns the parsed object.
export async function geminiVideo({ url, prompt, schema, seconds }) {
  const key = process.env.GEMINI_API_KEY;
  if (!key) throw new Error("GEMINI_API_KEY is not set");
  const model = process.env.GEMINI_MODEL || "gemini-4-hydrogen";
  // Netlify's AI Gateway injects GEMINI_API_KEY + GOOGLE_GEMINI_BASE_URL when no key of our own is set;
  // that key only works against the gateway URL. With our own key, the base URL isn't injected and we call Google.
  const base = (process.env.GOOGLE_GEMINI_BASE_URL || "https://generativelanguage.googleapis.com").replace(/\/+$/, "");
  const r = await fetch(`${base}/v1beta/models/${model}:generateContent`, {
    method: "POST",
    headers: { "content-type": "application/json", "x-goog-api-key": key },
    body: JSON.stringify({
      contents: [{
        role: "user",
        parts: [
          { file_data: { file_uri: url, mime_type: "video/*" }, video_metadata: { end_offset: `${seconds}s` } },
          { text: prompt },
        ],
      }],
      generationConfig: { responseMimeType: "application/json", responseSchema: schema, temperature: 0.4 },
    }),
  });
  const raw = await r.text();
  let j = null;
  try { j = JSON.parse(raw); } catch {}
  if (!r.ok) throw new Error(`Gemini ${r.status}: ${j?.error?.message || raw.slice(0, 200)}`);
  if (!j) throw new Error(`Gemini returned something that isn't JSON: ${raw.slice(0, 200)}`);
  if (j.promptFeedback?.blockReason) throw new Error(`Gemini blocked the request: ${j.promptFeedback.blockReason}`);
  const cand = j.candidates?.[0];
  const text = cand?.content?.parts?.map((p) => p.text || "").join("") || "";
  if (!text) throw new Error(`Gemini returned no answer (finishReason ${cand?.finishReason || "none"})`);
  try { return JSON.parse(text); }
  catch { throw new Error(`Gemini's answer was cut off or malformed (finishReason ${cand?.finishReason || "unknown"})`); }
}

// One automatic retry for hiccups that usually clear on a second try (answer cut
// off or malformed, Gemini busy or briefly down). Not for bad links, blocks or
// missing keys: those fail the same way twice. Used by owner test mode.
const TRANSIENT = /cut off|malformed|no answer|isn't JSON|Gemini 5\d\d|Gemini 429|quota|rate.?limit|overloaded|deadline|fetch failed|ECONNRESET|socket/i;
export function isTransient(e) {
  const m = String(e?.message || e);
  return TRANSIENT.test(m) && !/GEMINI_API_KEY|blocked|private|not found|permission/i.test(m);
}
export async function geminiVideoWithRetry(args, { tries = 2, waitMs = 5000 } = {}) {
  let last;
  for (let i = 0; i < tries; i++) {
    try { return await geminiVideo(args); }
    catch (e) {
      last = e;
      if (i === tries - 1 || !isTransient(e)) break;
      console.warn("Gemini attempt failed, retrying once:", String(e?.message || e).slice(0, 200));
      if (waitMs) await new Promise((r) => setTimeout(r, waitMs));
    }
  }
  throw last;
}

export function friendly(e) {
  const m = String(e?.message || e);
  if (/GEMINI_API_KEY is not set/.test(m)) return "The analyser isn't switched on for this site yet. Please try again later.";
  if (/cut off|malformed|no answer|isn't JSON|MAX_TOKENS/i.test(m)) return "The analyser's answer came back incomplete. Try again; it usually works the second time.";
  if (/blocked|SAFETY|RECITATION/i.test(m)) return "The analyser declined this video. Try a different upload of the beat, ideally an instrumental.";
  if (/too long|duration|exceeds|token count/i.test(m)) return "This video is too long for the analyser. Try a video under 10 minutes.";
  if (/private|unavailable|not found|permission|youtube/i.test(m)) return "Gemini couldn't open this video. It may be private or blocked in some countries.";
  if (/quota|rate|429|resource/i.test(m)) return "Our analyser is busy right now. Try again in a minute.";
  return "Something went wrong while listening to this beat. Try again.";
}
