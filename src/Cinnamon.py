from gi.repository import Gio

_cinnamon_gsettings = Gio.Settings.new("org.cinnamon")
_muffin_gsettings = Gio.Settings.new("org.cinnamon.muffin")
_nemo_preferences_gsettings = Gio.Settings.new("org.nemo.preferences")


def set_effects(value):
    if not isinstance(value, bool):
        return False

    _cinnamon_gsettings.set_boolean("desktop-effects-workspace", value)


def get_effects() -> bool:
    return _cinnamon_gsettings.get_boolean("desktop-effects-workspace")


def set_compositor(value):
    if not isinstance(value, bool):
        return False

    _muffin_gsettings.set_boolean("unredirect-fullscreen-windows", value)


def get_compositor() -> bool:
    return _muffin_gsettings.get_boolean("unredirect-fullscreen-windows")


def set_show_thumbnails(value):
    if not isinstance(value, bool):
        return False

    str_value = "local-only" if value else "never"

    _nemo_preferences_gsettings.set_string("show-image-thumbnails", str_value)


def get_show_thumbnails() -> str:
    return _nemo_preferences_gsettings.get_string("show-image-thumbnails")


def set_show_directory_item_counts(value):
    if not isinstance(value, bool):
        return False

    str_value = "local-only" if value else "never"

    _nemo_preferences_gsettings.set_string("show-directory-item-counts", str_value)


def get_show_directory_item_counts() -> str:
    return _nemo_preferences_gsettings.get_string("show-directory-item-counts")
