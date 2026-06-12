#!/usr/bin/python3

import os

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gio, GObject, Gtk, Gdk  # noqa

from locale import gettext as _

import Cinnamon
import Screen
import Settings


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

        # Setup UI
        self.setup_ui()

        # Setup CSS
        self.setup_css()

        # Connect main switch later:
        self.ui_switch.connect("state-set", self.on_ui_switch_state_set)

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
        self.ui_status_label.set_label(
            _("Active") if is_light_mode_active else _("Disabled")
        )

        self.ui_switch = UI("ui_switch")
        self.ui_switch.set_active(is_light_mode_active)

        self.ui_box_switches = UI("ui_box_switches")

        # Dialog:
        self.dialog_about = UI("dialog_about")

    def define_variables(self):
        # Boolean model backing every settings switch (and the global toggle).
        self.preferences = Settings.LightModeSettings()

    def setup_ui(self):
        # == One label + one switch per setting. ==
        for s in Settings.SETTINGS:
            box = Gtk.Box(spacing=7)
            switch = Gtk.Switch()

            self.preferences.bind_property(
                s["name"],
                switch,
                "active",
                GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
            )

            box.add(Gtk.Label(label=_(s["label"]), hexpand=True, halign="start"))
            box.add(switch)
            self.ui_box_switches.add(box)

    def setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .p-7 {padding: 7px;}
            .p-14 {padding: 14px;}
            """)

        style = self.window.get_style_context()
        style.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    # == FUNCTIONS ==
    def toggle_light_mode(self, state):
        # Flip every property
        self.preferences.set_all(state)

        label = _("Active") if state else _("Disabled")
        self.ui_status_label.set_label(label)

    def is_light_mode_active(self):
        return (
            not Cinnamon.get_effects()
            and Cinnamon.get_compositor()
            and not Cinnamon.get_app_monitoring()
        )

    # == CALLBACKS ==
    def on_ui_switch_state_set(self, switch, state):
        self.toggle_light_mode(state)
        print(state)

    # About Window
    def on_btn_about_clicked(self, btn):
        self.dialog_about.run()
        self.dialog_about.hide()
