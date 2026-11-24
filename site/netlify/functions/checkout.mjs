// POST /api/checkout { url } -> { url: <Stripe Checkout> }
// Checks the YouTube link first so nobody pays for a dead or private video.
import { json, parseYouTube, youTubeInfo, stripe, siteUrl, preflight } from "./lib/common.mjs";

export default async (req) => {
  const pre = preflight(req); if (pre) return pre;
  if (req.method !== "POST") return json(405, { error: "Use POST." });
  let body = {};
  try { body = await req.json(); } catch {}
  const yt = parseYouTube(body.url);
  if (!yt) return json(400, { error: "That doesn't look like a YouTube video link. Paste the link from the video's Share button." });

  const info = await youTubeInfo(yt.url);
  if (!info) return json(400, { error: "We can't open that video. It may be private, removed or age-restricted. Try another link." });

  // A Stripe Price id if one is set up; otherwise the $22.99 sale price inline.
  const price = process.env.BEAT_BREAKDOWN_PRICE_ID;
  const cents = Number(process.env.BEAT_BREAKDOWN_PRICE_CENTS || 2299);
  const item = price
    ? { "line_items[0][price]": price }
    : {
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][unit_amount]": String(cents),
        "line_items[0][price_data][product_data][name]": "BoothMate Beat Breakdown",
        "line_items[0][price_data][product_data][description]": "One beat breakdown: tempo, key, drums, 808, sounds, arrangement and BoothMate prompts.",
      };

  const site = siteUrl(req);
  let session;
  try {
  session = await stripe("checkout/sessions", {
    method: "POST",
    form: {
      mode: "payment",
      ...item,
      "line_items[0][quantity]": "1",
      success_url: `${site}/breakdown.html?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${site}/#beat-breakdown`,
      "metadata[youtube_url]": yt.url,
      "metadata[video_title]": (info.title || "").slice(0, 400),
      "payment_intent_data[description]": `Beat Breakdown: ${(info.title || yt.url).slice(0, 200)}`,
      "custom_text[submit][message]": `Breakdown of: ${(info.title || yt.url).slice(0, 180)}`,
    },
  });
  } catch (e) {
    console.error("checkout failed", e);
    return json(503, { error: "Checkout isn't available right now. Please try again in a few minutes." });
  }
  return json(200, { url: session.url, video: { id: yt.id, ...info } });
};

export const config = { path: "/api/checkout" };
