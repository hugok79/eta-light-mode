project('eta-light-mode', license: 'GPL-3.0')

# Dependencies
gnome = import('gnome')
gnome.post_install(
    glib_compile_schemas: true,
    gtk_update_icon_cache: true,
    update_desktop_database: true,
)

# Set Install Paths
prefix = get_option('prefix')
share = join_paths(prefix, 'share')

binary_dir = join_paths(prefix, 'bin')
source_dir = join_paths(share, 'eta', meson.project_name()) # /usr/share/eta/eta-light-mode

icon_dir = join_paths(share, 'icons', 'hicolor', 'scalable', 'apps')
desktop_file_dir = join_paths(share, 'applications')
xsession_dir = join_paths(get_option('sysconfdir'), 'X11', 'Xsession.d') # /etc/X11/Xsession.d

# Data
# subdir('data')

# Translations
subdir('po')

# Install
## Desktop File
install_data(
    ['export/tr.org.eta.light-mode.desktop'],
    install_dir: desktop_file_dir,
)
## Xsession.d snippet (registers the 1600x900 modes before the desktop starts)
install_data(
    ['xsession/45custom_xrandr-settings'],
    install_dir: xsession_dir,
)
## Icon
install_data(['export/eta-light-mode.svg'], install_dir: icon_dir)
## Sources
install_subdir('src', install_dir: source_dir)
install_subdir('ui', install_dir: source_dir)
install_subdir(
    'data/icons',
    install_dir: '/usr/share/icons/hicolor/scalable/status',
    strip_directory: true,
)

## Binary
install_data(['eta-light-mode'], install_dir: binary_dir)
