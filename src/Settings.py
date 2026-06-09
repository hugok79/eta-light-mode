from gi.repository import GObject  # noqa

from locale import gettext as _
import Cinnamon
import Screen

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
        "label": _("Disable Effects"),
        "read": lambda: not Cinnamon.get_effects(),
        "apply": lambda on: Cinnamon.set_effects(not on),
    },
    {
        "name": "compositor",
        "label": _("Direct Render Fullscreen Windows"),
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
        "label": _("Disable Cinnamon Monitoring"),
        "read": lambda: not Cinnamon.get_app_monitoring(),
        "apply": lambda on: Cinnamon.set_app_monitoring(not on),
    },
    {
        "name": "text-scaling",
        "label": _("Reduce Text Size"),
        "read": lambda: Cinnamon.get_font() == Cinnamon.FONT_LOW,
        "apply": lambda on: Cinnamon.set_font_all(
            Cinnamon.FONT_LOW if on else Cinnamon.FONT_NORMAL
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
    {
        "name": "low-resolution",
        "label": _("Reduce Resolution (1600x900)"),
        "read": lambda: Screen.is_low_resolution(),
        "apply": lambda on: Screen.set_resolution(on),
    },
    {
        "name": "low-refresh-rate",
        "label": _("Reduce Refresh Rate (50 Hz)"),
        "read": lambda: Screen.is_low_refresh_rate(),
        "apply": lambda on: Screen.set_refresh_rate(on),
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
