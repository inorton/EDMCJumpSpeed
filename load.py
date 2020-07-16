"""
The "Jump Speed" Plugin
"""
try:
    import Tkinter as tk
except ImportError:
    import tkinter as tk
import sys
import time
import math
from l10n import Locale

this = sys.modules[__name__]  # For holding module globals

try:
    from config import config
except ImportError:
    config = dict()

CFG_DISTANCE = "JumpSpeed_distance"
this.star_pos = None    #Used for carrier jumps to calculate distance

class Jump(object):
    """
    Represent a jump
    """

    distance = 0.0
    time = 0


class JumpSpeed(object):
    """
    The main class for the jumpspeed plugin
    """

    speed_widget = None
    rate_widget = None
    dist_widget = None
    saved_distance = 0
    jumps = []

    def reset(self):
        """
        Reset button pressed
        :return:
        """
        self.jumps = []
        self.saved_distance = 0
        self.update_window()
        self.save()

    def load(self):
        """
        Load saved distance from config
        :return:
        """
        saved = config.get(CFG_DISTANCE)
        if not saved:
            self.saved_distance = 0.0
        else:
            self.saved_distance = float(saved)

    def save(self):
        """
        Save the saved distance to config
        :return:
        """
        config.set(CFG_DISTANCE, str(self.saved_distance + self.trip_distance()))

    def jump(self, distance):
        """
        Record a jump
        :param distance:
        :return:
        """
        data = Jump()
        data.distance = distance
        data.time = time.time()
        self.jumps.append(data)
        self.update_window()
        self.save()

    def trip_distance(self):
        """
        Measure how far we've jumped
        :return:
        """
        return sum([x.distance for x in self.jumps])

    def rate(self):
        """
        Get the jump/hr rate
        :return:
        """
        if len(self.jumps) > 1:
            started = self.jumps[0].time
            now = time.time()
            return len(self.jumps) * 60.0 * 60.0 / (now - started)
        else:
            return 0.0

    def speed(self):
        """
        Get the jump speed in ly/hr
        :return:
        """
        dist = self.trip_distance()
        if dist > 0 and len(self.jumps) > 1:
            started = self.jumps[0].time
            now = time.time()
            return dist * 60.0 * 60.0 / (now - started)
        else:
            return 0.0

    def update_window(self):
        """
        Update the EDMC window
        :return:
        """
        self.update_jumpspeed_dist()
        self.update_jumpspeed_rate()
        self.update_jumpspeed_speed()

    def update_jumpspeed_rate(self):
        """
        Set the jump rate rate in the EDMC window
        :param msg:
        :return:
        """
        msg = "{} Jumps/hr".format(Locale.stringFromNumber(self.rate(), 2))
        self.rate_widget.after(0, self.rate_widget.config, {"text": msg})

    def update_jumpspeed_speed(self):
        """
        Set the jump speed rate in the EDMC window
        :param msg:
        :return:
        """
        msg = "{} Ly/hr".format(Locale.stringFromNumber(self.speed(), 2))
        self.speed_widget.after(0, self.speed_widget.config, {"text": msg})

    def update_jumpspeed_dist(self):
        """
        Set the jump speed rate in the EDMC window
        :param msg:
        :return:
        """
        msg = "{} Ly".format(Locale.stringFromNumber(self.trip_distance() + self.saved_distance, 2))
        self.dist_widget.after(0, self.dist_widget.config, {"text": msg})


def plugin_start():
    jumpspeed = JumpSpeed()
    jumpspeed.load()
    this.jumpspeed = jumpspeed


def plugin_start3(plugindir):
    plugin_start()


def plugin_app(parent):
    """
    Create a pair of TK widgets for the EDMC main window
    """
    jumpspeed = this.jumpspeed

    frame = tk.Frame(parent)

    jumpspeed.rate_widget = tk.Label(
        frame,
        text="...",
        justify=tk.RIGHT)
    rate_label = tk.Label(frame, text="Jump Rate:", justify=tk.LEFT)
    rate_label.grid(row=0, column=0, sticky=tk.W)
    jumpspeed.rate_widget.grid(row=0, column=2, sticky=tk.E)

    jumpspeed.speed_widget = tk.Label(
        frame,
        text="...",
        justify=tk.RIGHT)
    speed_label = tk.Label(frame, text="Speed:", justify=tk.LEFT)
    speed_label.grid(row=1, column=0, sticky=tk.W)
    jumpspeed.speed_widget.grid(row=1, column=2, sticky=tk.E)

    jumpspeed.dist_widget = tk.Label(
        frame,
        text="...",
        justify=tk.RIGHT)
    dist_label = tk.Label(frame, text="Distance:", justify=tk.LEFT)
    dist_label.grid(row=2, column=0, sticky=tk.W)
    jumpspeed.dist_widget.grid(row=2, column=2, sticky=tk.E)

    reset_btn = tk.Button(frame, text="Reset", command=jumpspeed.reset)
    reset_btn.grid(row=2, column=1, sticky=tk.W)

    frame.columnconfigure(2, weight=1)

    jumpspeed.update_window()
    return frame


def journal_entry(cmdr, is_beta, system, station, entry, state):
    """
    Process a journal event
    :param cmdr:
    :param is_beta:
    :param system:
    :param station:
    :param entry:
    :param state:
    :return:
    """
    if entry["event"] in ["FSDJump", "Location", "CarrierJump", "StartUp"]:
        #Original JumpDist calculation
        if "JumpDist" in entry:
            this.jumpspeed.jump(entry["JumpDist"])
        
        #calculate JumpDist from stored coords and new coords
        if this.star_pos and entry["event"] == "CarrierJump":
            this.jumpspeed.jump(math.sqrt((this.star_pos[0] - entry["StarPos"][0]) ** 2 + (this.star_pos[1] - entry["StarPos"][1]) ** 2 + (this.star_pos[2] - entry["StarPos"][2]) ** 2))
         
        #Store coords for possible CarrierJump
        if "StarPos" in entry:
            this.star_pos = entry["StarPos"]
