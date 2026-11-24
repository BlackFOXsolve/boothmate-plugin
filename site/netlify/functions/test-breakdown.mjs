// Owner test mode for Beat Breakdown: the FULL paid breakdown (same prompt and
// schema, whole video up to 10 minutes) with no payment, so Alan can judge the
// results before launch. Works regardless of BEAT_BREAKDOWN_OPEN, but ONLY on
// Netlify Deploy Previews / branch deploys, or with ?key=<BB_TEST_KEY>.
// Anywhere else it answers 404 as if it didn't exist.
//
// POST /api/test-breakdown { url, key? }  -> { id, status: "running", video }
// GET  /api/test-breakdown?id=<id>&key=   -> { status, video, result | error }
// GET  /api/test-breakdown?key=           -> { status: "ready", used, limit }
import { randomUUID } from "node:crypto";
import { json, parseYouTube, youTubeInfo, testStore, testModeAllowed } from "./lib/common.mjs";

export const DAILY_LIMIT = 25;
const STALE_MS = 15 * 60 * 1000;
const notFound = () => new Response("Not found", { status: 404, headers: { "content-type": "text/plain", "cache-control": "no-store" } });
const day = () => new Date().toISOString().slice(0, 10);

export default async (req, context) => {
  const url = new URL(req.url);
  let body = {};
  if (req.method === "POST") { try { body = await req.json(); } catch {} }
  const key = url.searchParams.get("key") || body.key || "";
  if (!testModeAllowed(key, context)) return notFound();

  const db = testStore();
  const countKey = `count:${day()}`;

  if (req.method === "GET") {
    const id = url.searchParams.get("id");
    if (!id) {
      const used = Number((await db.get(countKey)) || 0);
      return json(200, { status: "ready", used, limit: DAILY_LIMIT, geminiReady: !!process.env.GEMINI_API_KEY, gateway: { key: !!process.env.NETLIFY_AI_GATEWAY_KEY, url: !!(process.env.NETLIFY_AI_GATEWAY_URL || process.env.NETLIFY_AI_GATEWAY_BASE_URL), geminiBase: !!process.env.GOOGLE_GEMINI_BASE_URL, netlifyEnvKey: (() => { try { return !!globalThis.Netlify?.env?.get("GEMINI_API_KEY"); } catch { return false; } })() }, context: context?.deploy?.context || process.env.CONTEXT || "unknown" });
    }
    if (!/^[a-f0-9]{12}$/.test(id)) return json(400, { error: "Bad test id." });
    const rec = await db.get(`job:${id}`, { type: "json" });
    if (!rec) return json(404, { status: "missing", error: "No test run with that id. Start a new one." });
    const stale = rec.status === "running" && Date.now() - (rec.updated || 0) > STALE_MS;
    return json(200, {
      id, status: stale ? "error" : rec.status, video: rec.video, result: rec.result,
      error: stale ? "The analysis didn't finish within 15 minutes. Start it again." : rec.error,
      detail: rec.detail || null, started: rec.started, finished: rec.finished || null,
    });
  }

  if (req.method !== "POST") return json(405, { error: "Use GET or POST." });
  if (!process.env.GEMINI_API_KEY) return json(503, { error: "GEMINI_API_KEY isn't available to this deploy, so the analyser can't run. In Netlify, make sure the key (or the AI Gateway) applies to Deploy Previews too." });
  const yt = parseYouTube(body.url);
  if (!yt) return json(400, { error: "That doesn't look like a YouTube video link. Paste the link from the video's Share button." });
  const info = await youTubeInfo(yt.url).catch(() => null);
  if (!info) return json(400, { error: "We can't open that video. It may be private, removed or age-restricted. Try another link." });

  const used = Number((await db.get(countKey)) || 0);
  if (used >= DAILY_LIMIT) return json(429, { error: `That's all ${DAILY_LIMIT} test runs for today (UTC). More tomorrow.` });
  await db.set(countKey, String(used + 1));

  const id = randomUUID().replace(/-/g, "").slice(0, 12);
  const video = { id: yt.id, url: yt.url, ...info };
  const now = Date.now();
  await db.setJSON(`job:${id}`, { status: "running", video, started: now, updated: now });

  let started = false;
  try {
    // This deploy's own origin: on a Deploy Preview, process.env.URL is the
    // production site, which doesn't have this worker.
    const r = await fetch(`${new URL(req.url).origin}/.netlify/functions/run-test-breakdown-background`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ id }),
    });
    started = r.ok;
    if (!r.ok) console.error("test worker did not start", r.status);
  } catch (e) { console.error("test worker did not start", e); }
  if (!started) {
    await db.set(countKey, String(used)); // a run that never started doesn't count
    const error = "The analyser couldn't start. Try again in a minute.";
    await db.setJSON(`job:${id}`, { status: "error", video, started: now, updated: Date.now(), error });
    return json(200, { id, status: "error", video, error });
  }
  return json(202, { id, status: "running", video });
};

export const config = { path: "/api/test-breakdown" };
