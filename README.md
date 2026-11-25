# LINUX KEYBOARD PATCHER V 1.0

**Fixing unusable keyboard after GRUB**  
by Blek [www.farhanperdana.com](https://www.farhanperdana.com)

Linux Keyboard Patcher adds four temporary GRUB entries for diagnosing a
built-in keyboard that stops responding after Linux starts. After testing the
entries, the user can keep the working entry's kernel parameters as the
permanent default. The native launcher can target x86_64 or 32-bit x86 (i386).

Read the [English user manual](MANUAL.md) for installation, GUI and terminal
instructions, troubleshooting, and details about the GRUB changes.

## Project layout

- `src/app.py` — Zenity GUI and interactive terminal interface.
- `src/root-helper.py` — administrator-only GRUB operations and rollback.
- `src/linux-keyboard-patcher.S` — native x86_64 launcher for the embedded app.
- `src/linux-keyboard-patcher-i386.S` — native 32-bit x86 launcher.
- `packaging/` — Debian, RPM, and portable tarball packaging files.
- `share/` — desktop entry, application icon, and Polkit action.

## Build

On an x86_64 Linux build host, run the package builder for the target
architecture:

```sh
packaging/build-packages.sh x86_64
packaging/build-packages.sh i386
```

The builder needs Python 3, GNU `as` and `ld`, `dpkg-deb`, and `tar`. It creates
an architecture-matched `.deb` and `.tgz`, plus an RPM spec and source archive,
in `outputs/` two levels above the project directory. If `rpmbuild` is
installed, it also creates an `.rpm`. The i386 target maps to Debian `i386` and
RPM `i686`. Set `OUTPUT_DIR=/path/to/output` to choose another output directory.

To build only the 32-bit launcher inside this project, run:

```sh
mkdir -p build
src/build-binary.sh --arch i386 build/linux-keyboard-patcher-i386
```

See [MANUAL.md](MANUAL.md) for runtime requirements and end-user instructions.

## License

Copyright (C) 2026 Blek.

Linux Keyboard Patcher is licensed under **GNU GPL version 3 only**
([GPL-3.0-only](LICENSE)). The source files carry SPDX license identifiers.
