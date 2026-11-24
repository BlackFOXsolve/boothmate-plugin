"""Open FL Studio for the user, close its startup welcome window, and notice
trial mode, so a beginner never has to click through FL's start-up screens.

macOS uses `open` and System Events (needs the same Accessibility permission
BoothMate already uses for the piano-roll shortcut). Windows finds FL64.exe in
Program Files and uses pyautogui/pygetwindow when present.
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
import time

BUNDLE_ID = "com.image-line.flstudio"
_WIN_EXE = "FL64.exe"


def _osa(script: str, timeout: float = 10.0):
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except (OSError, subprocess.SubprocessError) as e:
        return 1, "", str(e)


def is_running() -> bool:
    if sys.platform == "darwin":
        rc, out, _ = _osa('application id "%s" is running' % BUNDLE_ID)
        return rc == 0 and out == "true"
    if sys.platform == "win32":
        try:
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq %s" % _WIN_EXE],
                                 capture_output=True, text=True, timeout=10).stdout
        except (OSError, subprocess.SubprocessError):
            return False
        return _WIN_EXE.lower() in out.lower()
    return False


def _windows_exe():
    roots = {os.environ.get("ProgramFiles", r"C:\Program Files"),
             os.environ.get("ProgramW6432", r"C:\Program Files"),
             os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")}
    hits = []
    for root in roots:
        hits += glob.glob(os.path.join(root, "Image-Line", "FL Studio*", _WIN_EXE))
    return sorted(hits)[-1] if hits else None


def launch() -> dict:
    if sys.platform == "darwin":
        r = subprocess.run(["open", "-b", BUNDLE_ID], capture_output=True, text=True)
        if r.returncode:
            return {"ok": False, "error": "FL Studio isn't installed on this Mac."}
        return {"ok": True}
    if sys.platform == "win32":
        exe = _windows_exe()
        if not exe:
            return {"ok": False, "error": "Couldn't find FL Studio in Program Files."}
        os.startfile(exe)  # noqa: S606 - user's own installed app
        return {"ok": True, "path": exe}
    return {"ok": False, "error": "Opening FL Studio works on Windows and macOS."}


def quit_app(timeout: float = 30.0) -> dict:
    """Ask FL Studio to quit normally. If a project has unsaved changes FL
    shows its own save prompt, which the user answers."""
    if sys.platform == "darwin":
        _osa('tell application id "%s" to quit' % BUNDLE_ID, timeout=timeout)
    elif sys.platform == "win32":
        subprocess.run(["taskkill", "/IM", _WIN_EXE], capture_output=True)
    else:
        return {"ok": False, "error": "Not supported on this system."}
    end = time.time() + timeout
    while time.time() < end:
        if not is_running():
            return {"ok": True}
        time.sleep(1.0)
    return {"ok": False, "error": "FL Studio is still open. It may be asking whether to "
                                  "save the project; answer it, then try again."}


# ---------------------------------------------------------------- windows (macOS)
_LIST_WINDOWS = '''
tell application "System Events"
  set p to first process whose bundle identifier is "%s"
  set out to ""
  repeat with w in windows of p
    set {x, y} to position of w
    set {ww, hh} to size of w
    set out to out & (name of w as text) & "|" & x & "|" & y & "|" & ww & "|" & hh & linefeed
  end repeat
  return out
end tell''' % BUNDLE_ID


def mac_windows():
    rc, out, err = _osa(_LIST_WINDOWS)
    if rc:
        return None, err
    wins = []
    for line in out.splitlines():
        parts = line.rsplit("|", 4)
        if len(parts) == 5:
            try:
                wins.append({"title": parts[0], "x": int(float(parts[1])), "y": int(float(parts[2])),
                             "w": int(float(parts[3])), "h": int(float(parts[4]))})
            except ValueError:
                continue
    return wins, None


def _is_welcome(win) -> bool:
    t = (win.get("title") or "").lower()
    if "welcome" in t:
        return True
    # FL draws the welcome screen in its own window of a fixed size.
    return abs(win["w"] - 874) <= 12 and abs(win["h"] - 573) <= 12


def dismiss_welcome(attempts: int = 3) -> dict:
    """Close FL Studio's start-up welcome window if it's showing."""
    if sys.platform == "darwin":
        trial = False
        for _ in range(attempts):
            wins, err = mac_windows()
            if wins is None:
                return {"ok": False, "error": "Can't read FL Studio's windows. Turn on "
                        "Accessibility for Claude in System Settings > Privacy & Security.",
                        "detail": err}
            trial = trial or any("trial" in (w["title"] or "").lower() for w in wins)
            welcome = [w for w in wins if _is_welcome(w)]
            if not welcome:
                return {"ok": True, "closed": True, "trial": trial}
            w = welcome[0]
            # Bring FL forward, then press Escape; if the window stays, click its X.
            _osa('tell application id "%s" to activate' % BUNDLE_ID)
            time.sleep(0.4)
            _osa('tell application "System Events" to key code 53')
            time.sleep(0.8)
            wins2, _ = mac_windows()
            if wins2 is not None and not [v for v in wins2 if _is_welcome(v)]:
                return {"ok": True, "closed": True, "method": "escape", "trial": trial}
            cx, cy = w["x"] + w["w"] - 14, w["y"] + 14
            _osa('tell application "System Events" to click at {%d, %d}' % (cx, cy))
            time.sleep(0.8)
        wins3, _ = mac_windows()
        still = bool(wins3 and [v for v in wins3 if _is_welcome(v)])
        return {"ok": not still, "closed": not still, "trial": trial}
    if sys.platform == "win32":
        try:
            import pyautogui
            import pygetwindow
        except ImportError:
            return {"ok": False, "error": "Window control isn't available on this PC."}
        for _ in range(attempts):
            wins = [w for w in pygetwindow.getAllWindows() if "welcome to fl studio" in w.title.lower()]
            if not wins:
                return {"ok": True, "closed": True}
            w = wins[0]
            trial = "trial" in w.title.lower()
            try:
                w.activate()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.4)
            pyautogui.press("esc")
            time.sleep(0.8)
            if not [v for v in pygetwindow.getAllWindows()
                    if "welcome to fl studio" in v.title.lower()]:
                return {"ok": True, "closed": True, "trial": trial}
            pyautogui.click(w.left + w.width - 14, w.top + 14)
            time.sleep(0.8)
        return {"ok": False, "closed": False}
    return {"ok": False, "error": "Not supported on this system."}
