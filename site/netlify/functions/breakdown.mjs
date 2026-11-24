// GET  /api/breakdown?session_id=cs_...  -> current status / result
// POST /api/breakdown { session_id }      -> start (or retry) the analysis
// The paid Stripe session id is the customer's private ticket.
import { json, paidSession, store, siteUrl } from "./lib/common.mjs";

const MAX_ATTEMPTS = 3;
const STALE_MS = 15 * 60 * 1000; // a background run never takes longer than this

export default async (req) => {
  const url = new URL(req.url);
  let sessionId = url.searchParams.get("session_id");
  if (req.method === "POST") {
    try { sessionId = (await req.json()).session_id || sessionId; } catch {}
  }
  const paid = await paidSession(sessionId).catch(() => null);
  if (!paid) return json(402, { status: "unpaid", error: "We couldn't find a completed payment for this link." });

  const db = store();
  const rec = (await db.get(paid.id, { type: "json" })) || null;
  const base = { video: { id: paid.youtube.id, url: paid.youtube.url, title: paid.title } };

  if (req.method === "GET") {
    if (!rec) return json(200, { ...base, status: "not_started" });
    const stale = rec.status === "running" && Date.now() - (rec.updated || 0) > STALE_MS;
    return json(200, { ...base, status: stale ? "error" : rec.status, result: rec.result, error: stale ? "The analysis timed out." : rec.error, attempts: rec.attempts || 0, canRetry: (rec.attempts || 0) < MAX_ATTEMPTS });
  }

  if (req.method !== "POST") return json(405, { error: "Use GET or POST." });
  if (rec?.status === "done") return json(200, { ...base, status: "done", result: rec.result });
  if (rec?.status === "running" && Date.now() - (rec.updated || 0) < STALE_MS) return json(202, { ...base, status: "running" });
  if ((rec?.attempts || 0) >= MAX_ATTEMPTS) return json(429, { ...base, status: "error", error: "We tried this video three times and couldn't break it down. Email contact@blackfoxsolve.com with your receipt for a refund." });

  await db.setJSON(paid.id, { status: "running", attempts: (rec?.attempts || 0) + 1, updated: Date.now(), video: base.video });
  // Background function: returns 202 at once and keeps running up to 15 minutes.
  await fetch(`${siteUrl(req)}/.netlify/functions/run-breakdown-background`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ session_id: paid.id }),
  });
  return json(202, { ...base, status: "running" });
};

export const config = { path: "/api/breakdown" };
