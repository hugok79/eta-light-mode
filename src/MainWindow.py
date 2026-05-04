#!/usr/bin/python3

import os
import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gio, Gtk  # noqa


class MainWindow:
    def __init__(self, application):
        # Gtk Builder
        self.builder = Gtk.Builder()
        self.application = application

        # Import UI file:
        self.builder.add_from_file(
            os.path.dirname(os.path.abspath(__file__)) + "/../ui/MainWindow.glade"
        )
        self.builder.connect_signals(self)

        # Window
        self.window = self.builder.get_object("window")
        self.window.set_application(application)
        self.window.connect("destroy", self.on_destroy)

        # UI Components
        self.define_components()

        # Variables
        self.define_variables()

        # Show Screen:
        self.window.show_all()

    # Window methods:
    def on_destroy(self, _action):
        self.window.get_application().quit()

    def define_components(self):
        def UI(s):
            return self.builder.get_object(s)

        self.stack = UI("stack")

        # Dialog:
        self.dialog_about = UI("dialog_about")

    def define_variables(self):
        self.cinnamon_gsettings = Gio.Settings.new("org.cinnamon")
        self.muffin_gsettings = Gio.Settings.new("org.cinnamon.muffin")
        self.nemo_preferences_gsettings = Gio.Settings.new("org.nemo.preferences")

    # == FUNCTIONS ==
    def set_effects(self, value):
        if not isinstance(value, bool):
            return False

        self.cinnamon_gsettings.set_boolean("desktop-effects-workspace", value)

    def set_compositor(self, value):
        if not isinstance(value, bool):
            return False

        self.muffin_gsettings.set_boolean("unredirect-fullscreen-windows", value)

    def set_show_thumbnails(self, value):
        if not isinstance(value, bool):
            return False

        str_value = "local-only" if value else "never"

        self.nemo_preferences_gsettings.set_string("show-image-thumbnails", str_value)

    def set_show_directory_item_counts(self, value):
        if not isinstance(value, bool):
            return False

        str_value = "local-only" if value else "never"

        self.nemo_preferences_gsettings.set_string(
            "show-directory-item-counts", str_value
        )

    def toggle_light_mode(self, state):
        self.set_effects(not state)
        self.set_compositor(state)
        self.set_show_thumbnails(not state)
        self.set_show_directory_item_counts(not state)

    # == CALLBACKS ==
    def on_ui_switch_state_set(self, switch, state):
        self.toggle_light_mode(state)

    # About Window
    def on_btn_about_clicked(self, btn):
        self.dialog_about.run()
        self.dialog_about.hide()
