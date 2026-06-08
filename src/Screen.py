from gi.repository import Gio, GLib

# == Monitor Resolution & Refresh Rate Change ==
# DBUS:
# - /org/cinnamon/Muffin/DisplayConfig
# - org.cinnamon.Muffin.DisplayConfig
# Methods:
# - GetResources () ↦ (UInt32 serial, Array of [Struct of (UInt32, Int64, Int32, Int32, Int32, Int32, Int32, UInt32, Array of [UInt32], Dict of {String, Variant})] crtcs, Array of [Struct of (UInt32, Int64, Int32, Array of [UInt32], String, Array of [UInt32], Array of [UInt32], Dict of {String, Variant})] outputs, Array of [Struct of (UInt32, Int64, UInt32, UInt32, Double, UInt32)] modes, Int32 max_screen_width, Int32 max_screen_height)
# - GetCurrentState () ↦ (UInt32 serial, Array of [Struct of (Struct of (String, String, String, String), Array of [Struct of (String, Int32, Int32, Double, Double, Array of [Double], Dict of {String, Variant})], Dict of {String, Variant})] monitors, Array of [Struct of (Int32, Int32, Double, UInt32, Boolean, Array of [Struct of (String, String, String, String)], Dict of {String, Variant})] logical_monitors, Dict of {String, Variant} properties)
# - ApplyMonitorsConfig (UInt32 serial, UInt32 method, Array of [Struct of (Int32 x, Int32 y, Double scale, UInt32 transform, Boolean primary, Array of [Struct of (String connector, String mode_id, Dict properties)])] logical_monitors, Dict properties)
#   method: 0 = verify, 1 = temporary (until reboot), 2 = persistent (saved to disk)

_DISPLAY_CONFIG_NAME = "org.cinnamon.Muffin.DisplayConfig"
_DISPLAY_CONFIG_PATH = "/org/cinnamon/Muffin/DisplayConfig"

_display_config_proxy = None


def _get_display_config_proxy():
    global _display_config_proxy
    if _display_config_proxy is None:
        _display_config_proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            _DISPLAY_CONFIG_NAME,
            _DISPLAY_CONFIG_PATH,
            _DISPLAY_CONFIG_NAME,
            None,
        )
    return _display_config_proxy


def _get_current_state():
    # Returns (serial, monitors, logical_monitors, properties) as native Python values.
    proxy = _get_display_config_proxy()
    result = proxy.call_sync("GetCurrentState", None, Gio.DBusCallFlags.NONE, -1, None)
    return result.unpack()


def _get_primary_connector(logical_monitors):
    for x, y, scale, transform, primary, monitors, props in logical_monitors:
        if primary and monitors:
            return monitors[0][0]  # monitor spec -> connector
    # No primary flagged: fall back to the first available monitor.
    if logical_monitors and logical_monitors[0][5]:
        return logical_monitors[0][5][0][0]
    return None


def _current_mode_id(monitors, connector):
    for monitor_spec, modes, props in monitors:
        if monitor_spec[0] != connector:
            continue
        for mode in modes:
            if mode[6].get("is-current", False):
                return mode[0]
        for mode in modes:
            if mode[6].get("is-preferred", False):
                return mode[0]
    return None


def _find_mode_id(monitors, connector, width, height, refresh_rate):
    candidates = []
    for monitor_spec, modes, props in monitors:
        if monitor_spec[0] != connector:
            continue
        for mode in modes:
            mode_id, mode_w, mode_h, mode_refresh = mode[0], mode[1], mode[2], mode[3]
            if mode_w == width and mode_h == height:
                candidates.append((mode_id, mode_refresh))

    if not candidates:
        return None
    if refresh_rate is None:
        # Highest available refresh rate at the requested resolution.
        return max(candidates, key=lambda candidate: candidate[1])[0]
    # Closest matching refresh rate (GetCurrentState reports e.g. 59.95 vs 60.0).
    return min(candidates, key=lambda candidate: abs(candidate[1] - refresh_rate))[0]


def get_resolution():
    """Current (width, height, refresh_rate) of the primary monitor, or None."""
    try:
        serial, monitors, logical_monitors, props = _get_current_state()
    except GLib.Error:
        return None

    connector = _get_primary_connector(logical_monitors)
    if connector is None:
        return None

    for monitor_spec, modes, mprops in monitors:
        if monitor_spec[0] != connector:
            continue
        for mode in modes:
            if mode[6].get("is-current", False):
                return (mode[1], mode[2], mode[3])
    return None


def get_available_resolutions() -> list:
    """List of available modes of the primary monitor as dicts."""
    try:
        serial, monitors, logical_monitors, props = _get_current_state()
    except GLib.Error:
        return []

    connector = _get_primary_connector(logical_monitors)
    if connector is None:
        return []

    result = []
    seen = set()
    for monitor_spec, modes, mprops in monitors:
        if monitor_spec[0] != connector:
            continue
        for mode in modes:
            key = (mode[1], mode[2], round(mode[3], 2))
            if key in seen:
                continue
            seen.add(key)
            result.append(
                {"width": mode[1], "height": mode[2], "refresh_rate": mode[3]}
            )
    return result


def set_resolution(width, height, refresh_rate=None, persistent=True):
    """Set the primary monitor to width x height (optionally a refresh rate).

    Other monitors keep their current mode. Returns False if the requested mode
    is unavailable or the call fails.
    """
    if not isinstance(width, int) or not isinstance(height, int):
        return False
    if refresh_rate is not None and not isinstance(refresh_rate, (int, float)):
        return False

    try:
        serial, monitors, logical_monitors, props = _get_current_state()

        new_logical_monitors = []
        for x, y, scale, transform, primary, lm_monitors, lprops in logical_monitors:
            assignments = []
            for monitor_spec in lm_monitors:
                connector = monitor_spec[0]
                if primary:
                    mode_id = _find_mode_id(
                        monitors, connector, width, height, refresh_rate
                    )
                else:
                    mode_id = _current_mode_id(monitors, connector)
                if mode_id is None:
                    return False
                assignments.append((connector, mode_id, {}))
            new_logical_monitors.append(
                (
                    int(x),
                    int(y),
                    float(scale),
                    int(transform),
                    bool(primary),
                    assignments,
                )
            )

        method = 2 if persistent else 1
        proxy = _get_display_config_proxy()
        proxy.call_sync(
            "ApplyMonitorsConfig",
            GLib.Variant(
                "(uua(iiduba(ssa{sv}))a{sv})",
                (serial, method, new_logical_monitors, {}),
            ),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
    except GLib.Error:
        return False
