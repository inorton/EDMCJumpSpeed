"""
The "Jump Speed" Plugin
EDMC 6 compatible
"""
import sys
import time
import math

try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk  # pragma: no cover (legacy)

# EDMC plugin API imports
try:
    # EDMC docs say "import L10n" is supported; older plugins often used l10n
    from L10n import Locale
except Exception:
    # fallback for older environments
    from l10n import Locale  # type: ignore

try:
    from config import config
except Exception:
    # Allow running outside EDMC without exploding
    class _DummyConfig:
        shutting_down = False
        def get_str(self, _k): return ""
        def set(self, _k, _v): pass
    config = _DummyConfig()

this = sys.modules[__name__]  # For holding module globals

CFG_DISTANCE = "JumpSpeed_distance"
this.star_pos = None  # Used for carrier jumps to calculate distance
this.jumpspeed = None
this._enabled = True


class Jump:
    """Represent a jump"""
    def __init__(self, distance: float, t: float):
        self.distance = float(distance)
        self.time = float(t)


class JumpSpeed:
    """The main class for the jumpspeed plugin"""

    def __init__(self):
        self.speed_widget = None
        self.rate_widget = None
        self.dist_widget = None
        self.saved_distance = 0.0
        self.jumps = []

    def reset(self):
        self.jumps = []
        self.saved_distance = 0.0
        self.update_window()
        self.save()

    def load(self):
        saved = ""
        try:
            saved = config.get_str(CFG_DISTANCE)
        except Exception:
            saved = ""
        self.saved_distance = float(saved) if saved else 0.0

    def save(self):
        # Respect EDMC shutdown + allow running outside EDMC
        if getattr(config, "shutting_down", False):
            return
        try:
            config.set(CFG_DISTANCE, str(self.saved_distance + self.trip_distance()))
        except Exception:
            pass

    def jump(self, distance):
        if not this._enabled:
            return
        data = Jump(distance, time.time())
        self.jumps.append(data)
        self.update_window()
        self.save()

    def trip_distance(self):
        return sum(j.distance for j in self.jumps)

    def rate(self):
        if len(self.jumps) > 1:
            started = self.jumps[0].time
            now = time.time()
            dt = now - started
            return (len(self.jumps) * 3600.0 / dt) if dt > 0 else 0.0
        return 0.0

    def speed(self):
        dist = self.trip_distance()
        if dist > 0 and len(self.jumps) > 1:
            started = self.jumps[0].time
            now = time.time()
            dt = now - started
            return (dist * 3600.0 / dt) if dt > 0 else 0.0
        return 0.0

    def update_window(self):
        if getattr(config, "shutting_down", False):
            return
        self.update_jumpspeed_dist()
        self.update_jumpspeed_rate()
        self.update_jumpspeed_speed()

    @staticmethod
    def _fmt(num, decimals=2):
        # EDMC 6 removed Locale.stringFromNumber -> use string_from_number
        if hasattr(Locale, "string_from_number"):
            return Locale.string_from_number(num, decimals)
        # fallback for very old EDMC
        if hasattr(Locale, "stringFromNumber"):
            return Locale.stringFromNumber(num, decimals)  # type: ignore
        return f"{num:.{decimals}f}"

    def update_jumpspeed_rate(self):
        if not self.rate_widget:
            return
        msg = f"{self._fmt(self.rate(), 2)} Jumps/hr"
        try:
            self.rate_widget.after(0, self.rate_widget.config, {"text": msg})
        except Exception:
            pass

    def update_jumpspeed_speed(self):
        if not self.speed_widget:
            return
        msg = f"{self._fmt(self.speed(), 2)} Ly/hr"
        try:
            self.speed_widget.after(0, self.speed_widget.config, {"text": msg})
        except Exception:
            pass

    def update_jumpspeed_dist(self):
        if not self.dist_widget:
            return
        msg = f"{self._fmt(self.trip_distance() + self.saved_distance, 2)} Ly"
        try:
            self.dist_widget.after(0, self.dist_widget.config, {"text": msg})
        except Exception:
            pass


def plugin_start():
    jumpspeed = JumpSpeed()
    jumpspeed.load()
    this.jumpspeed = jumpspeed


def plugin_start3(plugindir):
    plugin_start()
    return "jumpspeed"


def plugin_stop():
    # Needed for EDMC 6 plugin enable/disable; keep it simple.
    this._enabled = False


def plugin_app(parent):
    """Create a pair of TK widgets for the EDMC main window"""
    jumpspeed = this.jumpspeed

    frame = tk.Frame(parent)

    jumpspeed.rate_widget = tk.Label(frame, text="...", justify=tk.RIGHT)
    tk.Label(frame, text="Jump Rate:", justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W)
    jumpspeed.rate_widget.grid(row=0, column=2, sticky=tk.E)

    jumpspeed.speed_widget = tk.Label(frame, text="...", justify=tk.RIGHT)
    tk.Label(frame, text="Speed:", justify=tk.LEFT).grid(row=1, column=0, sticky=tk.W)
    jumpspeed.speed_widget.grid(row=1, column=2, sticky=tk.E)

    jumpspeed.dist_widget = tk.Label(frame, text="...", justify=tk.RIGHT)
    tk.Label(frame, text="Distance:", justify=tk.LEFT).grid(row=2, column=0, sticky=tk.W)
    jumpspeed.dist_widget.grid(row=2, column=2, sticky=tk.E)

    tk.Button(frame, text="Reset", command=jumpspeed.reset).grid(row=2, column=1, sticky=tk.W)

    frame.columnconfigure(2, weight=1)
    jumpspeed.update_window()
    return frame


def journal_entry(cmdr, is_beta, system, station, entry, state):
    if not this._enabled or this.jumpspeed is None:
        return

    if entry.get("event") in ["FSDJump", "Location", "CarrierJump", "StartUp"]:
        # Original JumpDist calculation (for normal ship jumps)
        if "JumpDist" in entry:
            this.jumpspeed.jump(entry["JumpDist"])

        # Calculate JumpDist for carrier jump from coords
        if this.star_pos and entry.get("event") == "CarrierJump" and "StarPos" in entry:
            x0, y0, z0 = this.star_pos
            x1, y1, z1 = entry["StarPos"]
            this.jumpspeed.jump(math.sqrt((x0 - x1) ** 2 + (y0 - y1) ** 2 + (z0 - z1) ** 2))

        # Store coords for possible CarrierJump
        if "StarPos" in entry:
            this.star_pos = entry["StarPos"]
