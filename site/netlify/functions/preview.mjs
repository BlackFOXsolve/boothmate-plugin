// Free preview before payment.
// POST /api/preview { url } -> starts (or returns cached) teaser for the video
// GET  /api/preview?v=<id> -> status / teaser
// Cached per video and capped per visitor per day, so pasting is cheap for us.
import { json, parseYouTube, youTubeInfo, previewStore, siteUrl, preflight, bbClosed } from "./lib/common.mjs";

const DAILY_LIMIT = Number(process.env.PREVIEW_DAILY_LIMIT || 6);
const STALE_MS = 5 * 60 * 1000;

export default async (req, context) => {
  const pre = preflight(req); if (pre) return pre;
  const db = previewStore();
  if (req.method === "GET") {
    const id = new URL(req.url).searchParams.get("v");
    if (!/^[\w-]{11}$/.test(id || "")) return json(400, { error: "Bad video id." });
    const rec = await db.get(`v:${id}`, { type: "json" });
    if (!rec) return json(200, { status: "not_started" });
    const stale = rec.status === "running" && Date.now() - rec.updated > STALE_MS;
    return json(200, { status: stale ? "error" : rec.status, preview: rec.preview, video: rec.video, error: stale ? "The preview timed out. Try again." : rec.error });
  }
  if (req.method !== "POST") return json(405, { error: "Use GET or POST." });
  const closed = bbClosed(); if (closed) return closed;
  if (!process.env.GEMINI_API_KEY) return json(503, { error: "Free previews are switched off for a moment. Please try again soon." });
  let body = {};
  try { body = await req.json(); } catch {}
  const yt = parseYouTube(body.url);
  if (!yt) return json(400, { error: "That doesn't look like a YouTube video link. Paste the link from the video's Share button." });
  const info = await youTubeInfo(yt.url);
  if (!info) return json(400, { error: "We can't open that video. It may be private, removed or age-restricted. Try another link." });
  const video = { id: yt.id, url: yt.url, ...info };

  const rec = await db.get(`v:${yt.id}`, { type: "json" });
  if (rec?.status === "done") return json(200, { status: "done", preview: rec.preview, video });
  if (rec?.status === "running" && Date.now() - rec.updated < STALE_MS) return json(202, { status: "running", video });

  const ip = context?.ip || req.headers.get("x-nf-client-connection-ip") || "unknown";
  const day = new Date().toISOString().slice(0, 10);
  const rlKey = `rl:${day}:${ip}`;
  const used = Number((await db.get(rlKey)) || 0);
  if (used >= DAILY_LIMIT) return json(429, { status: "limited", video, error: "You've used today's free previews. You can still unlock the full breakdown, or come back tomorrow." });
  await db.set(rlKey, String(used + 1));

  await db.setJSON(`v:${yt.id}`, { status: "running", updated: Date.now(), video });
  let started = false;
  try {
    const r = await fetch(`${siteUrl(req)}/.netlify/functions/run-preview-background`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ id: yt.id }),
    });
    started = r.ok;
    if (!r.ok) console.error("preview worker did not start", r.status);
  } catch (e) { console.error("preview worker did not start", e); }
  if (!started) {
    await db.setJSON(`v:${yt.id}`, { status: "error", updated: Date.now(), video, error: "The free preview couldn't start. Try again in a minute." });
    await db.set(rlKey, String(used)); // don't count a preview that never ran
    return json(200, { status: "error", video, error: "The free preview couldn't start. Try again in a minute." });
  }
  return json(202, { status: "running", video });
};

export const config = { path: "/api/preview" };
