# First-time setup (walk the user through it one step at a time)

Needs FL Studio 20.7 or newer (2025+ recommended) and `uv`, which installs Python automatically. Video-style walkthrough: https://github.com/BlackFOXsolve/boothmate-plugin#setup

## 0. Install BoothMate
Claude desktop app: download https://github.com/BlackFOXsolve/boothmate-plugin/raw/main/downloads/BoothMate.mcpb and double-click it. Claude Code: `/plugin marketplace add BlackFOXsolve/boothmate-plugin`, then `/plugin install boothmate@wilderfold`.

## 1. Install uv (both)
- Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Mac (Terminal): `curl -LsSf https://astral.sh/uv/install.sh | sh`

Then fully quit and reopen Claude so BoothMate's server can start.

## 2. Windows only: create the two MIDI ports
Install loopMIDI (tobias-erichsen.de). Delete its default port, then add two ports named exactly `FLStudioMCP RX` and `FLStudioMCP TX`. Keep loopMIDI running (it can start with Windows).

## 3. Ask Claude to set up BoothMate
Call `setup_boothmate`, then `open_fl_studio`. BoothMate installs its FL Studio scripts, opens FL Studio, closes the welcome window and connects. If FL Studio was already open, ask the user to save, then `open_fl_studio` with restart=true. 

## 4. Switch it on in FL Studio (once)
FL Studio should link BoothMate by itself, but FL Studio 2026.1.7 on macOS was seen not to. If `studio_check` still says NO_HEARTBEAT after a restart, walk the user through Options > MIDI Settings:
- Input: select `BoothMate` (Mac) or `FLStudioMCP RX` (Windows), turn on Enable, set Controller type to **FLStudioMCP**, set Port to 0.
- Output: select `BoothMate` (Mac) or `FLStudioMCP TX` (Windows) and set its Port to the same number.

## 5. Mac only: allow keystrokes
System Settings > Privacy & Security: turn on Claude under Accessibility, and under Automation > Claude turn on System Events. BoothMate's error names whichever one is missing.
System Settings > Privacy & Security > Accessibility: turn on Claude. This lets chords, 808s and melodies be applied.

## 6. Each FL session: arm the piano roll
Open the Piano roll and click Scripting > MCP Apply once.

## 7. Go
Call `studio_check`, then make a beat.

## Troubleshooting
- Tools missing in Claude: uv isn't installed, or Claude wasn't restarted after installing it.
- CONTROLLER_MISSING: run `setup_boothmate` again, then fully restart FL Studio. On Windows, recheck step 4.
- Ports not found (Windows): names must be exactly `FLStudioMCP RX` / `FLStudioMCP TX`, and loopMIDI must be running.
- Notes don't appear: arm MCP Apply (step 6) and keep FL Studio the focused window while writing.
