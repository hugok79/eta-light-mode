#!/usr/bin/python3

import os
import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gio, Gtk  # noqa

import Cinnamon


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

        is_light_mode_active = self.is_light_mode_active()

        self.ui_status_label = UI("ui_status_label")

        self.ui_switch = UI("ui_switch")
        self.ui_switch.set_active(is_light_mode_active)

        # Dialog:
        self.dialog_about = UI("dialog_about")

    def define_variables(self):
        pass

    # == FUNCTIONS ==

    def toggle_light_mode(self, state):
        Cinnamon.set_effects(not state)
        Cinnamon.set_compositor(state)
        Cinnamon.set_show_thumbnails(not state)
        Cinnamon.set_show_directory_item_counts(not state)

        label = "Etkin" if state else "Devre Dışı"
        self.ui_status_label.set_label(label)

    def is_light_mode_active(self):
        return not Cinnamon.get_effects() and Cinnamon.get_compositor()

    # == CALLBACKS ==
    def on_ui_switch_state_set(self, switch, state):
        self.toggle_light_mode(state)
        print(state)

    # About Window
    def on_btn_about_clicked(self, btn):
        self.dialog_about.run()
        self.dialog_about.hide()
