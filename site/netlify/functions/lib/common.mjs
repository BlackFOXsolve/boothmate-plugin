// Shared helpers for the Beat Breakdown functions.
import { getStore } from "@netlify/blobs";

// The landing page is also previewed inside Claude, so the two public endpoints
// (free preview and checkout) answer cross-origin requests. No cookies are used.
export const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "content-type",
  "access-control-max-age": "86400",
};

export const json = (status, body) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store", ...CORS },
  });

export const preflight = (req) => (req.method === "OPTIONS" ? new Response(null, { status: 204, headers: CORS }) : null);

// Accepts youtube.com/watch?v=, youtu.be/, /shorts/, /live/, m. and music. hosts.
export function parseYouTube(input) {
  let u;
  try { u = new URL(String(input || "").trim()); } catch { return null; }
  const host = u.hostname.replace(/^(www|m|music)\./, "");
  let id = null;
  if (host === "youtu.be") id = u.pathname.slice(1).split("/")[0];
  else if (host === "youtube.com") {
    if (u.pathname === "/watch") id = u.searchParams.get("v");
    else {
      const m = u.pathname.match(/^\/(shorts|live|embed)\/([^/?#]+)/);
      if (m) id = m[2];
    }
  }
  if (!id || !/^[\w-]{11}$/.test(id)) return null;
  return { id, url: `https://www.youtube.com/watch?v=${id}` };
}

// Public metadata; fails for private, removed or non-embeddable videos.
export async function youTubeInfo(url) {
  const r = await fetch(`https://www.youtube.com/oembed?format=json&url=${encodeURIComponent(url)}`);
  if (!r.ok) return null;
  const j = await r.json();
  return { title: j.title, author: j.author_name, thumbnail: j.thumbnail_url };
}

export async function stripe(path, { method = "GET", form } = {}) {
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) throw new Error("STRIPE_SECRET_KEY is not set");
  const r = await fetch(`https://api.stripe.com/v1/${path}`, {
    method,
    headers: {
      authorization: `Bearer ${key}`,
      ...(form ? { "content-type": "application/x-www-form-urlencoded" } : {}),
    },
    body: form ? new URLSearchParams(form).toString() : undefined,
  });
  const j = await r.json();
  if (!r.ok) throw new Error(j?.error?.message || `Stripe ${r.status}`);
  return j;
}

// A paid Checkout Session is the customer's ticket for one breakdown.
export async function paidSession(sessionId) {
  if (!/^cs_(live|test)_[\w]+$/.test(String(sessionId || ""))) return null;
  const s = await stripe(`checkout/sessions/${sessionId}`);
  if (s.payment_status !== "paid") return null;
  const yt = parseYouTube(s.metadata?.youtube_url);
  if (!yt) return null;
  return { id: s.id, youtube: yt, title: s.metadata?.video_title || "", email: s.customer_details?.email || "", paymentIntent: s.payment_intent || null };
}

export const store = () => globalThis.__BB_STORE || getStore({ name: "beat-breakdowns", consistency: "strong" });
export const previewStore = () => globalThis.__BB_PREVIEW_STORE || getStore({ name: "beat-previews", consistency: "strong" });

export function siteUrl(req) {
  return process.env.URL || new URL(req.url).origin;
}

// Full refund of a Checkout Session's payment (used when a breakdown fails for good).
export async function refundSession(paid, reason) {
  if (!paid?.paymentIntent) throw new Error("No payment to refund");
  return stripe("refunds", { method: "POST", form: {
    payment_intent: typeof paid.paymentIntent === "string" ? paid.paymentIntent : paid.paymentIntent.id,
    reason: "requested_by_customer",
    "metadata[app]": "boothmate-beat-breakdown",
    "metadata[why]": String(reason || "breakdown failed").slice(0, 400),
  }});
}
