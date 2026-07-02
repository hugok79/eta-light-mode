#!/usr/bin/python3

import json
import os
import subprocess

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gio, GLib, GObject, Gtk, Gdk  # noqa

from locale import gettext as _

import Settings

CWD = os.path.dirname(os.path.abspath(__file__))


ACTION = f"{CWD}/Action.py"
AUTOSTART_DST = "/etc/xdg/autostart/tr.org.eta.light-mode-autostart.desktop"
# Coalesce bursts of setting changes (e.g. the master switch) into one write.
RESAVE_DEBOUNCE_MS = 400


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

        # Variables
        self.define_variables()

        # UI Components
        self.define_components()

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

        self.ui_expander_details = UI("ui_expander_details")

        self.ui_box_switches = UI("ui_box_switches")

        # "Apply to all users" checkbox. Seed it from the live system state
        # (autostart entry present == active) with the handler guarded so
        # seeding doesn't trigger a pkexec call.
        self.ui_check_apply_all = UI("ui_check_apply_all")
        self._prevent_apply_all_toggle = True
        self.ui_check_apply_all.set_active(os.path.exists(AUTOSTART_DST))
        self._prevent_apply_all_toggle = False
        self.ui_check_apply_all.connect("toggled", self.on_ui_check_apply_all_toggled)

        # Dialog:
        self.dialog_about = UI("dialog_about")

    def define_variables(self):
        # Boolean model backing every settings switch (and the global toggle).
        self.preferences = Settings.LightModeSettings()

        # While "Apply to all users" is active, re-push the config to the shared
        # location on every change (debounced to coalesce bursts).
        self._resave_timer = 0
        self._prevent_apply_all_toggle = False

        # Serialize the privileged pushes: only one pkexec/helper runs at a time.
        # A change arriving mid-push sets _push_dirty so exactly one follow-up
        # push fires when the current one finishes (never stacks auth dialogs).
        self._push_inflight = False
        self._push_dirty = False
        self._push_pending = True

        self.preferences.connect("notify", self.on_preferences_changed)

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

        # If one disabled, show details:
        if not self.is_all_settings_active() and self.is_light_mode_active():
            self.ui_expander_details.set_expanded(True)

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

        try:
            # Refresh desktop
            subprocess.Popen([f"{CWD}/refresh-desktop.sh"])
        except Exception as e:
            print("{}".format(e))

    def is_light_mode_active(self):
        # Even if one setting is active, show Enabled
        for s in Settings.SETTINGS:
            if self.preferences.get_property(s["name"]):
                return True

        return False

    def is_all_settings_active(self):
        for s in Settings.SETTINGS:
            if not self.preferences.get_property(s["name"]):
                return False

        return True

    # == CALLBACKS ==
    def on_ui_switch_state_set(self, switch, state):
        self.toggle_light_mode(state)
        print(state)

    # About Window
    def on_btn_about_clicked(self, btn):
        self.dialog_about.run()
        self.dialog_about.hide()

    def on_ui_check_apply_all_toggled(self, btn):
        if self._prevent_apply_all_toggle:
            return

        # The checkbox reflects intent; the real state is reconciled in the
        # push callback (which reverts the box if pkexec fails/is cancelled).
        self._apply_all_users(btn.get_active())

    def on_preferences_changed(self, *_args):
        # Only mirror changes while the checkbox is active.
        if self._prevent_apply_all_toggle or not self.ui_check_apply_all.get_active():
            return

        if self._resave_timer:
            GLib.source_remove(self._resave_timer)
        self._resave_timer = GLib.timeout_add(RESAVE_DEBOUNCE_MS, self._resave_now)

    def _resave_now(self):
        self._resave_timer = 0
        self._apply_all_users(True)
        return False  # one-shot

    def _apply_all_users(self, enable):
        """Launch the privileged helper asynchronously so the UI never freezes
        behind the polkit dialog. Only one helper runs at a time; a request that
        arrives mid-push is coalesced into a single follow-up push."""
        if self._push_inflight:
            # Remember the latest desired state; fire it once the current one ends.
            self._push_pending = enable
            self._push_dirty = True
            return

        argv = ["pkexec", ACTION, "enable" if enable else "disable"]
        flags = Gio.SubprocessFlags.STDIN_PIPE if enable else Gio.SubprocessFlags.NONE
        try:
            proc = Gio.Subprocess.new(argv, flags)
        except GLib.Error as e:
            print("{}".format(e))
            self._on_push_failed(enable)
            return

        self._push_inflight = True
        payload = json.dumps(self.preferences._values) if enable else None
        proc.communicate_utf8_async(payload, None, self._on_push_done, enable)

    def _on_push_done(self, proc, result, enable):
        ok = True
        try:
            proc.communicate_utf8_finish(result)
            ok = proc.get_exit_status() == 0
        except GLib.Error as e:
            print("{}".format(e))
            ok = False

        self._push_inflight = False

        if not ok:
            # /etc no longer matches the UI: revert the checkbox and warn, so the
            # two never silently diverge. Drop any queued push.
            self._push_dirty = False
            self._on_push_failed(enable)
            return

        # Success: if changes arrived while pushing, fire exactly one follow-up.
        if self._push_dirty:
            self._push_dirty = False
            self._apply_all_users(self._push_pending)

    def _on_push_failed(self, enable):
        # Revert "Apply to all users" to the opposite of the attempted action:
        # a failed enable/re-save means it isn't really applied; a failed disable
        # means it's still applied.
        self._prevent_apply_all_toggle = True
        self.ui_check_apply_all.set_active(not enable)
        self._prevent_apply_all_toggle = False

        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK,
            text=_("Couldn't apply settings to all users"),
        )
        dialog.format_secondary_text(
            _("Authentication failed or was cancelled. The shared configuration "
              "was not changed.")
        )
        dialog.run()
        dialog.destroy()
