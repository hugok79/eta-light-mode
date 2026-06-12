import os
import subprocess
import xml.etree.ElementTree as ET

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
#
# We apply with method 1 (TEMPORARY) so Muffin switches silently -- method 2
# (PERSISTENT) always pops the "keep this configuration?" confirmation dialog.
# To still survive a reboot we write the chosen mode into ~/.config/monitors.xml
# ourselves (see _write_monitors_xml); Muffin restores it at startup with no
# dialog, and since /etc/X11/Xsession.d/45custom_xrandr-settings has already
# registered the custom 1600x900 modes there is no fallback flicker.
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


def _find_mode(monitors, connector, width, height, refresh_rate):
    """Return the full mode tuple (id, width, height, refresh, ...) of the best
    width x height match, or None. The caller needs both the id and the actual
    refresh rate (to persist it), hence the whole tuple."""
    candidates = []
    for monitor_spec, modes, props in monitors:
        if monitor_spec[0] != connector:
            continue
        for mode in modes:
            if mode[1] == width and mode[2] == height:
                candidates.append(mode)

    if not candidates:
        return None
    if refresh_rate is None:
        return max(candidates, key=lambda mode: mode[3])
    # Closest matching refresh rate (GetCurrentState reports e.g. 59.95 vs 60.0).
    return min(candidates, key=lambda mode: abs(mode[3] - refresh_rate))


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


XSessionScriptPath = "/etc/X11/Xsession.d/50-eta-light-mode-resolution"


def _create_1600_900_mode():
    return subprocess.run(["bash", XSessionScriptPath])


def set_mode(width, height, refresh_rate, second_try=False) -> bool:
    """Set the primary monitor to width x height at (about) refresh_rate."""
    if not isinstance(width, int) or not isinstance(height, int):
        return False

    primary_spec = None
    primary_logical = None
    applied_rate = refresh_rate
    try:
        serial, monitors, logical_monitors, props = _get_current_state()

        new_logical_monitors = []
        for x, y, scale, transform, primary, lm_monitors, lprops in logical_monitors:
            assignments = []
            for monitor_spec in lm_monitors:
                connector = monitor_spec[0]
                if primary:
                    mode = _find_mode(monitors, connector, width, height, refresh_rate)
                    if mode is None:
                        print(f"{width}x{height}@{refresh_rate} mode not found!")
                        print(
                            f"Triggering '{XSessionScriptPath}' to add xrandr mode..."
                        )

                        p = _create_1600_900_mode()
                        if p.returncode != 0:
                            print(f"Couldn't run {XSessionScriptPath}!")
                            return False

                        if not second_try:
                            print("Trying again...")
                            set_mode(width, height, refresh_rate, True)

                        return False

                    mode_id = mode[0]
                    applied_rate = mode[3]
                    primary_spec = monitor_spec
                    primary_logical = (int(x), int(y), float(scale))
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

        proxy = _get_display_config_proxy()
        proxy.call_sync(
            "ApplyMonitorsConfig",
            GLib.Variant(
                "(uua(iiduba(ssa{sv}))a{sv})",
                (
                    serial,
                    1,
                    new_logical_monitors,
                    {},
                ),  # method 1 = temporary (no dialog)
            ),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
    except GLib.Error:
        return False

    # The live change succeeded; persist it ourselves (a write failure is
    # non-fatal -- the mode is already applied for this session).
    if primary_spec is not None:
        _write_monitors_xml(primary_spec, primary_logical, width, height, applied_rate)
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


# == Persistence: write Cinnamon's monitors.xml directly ==
# Method 1 doesn't save the config, so we record the chosen mode in the same file
def _monitors_xml_path() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "monitors.xml")


def _fmt_scale(scale) -> str:
    scale = float(scale)
    return str(int(scale)) if scale.is_integer() else repr(scale)


def _set_mode_element(monitor, width, height, rate):
    """Replace <monitor>'s <mode> with width/height/rate (kept after <monitorspec>)."""
    old = monitor.find("mode")
    if old is not None:
        monitor.remove(old)
    mode = ET.SubElement(monitor, "mode")
    ET.SubElement(mode, "width").text = str(width)
    ET.SubElement(mode, "height").text = str(height)
    ET.SubElement(mode, "rate").text = repr(
        float(rate)
    )  # exact double -> matches at load


def _write_monitors_xml(spec, logical, width, height, rate):
    """Persist the primary monitor's mode to ~/.config/monitors.xml so Muffin
    restores it at startup. spec=(connector,vendor,product,serial); logical=(x,y,scale)."""
    connector, vendor, product, serial = spec[0], spec[1], spec[2], spec[3]
    x, y, scale = logical
    path = _monitors_xml_path()
    try:
        if os.path.exists(path):
            tree = ET.parse(path)
            root = tree.getroot()
        else:
            root = ET.Element("monitors", version="2")
            tree = ET.ElementTree(root)

        # Update the configuration whose monitor matches this EDID spec, if any.
        found = False
        for configuration in root.findall("configuration"):
            for monitor in configuration.findall(".//monitor"):
                mspec = monitor.find("monitorspec")
                if mspec is None:
                    continue
                if (
                    mspec.findtext("connector") == connector
                    and mspec.findtext("vendor") == vendor
                    and mspec.findtext("product") == product
                    and mspec.findtext("serial") == serial
                ):
                    _set_mode_element(monitor, width, height, rate)
                    sc = configuration.find(".//logicalmonitor/scale")
                    if sc is not None:
                        sc.text = _fmt_scale(scale)
                    found = True
                    break
            if found:
                break

        if not found:
            configuration = ET.SubElement(root, "configuration")
            logicalmonitor = ET.SubElement(configuration, "logicalmonitor")
            ET.SubElement(logicalmonitor, "x").text = str(int(x))
            ET.SubElement(logicalmonitor, "y").text = str(int(y))
            ET.SubElement(logicalmonitor, "scale").text = _fmt_scale(scale)
            ET.SubElement(logicalmonitor, "primary").text = "yes"
            monitor = ET.SubElement(logicalmonitor, "monitor")
            mspec = ET.SubElement(monitor, "monitorspec")
            ET.SubElement(mspec, "connector").text = connector
            ET.SubElement(mspec, "vendor").text = vendor
            ET.SubElement(mspec, "product").text = product
            ET.SubElement(mspec, "serial").text = serial
            _set_mode_element(monitor, width, height, rate)

        ET.indent(tree, space="  ")
        tree.write(path, encoding="utf-8", xml_declaration=False)
    except (OSError, ET.ParseError):
        pass
