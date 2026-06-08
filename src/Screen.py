from gi.repository import Gio, GLib

# The two toggles are independent: one switches the resolution, the other the
# refresh rate. They are combined into a single monitor mode when applied.
RESOLUTION_LOW = (1600, 900)
RESOLUTION_NORMAL = (1920, 1080)
REFRESH_RATE_LOW = 50.0
REFRESH_RATE_NORMAL = 60.0

# Refresh rates are reported with jitter (e.g. 59.94 instead of 60.0), so we
# match against the midpoint instead of comparing for equality.
_REFRESH_MIDPOINT = (REFRESH_RATE_LOW + REFRESH_RATE_NORMAL) / 2


# == Monitor Resolution & Refresh Rate Change (Muffin DisplayConfig DBus) ==
# - /org/cinnamon/Muffin/DisplayConfig  org.cinnamon.Muffin.DisplayConfig
# - GetCurrentState () -> (serial, monitors, logical_monitors, properties)
# - ApplyMonitorsConfig (serial, method, logical_monitors, properties)
#     method: 0 = verify, 1 = temporary (until reboot), 2 = persistent (saved)
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
    # Returns (serial, monitors, logical_monitors, properties) as native values.
    proxy = _get_display_config_proxy()
    result = proxy.call_sync("GetCurrentState", None, Gio.DBusCallFlags.NONE, -1, None)
    return result.unpack()


def _get_primary_connector(logical_monitors):
    for x, y, scale, transform, primary, monitors, props in logical_monitors:
        if primary and monitors:
            return monitors[0][0]  # monitor spec -> connector
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
        return max(candidates, key=lambda candidate: candidate[1])[0]
    # Closest matching refresh rate (GetCurrentState reports e.g. 59.95 vs 60.0).
    return min(candidates, key=lambda candidate: abs(candidate[1] - refresh_rate))[0]


def _get_current_mode():
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


def get_resolution():
    """Current (width, height) of the primary monitor, or None."""
    current = _get_current_mode()
    return (current[0], current[1]) if current else None


def get_refresh_rate():
    """Current refresh rate (Hz) of the primary monitor, or None."""
    current = _get_current_mode()
    return current[2] if current else None


def set_mode(width, height, refresh_rate) -> bool:
    """Set the primary monitor to width x height at (about) refresh_rate.

    Other monitors keep their current mode. Returns False if the requested mode
    isn't advertised (the 1600x900 modes are registered at session start by
    /etc/X11/Xsession.d/45custom_xrandr-settings) or the DBus call fails.
    """
    if not isinstance(width, int) or not isinstance(height, int):
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
                (int(x), int(y), float(scale), int(transform), bool(primary), assignments)
            )

        proxy = _get_display_config_proxy()
        proxy.call_sync(
            "ApplyMonitorsConfig",
            GLib.Variant(
                "(uua(iiduba(ssa{sv}))a{sv})",
                (serial, 2, new_logical_monitors, {}),  # method 2 = persistent
            ),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
    except GLib.Error:
        return False
    return True


# == High-level toggles used by the UI ==
def set_resolution(low: bool) -> bool:
    """Switch the resolution, keeping the current refresh rate."""
    width, height = RESOLUTION_LOW if low else RESOLUTION_NORMAL
    refresh_rate = get_refresh_rate()
    if refresh_rate is None:
        refresh_rate = REFRESH_RATE_LOW if low else REFRESH_RATE_NORMAL
    return set_mode(width, height, refresh_rate)


def set_refresh_rate(low: bool) -> bool:
    """Switch the refresh rate, keeping the current resolution."""
    refresh_rate = REFRESH_RATE_LOW if low else REFRESH_RATE_NORMAL
    resolution = get_resolution() or RESOLUTION_NORMAL
    return set_mode(resolution[0], resolution[1], refresh_rate)


def is_low_resolution() -> bool:
    resolution = get_resolution()
    if resolution is None:
        return False
    return resolution[0] <= RESOLUTION_LOW[0]


def is_low_refresh_rate() -> bool:
    refresh_rate = get_refresh_rate()
    if refresh_rate is None:
        return False
    return refresh_rate < _REFRESH_MIDPOINT


