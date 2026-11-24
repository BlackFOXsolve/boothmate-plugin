// Background worker for the free preview: listens to the first 90 seconds.
import { previewStore } from "./lib/common.mjs";
import { geminiVideo, friendly } from "./lib/gemini.mjs";
import { PREVIEW_PROMPT, PREVIEW_SCHEMA } from "./lib/prompt.mjs";

export default async (req) => {
  let id = null;
  try { id = (await req.json()).id; } catch {}
  if (!/^[\w-]{11}$/.test(id || "")) return;
  const db = previewStore();
  const rec = await db.get(`v:${id}`, { type: "json" });
  if (!rec || rec.status !== "running") return; // only jobs started by /api/preview
  try {
    const preview = await geminiVideo({ url: `https://www.youtube.com/watch?v=${id}`, prompt: PREVIEW_PROMPT, schema: PREVIEW_SCHEMA, seconds: 90 });
    await db.setJSON(`v:${id}`, { ...rec, status: "done", preview, error: null, updated: Date.now() });
  } catch (e) {
    console.error("preview failed", id, e);
    await db.setJSON(`v:${id}`, { ...rec, status: "error", error: friendly(e), updated: Date.now() });
  }
};
