#!/usr/bin/python3

import os

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gio, GObject, Gtk  # noqa

from locale import gettext as _

import Cinnamon


# == Settings model ==
# Every entry becomes a boolean GObject property on LightModeSettings.
# The property is True when the *power-saving* value is active. A switch is
# two-way bound to its property, and changing the property automatically calls
# the matching Cinnamon setter, so toggling either the global switch or a single
# row applies the change and keeps the UI in sync.
#   - name:  property/binding name (also the dconf-independent identifier)
#   - label: row label
#   - read:  reads the live Cinnamon state -> True if power-saving is on
#   - apply: applies the value to Cinnamon (True = power-saving value)
SETTINGS = [
    {
        "name": "effects",
        "label": _("Disable Desktop Effects"),
        "read": lambda: not Cinnamon.get_effects(),
        "apply": lambda on: Cinnamon.set_effects(not on),
    },
    {
        "name": "compositor",
        "label": _("Unredirect Fullscreen Windows"),
        "read": lambda: Cinnamon.get_compositor(),
        "apply": lambda on: Cinnamon.set_compositor(on),
    },
    {
        "name": "thumbnails",
        "label": _("Disable Image Thumbnails"),
        "read": lambda: Cinnamon.get_show_thumbnails() == "never",
        "apply": lambda on: Cinnamon.set_show_thumbnails(not on),
    },
    {
        "name": "directory-item-counts",
        "label": _("Disable Folder Item Counts"),
        "read": lambda: Cinnamon.get_show_directory_item_counts() == "never",
        "apply": lambda on: Cinnamon.set_show_directory_item_counts(not on),
    },
    {
        "name": "app-monitoring",
        "label": _("Disable App Usage Monitoring"),
        "read": lambda: not Cinnamon.get_app_monitoring(),
        "apply": lambda on: Cinnamon.set_app_monitoring(not on),
    },
    {
        "name": "text-scaling",
        "label": _("Reduce Text Scaling"),
        "read": lambda: Cinnamon.get_font_scaling() < Cinnamon.FONT_SCALING_NORMAL,
        "apply": lambda on: Cinnamon.set_font_scaling(
            Cinnamon.FONT_SCALING_LOW if on else Cinnamon.FONT_SCALING_NORMAL
        ),
    },
    {
        "name": "panel-height",
        "label": _("Reduce Panel Height"),
        "read": lambda: Cinnamon.get_panel_height() < Cinnamon.PANEL_HEIGHT_NORMAL,
        "apply": lambda on: Cinnamon.set_panel_height(
            Cinnamon.PANEL_HEIGHT_LOW if on else Cinnamon.PANEL_HEIGHT_NORMAL
        ),
    },
    {
        "name": "panel-icon-size",
        "label": _("Reduce Panel Icon Size"),
        "read": lambda: Cinnamon.get_panel_symbolic_icon_size()
        < Cinnamon.PANEL_ICON_NORMAL,
        "apply": lambda on: Cinnamon.set_panel_symbolic_icon_size(
            Cinnamon.PANEL_ICON_LOW if on else Cinnamon.PANEL_ICON_NORMAL
        ),
    },
    {
        "name": "file-icon-size",
        "label": _("Smaller File & Desktop Icons"),
        "read": lambda: Cinnamon.get_file_icon_size()
        in ("smallest", "smaller", "small"),
        "apply": lambda on: Cinnamon.set_file_icon_size(
            Cinnamon.FILE_ICON_LOW if on else Cinnamon.FILE_ICON_NORMAL
        ),
    },
]

_SETTINGS_BY_NAME = {s["name"]: s for s in SETTINGS}


class LightModeSettings(GObject.Object):
    __gtype_name__ = "LightModeSettings"
    __gproperties__ = {
        s["name"]: (
            bool,
            s["name"],
            s["label"],
            False,
            GObject.ParamFlags.READWRITE,
        )
        for s in SETTINGS
    }

    def __init__(self):
        super().__init__()
        # Seed each property with the current live state without applying it.
        self._values = {s["name"]: bool(s["read"]()) for s in SETTINGS}

    def do_get_property(self, prop):
        return self._values[prop.name]

    def do_set_property(self, prop, value):
        value = bool(value)
        if self._values.get(prop.name) == value:
            return
        self._values[prop.name] = value
        _SETTINGS_BY_NAME[prop.name]["apply"](value)

    def set_all(self, value):
        for name in self._values:
            self.set_property(name, value)


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
        self.preferences = LightModeSettings()

    def setup_ui(self):
        # == One label + one switch per setting. ==
        # Each switch is two-way bound to its boolean property on self.preferences.
        # SYNC_CREATE seeds the switch from the current state; BIDIRECTIONAL makes
        # a user toggle write the property, whose setter calls Cinnamon. The global
        # ui_switch only needs to flip the properties (see toggle_light_mode).
        for s in SETTINGS:
            box = Gtk.Box(spacing=7)
            switch = Gtk.Switch()

            self.preferences.bind_property(
                s["name"],
                switch,
                "active",
                GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
            )

            box.add(Gtk.Label(label=s["label"], hexpand=True, halign="start"))
            box.add(switch)
            self.ui_box_switches.add(box)

    # == FUNCTIONS ==
    def toggle_light_mode(self, state):
        # Flip every property; each setter call and switch update happens via the
        # property bindings, so we don't touch Cinnamon or the switches directly.
        self.preferences.set_all(state)

        label = _("Active") if state else _("Disabled")
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
