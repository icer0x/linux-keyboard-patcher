# Copyright (C) 2026 Blek
# SPDX-License-Identifier: GPL-3.0-only
Name:           linux-keyboard-patcher
Version:        1.0
Release:        5%{?dist}
Summary:        Fixing unusable keyboard after GRUB
License:        GPL-3.0-only
URL:            https://www.farhanperdana.com
Source0:        %{name}-%{version}-%{_target_cpu}.tar.gz
Requires:       python3, zenity, polkit, grub2-tools

%global debug_package %{nil}
%global _binary_payload w9.gzdio

%description
GUI and terminal tool that temporarily adds four keyboard-related GRUB
entries and lets the user make the working entry's kernel parameters permanent.

%prep
%setup -q -n %{name}-%{version}-%{_target_cpu}

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}
cp -a usr %{buildroot}/

%post
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || :
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -f -t /usr/share/icons/hicolor || :
fi

%postun
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -f -t /usr/share/icons/hicolor || :
fi

%preun
if [ "$1" -eq 0 ]; then
    helper=/usr/lib/linux-keyboard-patcher/root-helper.py
    if [ -x "$helper" ] && [ -r /var/lib/linux-keyboard-patcher/state.json ]; then
        phase=$(python3 -c 'import json; print(json.load(open("/var/lib/linux-keyboard-patcher/state.json")).get("phase", ""))' 2>/dev/null || :)
        if [ "$phase" = testing ]; then "$helper" cancel || :; fi
    fi
fi

%files
%license LICENSE
/usr/bin/linux-keyboard-patcher
/usr/lib/linux-keyboard-patcher/root-helper.py
/usr/share/applications/com.farhanperdana.linuxkeyboardpatcher.desktop
/usr/share/icons/hicolor/scalable/apps/com.farhanperdana.linuxkeyboardpatcher.svg
/usr/share/polkit-1/actions/com.farhanperdana.linux-keyboard-patcher.policy

%changelog
* Thu Nov 26 2026 Blek - 1.0-5
- License the application under GPL version 3 and include license notices.

* Thu Nov 26 2026 Blek - 1.0-4
- Add i386/i686 launcher and architecture-aware package build.

* Wed Nov 25 2026 Blek - 1.0-3
- Add terminal menus and application desktop identity with green keyboard icon.

* Wed Nov 25 2026 Blek - 1.0-2
- Clarify reboot instructions and add clickable website link.
