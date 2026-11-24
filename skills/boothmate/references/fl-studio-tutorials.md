# Workflows from FL Studio's official tutorials

Breakdowns of videos on FL Studio's official YouTube channel (youtube.com/@FL_STUDIO), made with Gemini in Nov 2026. Producer entries describe techniques only, never their melodies or patterns. Use these when a user asks how to do something in FL Studio or wants a producer's approach; link the source video.

When a step needs something BoothMate can't do (loading plugins or samples, exporting audio, stem separation, cut groups, unlocking), walk the user through it with the exact menu path. Check the user's edition (see 06) before suggesting plugins: Harmless and Gross Beat need Signature or above; Sakura and LuxeVerb need All Plugins; stem separation and audio recording need Producer or above. Only split or sample audio the user owns or has rights to.

# The complete guide to the Step Sequencer | FL Studio
Source: https://www.youtube.com/watch?v=t70sj4TjmYE (official FL Studio channel, 26:18)
Breakdown by Gemini (Google AI Studio, YouTube video input), Nov 24 2026.

GOAL
Build, edit, loop, route, and organize drum and melodic patterns using the Channel rack, Step sequencer, Graph editor, Loop starter, and channel menus.

WORKFLOW
- Open the Channel rack: toolbar button or F6.
- Beginner template: FILE > New from template > Minimal > Basic 808 with limiter.
- Steps: left-click adds, right-click removes, Spacebar plays/stops.
- Optional single-button removal: OPTIONS > General settings > General > Input > uncheck "Use both mouse buttons in step sequencer".
- Pattern length: drag the Channel rack's right edge, or the Pattern length selector (top right).
- Filter groups: Channel filter dropdown (top left): All, Unsorted, Automation.
- Mute/solo/lock: green LED toggles mute; right-click LED > Solo; Shift+Click LED locks its state; Channel Volume and Pan knobs next to it.
- Route to Mixer: F9 opens Mixer; drag the Mixer track selector numbers, or select channel + mixer track and Ctrl+L / Cmd+L (copies name, icon, color).
- Swing: Main swing knob (top right). Per-channel amount: Channel settings > wrench tab > Time > SWING.
- Channel looping: Loop button (top right) = "Loop step channels"; right-click for "Loop all channels" or "Advanced looping" (per-channel Bar/Beat/step). "Burn selected channels" / "Burn all looping channels" turns loops into real steps.
- Piano roll pattern: right-click channel > Clone > FLEX preset (Essential Pianos > Close Grand); right-click > Piano roll (F7); Piano roll Options > Tools > Generate chord progression > Accept. Toggle step / piano-roll view button (top right).
- Loop starter: button top-left of Channel rack; pick Genre and Key; dice icon rerolls all, per-channel dice rerolls one; right-click dice: Replace sample / Find similar samples / Generate steps. "Send to playlist" icon exports the loop.
- Graph editor: right-click channel > Graph editor, or hold K. Tabs: Note pitch, Velocity, Release velocity, Fine pitch, Panning, Mod X, Mod Y, Shift, Repeat.
- Channel button menu (right-click): rename/color/icon, Load sample, Cut itself, Insert/Replace/Patcherize/Clone/Delete, Assign to new instrument track, Fill each 2/4/8 steps, Rotate left/right (Ctrl/Cmd+Shift+Arrow), Advanced fill, Create DirectWave instrument, Burn MIDI to.
- Channel rack menu (down arrow top-left): Add one, Loop starter, Purge unused audio clips, Clone/Delete selected, Create layer, Move up/down (Alt/Opt+Up/Down), Sort by, Group selected (Alt/Opt+G), Color selected, Transpose selected, Set swing mix for selected, Burn selected loops, Assign selected to free mixer tracks (Ctrl/Cmd+L), Zip (Alt/Opt+Z) / Unzip all (Alt/Opt+U), Show mixer track selectors (Alt/Opt+M), Smart disable, Mute removed steps.

KEY SETTINGS
- Pattern length: default adaptive "--"; demo at 32 steps.
- Main swing: 0%, moderate, maximum demonstrated.
- Advanced fill: "Fill every", sequence length 16, interval 4 -> 5 -> 6.
- Cut groups: 808 Snare Cut 3 / By 3; open hat choked by closed hat (Cut 1 by 2).
- Loop starter demo: Boom bap, E minor.
- Transpose selected: +12 semitones (one octave).
- Swing mix for selected: 35%.

TIPS
- Beginners: start from the "Basic 808 with limiter" template (kick, clap, hat, snare, bass ready).
- Keep pattern length adaptive for most projects.
- Shift+Click-locked channels stay on when you solo others.
- Turn off "Auto switch display filter" in big projects.
- Keep Mixer track selectors visible.
- "Mute removed steps" keeps Graph editor edits when a step is toggled back on.
- "Create DirectWave instrument" before sharing a project with someone who lacks your plugins.
- Smart disable saves CPU but can break reverbs.

PROMPTS (Gemini's suggestions)
- Start a simple drum beat in the Channel rack.
- Loop shorter drum channels to match a longer chord progression.
- Add swing to hi-hats; adjust step velocity and pitch.
- Make the closed hi-hat cut off the open hi-hat.
- Route every instrument to its own Mixer track and color-code them.

---

# How to follow a Linear Workflow | FL Studio
Source: https://www.youtube.com/watch?v=et-sYCqVEms (official FL Studio channel, 6:49). Breakdown by Gemini via Google AI Studio.

GOAL: Use Instrument Tracks and Audio Tracks so the Playlist, Channel rack, Mixer, patterns, audio and automation stay linked, named, colored and organized.

WORKFLOW
- Playlist, Channel rack and Mixer are NOT linked by default.
- Instrument Track: drag a sample or plugin (e.g. FLEX) from the Browser onto a Playlist track header; for a sample choose "Instrument track(s)" in the "Dropped sample(s)" popup. A plugin drop also creates a pattern clip.
- Playlist options menu: set pattern double-click to "Piano roll" (keep "Adjust start time").
- Double-click a pattern clip = its Piano roll; double-click the track header = its instrument.
- Renaming/recoloring any linked part updates all of them; changing the mixer number moves the whole mixer track with its effects.
- Automation: right-click a knob (e.g. FLEX Master filter cutoff, Parametric EQ 2 band freq) > Create automation clip; it lands on a named sub-track under the instrument track.
- Audio Track: drag a sample onto a track header > "Audio track(s)". More audio dropped there uses the same mixer track.
- Batch: drop several WAVs at once > Audio track(s) makes one track each; or select several track headers and drop a plugin to make them all instrument tracks.
- Menus: Channel rack right-click > "Assign to new instrument track"; track header right-click > Track mode > Instrument/Audio track; Playlist "+" button (right-click for quick empty audio track).
- Delete: right-click track header > Delete; choose what goes with it (patterns, mixer track, automations).

TIPS
- Don't assume clips on a plain Playlist track are routed to a mixer track.
- Let instrument/audio tracks name and group automation for you; old projects stay readable.
- Read the delete dialog carefully so you don't lose patterns, effects or automation.

---

# The best way to export your music | Learn FL Studio
Source: https://www.youtube.com/watch?v=wBgJGuLZ-CY (official FL Studio channel, 4:01). Breakdown by Gemini via Google AI Studio.

GOAL: Export a finished project to an audio file (optionally upload to SoundCloud) with the right mode, tail, format and quality.

WORKFLOW
- Transport toggle: SONG exports the whole Playlist; PAT exports only the selected pattern.
- A highlighted Playlist selection exports only that part; clear it with Ctrl+D / Cmd+D.
- Open export: File > Export, or Ctrl+R / Cmd+R. Name it, pick a format (WAV shown), Save.
- Rendering window > Project type: Mode (Full song / Pattern / Song selection); Tail (Cut / Leave / Wrap remainder).
- Output format: WAV, MP3, OGG, FLAC, MID, M4A (several at once). WAV bit depth 16 / 24 int, 32 float; MP3 bitrate slider.
- Quality: Resampling at least 64-point sinc for finals (up to 512); HQ for all plugins; Disable maximum polyphony; Dithering.
- Miscellaneous: save markers/tempo; Split mixer tracks (stems); Trim PDC silence; Enable insert / master effects.
- Optional SoundCloud upload; "Show file(s) when complete"; Start.

KEY SETTINGS
- Tail: Leave remainder for songs (keeps reverb tails); Wrap remainder for seamless loops; Cut remainder stops dead.
- WAV: 16-bit int for normal release, 32-bit float to reuse in production, 24-bit for older software. MP3: above 224 kbps; 320 kbps shown.
- HQ for all plugins on, Disable max polyphony on, Dithering off, Trim PDC silence on, insert + master effects on, Split mixer tracks off unless making stems.

TIPS
- Most common mistake: exporting in PAT mode or with a Playlist selection active, so only part of the song renders.
- Cut remainder chops reverb/delay tails.
- Split mixer tracks = stems for collaborators.
- Turn off insert/master effects only for an unmixed/unmastered version.

---

# Split any audio with Stem Separation | 3 ways to use it in FL Studio
Source: https://www.youtube.com/watch?v=69Voz6NE-oo (official FL Studio channel, 10:08). Breakdown by Gemini via Google AI Studio.

GOAL: Use stem separation to remix a stereo track, turn separated drums into editable MIDI grooves, and study how a song is arranged.

EDITIONS: Producer, Signature, All Plugins. NOT in Fruity Edition.

WORKFLOW
1. Remix: Welcome window > "Remix a song" and pick the file; or drag audio into the Playlist > clip menu (top-left) > "Extract stems from sample". Tick Drums, Bass, Instruments, Vocals; keep Mute source track, Group playlist tracks, Assign to new mixer tracks; Extract.
   - Mute Vocals for an instant instrumental; or move vocal phrases around.
   - Genre swap: mute the Drums stem, record new drums (demo: FLEX drum kit, half-time), add FL Cloud loops.
2. Audio to MIDI: Slice tool on the Drums stem > clip menu > "Make unique as sample" > drop it on a Slicex channel > Piano roll shows the slices as notes; redraw or replay the groove. Hi-hat rolls: controller Arp mode (1/16, 1/32 triplet, 1/8 triplet).
3. Study a song: look at stem waveforms for energy changes; Playlist menu > Time markers > Add one (Alt+T / Option+T) for Intro, Verse, Chorus, Bridge; solo Drums through each marker; Vocals clip > Edit sample > Edison spectrogram to compare layer density.

KEY SETTINGS: Limit CPU usage and Safe mode off; demo tempo 178 BPM (89 half-time); 16-bar hook.

TIPS
- Half-time tempos let you drop in new rhythms without stretching the audio.
- Save big drum elements (like the snare) for the chorus for a lift.
- Add small layers between sections so the song doesn't feel like one loop.
- Separate your own old bounces to find reusable phrases, fills and transitions.

NOTE FOR BOOTHMATE: only separate audio the user owns or has rights to. Studying a released song's structure is fine; reusing its parts in a release needs permission.

---

# Let's record MIDI | Learn FL Studio
Source: https://www.youtube.com/watch?v=Z9RZpnj2uqo (official FL Studio channel, 5:38). Breakdown by Gemini via Google AI Studio.

GOAL: Set up a MIDI keyboard (or the computer keyboard), record MIDI in Pattern and Song mode, and tighten timing with snap or the Piano roll quantizer.

WORKFLOW
1. Plug in the keyboard and install its drivers BEFORE opening FL Studio. No keyboard? Options > Typing keyboard to piano (Cmd+T on Mac).
2. Options > MIDI settings (F10): under Input select the device, Enable, choose its Controller type (or "(generic controller)").
3. Select the channel to play in the Channel rack (arrow keys move the selection).
4. Optional lock/layer: right-click channel > Receive notes from > your keyboard; unlock the same way.
5. Choose PAT or SONG on the transport.
6. Right-click Record > Recording filter: make sure "Notes" is ticked.
7. Click Record, then Play, and play.
   - Song mode: select an empty pattern in the Playlist first.
8. Auto-quantize while recording: Piano roll snap on "Main", then the main toolbar snap to Beat, 1/2 beat or 1/4 beat. Turn it off with Line/Cell/(none), or untick the Quantize options under the Record button's right-click menu.
9. Quantize afterwards: Piano roll > Tools > Quantize (Opt+Q on Mac) > raise Sensitivity and Start time > Accept.

TIPS
- MIDI records notes, not sound; to capture a hardware synth's sound, record audio.
- The main toolbar snap controls recording quantize, not the Piano roll magnet.
- Unlock locked channels when you're done layering.
- Playing past the pattern end is fine: FL extends the pattern.
- Record loose and quantize later if you like natural timing.

---

# FL Studio: What Edition is right for me?
Source: https://www.youtube.com/watch?v=VU29E38z4s4 (official FL Studio channel, 9:32). Breakdown by Gemini via Google AI Studio. Prices not shown in the video.

FRUITY: 12 core features; Loop starter, FLEX, 3x Osc, Parametric EQ 2, Patcher, Fruity Compressor. NO audio recording, max 8 audio clips in the Playlist, NO stem separation, NO Edison.
PRODUCER: all 17 core features; unlimited audio clips; audio recording (Playlist or Edison); stem separation; Edison; ~100 plugins incl. Sytrus, Kepler, Slicex, Maximus, Hyper Chorus, Vocodex. Not included: NewTone, Harmless, full DirectWave, Gross Beat, Harmor, LuxeVerb.
SIGNATURE BUNDLE: Producer + extra plugins: NewTone, Harmless, full DirectWave, Gross Beat, Vintage Phaser, Vintage Chorus, Pitcher, Low Lifter. Not: Harmor, Kepler Exo, Transistor Bass, Ogun, Sakura, Emphasis, Pitch Shifter, LuxeVerb, Transient Processor, Transporter.
ALL PLUGINS: every native plugin made up to the time of purchase (adds Harmor, Kepler Exo, Transistor Bass, Ogun, Sakura, Emphasis, Pitch Shifter, LuxeVerb, Transient Processor, Transporter).
ALL EDITIONS: Lifetime Free Updates.

HOW TO CHOOSE: Fruity = curious beginners who don't record audio. Producer = recording vocals/instruments, stem separation, sampling. Signature = Producer + signature instruments/effects. All Plugins = everything.

TIPS: don't buy Fruity if you'll record vocals; check the Compare Editions page; edition demo projects are linked under the video.

NOTE FOR BOOTHMATE: some breakdowns use plugins above Producer (Harmless, Gross Beat = Signature+; Sakura, LuxeVerb = All Plugins). Prompts must offer stock alternatives for lower editions; on the trial, plugins from the chosen edition work.

---

# FL STUDIO | Hip hop & Trap Tutorial
Source: https://www.youtube.com/watch?v=dxbPXPq9aeA (official FL Studio channel). Breakdown by Gemini via Google AI Studio.

GOAL: Make a hip hop / trap beat with the stock template, step-sequenced drums, a tuned 808 with slides, chopped loops, piano chords and pitched hi-hat rolls.

WORKFLOW
1. File > New from template > Minimal > Basic 808 with limiter (808 Kick, Clap, HiHat, Snare).
2. Tempo: right-click the tempo display > Type in value > 140.
3. Drums in the step sequencer (left-click add, right-click delete, Spacebar preview).
4. Kick shaping in Channel settings: POGO (Precomputed effects) for the transient; SMP START / LENGTH for clean trimming; Envelope tab for the volume envelope.
5. Hats: right-click 808 HiHat > Fill each 2 steps; Rotate left/right (Shift+Ctrl+Left/Right on Windows); Graph editor to vary velocity.
6. Playlist: paint Pattern 1 twice; clip menu > Make unique (Pattern 2) for a variation; switch to SONG mode.
7. 808: FLEX > Mobile Tuned 808 Bass > "808 Synth Blasted"; Piano roll Slide notes (green triangle) for glides.
8. Tuning your own 808 sample: drag it onto a Playlist header as an Instrument track; Tuner on its mixer track reads the pitch (demo: G2, 49.6 Hz); right-click that key on the Sampler Envelope keyboard to set the root note.
9. Loops: percussion loop as an audio track > clip menu > Chop > Time based > quarter beats; shaker loop in Fruity Slicer, Quantizer (Alt+Q) to straighten it, Ctrl+B to duplicate a bar.
10. Chords: FLEX > Essential Pianos > Bosendorfer, click chords into the Piano roll.
11. Slicex: drop a guitar loop, it auto-slices transients; sequence the slices.
12. Hat rolls: draw a long note > Piano roll Tools > Chop (Alt+U) > Time mul for speed; ramp Velocity and Fine pitch in the control lane.

TIPS
- SMP START/LENGTH trims cleanly; START OFFSET can click.
- Switch to SONG mode to hear the arrangement.
- Make unique before editing a copied pattern.
- Tune custom 808s before writing basslines.
- Straighten swung loops when pairing with a straight beat.

---

# What's new in FL Studio 2026?
Source: https://www.youtube.com/watch?v=IvJ1EAs8Sxw (official FL Studio channel, 20:17). Breakdown by Gemini via Google AI Studio.

NEW FEATURES (selected)
- New FLEX: rebuilt, up to 50% less CPU on updated packs, faster loading, tabs Play/Edit/Library/Store. Core Packs in all editions, even the trial.
- Transmitter (Mixer effect): splits transient and sustain, per-part Saturation/Bounce/Diffusion/Delay, separate outputs for parallel processing. Good on a drum bus or 808.
- Loop starter: bigger sound pool for FL Cloud Plus/Pro.
- Project backup to FL Cloud: 500 MB free for everyone (up to 1 TB on Plus/Pro); "Back up to FL Cloud storage" in the Save dialog.
- Gopher (FL Studio's built-in AI assistant): edits track colors, sorting, mixer levels and routing, launches interactive tutorials, writes Piano roll and VFX scripts. Browser > GOPHER tab.
- Channel rack: "Use both mouse buttons" now off by default (right-click still deletes); Sort by > Type.
- Audio logger (Tools > Audio logger): records the master in the background; "Dump to audio editor" rescues a great take you forgot to record.
- Chord detection panel on the toolbar.
- Remix a song: one-click stem separation from the Welcome window.
- Playlist: normalize clip gain; pan knob in clip properties; Stretch toggle (hold A).
- Piano roll: rename keys; Chord stamp voice-leading modes; Chord progression tool (Alt/Opt+P) with preview, Swap/Slide.
- Mixer: click an empty FX slot to open the plugin menu; "Open audio editor and record".
- MIDI scripting API: undo/redo flags, pattern length and swing functions (useful for BoothMate later).

BEATMAKER WORKFLOWS
- FLEX > Library/Store > Hard 808s or a Core Pack > preset > tweak macros.
- Transmitter on the drum bus or 808: set Sensitivity, shape Transient/Sustain, saturate transients.
- Audio logger on while freestyling melodies; dump the best take to Edison and drag it to the Playlist.
- Remix a song: split stems, mute drums, chop vocals (only on audio you have rights to).

NOTE FOR BOOTHMATE: Gopher overlaps with simple mixer/color requests inside FL Studio. BoothMate's edge is writing the music itself (drums, 808s, chords, melodies by genre), studio-talk booth control, and working from Claude anywhere.

---

# How to unlock FL Studio
Source: https://www.youtube.com/watch?v=B3h94_MSjyY (official FL Studio channel, 7:21). Breakdown by Gemini via Google AI Studio.

GOAL: Unlock a purchased license from trial mode with an Image-Line account or a redemption code.

TRIAL: same installer as the full version; save and export as many projects as you want (the video doesn't list restrictions; BoothMate keeps its existing note that saved trial projects can't be reopened until purchase).

UNLOCK
- Bought from Image-Line: confirm the verification email; in FL Studio HELP > Unlock FL Studio.
  - "Unlock on web" > Sign in and unlock > browser sign-in > back in FL Studio click Restart.
  - or "Unlock with account": email + password + emailed 2FA code > Continue > Restart.
- Boxed copy / other retailer: More options > Redeem code (20 digits) > sign in or sign up in the browser > Register your product (Add, Next, Proceed) > then unlock as above.
- Check: HELP > About shows unlocked, your account and your edition.
- One license works on Windows and Mac.

PROBLEMS: ask Gopher; check spam for the verification email; "Send new code" for 2FA; still in trial after unlocking > support.image-line.com.

NOTE FOR BOOTHMATE: unlocking involves the user's password and 2FA; Claude explains the steps but never types credentials for them.

---

# METRO BOOMIN | Beats Tutorial | FL Studio & Razer Music
Source: https://www.youtube.com/watch?v=Av4NhUWQ-24 (official FL Studio channel). Technique breakdown by Gemini via Google AI Studio. Techniques only, no melodies or patterns copied.

STYLE: trap / hip-hop drum programming. Tempo on screen: 118 BPM. Key not shown (drums only).

DRUMS
- Kick is placed selectively, not on every beat, leaving room to bounce against the 808.
- A main clap holds the backbeat; a second snare is layered on top only at chosen spots for groove and emphasis.
- The layered snare is pitched down one semitone (Channel settings preview keyboard) to sit with low drums and sound meaner.
- Hi-hats: start from a steady every-step pattern, then add rolls by slicing chosen spots in the Piano roll, with intent, not scattered at random.
- Hi-hat tail tightened with the OUT (release) knob in Channel settings; Fruity Reeverb 2 on the hat's mixer track for space.
- Small velocity variations visible on hats.

808 / BASS
- Kick and 808 are spaced apart instead of a kick under every 808 hit, so they play off each other.
- (Tuning and glides are covered in his next video.)

ARRANGEMENT / WORKFLOW
- Builds variety by muting and soloing parts: clap alone first, layered snare later.
- Compares a basic and a complex version of the hat pattern by switching.
- Mouse programming in the Step sequencer and Piano roll; quick sound shaping in Channel settings.

ADVICE (paraphrased)
- Space kicks and 808s apart.
- Layer snares and claps only at certain spots so the drums bounce.
- Pitch snares down when the drums sit low.
- Don't overdo hi-hat rolls; place them with feel.
- Tighten hat tails and add a little reverb.

---

# METRO BOOMIN | Kicks and Basslines | FL Studio & Razer Music
Source: https://www.youtube.com/watch?v=7HgV0uyHwt0 (official FL Studio channel). Technique breakdown by Gemini via Google AI Studio. Techniques only.

STYLE: dark, spacious trap / hip-hop. Tempo and key not stated.

808 / BASS
- Treat the 808 as its own instrument: tune it to the key of the melody so the low end glues.
- Sustained 808 with occasional higher "jump" notes at the end of phrases.
- Contrast: alternate 808 sections with a synth-bass breakdown; stack a complementary synth playing the same progression on top of the synth bass.
- Stop the 808 tail bleeding into the synth bass (low-end "bubble"): give both channels the same Cut / Cut by group (Channel settings > MISC; demo changes the 808 from 16/16 to 5/5 to match).

DRUMS: kick under the 808, clap on the standard trap backbeat, steady hats with occasional fast rolls.

SOUNDS: keeps go-to sounds and presets memorized for speed; named synths reFX Nexus (a sidechain-bass preset) and Omnisphere (third-party plugins).

WORKFLOW
- Loops a section in the Playlist to audition before/after changes.
- Listens for overlapping sub frequencies.

ADVICE (paraphrased)
- Tune the 808 to the song's key or the beat sounds random.
- Memorize reliable go-to sounds so ideas come out fast.
- Switch between 808 and synth basslines for contrast.
- Use cut groups so one bass silences the other cleanly.

---

# Official Drill FL Studio Demo Project from Jay Cactus & Confz
Source: https://www.youtube.com/watch?v=Ab-mP9aRLuc (official FL Studio channel). Technique breakdown by Gemini via Google AI Studio. Techniques only.

STYLE: UK drill, built as an official FL Studio demo project (it ships with FL Studio so users can open it). Tempo/key not shown.

DRUMS
- Drum sounds from FL Cloud. Separate tracks: kick, two layered snares, three "counter-snare" tracks, percussion, plus FX (gunshots, risers, a hi-fill transition).
- The counter-snares carry the syncopated high-end, rapid rolls and stutters of the UK drill bounce, against offset snare hits.

808: sits right under the kick; UK drill patterns with pitch glides/slides locking around the kick.

MELODY / SOUNDS
- Starts with pads layered across octaves using stock plugins FLEX, Harmless and Sytrus (Pad 1, Pad 2, Strings, Pad High, Choir).
- Consolidates the pad stack to one audio clip, reverses it and pitches it up 3 semitones in the audio clip settings for energy.
- Adds vocal chops from FL Cloud, then a simple counter-melody on FL Keys (Grand Piano), plus a subtle bell.

ARRANGEMENT / MIX
- Color-coded sections: melody, drums, FX, vocals.
- Tension and release by muting/swapping drum layers, dropping in the piano, risers before hooks.
- Stock plugins only. Group buses: Melody Bus, Beat Bus, Lead Vocal, Ad-lib, Hook Vocal; sends: Reverb, 1/4 Delay, 1/2 Delay. Clip gain on chops and risers.

ADVICE (paraphrased)
- Bounce a layered pad to audio, reverse it, pitch it up for instant energy.
- A full release-ready track is possible with FL Studio stock plugins and FL Cloud sounds.
- Open the demo project to study its routing.

---

# FL STUDIO Signature Sound | TM88 Track Breakdown
Source: https://www.youtube.com/watch?v=TLfH7s60Z_w (official FL Studio channel). Technique breakdown by Gemini via Google AI Studio. Techniques only.

STYLE: dark, horror-orchestral trap. 157 BPM (on screen). Minor key, built by ear.

MELODY / SOUNDS (all stock FL Studio)
- Builds minor chords by counting semitones in the Piano roll, no sheet music. (Gemini wasn't sure of his exact count; a minor triad is root, +3, +7 semitones.)
- Layers the same progression across several stock instruments for a thick, spooky sound: GMS (a square synth), Sakura (strings), FL Keys (low grand-piano hits), Harmless (rhythmic pluck for energy), Sytrus (cello with slides).
- Writes the core part dry first (FL Keys), effects later.
- Piano roll slide notes make the cello glide between notes.

808
- Programmed in the Piano roll (not the step sequencer) for more range, pitch changes, velocity and panning.
- Kept fairly simple, with occasional octave/note jumps and a fast roll at the end of the loop.
- 808 sample in Sampler with time-stretching set to Resample and declicking set to "Out only".

DRUMS
- One favorite hi-hat sample (chosen because it rolls cleanly); steady pattern with painted-in rapid rolls and some lower-pitched accent doubles for bounce.
- Velocity dips during rolls; varied accents; panning adjusted in the Piano roll.
- The 808 provides most of the low punch.

ARRANGEMENT
- 8-bar drumless horror intro (chords, low piano, sliding cello), then at bar 9 the 808, hats, claps/snares and pluck drop together. Layers mute in and out to keep movement.

ADVICE (paraphrased)
- Stock FL Studio sounds are enough if you layer them well.
- You don't need to read music; trust your ear and count intervals.
- Write the melody dry first so it stands on its own.
- Layer simple parts to build a big vibe.

---

# FL CLOUD | Purps Trap Beat Breakdown
Source: https://www.youtube.com/watch?v=NmgSwgayqhU (official FL Studio channel). Technique breakdown by Gemini via Google AI Studio. Techniques only.

STYLE: dark trap, built from his FL Cloud pack. 120 BPM on screen; one-shots in C.

MELODY / SOUNDS
- Starts with a dry string chord progression, then shapes it before layering anything else.
- Strings get Fruity Convolver + Fruity Parametric EQ 2 for an "underwater" bed that leaves room, then Gross Beat with a curved volume envelope for a breathing, sidechain-like pump.
- Treats one-shots like synths: trims length, crossfades the loop in Sampler, turns on loop points so short sounds sustain.
- Slide notes in the Piano roll for slow pad pitch sweeps and quick bends on a bell SFX.
- Bell SFX through Fruity Delay 3 at 1/8, ping-pong, panned right.

HI-HATS
- Glitchy hats: some notes and rolls pitched down, velocity ramps drawn in the control lane.
- Fast rolls: place one note, use the Piano roll arpeggiator at a fast rate, sweep velocities up.
- Hat mixer track left completely dry.

808
- Main 808 pattern with fast repeats and pitch jumps; a second, more aggressive 808 only enters on the second time through the loop.
- Fruity Soft Clipper on the master so heavy bass saturates gently and stays loud without clipping.

ADVICE (paraphrased)
- Start with dry, simple chords; sculpt them so there's space to layer.
- Use loop points, crossfades and slides to turn one-shots into playable instruments.
- Vary hat pitch and velocity (or use the arpeggiator) for glitchy rolls.
- A soft clipper on the master lets 808s push through.

---

# Novation FLkey | Lex Luger making a beat using FLkey
Source: https://www.youtube.com/watch?v=6WEh64feSjg (official FL Studio channel). Technique breakdown by Gemini via Google AI Studio. Techniques only.

STYLE: hard, aggressive, simple trap. Tempo/key not shown.

ORDER: never starts with drums. Starts with a simple melody you could whistle (keys), layers a synth whistle on top, then adds signature tubular bells, pizzicato strings and sustained strings as counter-melodies.

DRUMS
- Crisp trap snare backbeat; extra snares and accent hits layered later for bounce.
- Hi-hats played live with Note Repeat, switching 1/8, 1/16 and faster rolls, bending pitch with the pitch wheel.
- Kick tuned (octave/pitch changed) until it meshes with the 808, instead of heavy processing.

808: played melodically; kick and 808 made to mesh by retuning the kick.

ARRANGEMENT / MIX
- Builds core patterns, adds counter-melodies, lays them out with sections where parts enter and drop out.
- Revisits a beat the next day and removes sounds that no longer feel needed.
- Balances mixer levels by hand.

ADVICE (paraphrased)
- Put feeling and time into each beat rather than chasing quantity.
- Keep it simple and memorable; if you can't whistle it, it's not a hit.
- Never throw ideas away.
- Make music that makes you happy.
- Gear can be simple: laptop, keyboard, mouse.

---

# How to use the Audio Clip Properties
Source: https://www.youtube.com/watch?v=AnNWKLXBduQ (official FL Studio channel, 6:28). Breakdown by Gemini via Google AI Studio.

GOAL: Change one audio clip's gain, pitch, mute, reverse, start and length without "Make unique" duplicates.

WORKFLOW
- Drag a loop into the Playlist (optionally cut it with the Slice tool).
- Alt+double-click (Option on Mac) a clip opens Clip properties. (Options > General settings > Input > Manage shortcuts can make plain double-click open it.)
- GAIN knob, or drag the clip-gain handle at the bottom center of the clip.
- PITCH (-12..+12 semitones) and FINE (-100..+100 cents). Shortcut: select clips, 8 = up a semitone, 7 = down.
- Mute; Reverse (flips only the visible part). Shortcut: 9 reverses selected clips.
- Time: Start time and Duration; the Playlist stretch toggle decides trim vs time-stretch. "Reset clip stretch" returns to 100% speed.
- Channel settings button opens the source channel (its own +/-12 pitch stacks with the clip's).

TIPS
- The clip title shows its pitch offset; a small icon marks clips with their own properties.
- Don't reverse slices in Channel settings (that flips the whole file); use clip Reverse.
- Don't Make unique just for gain/pitch/mute/reverse changes.
- Check the stretch toggle before dragging Duration.

---

