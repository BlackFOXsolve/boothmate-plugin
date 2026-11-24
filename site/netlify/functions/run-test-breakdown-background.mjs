// Background worker for owner test mode (see test-breakdown.mjs). Runs exactly
// the paid breakdown (same prompt, schema and 10-minute window) but stores the
// result in its own Blobs store. Acts only on jobs /api/test-breakdown started.
import { testStore } from "./lib/common.mjs";
import { geminiVideo, friendly } from "./lib/gemini.mjs";
import { breakdownPrompt, BREAKDOWN_SCHEMA, tidyBreakdown } from "./lib/prompt.mjs";

const MAX_SECONDS = Number(process.env.BREAKDOWN_MAX_SECONDS || 600);

export default async (req) => {
  let id = null;
  try { id = (await req.json()).id; } catch {}
  if (!/^[a-f0-9]{12}$/.test(String(id || ""))) return;
  const db = testStore();
  const rec = await db.get(`job:${id}`, { type: "json" });
  if (!rec || rec.status !== "running") return;
  const save = (patch) => db.setJSON(`job:${id}`, { ...rec, ...patch, updated: Date.now() });
  try {
    const result = tidyBreakdown(await geminiVideo({ url: rec.video.url, prompt: breakdownPrompt({ title: rec.video.title, author: rec.video.author }), schema: BREAKDOWN_SCHEMA, seconds: MAX_SECONDS }));
    if (!result?.boothmate_prompts?.length) throw new Error("Empty breakdown: no prompts came back");
    await save({ status: "done", result, error: null, finished: Date.now() });
  } catch (e) {
    console.error("test breakdown failed", id, e);
    // The owner sees the technical detail too; this page is never public.
    await save({ status: "error", error: friendly(e), detail: String(e?.message || e).slice(0, 500), finished: Date.now() });
  }
};
