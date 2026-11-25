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
    echo "Install with administrator access: sudo $0" >&2
    exit 1
fi

[ -d "$root/usr" ] || { echo "The archive is missing its usr/ tree." >&2; exit 1; }
cp -a "$root/usr/." /usr/
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -f -t /usr/share/icons/hicolor || true
fi
echo "Installed LINUX KEYBOARD PATCHER V 1.0. Launch it from the Applications menu."
