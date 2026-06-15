#!/bin/bash
set -euo pipefail

METADATA_FILE="$HOME/.config/nemo/desktop-metadata"
[ -f "$METADATA_FILE" ] || exit 0

set_key() {
    local key="$1"
    local value="$2"
    if grep -q "^$key=" "$METADATA_FILE"; then
        sed -i "s/^$key=.*/$key=$value/" "$METADATA_FILE"
    fi
}

# Nemo'yu D-Bus üzerinden nazikçe kapatan fonksiyon
quit_nemo_cleanly() {
    # 1. Yöntem: Nemo'nun kendi D-Bus tetikleyicisini kullanmak
    nemo-desktop --quit 2>/dev/null || true
    
    # Alternatif (Saf D-Bus komutu kullanmak istersen üstteki satır yerine bunu yazabilirsin):
    # dbus-send --type=method_call --session --dest=org.Nemo /org/Nemo org.Nemo.Quit 2>/dev/null || true

    # Sürecin kendi kendine kapanmasını bekle (Zombi süreç bırakmaz)
    for i in {1..20}; do
        pgrep -x nemo-desktop >/dev/null || break
        sleep 0.1
    done
}

start_nemo_cleanly() {
    # nohup yerine doğrudan arka plana atıp terminalden bağımsızlaştırıyoruz (disown)
    nemo-desktop >/dev/null 2>&1 &
    disown
}

### --- İŞLEM AKIŞI ---

# 1. AUTO-LAYOUT TRUE
set_key "nemo-icon-view-auto-layout" "true"

# Tüm sistemdeki klasör özel zoom ayarlarını temizler
find ~/.local/share/gvfs-metadata/ -type f -exec rm {} +

# D-Bus ile nazikçe kapatıp başlat
quit_nemo_cleanly
start_nemo_cleanly

# Simgelerin ızgaraya oturması için bekle
sleep 0.8

# 2. NEMO'YU KAPAT (Simgeler hizalanmış durumdayken)
quit_nemo_cleanly

# 3. AUTO-LAYOUT FALSE (Nemo kapalıyken özgür bırak)
set_key "nemo-icon-view-auto-layout" "false"

# 4. TEKRAR BAŞLAT
start_nemo_cleanly