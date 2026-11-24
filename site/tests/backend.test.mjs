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
globalThis.__BB_TEST_STORE = mkStore("t:");
let testWorkerOk = true;
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
  if (url.includes("run-test-breakdown-background")) return new Response(null, { status: testWorkerOk ? 202 : 500 });
  throw new Error("unexpected fetch " + url);
};
process.env.STRIPE_SECRET_KEY = "sk_test_x";
process.env.GEMINI_API_KEY = "g_x";
process.env.BEAT_BREAKDOWN_PRICE_ID = "price_x";
process.env.URL = "https://boothmate.example";
process.env.BEAT_BREAKDOWN_OPEN = "true";

const { parseYouTube } = await import("../netlify/functions/lib/common.mjs");
const checkout = (await import("../netlify/functions/checkout.mjs")).default;
const breakdown = (await import("../netlify/functions/breakdown.mjs")).default;
const runBg = (await import("../netlify/functions/run-breakdown-background.mjs")).default;
const preview = (await import("../netlify/functions/preview.mjs")).default;
const runPreview = (await import("../netlify/functions/run-preview-background.mjs")).default;
const post = (path, body) => new Request("https://boothmate.example" + path, { method: "POST", body: JSON.stringify(body), headers: { "content-type": "application/json" } });

beforeEach(() => { mem.clear(); testWorkerOk = true; calls = []; sessions = {}; oembedOk = true; refunds = []; gemini = () => ({ ok: true, body: { candidates: [{ content: { parts: [{ text: JSON.stringify({ style: "dark trap", bpm: 140, key: "C minor", mood: ["dark"], hook: "Moody.", boothmate_prompts: ["Set the tempo to 140 BPM."] }) }] } }] } }); });

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

test("Beat Breakdown stays closed until BEAT_BREAKDOWN_OPEN=true", async () => {
  delete process.env.BEAT_BREAKDOWN_OPEN;
  try {
    const { default: preview } = await import("../netlify/functions/preview.mjs");
    const { default: checkout } = await import("../netlify/functions/checkout.mjs");
    const body = JSON.stringify({ url: "https://www.youtube.com/watch?v=u1Gte5Jt-P4" });
    const opts = { method: "POST", headers: { "content-type": "application/json" }, body };
    for (const fn of [preview, checkout]) {
      const r = await fn(new Request("https://boothmate.example/api/x", opts), {});
      assert.equal(r.status, 503);
      assert.equal((await r.json()).status, "closed");
    }
  } finally {
    process.env.BEAT_BREAKDOWN_OPEN = "true";
  }
});

// ---- Owner test mode -------------------------------------------------------
const testBd = (await import("../netlify/functions/test-breakdown.mjs")).default;
const runTestBg = (await import("../netlify/functions/run-test-breakdown-background.mjs")).default;
const { tidyBreakdown, breakdownPrompt, BREAKDOWN_SCHEMA, BREAKDOWN_PROMPT } = await import("../netlify/functions/lib/prompt.mjs");
const PREVIEW_CTX = { deploy: { context: "deploy-preview" } };
const PROD_CTX = { deploy: { context: "production" } };
const fullResult = { style: "Chicago drill", bpm: 133.4, key: "D minor", boothmate_genre: "drill", sound_setup: { channels: [], mixer_chains: [], performance_tips: [] },
  boothmate_prompts: ["Program drill drums for 4 bars on Kick, Snare, Hat.", "Set the tempo to 180 BPM and add markers.", "Load a FLEX bell preset on the Bell channel.", "Name the mixer tracks and pan the hats a little left."] };
const geminiFull = () => ({ ok: true, body: { candidates: [{ content: { parts: [{ text: JSON.stringify(fullResult) }] } }] } });

test("test mode is a 404 on production without the key, even when Beat Breakdown is closed", async () => {
  delete process.env.BEAT_BREAKDOWN_OPEN;
  try {
    for (const req of [post("/api/test-breakdown", { url: "https://youtu.be/u1Gte5Jt-P4" }), new Request("https://boothmate.example/api/test-breakdown"), post("/api/test-breakdown", { url: "https://youtu.be/u1Gte5Jt-P4", key: "guess" })]) {
      const r = await testBd(req, PROD_CTX);
      assert.equal(r.status, 404);
    }
    process.env.BB_TEST_KEY = "secret-key-123";
    let r = await testBd(post("/api/test-breakdown", { url: "https://youtu.be/u1Gte5Jt-P4", key: "secret-key-12X" }), PROD_CTX);
    assert.equal(r.status, 404, "wrong key");
    r = await testBd(post("/api/test-breakdown?key=secret-key-123", { url: "https://youtu.be/u1Gte5Jt-P4" }), PROD_CTX);
    assert.equal(r.status, 202, "right key works on production, closed or not");
  } finally { delete process.env.BB_TEST_KEY; process.env.BEAT_BREAKDOWN_OPEN = "true"; }
  assert.ok(!calls.some((c) => c.url.includes("stripe")), "never touches Stripe");
});

test("test mode on a deploy preview runs the full paid breakdown with no payment", async () => {
  gemini = geminiFull;
  let r = await testBd(new Request("https://deploy-preview-7--boothmate.netlify.app/api/test-breakdown"), PREVIEW_CTX);
  assert.deepEqual(await r.json(), { status: "ready", used: 0, limit: 25, geminiReady: true, context: "deploy-preview" });
  r = await testBd(new Request("https://deploy-preview-7--boothmate.netlify.app/api/test-breakdown", { method: "POST", body: JSON.stringify({ url: "https://youtu.be/u1Gte5Jt-P4" }) }), PREVIEW_CTX);
  assert.equal(r.status, 202);
  const { id, video } = await r.json();
  assert.match(id, /^[a-f0-9]{12}$/);
  assert.equal(video.title, "Test Beat");
  assert.ok(calls.some((c) => c.url === "https://deploy-preview-7--boothmate.netlify.app/.netlify/functions/run-test-breakdown-background"), "worker is called on this deploy, not production");
  r = await testBd(new Request(`https://x/api/test-breakdown?id=${id}`), PREVIEW_CTX);
  assert.equal((await r.json()).status, "running");
  await runTestBg(post("/x", { id }));
  const g = calls.find((c) => c.url.includes("generativelanguage"));
  const body = JSON.parse(g.opts.body);
  assert.equal(body.contents[0].parts[0].file_data.file_uri, "https://www.youtube.com/watch?v=u1Gte5Jt-P4");
  assert.equal(body.contents[0].parts[0].video_metadata.end_offset, "600s", "whole video up to 10 minutes");
  assert.ok(body.contents[0].parts[1].text.startsWith(BREAKDOWN_PROMPT), "same prompt as the paid breakdown");
  assert.match(body.contents[0].parts[1].text, /Video title .*"Test Beat"/);
  assert.deepEqual(body.generationConfig.responseSchema, BREAKDOWN_SCHEMA, "same schema as the paid breakdown");
  r = await testBd(new Request(`https://x/api/test-breakdown?id=${id}`), PREVIEW_CTX);
  const j = await r.json();
  assert.equal(j.status, "done");
  assert.equal(j.result.bpm, 133);
  assert.equal(j.result.boothmate_prompts[0], "Set the tempo to 133 BPM and add markers.", "tempo first and matching the reported bpm");
  assert.ok(!j.result.boothmate_prompts.some((p) => /Load a FLEX/.test(p)), "load steps are not prompts");
  assert.deepEqual(j.result.sound_setup.manual_steps, ["Load a FLEX bell preset on the Bell channel."]);
  const n = calls.filter((c) => c.url.includes("generativelanguage")).length;
  await runTestBg(post("/x", { id }));
  await runTestBg(post("/x", { id: "abcdefabcdef" }));
  assert.equal(calls.filter((c) => c.url.includes("generativelanguage")).length, n, "worker only runs jobs the endpoint started, once");
  assert.ok(!mem.has("b:" + id), "test jobs live in their own store");
});

test("test mode is capped at 25 runs per UTC day; runs that never start don't count", async () => {
  testWorkerOk = false;
  let r = await testBd(post("/api/test-breakdown", { url: "https://youtu.be/u1Gte5Jt-P4" }), PREVIEW_CTX);
  const j = await r.json();
  assert.equal(j.status, "error");
  assert.match(j.error, /couldn't start/);
  testWorkerOk = true;
  for (let i = 0; i < 25; i++) {
    r = await testBd(post("/api/test-breakdown", { url: "https://youtu.be/u1Gte5Jt-P4" }), PREVIEW_CTX);
    assert.equal(r.status, 202, "run " + (i + 1));
  }
  r = await testBd(post("/api/test-breakdown", { url: "https://youtu.be/u1Gte5Jt-P4" }), PREVIEW_CTX);
  assert.equal(r.status, 429);
  assert.match((await r.json()).error, /25 test runs/);
});

test("test mode: bad links, failures and missing keys give clear messages", async () => {
  let r = await testBd(post("/api/test-breakdown", { url: "nope" }), PREVIEW_CTX);
  assert.equal(r.status, 400);
  oembedOk = false;
  r = await testBd(post("/api/test-breakdown", { url: "https://youtu.be/u1Gte5Jt-P4" }), PREVIEW_CTX);
  assert.equal(r.status, 400);
  oembedOk = true;
  gemini = () => ({ ok: true, body: { candidates: [{ finishReason: "MAX_TOKENS", content: { parts: [{ text: '{"style": "dri' }] } }] } });
  r = await testBd(post("/api/test-breakdown", { url: "https://youtu.be/u1Gte5Jt-P4" }), PREVIEW_CTX);
  const { id } = await r.json();
  await runTestBg(post("/x", { id }));
  const j = await (await testBd(new Request(`https://x/api/test-breakdown?id=${id}`), PREVIEW_CTX)).json();
  assert.equal(j.status, "error");
  assert.match(j.error, /incomplete/);
  assert.match(j.detail, /MAX_TOKENS/, "owner sees the technical detail");
  r = await testBd(new Request("https://x/api/test-breakdown?id=../../x"), PREVIEW_CTX);
  assert.equal(r.status, 400);
  const k = process.env.GEMINI_API_KEY; delete process.env.GEMINI_API_KEY;
  try {
    r = await testBd(post("/api/test-breakdown", { url: "https://youtu.be/u1Gte5Jt-P4" }), PREVIEW_CTX);
    assert.equal(r.status, 503);
    assert.match((await r.json()).error, /GEMINI_API_KEY/);
  } finally { process.env.GEMINI_API_KEY = k; }
});

test("paid breakdown uses the same tidy-up and the video title hint", async () => {
  gemini = geminiFull;
  await checkout(post("/api/checkout", { url: "https://youtu.be/u1Gte5Jt-P4" }));
  sessions.cs_test_1.payment_status = "paid";
  await breakdown(post("/api/breakdown", { session_id: "cs_test_1" }));
  await runBg(post("/x", { session_id: "cs_test_1" }));
  const g = calls.find((c) => c.url.includes("generativelanguage"));
  assert.match(JSON.parse(g.opts.body).contents[0].parts[1].text, /"Test Beat"/);
  const j = await (await breakdown(new Request("https://boothmate.example/api/breakdown?session_id=cs_test_1"))).json();
  assert.equal(j.result.boothmate_prompts[0], "Set the tempo to 133 BPM and add markers.");
});

test("prompt + schema: tempo check, capabilities, sound setup, old fields kept", () => {
  for (const f of ["style", "vibe", "bpm", "bpm_confidence", "key", "key_confidence", "drums", "bass_808", "melody", "arrangement", "mix_notes", "fl_studio_sounds", "boothmate_prompts", "notes"])
    assert.ok(BREAKDOWN_SCHEMA.required.includes(f), "still required: " + f);
  for (const f of ["sound_setup", "bpm_why", "key_why", "style_why", "tempo_check", "mode", "boothmate_genre"])
    assert.ok(BREAKDOWN_SCHEMA.properties[f], "new field: " + f);
  assert.deepEqual(BREAKDOWN_SCHEMA.properties.boothmate_genre.enum, ["trap", "drill", "boom_bap", "rnb", "lofi", "jersey_club"]);
  assert.match(BREAKDOWN_PROMPT, /Half\/double-time check/);
  assert.match(BREAKDOWN_PROMPT, /Chicago drill: about 130-150/);
  assert.match(BREAKDOWN_PROMPT, /BoothMate CANNOT/);
  assert.match(BREAKDOWN_PROMPT, /Fruity Soft Clipper/);
  assert.match(BREAKDOWN_PROMPT, /never names the original song/);
  assert.equal(breakdownPrompt({}), BREAKDOWN_PROMPT);
  assert.ok(!breakdownPrompt({ title: "a\nb" }).includes("a\nb"), "title can't inject new lines");
});

test("tidyBreakdown: adds a tempo prompt when missing and leaves good results alone", () => {
  let t = tidyBreakdown({ bpm: 142, boothmate_prompts: ["Program drill drums for 4 bars."] });
  assert.deepEqual(t.boothmate_prompts, ["Set the tempo to 142 BPM.", "Program drill drums for 4 bars."]);
  const good = { bpm: 140, boothmate_prompts: ["Set the tempo to 140 BPM.", "Program trap drums for 8 bars.", "Name mixer track 1 '808' and keep it centered."] };
  t = tidyBreakdown(good);
  assert.deepEqual(t.boothmate_prompts, good.boothmate_prompts);
  assert.equal(t.sound_setup, undefined);
  assert.equal(tidyBreakdown(null), null);
});

const { reconcileTempo, PREVIEW_PROMPT } = await import("../netlify/functions/lib/prompt.mjs");
const { isTransient } = await import("../netlify/functions/lib/gemini.mjs");

test("tempo: a half/double-time slip is fixed against the genre, and every prompt uses one BPM", () => {
  assert.deepEqual(reconcileTempo(133, "drill"), { bpm: 133, changed: false });
  assert.equal(reconcileTempo(66.5 * 2, "drill").changed, false);
  assert.equal(reconcileTempo(67, "drill").bpm, 134, "half-time drill reading doubled");
  assert.equal(reconcileTempo(280, "trap").bpm, 140, "double-time trap reading halved");
  assert.equal(reconcileTempo(180, "boom_bap").bpm, 90);
  assert.equal(reconcileTempo(200, "unknown").changed, false, "no genre, no guess");
  const t = tidyBreakdown({ bpm: 67, bpm_confidence: "high", boothmate_genre: "drill", notes: "Instrumental.",
    boothmate_prompts: ["Set the tempo to 67 BPM.", "Program drill drums for 8 bars at 67 BPM.", "Write a dark 808 in D minor."] });
  assert.equal(t.bpm, 134);
  assert.equal(t.bpm_confidence, "medium");
  assert.deepEqual(t.boothmate_prompts.slice(0, 2), ["Set the tempo to 134 BPM.", "Program drill drums for 8 bars at 134 BPM."]);
  assert.match(t.notes, /^Instrumental\. Tempo corrected from 67 to 134 BPM/);
  const ok = tidyBreakdown({ bpm: 142, boothmate_genre: "drill", notes: "x", boothmate_prompts: ["Set the tempo to 142 BPM."] });
  assert.equal(ok.notes, "x", "in-range tempo is left alone");
});

test("tidyBreakdown keeps doable prompts that merely mention an effect", () => {
  const t = tidyBreakdown({ bpm: 140, boothmate_prompts: ["Set the tempo to 140 BPM.", "Write dark chords in C minor on the Pad channel, 2 bars each; they'll sit under reverb later.", "Add Fruity Reeverb 2 to the Pad track."] });
  assert.equal(t.boothmate_prompts.length, 2);
  assert.match(t.boothmate_prompts[1], /Write dark chords/);
  assert.deepEqual(t.sound_setup.manual_steps, ["Add Fruity Reeverb 2 to the Pad track."]);
});

test("test mode retries once when Gemini's answer is cut off or Gemini is busy, never for blocks", async () => {
  process.env.BB_RETRY_WAIT_MS = "0";
  try {
    let n = 0;
    gemini = () => (++n === 1 ? { ok: true, body: { candidates: [{ finishReason: "MAX_TOKENS", content: { parts: [{ text: '{"sty' }] } }] } } : geminiFull());
    let r = await testBd(post("/api/test-breakdown", { url: "https://youtu.be/u1Gte5Jt-P4" }), PREVIEW_CTX);
    let { id } = await r.json();
    await runTestBg(post("/x", { id }));
    let j = await (await testBd(new Request(`https://x/api/test-breakdown?id=${id}`), PREVIEW_CTX)).json();
    assert.equal(j.status, "done");
    assert.equal(n, 2);
    n = 0;
    gemini = () => { n++; return { ok: true, body: { promptFeedback: { blockReason: "SAFETY" } } }; };
    r = await testBd(post("/api/test-breakdown", { url: "https://youtu.be/u1Gte5Jt-P4" }), PREVIEW_CTX);
    ({ id } = await r.json());
    await runTestBg(post("/x", { id }));
    j = await (await testBd(new Request(`https://x/api/test-breakdown?id=${id}`), PREVIEW_CTX)).json();
    assert.equal(j.status, "error");
    assert.equal(n, 1, "a blocked video isn't retried");
    assert.match(j.error, /declined/);
  } finally { delete process.env.BB_RETRY_WAIT_MS; }
  assert.ok(isTransient(new Error("Gemini 503: The model is overloaded.")));
  assert.ok(isTransient(new Error("Gemini 429: Resource has been exhausted (check quota).")));
  assert.ok(!isTransient(new Error("Gemini 400: Video is private.")));
  assert.ok(!isTransient(new Error("GEMINI_API_KEY is not set")));
});

test("free preview uses the same tempo rules as the full breakdown", () => {
  assert.match(PREVIEW_PROMPT, /Half\/double-time check/);
  assert.match(PREVIEW_PROMPT, /Chicago drill: about 130-150/);
});
