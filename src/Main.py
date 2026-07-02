#!/usr/bin/python3

import argparse
import sys

import gi

import Settings

gi.require_version("Gtk", "3.0")
import locale

from gi.repository import Gio, Gtk

# Translation Constants:
APPNAME = "eta-light-mode"
TRANSLATIONS_PATH = "/usr/share/locale"
locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
locale.textdomain(APPNAME)


from MainWindow import MainWindow


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="tr.org.eta.light-mode",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            **kwargs,
        )
        self.window = None

    def do_activate(self):
        self.window = MainWindow(self)


# Argument Parsing
parser = argparse.ArgumentParser(
    description="ETA Light Mode, Lighten your cinnamon desktop."
)

parser.add_argument("-e", "--enable", action="store_true", help="Enable light mode.")
parser.add_argument("-d", "--disable", action="store_true", help="Disable light mode.")
parser.add_argument(
    "-a", "--apply-config", action="store_true", help="Applies config file to the user."
)

args = parser.parse_args()

if args.enable:
    settings = Settings.LightModeSettings()
    settings.set_all(True)
elif args.disable:
    settings = Settings.LightModeSettings()
    settings.set_all(False)
elif args.apply_config:
    settings = Settings.LightModeSettings()
    try:
        settings.load_and_apply(Settings.SETTINGS_FILE_PATH)
    except Exception as e:
        print(f"Couldn't apply: {e}")
        pass
else:
    app = Application()
    app.run(sys.argv)
