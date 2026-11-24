import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";

// In-memory Blobs store + fake network for Stripe, YouTube oEmbed and Gemini.
const mem = new Map();
const mkStore = (prefix) => ({
  get: async (k, o) => { const v = mem.get(prefix + k); if (v == null) return null; return o?.type === "json" ? JSON.parse(v) : v; },
  set: async (k, v) => { mem.set(prefix + k, String(v)); },
  setJSON: async (k, v) => { mem.set(prefix + k, JSON.stringify(v)); },
});
globalThis.__BB_STORE = mkStore("b:");
globalThis.__BB_PREVIEW_STORE = mkStore("p:");
let refunds = [];
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
    sessions[id] = { id, payment_status: "unpaid", payment_intent: "pi_" + id, metadata: { youtube_url: f.get("metadata[youtube_url]"), video_title: f.get("metadata[video_title]") } };
    return res(200, { id, url: "https://checkout.stripe.com/c/pay/" + id, _form: Object.fromEntries(f) });
  }
  if (url === "https://api.stripe.com/v1/refunds") { const f = new URLSearchParams(opts.body); refunds.push(Object.fromEntries(f)); return res(200, { id: "re_" + refunds.length }); }
  if (url.includes("run-preview-background")) return new Response(null, { status: 202 });
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
const preview = (await import("../netlify/functions/preview.mjs")).default;
const runPreview = (await import("../netlify/functions/run-preview-background.mjs")).default;
const post = (path, body) => new Request("https://boothmate.example" + path, { method: "POST", body: JSON.stringify(body), headers: { "content-type": "application/json" } });

beforeEach(() => { mem.clear(); calls = []; sessions = {}; oembedOk = true; refunds = []; gemini = () => ({ ok: true, body: { candidates: [{ content: { parts: [{ text: JSON.stringify({ style: "dark trap", bpm: 140, key: "C minor", mood: ["dark"], hook: "Moody.", boothmate_prompts: ["Set the tempo to 140 BPM."] }) }] } }] } }); });

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

test("failures are friendly, retryable, and the 3rd failure refunds automatically", async () => {
  await checkout(post("/api/checkout", { url: "https://youtu.be/u1Gte5Jt-P4" }));
  sessions.cs_test_1.payment_status = "paid";
  gemini = () => ({ ok: false, body: { error: { message: "Video is private" } } });
  for (let i = 0; i < 3; i++) {
    const r = await breakdown(post("/api/breakdown", { session_id: "cs_test_1" }));
    assert.equal(r.status, 202);
    await runBg(post("/x", { session_id: "cs_test_1" }));
    const st = await (await breakdown(new Request("https://boothmate.example/api/breakdown?session_id=cs_test_1"))).json();
    assert.equal(st.status, "error");
    assert.match(st.error, /private/);
    assert.equal(st.refunded, i === 2, "refunded only after the last attempt");
    assert.equal(st.canRetry, i < 2);
  }
  assert.equal(refunds.length, 1);
  assert.equal(refunds[0].payment_intent, "pi_cs_test_1");
  const r = await breakdown(post("/api/breakdown", { session_id: "cs_test_1" }));
  assert.equal((await r.json()).refunded, true);
  await runBg(post("/x", { session_id: "cs_test_1" }));
  assert.equal(refunds.length, 1, "never refunded twice");
});

test("free preview: validates, runs once per video, caches, and caps per visitor", async () => {
  const ctx = { ip: "1.2.3.4" };
  let r = await preview(post("/api/preview", { url: "nope" }), ctx);
  assert.equal(r.status, 400);
  r = await preview(post("/api/preview", { url: "https://youtu.be/u1Gte5Jt-P4" }), ctx);
  assert.equal(r.status, 202);
  await runPreview(post("/x", { id: "u1Gte5Jt-P4" }));
  const g = calls.find((c) => c.url.includes("generativelanguage"));
  assert.equal(JSON.parse(g.opts.body).contents[0].parts[0].video_metadata.end_offset, "90s");
  r = await preview(new Request("https://boothmate.example/api/preview?v=u1Gte5Jt-P4"), ctx);
  const j = await r.json();
  assert.equal(j.status, "done");
  assert.equal(j.preview.key, "C minor");
  const n = calls.filter((c) => c.url.includes("generativelanguage")).length;
  r = await preview(post("/api/preview", { url: "https://www.youtube.com/watch?v=u1Gte5Jt-P4" }), { ip: "9.9.9.9" });
  assert.equal((await r.json()).status, "done", "cached for everyone");
  assert.equal(calls.filter((c) => c.url.includes("generativelanguage")).length, n, "no second Gemini call");
  for (let i = 0; i < 5; i++) await preview(post("/api/preview", { url: `https://youtu.be/AAAAAAAAAA${i}` }), ctx);
  r = await preview(post("/api/preview", { url: "https://youtu.be/BBBBBBBBBBB" }), ctx);
  assert.equal(r.status, 429, "7th new preview in a day is capped");
  await runPreview(post("/x", { id: "ZZZZZZZZZZZ" }));
  assert.equal(calls.filter((c) => c.url.includes("generativelanguage")).length, n, "worker ignores jobs nobody started");
});
