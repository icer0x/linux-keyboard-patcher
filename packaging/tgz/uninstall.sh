#!/bin/sh
# Copyright (C) 2026 Blek
# SPDX-License-Identifier: GPL-3.0-only
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
script_path="$root/$(basename -- "$0")"
if [ "$(id -u)" -ne 0 ]; then
    if command -v pkexec >/dev/null 2>&1; then
        exec pkexec /bin/sh "$script_path" "$@"
    fi
    echo "Uninstall with administrator access: sudo $0" >&2
    exit 1
fi

helper=/usr/lib/linux-keyboard-patcher/root-helper.py
if [ -x "$helper" ] && [ -r /var/lib/linux-keyboard-patcher/state.json ]; then
    phase=$(python3 -c 'import json; print(json.load(open("/var/lib/linux-keyboard-patcher/state.json")).get("phase", ""))' 2>/dev/null || true)
    if [ "$phase" = testing ]; then
        "$helper" cancel || true
    fi
fi
rm -f /usr/bin/linux-keyboard-patcher
# Remove the separate launcher installed by earlier releases.
rm -f /usr/lib/linux-keyboard-patcher/launcher.sh
rm -f /usr/lib/linux-keyboard-patcher/root-helper.py
rm -f /usr/share/applications/com.farhanperdana.linuxkeyboardpatcher.desktop
rm -f /usr/share/icons/hicolor/scalable/apps/com.farhanperdana.linuxkeyboardpatcher.svg
rm -f /usr/share/polkit-1/actions/com.farhanperdana.linux-keyboard-patcher.policy
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -f -t /usr/share/icons/hicolor || true
fi
rmdir /usr/lib/linux-keyboard-patcher 2>/dev/null || true
echo "Uninstalled LINUX KEYBOARD PATCHER V 1.0. A completed keyboard patch remains active."
