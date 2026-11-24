// Background function (name ends in -background): Netlify answers 202 right away
// and lets this run for up to 15 minutes. It re-checks the payment itself, so a
// direct call without a paid session does nothing. If the breakdown fails on
// the customer's last allowed attempt, the payment is refunded automatically.
import { paidSession, store, refundSession } from "./lib/common.mjs";
import { geminiVideo, friendly } from "./lib/gemini.mjs";
import { breakdownPrompt, BREAKDOWN_SCHEMA, tidyBreakdown } from "./lib/prompt.mjs";

export const MAX_ATTEMPTS = 3;
const MAX_SECONDS = Number(process.env.BREAKDOWN_MAX_SECONDS || 600); // analyse at most the first 10 minutes

export default async (req) => {
  let sessionId = null;
  try { sessionId = (await req.json()).session_id; } catch {}
  const paid = await paidSession(sessionId).catch(() => null);
  if (!paid) return;

  const db = store();
  const rec = (await db.get(paid.id, { type: "json" })) || {};
  if (rec.status === "done" || rec.refunded) return;
  const save = (patch) => db.setJSON(paid.id, { ...rec, ...patch, updated: Date.now() });

  try {
    const result = tidyBreakdown(await geminiVideo({ url: paid.youtube.url, prompt: breakdownPrompt({ title: paid.title }), schema: BREAKDOWN_SCHEMA, seconds: MAX_SECONDS }));
    if (!result?.boothmate_prompts?.length) throw new Error("Empty breakdown");
    await save({ status: "done", result, error: null, finished: Date.now() });
  } catch (e) {
    console.error("breakdown failed", paid.id, e);
    const error = friendly(e);
    if ((rec.attempts || 0) >= MAX_ATTEMPTS) {
      try {
        const refund = await refundSession(paid, error);
        return await save({ status: "error", error, refunded: true, refundId: refund.id });
      } catch (re) {
        console.error("auto refund failed", paid.id, re);
        return await save({ status: "error", error, refundFailed: true });
      }
    }
    await save({ status: "error", error });
  }
};
