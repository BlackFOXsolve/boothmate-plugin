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
  const j = await r.json();
  if (!r.ok) throw new Error(j?.error?.message || `Gemini ${r.status}`);
  const text = j?.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("") || "";
  return JSON.parse(text);
}

export function friendly(e) {
  const m = String(e?.message || e);
  if (/private|unavailable|not found|permission|youtube/i.test(m)) return "Gemini couldn't open this video. It may be private or blocked in some countries.";
  if (/quota|rate|429|resource/i.test(m)) return "Our analyser is busy right now. Try again in a minute.";
  return "Something went wrong while listening to this beat. Try again.";
}
