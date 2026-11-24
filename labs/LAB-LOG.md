# BoothMate Labs: overnight log (Nov 24, 2026)

Alan's test tonight: the landing-page prompt set (180 BPM, D minor pad/bell/half-time drums/808 slide, breakdown clone, mixer) ran fine in FL Studio but "sounded nothing like" the King Von / Lil Durk type beat it was meant to resemble.

## The four problems
1. **Sounds.** Stock trial sounds (classic 808 kit, Choir Aahs, FL Keys) instead of drill sounds; BoothMate can't load instruments/samples/presets.
2. **No mixing.** No 808 distortion/saturation, compression, reverb; flat velocities.
3. **Analysis contradicts itself.** site/public/sample-breakdown.json says "Melodic Trap, 180 BPM, D minor" for video u1Gte5Jt-P4; a live Gemini preview of the same video said "Chicago drill, 133 BPM, D minor".
4. **Missing tools.** Link a channel to a mixer track; load an instrument/sample/preset; delete markers; pattern length reported as 32 bars for 8 bars of music.

## Rules for every run
- Work only on branch `labs/overnight-2026-11-24`. Never push to `main` (main auto-deploys the live site).
- Techniques and style only: never reproduce a real producer's melody, drum pattern or samples.
- No FL Studio, no Alan's Mac, no live site, no payments. Offline code, math, tests and research only.
- Every claim about FL Studio's Python API must cite the Image-Line docs page it came from, or be marked UNVERIFIED.
- Append to this log at the end of every run: what you tried, measured results, what's next.

## Log

### 2026-11-24 run (owner test mode + accuracy), PR #1
**Preview to test:** https://deploy-preview-1--boothmate-d4e6.netlify.app/test.html (Netlify reported "Deploy Preview ready" for commit 4471a6e). PR: https://github.com/BlackFOXsolve/boothmate-plugin/pull/1. Don't merge before Alan reviews; main auto-deploys.

Done
1. Test mode: `site/public/test.html` plus `/api/test-breakdown` (POST {url} starts a run, GET ?id= polls it) and `run-test-breakdown-background.mjs`.
   - Runs the same prompt, schema and 10-minute window as the paid breakdown, with no Stripe and regardless of BEAT_BREAKDOWN_OPEN.
   - Allowed only when the Netlify deploy context (`context.deploy.context`, falling back to `process.env.CONTEXT`) is deploy-preview or branch-deploy, or when `key` matches BB_TEST_KEY. Otherwise it returns 404.
   - Stores runs in the Blobs store `beat-breakdown-tests`, capped at 25 per UTC day; a run that fails to start doesn't count.
   - The worker is called on the request's own origin, because on a preview `process.env.URL` is production.
   - The page shows the embedded video, progress with an elapsed timer, the shared result view, Copy all prompts, the raw JSON, and the technical error detail (owner only).
2. Accuracy (`lib/prompt.mjs`):
   - Order of work: style from the drums, then tempo with a required half/double-time check against genre tempo ranges, then key + mode.
   - Each of style, tempo and key gets a confidence and a "why".
   - New fields: `tempo_check`, `boothmate_genre`/`boothmate_mood` enums, and `sound_setup` (stock channel loads with channel names and editions, mixer chains, velocity/glide tips).
   - The video title is passed as a hint. All old fields are kept, so old results still render.
3. Prompts: a compact BoothMate capability list (from SKILL.md and tools/beginner.py: genres, moods, channel-name matching, the CANNOT list) is now in the prompt, which asks for 6-9 ordered prompts.
   - `tidyBreakdown()` makes the tempo prompt come first and match the reported BPM, and moves load/effect/export prompts to `sound_setup.manual_steps`.
   - Used by both the paid and test runs.
4. PR #1 is open, and the Netlify deploy preview built successfully.
5. `sample-breakdown.json` is now marked illustrative and reconciled to Chicago drill, 133 BPM, D minor, with a sound setup and drill prompts.
   - `gemini.mjs`: clear errors when Gemini's answer is cut off, empty or blocked.
   - The result renderer is shared (`breakdown-view.js`, `breakdown.css`).

Tests: `cd site && npm test` 16/16 pass (7 new). `python -m pytest -q`: 378 passed, 13 skipped. This sandbox needed `pytest-asyncio` installed; there are no Python changes. Both pages were rendered in headless Chromium against a mock API at 1280 px and 390 px: no JS errors and no sideways scrolling.

NOT verified: no live Gemini call. The sandbox can't reach Google or netlify.app, so prompt quality is untested on real audio. Also unconfirmed:
- that Gemini (through the Netlify AI Gateway) accepts the bigger schema, which includes `propertyOrdering`;
- that GEMINI_API_KEY applies to the Deploy Preview context. test.html warns if it doesn't.
If a run fails with "incomplete", open the technical detail; MAX_TOKENS would mean the schema needs trimming.

How Alan tests: open the preview /test.html, paste a link, wait 1-4 minutes, load the sounds in step 1, run the step 2 prompts in FL Studio, then A/B against the embedded video.

Next: run u1Gte5Jt-P4 on the preview and compare it with the live preview's reading (Chicago drill 133). If the tempo still disagrees, consider a second, cheap tempo-only Gemini pass.

### 2026-11-24 second run (reliability pass), PR #1
Items 1-5 were already done by the first run, so this run hardened what Alan will hit in the morning. Same preview URL: https://deploy-preview-1--boothmate-d4e6.netlify.app/test.html. (Netlify "canceled" the preview for the log-only commit cec89dc because site/ hadn't changed. That's normal; the preview kept serving 4471a6e. This run's commit fecb5e8 changed site/; Netlify reported "Deploy Preview ready!" for it at 11:45 UTC.)

Done
1. **Tempo slips are fixed in code, not just in the prompt.** `reconcileTempo()` in `lib/prompt.mjs`: if the BPM falls outside the chosen BoothMate genre's range (drill 125-155, trap 125-175, boom bap 75-100, lo-fi 65-95, R&B 55-110, jersey club 125-150) but half or double falls inside, it uses that value. It also adds a sentence to `notes` ("Tempo corrected from 67 to 134 BPM... if it feels wrong, try 67") and lowers `bpm_confidence` from high to medium. Every prompt now uses the same BPM, not only the first.
2. **Can't-do filter fixed.** "Add Fruity Reeverb 2 to the Pad track" used to slip through as a prompt (the filter only knew generic words like "reverb"). It now catches Fruity *, FLEX, Sytrus, Harmor, EQ, compressor, limiter, Gross Beat, Maximus and Pitcher. A doable prompt that only *mentions* an effect ("write dark chords... they'll sit under reverb") is no longer thrown out.
3. **One automatic retry in test mode.** It covers a cut-off or malformed Gemini answer, 429 and 5xx, waiting 5 s first (`BB_RETRY_WAIT_MS`). It never retries blocked, private or missing-key errors. Gemini errors now start with the HTTP status, e.g. "Gemini 503: ...". The paid flow is unchanged and keeps its own retry-then-refund logic.
4. **Free preview uses the same tempo guide** as the full breakdown, so the teaser and the full breakdown shouldn't disagree the way "180 melodic trap" and "133 Chicago drill" did.

Tests: `cd site && npm test` 20/20 pass (4 new: tempo reconcile, the effect-mention filter, retry vs. no-retry, preview tempo rules). Python: 378 passed, 11 skipped. 2 failures in `test_offline.py` come only from `rtmidi` not being installable in this sandbox; there are no Python changes. Ran `sample-breakdown.json` through the new tidy-up: unchanged (133, drill), all 7 prompts kept.

NOT verified: still no live Gemini call (the sandbox can't reach Google or netlify.app). The Netlify MCP doesn't show env-var scopes, so whether GEMINI_API_KEY applies to Deploy Previews is unconfirmed. test.html shows a warning if it doesn't.

How Alan tests: same as above. Open the preview /test.html, paste a link, wait 1-4 minutes, load the sounds, copy the prompts and run them in FL Studio, then A/B against the video. If the result says "Tempo corrected", try both tempos against the video.

Next: compare a real run of u1Gte5Jt-P4 with the 133 reading. If key or tempo still wanders between runs, add a cheap second Gemini pass that only asks for tempo and key.

### 2026-11-24 third run (final check before Alan wakes), PR #1
**Preview to test:** https://deploy-preview-1--boothmate-d4e6.netlify.app/test.html. Netlify reported "Deploy Preview ready!" for commit 745291e at 13:14 UTC. This log-only commit will show as "Deploy Preview canceled" on GitHub because site/ didn't change. That's expected: the preview keeps serving 745291e.

Verified first
- Items 1-5 were all done by the earlier runs. `cd site && npm test` passed 20/20 before any changes. Python passed 378, with 2 failures in `test_offline.py` because `rtmidi` can't be installed in this sandbox. GitHub CI is green on Windows and Linux. 3 macOS jobs on 11:47's run were *cancelled* after 15 minutes, not failed (a runner queue/timeout, not code).
- PR #1 is open. Netlify project settings show no password or SSO on previews, so the page and its background worker are reachable. I can't see env-var scopes, so I couldn't confirm that GEMINI_API_KEY applies to Deploy Previews. test.html warns if it doesn't.

Done
1. **Steadier readings.** Gemini temperature is now 0.2 (was 0.4) for the free preview, the paid breakdown and test runs, so the same video should give the same style, tempo and key run to run. To change it, set the `GEMINI_TEMPERATURE` env var. No code change is needed.
2. **Honest error messages.** A Gemini outage ("Gemini 503: Service Unavailable") used to show "Gemini couldn't open this video" because the text contains "unavailable". It now says "Our analyser is busy right now". Lost connections say so too.
3. PR body updated with both changes.

Tests: site 21/21 (1 new: temperature default/override and error wording). Python unchanged (378 passed).

NOT verified: still no live Gemini call (the sandbox can't reach Google or netlify.app).

How Alan tests: open the preview /test.html and paste a beat link. Wait 1-4 minutes. Load the sounds in step 1, then Copy all prompts and run them in FL Studio, and A/B against the video. For the accuracy check, run u1Gte5Jt-P4 twice: style, tempo and key should match both times (expected: around Chicago drill, ~133 BPM).

Next: if a run fails, the "Technical detail" box says why. `Gemini 4xx` on the schema means trim the schema; "no GEMINI_API_KEY" means switch the key on for Deploy Previews in Netlify (Alan's call).
