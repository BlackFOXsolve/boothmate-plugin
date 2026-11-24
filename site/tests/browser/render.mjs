import { JSDOM } from "jsdom";
import { readFileSync } from "node:fs";
const html = readFileSync("public/index.html", "utf8");
const dom = new JSDOM(html, { runScripts: "outside-only", url: "https://boothmate.example/", pretendToBeVisual: true });
const w = dom.window;
w.eval(readFileSync("public/morphdom.min.js", "utf8"));
w.eval(readFileSync("public/dc-lite.js", "utf8"));
const inline = [...w.document.querySelectorAll("script:not([src])")].map(s => s.textContent).join("\n");
let fetched = [];
w.fetch = async (u, o = {}) => { fetched.push({ u, o });
  if (u === "/api/preview") return { ok: true, json: async () => ({ status: "running", video: { id: "u1Gte5Jt-P4", url: "https://www.youtube.com/watch?v=u1Gte5Jt-P4", title: "Test beat" } }) };
  if (String(u).startsWith("/api/preview?v=")) return { ok: true, json: async () => ({ status: "done", preview: { style: "Chicago drill", bpm: 141.6, key: "C# minor", mood: ["dark"], hook: "Cold, menacing and ready for a verse." } }) };
  if (u === "/api/checkout") return { ok: false, json: async () => ({ error: "Checkout isn't set up yet." }) };
};
w.setTimeout = (f, ms) => setTimeout(f, Math.min(ms, 5));
w.eval(inline);
w.document.dispatchEvent(new w.Event("DOMContentLoaded"));
const tick = () => new Promise(r => setTimeout(r, 30));
await tick();
const app = w.document.getElementById("app");
const text = app.textContent;
const checks = {
  hero: text.includes("BoothMate"),
  prompts: text.includes("Prompt library") && app.querySelectorAll("article").length === 4,
  bb: text.includes("$22.99") && text.includes("$49.99") && text.includes("54% off"),
  noOld: !text.includes("$92") && !text.includes("Coming soon"),
  setup: text.includes("Set up once"),
  unboundLeft: (app.innerHTML.match(/\{\{/g) || []).length,
  logos: [...app.querySelectorAll("img")].map(i => i.getAttribute("src")).filter(s => s.includes("assets")).length,
};
// switch prompt tab
const tab = [...app.querySelectorAll('[role=tab]')].find(b => b.textContent.includes("Drums"));
tab.click(); await tick();
checks.tabSwitched = app.querySelectorAll("article").length === 5 && app.textContent.includes("Space my kicks");
// copy

w.navigator.clipboard = { writeText: async t => { checks.copiedText = t.slice(0, 30); } };
[...app.querySelectorAll("article button")][0].click(); await tick(); await tick();
checks.copyLabel = [...app.querySelectorAll("article button")][0].textContent.trim();
// Beat Breakdown form
const input = app.querySelector("#bm-yt");
input.value = "https://youtu.be/u1Gte5Jt-P4"; input.dispatchEvent(new w.Event("input", { bubbles: true })); await tick();
app.querySelector("form").dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true })); await tick(); await tick();
await new Promise(r => setTimeout(r, 60));
checks.previewCall = fetched[0] && fetched[0].u + " " + fetched[0].o.body;
checks.embed = (app.querySelector("iframe") || {}).src;
checks.preview = app.textContent.includes("Cold, menacing") && app.textContent.includes("142 BPM") && app.textContent.includes("C# minor");
checks.lockedItems = app.querySelectorAll(".bm-locked").length;
const unlock = [...app.querySelectorAll("button")].find(b => b.textContent.includes("Unlock the full blueprint"));
unlock.click(); await tick(); await tick();
checks.unlockCall = fetched.find(f => f.u === "/api/checkout")?.o.body;
checks.errorShown = (app.querySelector('[role=alert]') || {}).textContent;
checks.inputKept = app.querySelector("#bm-yt").value;
checks.logosInFlow = [...app.querySelectorAll("#beat-breakdown img")].map(i => i.getAttribute("src")).filter(s => s.startsWith("/assets/")).length;
// setup walkthrough mac tab
[...app.querySelectorAll('[role=tab]')].find(b => b.textContent.trim() === "Mac").click(); await tick();
checks.macSteps = [...app.querySelectorAll("ol li")].map(li => li.textContent.trim().replace(/^\d+/, "")).join(" | ");
console.log(JSON.stringify(checks, null, 1));
process.exit(0);
