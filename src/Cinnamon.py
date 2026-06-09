import json

from gi.repository import Gio, GLib

# Normal / low-power value pairs for the non-boolean settings.
FONT_LOW, FONT_NORMAL = "Ubuntu Regular 9.5", "Ubuntu Regular 11"
FONT_SCALING_LOW, FONT_SCALING_NORMAL = 0.8, 1.0  # NOT USED, JUST CHANGING FONT SIZE
_FONT_SCALING_MIN, _FONT_SCALING_MAX = 0.5, 3.0
PANEL_HEIGHT_LOW, PANEL_HEIGHT_NORMAL = 32, 40
PANEL_ICON_LOW, PANEL_ICON_NORMAL = 20, 28
FILE_ICON_LOW, FILE_ICON_NORMAL = "small", "standard"
ICON_ZOOM_LEVELS = (
    "smallest",
    "smaller",
    "small",
    "standard",
    "large",
    "larger",
    "largest",
)

_cinnamon_gsettings = Gio.Settings.new("org.cinnamon")
_muffin_gsettings = Gio.Settings.new("org.cinnamon.muffin")
_interface_gsettings = Gio.Settings.new("org.cinnamon.desktop.interface")
_wm_gsettings = Gio.Settings.new("org.cinnamon.desktop.wm.preferences")
_nemo_preferences_gsettings = Gio.Settings.new("org.nemo.preferences")
_nemo_icon_view_gsettings = Gio.Settings.new("org.nemo.icon-view")
_nemo_desktop_gsettings = Gio.Settings.new("org.nemo.desktop")


# == Global Effects ==
def set_effects(value):
    if not isinstance(value, bool):
        return False

    _cinnamon_gsettings.set_boolean("desktop-effects-workspace", value)


def get_effects() -> bool:
    return _cinnamon_gsettings.get_boolean("desktop-effects-workspace")


# == Full Screen Compositor ==
def set_compositor(value):
    if not isinstance(value, bool):
        return False

    _muffin_gsettings.set_boolean("unredirect-fullscreen-windows", value)


def get_compositor() -> bool:
    return _muffin_gsettings.get_boolean("unredirect-fullscreen-windows")


# == Thumbnails ==
def set_show_thumbnails(value):
    if not isinstance(value, bool):
        return False

    str_value = "local-only" if value else "never"

    _nemo_preferences_gsettings.set_string("show-image-thumbnails", str_value)


def get_show_thumbnails() -> str:
    return _nemo_preferences_gsettings.get_string("show-image-thumbnails")


# == Directory item count calculations ==
def set_show_directory_item_counts(value):
    if not isinstance(value, bool):
        return False

    str_value = "local-only" if value else "never"

    _nemo_preferences_gsettings.set_string("show-directory-item-counts", str_value)


def get_show_directory_item_counts() -> str:
    return _nemo_preferences_gsettings.get_string("show-directory-item-counts")


# == Font Scaling ==
# dconf: org.cinnamon.desktop.interface.text-scaling-factor (double, range 0.5 - 3.0)
def set_font_scaling(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False

    value = max(_FONT_SCALING_MIN, min(_FONT_SCALING_MAX, float(value)))
    _interface_gsettings.set_double("text-scaling-factor", value)


def get_font_scaling() -> float:
    return _interface_gsettings.get_double("text-scaling-factor")


# == Panel Size ==
# - org.cinnamon.panels-height (panel yüksekliği)
#       type "as", entries are "<panelId>:<height>", e.g. ['1:40']
# - org.cinnamon.panel-zone-symbolic-icon-sizes (panel applet ikon boyutu)
#       JSON string, e.g. '[{"panelId": 1, "left": 28, "center": 28, "right": 16}]'
# - org.cinnamon.panel-zone-text-sizes (panel yazı boyutu, punto)
#       JSON string, e.g. '[{"panelId": 1, "left": 0.0, "center": 0.0, "right": 0.0}]'


def set_panel_height(value, panel_id=1):
    if not isinstance(value, int) or isinstance(value, bool):
        return False

    entries = _cinnamon_gsettings.get_strv("panels-height")
    updated = []
    found = False
    for entry in entries:
        entry_id, _, _height = entry.partition(":")
        if entry_id == str(panel_id):
            updated.append(f"{panel_id}:{value}")
            found = True
        else:
            updated.append(entry)
    if not found:
        updated.append(f"{panel_id}:{value}")

    _cinnamon_gsettings.set_strv("panels-height", updated)


def get_panel_height(panel_id=1) -> int:
    entries = _cinnamon_gsettings.get_strv("panels-height")
    for entry in entries:
        entry_id, _, height = entry.partition(":")
        if entry_id == str(panel_id):
            try:
                return int(height)
            except ValueError:
                return 0
    return 0


def _get_panel_zone_entry(data, panel_id):
    for entry in data:
        if entry.get("panelId") == panel_id:
            return entry
    new_entry = {"panelId": panel_id}
    data.append(new_entry)
    return new_entry


def set_panel_symbolic_icon_size(value, panel_id=1):
    if not isinstance(value, int) or isinstance(value, bool):
        return False

    data = json.loads(_cinnamon_gsettings.get_string("panel-zone-symbolic-icon-sizes"))
    entry = _get_panel_zone_entry(data, panel_id)
    entry["left"] = entry["center"] = entry["right"] = value
    _cinnamon_gsettings.set_string("panel-zone-symbolic-icon-sizes", json.dumps(data))


def get_panel_symbolic_icon_size(panel_id=1) -> int:
    data = json.loads(_cinnamon_gsettings.get_string("panel-zone-symbolic-icon-sizes"))
    for entry in data:
        if entry.get("panelId") == panel_id:
            return int(entry.get("left", 0))
    return 0


def set_panel_text_size(value, panel_id=1):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False

    data = json.loads(_cinnamon_gsettings.get_string("panel-zone-text-sizes"))
    entry = _get_panel_zone_entry(data, panel_id)
    entry["left"] = entry["center"] = entry["right"] = float(value)
    _cinnamon_gsettings.set_string("panel-zone-text-sizes", json.dumps(data))


def get_panel_text_size(panel_id=1) -> float:
    data = json.loads(_cinnamon_gsettings.get_string("panel-zone-text-sizes"))
    for entry in data:
        if entry.get("panelId") == panel_id:
            return float(entry.get("left", 0.0))
    return 0.0


# == App Monitoring ==
# dconf: org.cinnamon.enable-app-monitoring (uygulama verisi topluyor?)
def set_app_monitoring(value):
    if not isinstance(value, bool):
        return False

    _cinnamon_gsettings.set_boolean("enable-app-monitoring", value)


def get_app_monitoring() -> bool:
    return _cinnamon_gsettings.get_boolean("enable-app-monitoring")


# == Desktop and File Viewer Icons ==
# - org.nemo.icon-view.default-zoom-level (dosya ikon boyutu), enum:
#       'smallest', 'smaller', 'small', 'standard', 'large', 'larger', 'largest'
def set_file_icon_size(value):
    if value not in ICON_ZOOM_LEVELS:
        return False

    _nemo_icon_view_gsettings.set_string("default-zoom-level", value)


def get_file_icon_size() -> str:
    return _nemo_icon_view_gsettings.get_string("default-zoom-level")


# == Fonts ==
# - org.nemo.desktop.font (masaüstü dosya font boyutu), e.g. 'Noto Sans 10'
# - org.cinnamon.desktop.interface.font-name (genel font), e.g. 'Noto Sans 10'
def set_desktop_font(value):
    if not isinstance(value, str):
        return False

    _nemo_desktop_gsettings.set_string("font", value)


def get_desktop_font() -> str:
    return _nemo_desktop_gsettings.get_string("font")


def set_font(value):
    if not isinstance(value, str):
        return False

    _interface_gsettings.set_string("font-name", value)


def get_font() -> str:
    return _interface_gsettings.get_string("font-name")


def set_title_font(value):
    if not isinstance(value, str):
        return False

    _wm_gsettings.set_string("titlebar-font", value)


def get_title_font() -> str:
    return _wm_gsettings.get_string("titlebar-font")


def set_font_all(value):
    set_font(value)
    set_desktop_font(value)
    set_title_font(value.replace("Regular", "Bold"))
