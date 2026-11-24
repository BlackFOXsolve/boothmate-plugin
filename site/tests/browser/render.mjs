import { JSDOM } from "jsdom";
import { readFileSync } from "node:fs";
const html = readFileSync("public/index.html", "utf8");
const dom = new JSDOM(html, { runScripts: "outside-only", url: "https://boothmate.example/", pretendToBeVisual: true });
const w = dom.window;
w.eval(readFileSync("public/morphdom.min.js", "utf8"));
w.eval(readFileSync("public/dc-lite.js", "utf8"));
const inline = [...w.document.querySelectorAll("script:not([src])")].map(s => s.textContent).join("\n");
let fetched = null;
w.fetch = async (u, o) => { fetched = { u, o }; return { ok: false, json: async () => ({ error: "We can't open that video. It may be private." }) }; };
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
checks.fetchUrl = fetched && fetched.u;
checks.fetchBody = fetched && fetched.o.body;
checks.errorShown = (app.querySelector('[role=alert]') || {}).textContent;
checks.inputKept = app.querySelector("#bm-yt").value;
// setup walkthrough mac tab
[...app.querySelectorAll('[role=tab]')].find(b => b.textContent.trim() === "Mac").click(); await tick();
checks.macSteps = [...app.querySelectorAll("ol li")].map(li => li.textContent.trim().replace(/^\d+/, "")).join(" | ");
console.log(JSON.stringify(checks, null, 1));
process.exit(0);
