// Shared Beat Breakdown result renderer, used by breakdown.html (paid) and
// test.html (owner test mode) so both show exactly the same thing.
(function () {
  "use strict";
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function list(a) { return Array.isArray(a) ? a : []; }

  function videoBlock(v, label) {
    if (!v || !v.id) return "";
    return '<div class="video in"><img src="https://img.youtube.com/vi/' + esc(v.id) + '/hqdefault.jpg" alt=""><div><div class="label">' + esc(label || "Your breakdown") + '</div><h1 style="font-size:clamp(24px,3.4vw,34px)">' + esc(v.title || "Your beat") + '</h1><a href="' + esc(v.url) + '" target="_blank" rel="noopener" style="font-size:14px">Open on YouTube &#8599;</a></div></div>';
  }

  function soundSetup(ss) {
    if (!ss) return "";
    var ch = list(ss.channels), mx = list(ss.mixer_chains), tips = list(ss.performance_tips), manual = list(ss.manual_steps);
    if (!ch.length && !mx.length && !tips.length && !manual.length) return "";
    var h = '<div class="glass card"><div class="label"><span class="steps-n">1</span>Before the prompts</div><h2>Load these sounds</h2>' +
      '<p class="muted" style="margin:0">BoothMate can\'t load sounds or effects yet, so do this part by hand. Name each channel exactly as shown so BoothMate finds it.</p>';
    if (ch.length) h += '<table class="setup"><thead><tr><th>Part</th><th>Name the channel</th><th>Load (FL Studio stock)</th><th>Edition</th></tr></thead><tbody>' +
      ch.map(function (c) { return "<tr><td>" + esc(c.role) + "</td><td><code>" + esc(c.channel_name) + "</code></td><td>" + esc(c.load) + '</td><td class="muted">' + esc(c.edition) + "</td></tr>"; }).join("") + "</tbody></table>";
    if (mx.length) h += '<h3 style="margin-top:8px">Mixer chains</h3><dl>' +
      mx.map(function (m) { return "<dt>" + esc(m.track) + '</dt><dd><span class="chain">' + esc(m.chain) + "</span>" + (m.why ? '<div class="why">' + esc(m.why) + "</div>" : "") + "</dd>"; }).join("") + "</dl>";
    if (tips.length) h += '<h3 style="margin-top:8px">Make it feel right</h3><ul style="margin:0;padding-left:20px;display:flex;flex-direction:column;gap:6px">' + tips.map(function (t) { return "<li>" + esc(t) + "</li>"; }).join("") + "</ul>";
    if (manual.length) h += '<h3 style="margin-top:8px">Also do by hand</h3><ul style="margin:0;padding-left:20px;display:flex;flex-direction:column;gap:6px">' + manual.map(function (t) { return "<li>" + esc(t) + "</li>"; }).join("") + "</ul>";
    return h + "</div>";
  }

  function renderResult(main, v, r, opts) {
    opts = opts || {};
    r = r || {};
    var conf = function (c) { return c ? '<span class="conf">' + esc(c) + " confidence</span>" : ""; };
    var why = function (w) { return w ? '<div class="why">' + esc(w) + "</div>" : ""; };
    var d = r.drums || {}, m = r.melody || {};
    var prompts = list(r.boothmate_prompts);
    var tc = r.tempo_check || {};
    var tempoAlt = (tc.half_time_bpm || tc.double_time_bpm) ? '<div class="why">Checked against ' + esc(tc.half_time_bpm) + " / " + esc(tc.double_time_bpm) + " BPM" + (tc.genre_range ? "; genre range " + esc(tc.genre_range) : "") + "</div>" : "";
    var hasSetup = !!soundSetup(r.sound_setup);
    var html = videoBlock(v, opts.label || "Your breakdown") +
      '<section class="in" style="margin-top:28px;display:flex;flex-direction:column;gap:18px">' +
      '<div class="glass card"><div class="label">The vibe</div><h2 style="font-size:clamp(26px,3.6vw,38px)">' + esc(r.style) + (r.style_confidence ? conf(r.style_confidence) : "") + '</h2>' + why(r.style_why) + '<p class="muted" style="margin:0;font-size:19px">' + esc(r.vibe) + '</p>' +
      '<div class="stats"><div class="stat"><small>Tempo</small><b>' + esc(r.bpm) + ' BPM</b>' + conf(r.bpm_confidence) + why(r.bpm_why) + tempoAlt + '</div><div class="stat"><small>Key</small><b>' + esc(r.key) + '</b>' + conf(r.key_confidence) + (r.mode ? '<div class="why">' + esc(r.mode) + "</div>" : "") + why(r.key_why) + '</div>' +
      (r.boothmate_genre ? '<div class="stat"><small>BoothMate style</small><b>' + esc(r.boothmate_genre) + "</b>" + (r.boothmate_mood ? '<div class="why">mood: ' + esc(r.boothmate_mood) + "</div>" : "") + "</div>" : "") + '</div></div>' +
      soundSetup(r.sound_setup) +
      '<div class="glass card" style="border-color:var(--acc)"><div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center"><div><div class="label">' + (hasSetup ? '<span class="steps-n">2</span>' : "") + 'Build your own</div><h2>Your BoothMate prompts</h2></div><button class="btn" id="copyAll">Copy all prompts</button></div><p class="muted" style="margin:0">Paste these into Claude one at a time, in order, with BoothMate installed and FL Studio open. ' + (hasSetup ? "Load the sounds above first." : "Add the sounds below to your Channel rack first.") + '</p><ol class="prompts">' +
      prompts.map(function (p, i) { return '<li><p>' + esc(p) + '</p><button class="btn" data-copy="' + i + '">Copy</button></li>'; }).join("") + '</ol></div>' +
      '<div class="grid"><div class="glass card"><h3>Drums</h3><dl><dt>Kick</dt><dd>' + esc(d.kick) + '</dd><dt>Snare / clap</dt><dd>' + esc(d.snare_clap) + '</dd><dt>Hi-hats</dt><dd>' + esc(d.hi_hats) + '</dd><dt>Percussion</dt><dd>' + esc(d.percussion) + '</dd><dt>Groove</dt><dd>' + esc(d.groove) + '</dd></dl></div>' +
      '<div class="glass card"><h3>808</h3><p style="margin:0">' + esc(r.bass_808) + '</p><h3 style="margin-top:8px">Melody</h3><dl><dt>Lead</dt><dd>' + esc(m.lead_sound) + '</dd><dt>Approach</dt><dd>' + esc(m.approach) + '</dd><dt>Harmony</dt><dd>' + esc(m.harmony) + '</dd><dt>Layers</dt><dd>' + esc(m.layers) + '</dd></dl></div></div>' +
      '<div class="glass card"><h3>Arrangement</h3><div class="timeline">' + list(r.arrangement).map(function (s) { return '<div class="seg"><b>' + esc(s.section) + '</b><div class="bars">' + (s.bars ? esc(s.bars) + " bars" : "") + '</div><div style="font-size:14px" class="muted">' + esc(s.what_happens) + '</div></div>'; }).join("") + '</div></div>' +
      '<div class="grid"><div class="glass card"><h3>Sounds to use in FL Studio</h3><dl>' + list(r.fl_studio_sounds).map(function (s) { return "<dt>" + esc(s.role) + "</dt><dd>" + esc(s.suggestion) + "</dd>"; }).join("") + '</dl></div>' +
      '<div class="glass card"><h3>Mix notes</h3><ul style="margin:0;padding-left:20px;display:flex;flex-direction:column;gap:6px">' + list(r.mix_notes).map(function (n) { return "<li>" + esc(n) + "</li>"; }).join("") + "</ul></div></div>" +
      (r.notes ? '<p class="muted" style="margin:0;font-size:15px">' + esc(r.notes) + "</p>" : "") +
      (opts.hideCta ? "" : '<div class="glass card"><h3>Don\'t have BoothMate yet?</h3><p class="muted" style="margin:0">It\'s free. Install it once and these prompts build the beat in your FL Studio.</p><div><a class="btn btn-p" style="display:inline-flex;align-items:center;text-decoration:none" href="/#setup">Get BoothMate free</a></div></div>') +
      (opts.extra || "") +
      "</section>";
    main.innerHTML = html;

    function fallback(text) { var t = document.createElement("textarea"); t.value = text; t.style.position = "fixed"; t.style.opacity = "0"; document.body.appendChild(t); t.select(); try { document.execCommand("copy"); } finally { document.body.removeChild(t); } }
    function copy(text, btn) {
      var done = function () { btn.textContent = "Copied ✓"; btn.classList.add("on"); setTimeout(function () { btn.textContent = btn.id === "copyAll" ? "Copy all prompts" : "Copy"; btn.classList.remove("on"); }, 1800); };
      try { navigator.clipboard.writeText(text).then(done, function () { fallback(text); done(); }); } catch (e) { fallback(text); done(); }
    }
    main.querySelectorAll("[data-copy]").forEach(function (b) { b.onclick = function () { copy(prompts[Number(b.getAttribute("data-copy"))], b); }; });
    var all = main.querySelector("#copyAll");
    if (all) all.onclick = function () { copy(prompts.map(function (p, i) { return (i + 1) + ". " + p; }).join("\n"), this); };
  }

  window.BBView = { esc: esc, videoBlock: videoBlock, renderResult: renderResult, allPromptsText: function (r) { return list(r && r.boothmate_prompts).map(function (p, i) { return (i + 1) + ". " + p; }).join("\n"); } };
})();
