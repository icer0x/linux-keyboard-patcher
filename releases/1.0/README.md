# Linux Keyboard Patcher 1.0 — Release Files

This directory contains the build outputs for both supported x86 architectures.

## 64-bit x86

- Standalone binary: `binaries/linux-keyboard-patcher`
- Debian/Ubuntu package: `deb/linux-keyboard-patcher_1.0-8_amd64.deb`
- RPM package: `rpm/linux-keyboard-patcher-1.0-5.x86_64.rpm`
- Portable archive: `tarball/linux-keyboard-patcher-1.0-x86_64.tgz`

## 32-bit x86

- Standalone binary: `binaries/linux-keyboard-patcher-i386`
- Debian/Ubuntu package: `deb/linux-keyboard-patcher_1.0-8_i386.deb`
- RPM package: `rpm/linux-keyboard-patcher-1.0-5.i686.rpm`
- Portable archive: `tarball/linux-keyboard-patcher-1.0-i386.tgz`

## Source code and RPM build inputs

- Architecture-independent source archive:
  `source/linux-keyboard-patcher-source-1.0.tar.gz`

All release artifacts are distributed under GNU GPL version 3 only
([GPL-3.0-only](../../LICENSE)).
- RPM specification: `rpm/linux-keyboard-patcher.spec`
- RPM payload source archives: `rpm/sources/`

The source includes the clickable website URL `https://www.farhanperdana.com`
in the application byline. The source archive contains both launcher assembly
files, the Python application and GRUB helper, packaging files, license, and
manual.

`SHA256SUMS` contains checksums for the files in this release directory.
