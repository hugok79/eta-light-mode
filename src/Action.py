#!/usr/bin/python3

# Privileged helper for the "Apply to all users" feature.
# Runs as root via pkexec (see data/tr.org.eta.light-mode.policy).
# It writes the shared settings file and installs/removes the system-wide
# autostart entry so every user gets the configuration applied at login.
#
# Verbs (argv[1]):
#   enable  - read settings JSON from stdin, write SETTINGS_FILE, install autostart
#   disable - remove SETTINGS_FILE and the autostart entry
#
# Per project policy the autostart entry is a static, packaged file that we
# copy into place - it is never generated here.

import json
import os
import shutil
import sys

SETTINGS_FILE = "/etc/eta-light-mode/settings.json"
AUTOSTART_SRC = (
    "/usr/share/eta/eta-light-mode/data/tr.org.eta.light-mode-autostart.desktop"
)
AUTOSTART_DST = "/etc/xdg/autostart/tr.org.eta.light-mode-autostart.desktop"


def enable():
    # Validate the payload before touching the global file so a malformed
    # stdin can't corrupt the shared config.
    raw = sys.stdin.read()
    data = json.loads(raw)

    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f)

    shutil.copyfile(AUTOSTART_SRC, AUTOSTART_DST)


def disable():
    for path in (SETTINGS_FILE, AUTOSTART_DST):
        if os.path.exists(path):
            os.remove(path)


def main():
    if len(sys.argv) < 2:
        print("usage: Action.py {enable|disable}", file=sys.stderr)
        return 2

    cmd = sys.argv[1]
    if cmd == "enable":
        enable()
    elif cmd == "disable":
        disable()
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
