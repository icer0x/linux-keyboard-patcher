#!/bin/sh
# Copyright (C) 2026 Blek
# SPDX-License-Identifier: GPL-3.0-only
set -eu

src_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
target_arch=x86_64

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    echo "Usage: $0 [--arch x86_64|i386] [output-path]"
    exit 0
fi

if [ "${1:-}" = "--arch" ]; then
    [ "$#" -ge 2 ] || {
        echo "Missing architecture after --arch." >&2
        exit 2
    }
    target_arch=$2
    shift 2
fi
[ "$#" -le 1 ] || {
    echo "Usage: $0 [--arch x86_64|i386] [output-path]" >&2
    exit 2
}

case "$target_arch" in
    x86_64)
        assembler_mode=--64
        linker_mode=elf_x86_64
        assembly_source=linux-keyboard-patcher.S
        binary_name=linux-keyboard-patcher
        ;;
    i386)
        assembler_mode=--32
        linker_mode=elf_i386
        assembly_source=linux-keyboard-patcher-i386.S
        binary_name=linux-keyboard-patcher-i386
        ;;
    *)
        echo "Unsupported architecture: $target_arch (choose x86_64 or i386)." >&2
        exit 2
        ;;
esac

default_output="$src_dir/../../../outputs/$binary_name"
output=${1:-$default_output}
output_dir=$(dirname -- "$output")
mkdir -p "$output_dir"

command -v python3 >/dev/null 2>&1 || { echo "python3 is required to embed the application." >&2; exit 1; }
command -v as >/dev/null 2>&1 || { echo "GNU assembler (as) is required." >&2; exit 1; }
command -v ld >/dev/null 2>&1 || { echo "GNU linker (ld) is required." >&2; exit 1; }

embedded="$src_dir/app-embedded.py"
object=$(mktemp)
binary_tmp=$(mktemp "$output_dir/.linux-keyboard-patcher.XXXXXX")
trap 'rm -f "$object" "$binary_tmp" "$embedded"' EXIT HUP INT TERM

python3 - "$src_dir/app.py" "$src_dir/root-helper.py" "$embedded" <<'PY'
from pathlib import Path
import sys

app_path, helper_path, destination = map(Path, sys.argv[1:])
app = app_path.read_text(encoding="utf-8")
helper = helper_path.read_text(encoding="utf-8")
compile(helper, str(helper_path), "exec")
placeholder = "ROOT_HELPER_SOURCE = __ROOT_HELPER_SOURCE__"
if app.count(placeholder) != 1:
    raise SystemExit("Could not find the root-helper embedding point in app.py")
app = app.replace(placeholder, "ROOT_HELPER_SOURCE = " + repr(helper))
compile(app, "app-embedded.py", "exec")
destination.write_text(app, encoding="utf-8")
PY

(
    cd "$src_dir"
    as "$assembler_mode" -o "$object" "$assembly_source"
)
ld -m "$linker_mode" -static -e _start -o "$binary_tmp" "$object"
chmod 755 "$binary_tmp"
mv -f "$binary_tmp" "$output"
echo "Built standalone $target_arch binary: $output"
