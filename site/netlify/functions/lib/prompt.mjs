// The Beat Breakdown request sent to Gemini with the customer's YouTube link.
// Same workflow BoothMate used on FL Studio's tutorials (Nov 24, 2026), packaged:
// watch + listen, describe the STYLE and APPROACH, then write BoothMate prompts
// that build an ORIGINAL beat in that style. Never transcribe the source.

// What BoothMate can actually do from a pasted prompt (kept in sync with
// skills/boothmate/SKILL.md and src/fl_studio_mcp/tools). Prompts must stay inside this list.
export const BOOTHMATE_CAPABILITIES = `BoothMate tools (the ONLY things a prompt may ask for):
- Set the project tempo (any BPM).
- Add named arrangement markers at bars (Intro, Hook, Verse, Breakdown, Outro).
- Program a drum pattern in the step sequencer, 1-16 bars, with an optional fill in the last bar, for ONE of these genres: trap, drill, boom_bap, rnb, lofi, jersey_club. It finds drum channels by name: Kick, Snare, Clap, Hat, Open Hat. (trap = half-time clap/snare on beat 3 with rolling hats; drill = syncopated snares, triplet-feel hats, sliding 808s; boom_bap = snare on 2 and 4.)
- Write an 808 in a key that hits with that genre's kick and follows the chord roots (drill adds octave slides). Finds the channel named 808.
- Write a 4-chord progression in a key, either by mood (dark, sad, menacing, hype, chill, love, happy) or by custom scale degrees 1-7 (e.g. 1-6-3-7), with bars per chord (0.25-4) and repeats (1-4). Finds a channel named Keys, Piano, Pad, Strings, Bell, Pluck or Synth.
- Write an original melody into the piano roll of a named channel, in the key's scale; the prompt describes register, rhythm density, note lengths and contour in words.
- Clone a pattern under a new name (for variations / breakdowns).
- Mixer: name tracks, set volume and pan; channel volume and pan.
- Undo the last change.
BoothMate CANNOT: load instruments, presets, samples or effect plugins; turn effect knobs on plugins that aren't loaded; set swing; change individual note velocities from a prompt; export audio; edit audio clips. Those go in sound_setup as manual steps, never in boothmate_prompts.`;

// Tempo ranges by sub-genre, in the convention BoothMate's patterns use.
export const TEMPO_GUIDE = `Tempo conventions (write BPM the way producers label these beats, the way FL Studio's tempo box would read):
- Chicago drill: about 130-150 (often 130-140). UK drill and NY/Brooklyn drill: about 138-146. Snares/claps land on beat 3 plus syncopated off-beat snares; 808s glide.
- Trap and dark trap: about 130-170, felt half-time (clap/snare on beat 3 of each bar). Melodic/emotional trap: about 140-160. Rage: about 150-170. Plugg/pluggnb: about 140-160.
- Boom bap: about 80-98 (snare on 2 and 4). R&B: about 60-100. Lo-fi: about 70-90. Jersey club: about 130-145 (kick bursts).
Half/double-time check (do this every time): (1) count the kick/snare backbeat and the hi-hat rate; (2) write down the candidate, half of it and double it; (3) choose the one where the main clap/snare falls where the genre puts it (beat 3 for trap/drill, beats 2 and 4 for boom bap) AND that sits in the genre's range above; (4) if the video title or description states a BPM, prefer it unless the audio clearly disagrees. Never report a tempo outside the chosen genre's range without explaining why in bpm_why. Style and tempo must agree: a "drill" answer at 180 BPM, or "melodic trap" when the drums are syncopated drill drums with sliding 808s, is a contradiction to fix before answering.`;

export const BREAKDOWN_PROMPT = `You are a hip-hop and trap producer analysing a beat for a customer who wants to make an ORIGINAL beat in the same style in FL Studio, using BoothMate (an assistant that writes drums, 808s, chords and melodies into FL Studio for them).

Watch and listen to the attached YouTube video all the way through.

Rules:
- Describe the style, feel and production approach. Do NOT transcribe the melody, chord voicings, sample or drum pattern note for note, and do NOT tell the customer how to recreate the exact song. The goal is a new beat with the same vibe.
- Only state what you can hear or see. Use "unclear" for a key you can't hear.
- Work in this order: (1) STYLE from the drums and 808 (sliding 808s + syncopated off-beat snares = drill; steady rolling hats + half-time clap on beat 3 = trap; snare on 2 and 4 with swing = boom bap); (2) TEMPO with the half/double-time check below; (3) KEY and MODE (minor, major, phrygian, harmonic minor) from the bass notes and the chord the loop resolves to; (4) everything else. For style, tempo and key give a confidence and a one-sentence "why" based on what you heard.
- If the audio is not a beat or instrumental (a vlog, a full commercial song with vocals throughout, silence), still describe the musical style you can hear, and say so in "notes".
- Write everything in plain, friendly language for beginners.

${TEMPO_GUIDE}

Sound setup (sound_setup): BoothMate can't load sounds, so tell the customer exactly what to load BEFORE running the prompts, using only FL Studio STOCK content: instruments (FLEX and its free preset packs, FL Keys, Sytrus, 3x Osc, GMS, Harmor, Transistor Bass, Fruity DX10, BooBass), the FL Studio browser's Packs folder samples (kicks, claps, snares, hats, 808s), and stock effects (Fruity Soft Clipper, Fruity Blood Overdrive, Fruity Fast Dist, Fruity Waveshaper, Fruity Parametric EQ 2, Fruity Limiter, Fruity Compressor, Fruity Reeverb 2, Fruity Delay 3, Fruity Stereo Shaper, Fruity Filter, Gross Beat, Maximus, Pitcher). For each channel say what to name it so BoothMate finds it (Kick, Snare, Clap, Hat, Open Hat, 808, Keys/Pad/Bell/Pluck/Strings, Melody) and which FL Studio edition includes that sound (e.g. "all editions incl. trial", "Producer and up", "Signature and up", "All Plugins Edition"). Give a mixer chain per important track in signal order (e.g. 808: Fruity Soft Clipper -> Fruity Blood Overdrive at low mix -> Fruity Parametric EQ 2 low-cut under 30 Hz -> Fruity Limiter), and practical tips on velocity, humanizing and swing that make it sound like the reference (e.g. hats at 60-80% velocity with accents, 808 glide time in the channel settings).

${BOOTHMATE_CAPABILITIES}

boothmate_prompts: write 6 to 9 prompts the customer pastes into Claude one at a time, in this order: (1) set the tempo to exactly the bpm you reported and add the arrangement markers; (2) program the drums naming the BoothMate genre and bar count; (3) write the 808 in the key with the genre; (4) write the chords in the key with a mood or scale degrees and chord length; (5) write an original melody on the named lead channel, describing its feel in words; (6) clone patterns for a variation or breakdown if the arrangement needs it; (7) name, level and pan the mixer tracks. Each prompt is one or two sentences, names concrete choices (BPM, key, genre word, mood, bars, channel names from sound_setup) and never names the original song, artist or producer. Use the same bpm, key and genre word everywhere in the result.`;

// The full prompt with the video's public title, which often states the BPM and key.
export function breakdownPrompt({ title, author } = {}) {
  const t = String(title || "").slice(0, 300).replace(/[\r\n]+/g, " ");
  const a = String(author || "").slice(0, 120).replace(/[\r\n]+/g, " ");
  if (!t && !a) return BREAKDOWN_PROMPT;
  return `${BREAKDOWN_PROMPT}\n\nVideo title (a hint, not proof; trust the audio): "${t}"${a ? ` by "${a}"` : ""}.`;
}

const CONF = { type: "STRING", enum: ["high", "medium", "low"] };

// Structured output (Gemini responseSchema, OpenAPI subset).
export const BREAKDOWN_SCHEMA = {
  type: "OBJECT",
  properties: {
    style: { type: "STRING", description: "Sub-genre in a few words, e.g. 'Chicago drill', 'dark trap'." },
    style_confidence: CONF,
    style_why: { type: "STRING", description: "One sentence: what in the drums/808/sounds makes it this style." },
    boothmate_genre: { type: "STRING", enum: ["trap", "drill", "boom_bap", "rnb", "lofi", "jersey_club"], description: "Closest BoothMate drum genre." },
    boothmate_mood: { type: "STRING", enum: ["dark", "sad", "menacing", "hype", "chill", "love", "happy"], description: "Closest BoothMate chord mood." },
    vibe: { type: "STRING", description: "One sentence on the mood and energy." },
    bpm: { type: "NUMBER", description: "Final tempo after the half/double-time check." },
    bpm_confidence: CONF,
    bpm_why: { type: "STRING", description: "One sentence: where the backbeat falls and why this tempo, not half or double." },
    tempo_check: {
      type: "OBJECT",
      properties: {
        half_time_bpm: { type: "NUMBER" },
        double_time_bpm: { type: "NUMBER" },
        genre_range: { type: "STRING", description: "e.g. '130-150 BPM'." }
      },
      required: ["half_time_bpm", "double_time_bpm", "genre_range"]
    },
    key: { type: "STRING", description: "e.g. 'C# minor', or 'unclear'." },
    mode: { type: "STRING", description: "e.g. 'natural minor', 'harmonic minor', 'phrygian', 'major'." },
    key_confidence: CONF,
    key_why: { type: "STRING", description: "One sentence: the bass/root notes and resolution you heard." },
    drums: {
      type: "OBJECT",
      properties: {
        kick: { type: "STRING" },
        snare_clap: { type: "STRING" },
        hi_hats: { type: "STRING" },
        percussion: { type: "STRING" },
        groove: { type: "STRING", description: "Swing, half-time feel, bounce." }
      },
      required: ["kick", "snare_clap", "hi_hats", "percussion", "groove"]
    },
    bass_808: { type: "STRING", description: "How the 808/bass behaves: length, slides, relation to the kick, distortion." },
    melody: {
      type: "OBJECT",
      properties: {
        lead_sound: { type: "STRING" },
        approach: { type: "STRING", description: "How the melody moves and sits, described, not transcribed." },
        harmony: { type: "STRING", description: "Chord feel and movement in general terms." },
        layers: { type: "STRING" }
      },
      required: ["lead_sound", "approach", "harmony", "layers"]
    },
    arrangement: {
      type: "ARRAY",
      items: {
        type: "OBJECT",
        properties: {
          section: { type: "STRING" },
          bars: { type: "INTEGER" },
          what_happens: { type: "STRING" }
        },
        required: ["section", "what_happens"]
      }
    },
    mix_notes: { type: "ARRAY", items: { type: "STRING" } },
    fl_studio_sounds: {
      type: "ARRAY",
      items: {
        type: "OBJECT",
        properties: {
          role: { type: "STRING", description: "e.g. 'lead', '808', 'pad'." },
          suggestion: { type: "STRING", description: "Stock FL Studio instrument/preset or plugin." }
        },
        required: ["role", "suggestion"]
      }
    },
    sound_setup: {
      type: "OBJECT",
      description: "Manual steps BEFORE the prompts: what to load (stock FL Studio only) and how to mix it.",
      properties: {
        channels: {
          type: "ARRAY",
          items: {
            type: "OBJECT",
            properties: {
              role: { type: "STRING", description: "e.g. 'kick', '808', 'lead'." },
              channel_name: { type: "STRING", description: "Name to give the Channel rack channel so BoothMate finds it, e.g. '808', 'Hat', 'Bell'." },
              load: { type: "STRING", description: "Stock instrument + preset, or stock sample and where it is in the browser." },
              edition: { type: "STRING", description: "Which FL Studio editions include it." }
            },
            required: ["role", "channel_name", "load", "edition"]
          }
        },
        mixer_chains: {
          type: "ARRAY",
          items: {
            type: "OBJECT",
            properties: {
              track: { type: "STRING", description: "Mixer track name, e.g. '808'." },
              chain: { type: "STRING", description: "Stock effects in signal order with rough settings, joined by ' -> '." },
              why: { type: "STRING" }
            },
            required: ["track", "chain"]
          }
        },
        performance_tips: { type: "ARRAY", items: { type: "STRING" }, description: "Velocity, humanize, swing, 808 glide tips." }
      },
      required: ["channels", "mixer_chains", "performance_tips"]
    },
    boothmate_prompts: { type: "ARRAY", items: { type: "STRING" }, description: "6 to 9 prompts, in build order, only things BoothMate can do." },
    notes: { type: "STRING", description: "Anything the customer should know (uncertainty, not a beat, etc.)." }
  },
  required: ["style", "style_confidence", "style_why", "boothmate_genre", "boothmate_mood", "vibe", "bpm", "bpm_confidence", "bpm_why", "tempo_check", "key", "mode", "key_confidence", "key_why", "drums", "bass_808", "melody", "arrangement", "mix_notes", "fl_studio_sounds", "sound_setup", "boothmate_prompts", "notes"],
  propertyOrdering: ["style", "style_confidence", "style_why", "boothmate_genre", "boothmate_mood", "vibe", "tempo_check", "bpm", "bpm_confidence", "bpm_why", "key", "mode", "key_confidence", "key_why", "drums", "bass_808", "melody", "arrangement", "mix_notes", "fl_studio_sounds", "sound_setup", "boothmate_prompts", "notes"]
};

// Things BoothMate can't do; a prompt asking for them is moved out of the list.
const CANT = /\b(load|drag|add (?:a |an )?(?:plugin|preset|sample|effect)|insert .*(?:plugin|effect)|export|render|bounce|soft clipper|overdrive|distortion|reverb|delay|sidechain)\b/i;

// Makes a model result safe and consistent before anyone sees it:
// rounds the tempo, makes the first prompt set exactly that tempo, and moves
// prompts BoothMate can't do into sound_setup.manual_steps.
export function tidyBreakdown(r) {
  if (!r || typeof r !== "object") return r;
  const out = { ...r };
  const bpm = Math.round(Number(out.bpm));
  if (Number.isFinite(bpm) && bpm > 0) out.bpm = bpm;
  let prompts = (Array.isArray(out.boothmate_prompts) ? out.boothmate_prompts : []).map((p) => String(p || "").trim()).filter(Boolean);
  const manual = [];
  prompts = prompts.filter((p, i) => {
    if (i > 0 && CANT.test(p) && !/\b(name|pan|volume|level)\b/i.test(p)) { manual.push(p); return false; }
    return true;
  });
  if (Number.isFinite(bpm) && bpm > 0) {
    const tempoRe = /(\d{2,3}(?:\.\d+)?)\s*bpm/i;
    const first = prompts.findIndex((p) => /tempo|bpm/i.test(p));
    if (first === -1) prompts.unshift(`Set the tempo to ${bpm} BPM.`);
    else {
      const m = prompts[first].match(tempoRe);
      if (!m || Math.round(Number(m[1])) !== bpm) prompts[first] = m ? prompts[first].replace(tempoRe, `${bpm} BPM`) : `Set the tempo to ${bpm} BPM. ${prompts[first]}`;
      if (first > 0) prompts.unshift(prompts.splice(first, 1)[0]);
    }
  }
  out.boothmate_prompts = prompts.slice(0, 10);
  if (manual.length) {
    const ss = { ...(out.sound_setup || {}) };
    ss.manual_steps = [...(Array.isArray(ss.manual_steps) ? ss.manual_steps : []), ...manual];
    out.sound_setup = ss;
  }
  return out;
}

// Free teaser shown before payment: style, tempo and key from the first 90s.
export const PREVIEW_PROMPT = `Listen to the first part of the attached YouTube video, a beat or type beat. In plain, exciting but honest language for a beginner producer, identify its style, tempo and key, and write a one-sentence hook describing the vibe. Do not describe the melody or drum pattern in detail. If it isn't music, say so in "hook" and set style to "not a beat".`;

export const PREVIEW_SCHEMA = {
  type: "OBJECT",
  properties: {
    style: { type: "STRING" },
    bpm: { type: "NUMBER" },
    key: { type: "STRING" },
    mood: { type: "ARRAY", items: { type: "STRING" }, description: "Three mood words." },
    hook: { type: "STRING", description: "One sentence on the vibe." }
  },
  required: ["style", "bpm", "key", "mood", "hook"]
};
