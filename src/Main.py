#!/usr/bin/python3

import sys

import gi

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


app = Application()
app.run(sys.argv)
