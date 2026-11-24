import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";

// In-memory Blobs store + fake network for Stripe, YouTube oEmbed and Gemini.
const mem = new Map();
globalThis.__BB_STORE = {
  get: async (k) => (mem.has(k) ? JSON.parse(mem.get(k)) : null),
  setJSON: async (k, v) => { mem.set(k, JSON.stringify(v)); },
};
let calls = [];
let sessions = {};
let gemini = () => ({ ok: true, body: { candidates: [{ content: { parts: [{ text: JSON.stringify({ style: "dark trap", boothmate_prompts: ["Set the tempo to 140 BPM."] }) }] } }] } });
let oembedOk = true;
globalThis.fetch = async (url, opts = {}) => {
  url = String(url); calls.push({ url, opts });
  const res = (status, body) => new Response(JSON.stringify(body), { status });
  if (url.startsWith("https://www.youtube.com/oembed")) return oembedOk ? res(200, { title: "Test Beat", author_name: "Prod X" }) : res(404, {});
  if (url === "https://api.stripe.com/v1/checkout/sessions" && opts.method === "POST") {
    const f = new URLSearchParams(opts.body);
    const id = "cs_test_" + (Object.keys(sessions).length + 1);
    sessions[id] = { id, payment_status: "unpaid", metadata: { youtube_url: f.get("metadata[youtube_url]"), video_title: f.get("metadata[video_title]") } };
    return res(200, { id, url: "https://checkout.stripe.com/c/pay/" + id, _form: Object.fromEntries(f) });
  }
  const m = url.match(/^https:\/\/api\.stripe\.com\/v1\/checkout\/sessions\/(.+)$/);
  if (m) return sessions[m[1]] ? res(200, sessions[m[1]]) : res(404, { error: { message: "No such session" } });
  if (url.includes("generativelanguage.googleapis.com")) { const g = gemini(opts); return res(g.ok ? 200 : 400, g.body); }
  if (url.includes("run-breakdown-background")) return new Response(null, { status: 202 });
  throw new Error("unexpected fetch " + url);
};
process.env.STRIPE_SECRET_KEY = "sk_test_x";
process.env.GEMINI_API_KEY = "g_x";
process.env.BEAT_BREAKDOWN_PRICE_ID = "price_x";
process.env.URL = "https://boothmate.example";

const { parseYouTube } = await import("../netlify/functions/lib/common.mjs");
const checkout = (await import("../netlify/functions/checkout.mjs")).default;
const breakdown = (await import("../netlify/functions/breakdown.mjs")).default;
const runBg = (await import("../netlify/functions/run-breakdown-background.mjs")).default;
const post = (path, body) => new Request("https://boothmate.example" + path, { method: "POST", body: JSON.stringify(body), headers: { "content-type": "application/json" } });

beforeEach(() => { mem.clear(); calls = []; sessions = {}; oembedOk = true; });

test("parses every common YouTube link shape", () => {
  for (const u of ["https://www.youtube.com/watch?v=u1Gte5Jt-P4&t=3s", "https://youtu.be/u1Gte5Jt-P4?si=x", "https://m.youtube.com/watch?v=u1Gte5Jt-P4", "https://www.youtube.com/shorts/u1Gte5Jt-P4", "https://music.youtube.com/watch?v=u1Gte5Jt-P4"])
    assert.equal(parseYouTube(u)?.url, "https://www.youtube.com/watch?v=u1Gte5Jt-P4", u);
  for (const u of ["", "hello", "https://vimeo.com/123", "https://www.youtube.com/watch?v=short", "https://evil.com/watch?v=u1Gte5Jt-P4"])
    assert.equal(parseYouTube(u), null, u);
});

test("checkout rejects bad and private links before any charge", async () => {
  let r = await checkout(post("/api/checkout", { url: "not a link" }));
  assert.equal(r.status, 400);
  oembedOk = false;
  r = await checkout(post("/api/checkout", { url: "https://youtu.be/u1Gte5Jt-P4" }));
  assert.equal(r.status, 400);
  assert.ok(!calls.some((c) => c.url.includes("stripe")), "no Stripe call for a dead video");
});

test("checkout creates a $22.99 session carrying the video", async () => {
  const r = await checkout(post("/api/checkout", { url: "https://youtu.be/u1Gte5Jt-P4" }));
  assert.equal(r.status, 200);
  const j = await r.json();
  assert.match(j.url, /^https:\/\/checkout\.stripe\.com/);
  const form = new URLSearchParams(calls.find((c) => c.opts.method === "POST").opts.body);
  assert.equal(form.get("line_items[0][price]"), "price_x");
  assert.equal(form.get("metadata[youtube_url]"), "https://www.youtube.com/watch?v=u1Gte5Jt-P4");
  assert.equal(form.get("success_url"), "https://boothmate.example/breakdown.html?session_id={CHECKOUT_SESSION_ID}");
});

test("without a Price id, checkout charges $22.99 inline", async () => {
  delete process.env.BEAT_BREAKDOWN_PRICE_ID;
  try {
    const r = await checkout(post("/api/checkout", { url: "https://youtu.be/u1Gte5Jt-P4" }));
    assert.equal(r.status, 200);
    const form = new URLSearchParams(calls.find((c) => c.opts.method === "POST").opts.body);
    assert.equal(form.get("line_items[0][price_data][unit_amount]"), "2299");
    assert.equal(form.get("line_items[0][price_data][currency]"), "usd");
    assert.equal(form.get("line_items[0][price]"), null);
  } finally { process.env.BEAT_BREAKDOWN_PRICE_ID = "price_x"; }
});

test("unpaid or made-up sessions get nothing", async () => {
  await checkout(post("/api/checkout", { url: "https://youtu.be/u1Gte5Jt-P4" }));
  let r = await breakdown(post("/api/breakdown", { session_id: "cs_test_1" }));
  assert.equal(r.status, 402);
  r = await breakdown(post("/api/breakdown", { session_id: "cs_test_999" }));
  assert.equal(r.status, 402);
  r = await breakdown(post("/api/breakdown", { session_id: "../../etc" }));
  assert.equal(r.status, 402);
  await runBg(post("/x", { session_id: "cs_test_1" }));
  assert.ok(!calls.some((c) => c.url.includes("generativelanguage")), "no Gemini call without payment");
});

test("paid session runs once, stores the result, and doesn't run again", async () => {
  await checkout(post("/api/checkout", { url: "https://youtu.be/u1Gte5Jt-P4" }));
  sessions.cs_test_1.payment_status = "paid";
  let r = await breakdown(post("/api/breakdown", { session_id: "cs_test_1" }));
  assert.equal(r.status, 202);
  r = await breakdown(post("/api/breakdown", { session_id: "cs_test_1" }));
  assert.equal((await r.json()).status, "running", "second start while running doesn't re-run");
  await runBg(post("/x", { session_id: "cs_test_1" }));
  const g = calls.find((c) => c.url.includes("generativelanguage"));
  const body = JSON.parse(g.opts.body);
  assert.equal(body.contents[0].parts[0].file_data.file_uri, "https://www.youtube.com/watch?v=u1Gte5Jt-P4");
  assert.equal(body.generationConfig.responseMimeType, "application/json");
  assert.match(g.url, /gemini-4-hydrogen:generateContent$/);
  r = await breakdown(new Request("https://boothmate.example/api/breakdown?session_id=cs_test_1"));
  const j = await r.json();
  assert.equal(j.status, "done");
  assert.equal(j.result.style, "dark trap");
  const before = calls.filter((c) => c.url.includes("generativelanguage")).length;
  await runBg(post("/x", { session_id: "cs_test_1" }));
  assert.equal(calls.filter((c) => c.url.includes("generativelanguage")).length, before, "done is never re-billed to Gemini");
});

test("failures are friendly, retryable, and capped at 3 attempts", async () => {
  await checkout(post("/api/checkout", { url: "https://youtu.be/u1Gte5Jt-P4" }));
  sessions.cs_test_1.payment_status = "paid";
  gemini = () => ({ ok: false, body: { error: { message: "Video is private" } } });
  for (let i = 0; i < 3; i++) {
    const r = await breakdown(post("/api/breakdown", { session_id: "cs_test_1" }));
    assert.equal(r.status, 202);
    await runBg(post("/x", { session_id: "cs_test_1" }));
    const s = await (await breakdown(new Request("https://boothmate.example/api/breakdown?session_id=cs_test_1"))).json();
    assert.equal(s.status, "error");
    assert.match(s.error, /private/);
  }
  const r = await breakdown(post("/api/breakdown", { session_id: "cs_test_1" }));
  assert.equal(r.status, 429);
  assert.match((await r.json()).error, /refund/);
});
