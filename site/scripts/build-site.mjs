// Turns the Claude Design page (Main.dc.html) into the public homepage.
// Usage: node scripts/build-site.mjs path/to/Main.dc.html
import { readFileSync, writeFileSync } from "node:fs";

const src = readFileSync(process.argv[2] || "design/Main.dc.html", "utf8");
const pick = (re, what) => { const m = src.match(re); if (!m) throw new Error("missing " + what); return m[1]; };

const helmet = pick(/<helmet>([\s\S]*?)<\/helmet>/, "helmet");
const logicTag = src.match(/<script type="text\/x-dc"[^>]*data-props='([^']*)'[^>]*>([\s\S]*?)<\/script>/);
if (!logicTag) throw new Error("missing logic script");
const props = JSON.parse(logicTag[1]);
const defaults = Object.fromEntries(Object.entries(props).filter(([k, v]) => !k.startsWith("$") && v && "default" in v).map(([k, v]) => [k, v.default]));
const afterHelmet = src.slice(src.indexOf("</helmet>") + "</helmet>".length, src.indexOf('<script type="text/x-dc"'));
const template = afterHelmet.replace(/\/_blob\/([a-f0-9]{32})/g, "/assets/$1.png").trim();
if (/<\/template>/i.test(template)) throw new Error("template contains </template>");
const logic = logicTag[2];

const title = "BoothMate: make beats in FL Studio by talking to Claude";
const desc = "Free Claude plugin for FL Studio. Ask for a beat in plain words and BoothMate writes the drums, 808s and chords. It runs inside Claude, free.";

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<meta name="description" content="${desc}">
<meta property="og:title" content="${title}">
<meta property="og:description" content="${desc}">
<meta property="og:type" content="website">
<meta name="theme-color" content="#0E0E11">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
${helmet.trim()}
<script src="/morphdom.min.js" defer></script>
<script src="/dc-lite.js" defer></script>
</head>
<body>
<div id="app"></div>
<noscript><p style="color:#ECECEF;font-family:system-ui;padding:32px">BoothMate's site needs JavaScript. You can also get BoothMate on <a href="https://github.com/BlackFOXsolve/boothmate-plugin">GitHub</a>.</p></noscript>
<template id="tpl">
${template}
</template>
<script>
window.addEventListener("DOMContentLoaded", function () {
${logic}
  window.dcLite.mount(Component, document.getElementById("app"), document.getElementById("tpl"), ${JSON.stringify(defaults)});
  if (location.hash) { var t = document.querySelector(location.hash); if (t) setTimeout(function () { t.scrollIntoView(); }, 60); }
});
</script>
</body>
</html>
`;
writeFileSync("public/index.html", html);
console.log("built public/index.html", html.length, "bytes; props", defaults);
