// The Beat Breakdown request sent to Gemini with the customer's YouTube link.
// Same workflow BoothMate used on FL Studio's tutorials (Nov 24, 2026), packaged:
// watch + listen, describe the STYLE and APPROACH, then write BoothMate prompts
// that build an ORIGINAL beat in that style. Never transcribe the source.

export const BREAKDOWN_PROMPT = `You are a hip-hop and trap producer analysing a beat for a customer who wants to make an ORIGINAL beat in the same style in FL Studio, using BoothMate (an assistant that writes drums, 808s, chords and melodies into FL Studio for them).

Watch and listen to the attached YouTube video all the way through.

Rules:
- Describe the style, feel and production approach. Do NOT transcribe the melody, chord voicings, sample or drum pattern note for note, and do NOT tell the customer how to recreate the exact song. The goal is a new beat with the same vibe.
- Only state what you can hear or see. Give your best estimate for tempo and key and say how confident you are; use "unclear" when you can't tell.
- If the audio is not a beat or instrumental (a vlog, a full commercial song with vocals throughout, silence), still describe the musical style you can hear, and say so in "notes".
- Suggest FL Studio stock sounds (FLEX presets, FL Keys, Sytrus, 3x Osc, Fruity plugins) the customer can use instead of the original samples.
- Write everything in plain, friendly language for beginners.

The boothmate_prompts must be things the customer can paste into Claude, in order, to build their own beat with BoothMate. BoothMate can: set tempo, program drums (kick, clap, snare, hats, open hats) in the step sequencer, write 808 lines with slides, write chord progressions and melodies into the piano roll, add arrangement markers, clone patterns, and control the mixer (volume, pan, names, routing). It cannot load plugins or samples (the customer adds those), export audio, or edit audio clips. Each prompt is one sentence and names concrete choices (tempo, key, feel), never the original song or artist's melody.`;

// Structured output (Gemini responseSchema, OpenAPI subset).
export const BREAKDOWN_SCHEMA = {
  type: "OBJECT",
  properties: {
    style: { type: "STRING", description: "Sub-genre in a few words, e.g. 'Chicago drill', 'dark trap'." },
    vibe: { type: "STRING", description: "One sentence on the mood and energy." },
    bpm: { type: "NUMBER" },
    bpm_confidence: { type: "STRING", enum: ["high", "medium", "low"] },
    key: { type: "STRING", description: "e.g. 'C# minor', or 'unclear'." },
    key_confidence: { type: "STRING", enum: ["high", "medium", "low"] },
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
    boothmate_prompts: { type: "ARRAY", items: { type: "STRING" }, description: "6 to 9 prompts, in build order." },
    notes: { type: "STRING", description: "Anything the customer should know (uncertainty, not a beat, etc.)." }
  },
  required: ["style", "vibe", "bpm", "bpm_confidence", "key", "key_confidence", "drums", "bass_808", "melody", "arrangement", "mix_notes", "fl_studio_sounds", "boothmate_prompts", "notes"]
};
