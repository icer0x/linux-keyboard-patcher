#!/bin/sh
# Copyright (C) 2026 Blek
# SPDX-License-Identifier: GPL-3.0-only
set -eu
umask 022

PROJECT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT=${OUTPUT_DIR:-"$PROJECT/../../outputs"}
VERSION=1.0
DEB_RELEASE=8
PKG=linux-keyboard-patcher
TARGET_ARCH=${1:-x86_64}

case "$TARGET_ARCH" in
    x86_64)
        DEB_ARCH=amd64
        TARBALL_ARCH=x86_64
        RPM_ARCH=x86_64
        ;;
    i386)
        DEB_ARCH=i386
        TARBALL_ARCH=i386
        RPM_ARCH=i686
        ;;
    *)
        echo "Usage: $0 [x86_64|i386]" >&2
        exit 2
        ;;
esac

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT HUP INT TERM

mkdir -p "$OUT"
ROOT="$STAGE/root"
mkdir -p \
    "$ROOT/usr/bin" \
    "$ROOT/usr/lib/linux-keyboard-patcher" \
    "$ROOT/usr/share/applications" \
    "$ROOT/usr/share/icons/hicolor/scalable/apps" \
    "$ROOT/usr/share/polkit-1/actions"

"$PROJECT/src/build-binary.sh" --arch "$TARGET_ARCH" \
    "$ROOT/usr/bin/linux-keyboard-patcher"
install -m 755 "$PROJECT/src/root-helper.py" \
    "$ROOT/usr/lib/linux-keyboard-patcher/root-helper.py"
install -m 644 "$PROJECT/share/com.farhanperdana.linuxkeyboardpatcher.desktop" \
    "$ROOT/usr/share/applications/com.farhanperdana.linuxkeyboardpatcher.desktop"
install -m 644 \
    "$PROJECT/share/icons/hicolor/scalable/apps/com.farhanperdana.linuxkeyboardpatcher.svg" \
    "$ROOT/usr/share/icons/hicolor/scalable/apps/com.farhanperdana.linuxkeyboardpatcher.svg"
install -m 644 "$PROJECT/share/com.farhanperdana.linux-keyboard-patcher.policy" \
    "$ROOT/usr/share/polkit-1/actions/com.farhanperdana.linux-keyboard-patcher.policy"

# Debian package.
DEB="$STAGE/deb"
mkdir -p "$DEB/DEBIAN"
cp -a "$ROOT/usr" "$DEB/usr"
mkdir -p "$DEB/usr/share/doc/$PKG"
install -m 644 "$PROJECT/LICENSE" "$DEB/usr/share/doc/$PKG/copyright"
sed "s/^Architecture: .*/Architecture: $DEB_ARCH/" \
    "$PROJECT/packaging/debian/control" > "$DEB/DEBIAN/control"
install -m 755 "$PROJECT/packaging/debian/postinst" "$DEB/DEBIAN/postinst"
install -m 755 "$PROJECT/packaging/debian/prerm" "$DEB/DEBIAN/prerm"
dpkg-deb --build --root-owner-group "$DEB" \
    "$OUT/${PKG}_${VERSION}-${DEB_RELEASE}_${DEB_ARCH}.deb"

# Portable tarball.
TGZ="$STAGE/tgz"
mkdir -p "$TGZ"
cp -a "$ROOT/usr" "$TGZ/usr"
install -m 755 "$PROJECT/packaging/tgz/install.sh" "$TGZ/install.sh"
install -m 755 "$PROJECT/packaging/tgz/uninstall.sh" "$TGZ/uninstall.sh"
install -m 644 "$PROJECT/LICENSE" "$TGZ/LICENSE"
tar -C "$TGZ" -czf "$OUT/${PKG}-${VERSION}-${TARBALL_ARCH}.tgz" .

# RPM spec and architecture-specific source archive.
install -m 644 "$PROJECT/packaging/rpm/linux-keyboard-patcher.spec" \
    "$OUT/${PKG}.spec"
RPM_SOURCE="$STAGE/${PKG}-${VERSION}-${RPM_ARCH}"
mkdir -p "$RPM_SOURCE"
cp -a "$ROOT/usr" "$RPM_SOURCE/usr"
install -m 644 "$PROJECT/LICENSE" "$RPM_SOURCE/LICENSE"
tar -C "$STAGE" -czf "$OUT/${PKG}-${VERSION}-${RPM_ARCH}.tar.gz" \
    "${PKG}-${VERSION}-${RPM_ARCH}"
tar -C "$PROJECT/.." \
    --exclude="$(basename "$PROJECT")/build" \
    --exclude="$(basename "$PROJECT")/dist" \
    --exclude="$(basename "$PROJECT")/releases" \
    --exclude="$(basename "$PROJECT")/.git" \
    -czf "$OUT/${PKG}-source-${VERSION}.tar.gz" "$(basename "$PROJECT")"

if command -v rpmbuild >/dev/null 2>&1; then
    RPMROOT="$STAGE/rpmbuild"
    mkdir -p "$RPMROOT/BUILD" "$RPMROOT/BUILDROOT" "$RPMROOT/RPMS" \
        "$RPMROOT/SOURCES" "$RPMROOT/SPECS" "$RPMROOT/SRPMS" \
        "$RPMROOT/db" "$RPMROOT/tmp"
    cp "$OUT/${PKG}-${VERSION}-${RPM_ARCH}.tar.gz" "$RPMROOT/SOURCES/"
    cp "$PROJECT/packaging/rpm/linux-keyboard-patcher.spec" "$RPMROOT/SPECS/"
    rpmbuild -bb --target "$RPM_ARCH" \
        --define "_topdir $RPMROOT" \
        --define "_dbpath $RPMROOT/db" \
        --define "_tmppath $RPMROOT/tmp" \
        --define '__debug_install_post %{nil}' \
        "$RPMROOT/SPECS/linux-keyboard-patcher.spec"
    find "$RPMROOT/RPMS" -type f -name '*.rpm' -exec cp '{}' "$OUT/" \;
else
    echo "rpmbuild is unavailable; the RPM spec and source archive were created."
fi

echo "Created: $OUT/${PKG}_${VERSION}-${DEB_RELEASE}_${DEB_ARCH}.deb"
echo "Created: $OUT/${PKG}-${VERSION}-${TARBALL_ARCH}.tgz"
echo "Created: $OUT/${PKG}-${VERSION}-${RPM_ARCH}.tar.gz and $OUT/${PKG}.spec"
