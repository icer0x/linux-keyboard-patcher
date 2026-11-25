#!/usr/bin/python3
"""Privileged GRUB operations for Linux Keyboard Patcher."""
# Copyright (C) 2026 Blek
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path


APP_DIR = Path("/var/lib/linux-keyboard-patcher")
STATE_FILE = APP_DIR / "state.json"
GRUB_DEFAULT = Path("/etc/default/grub")
CUSTOM_GRUB = Path("/etc/grub.d/49_keyboard_tests")
MARKER = "LINUX KEYBOARD PATCHER V 1.0"

BASE_PARAMS = ["i8042.reset", "i8042.nomux=1", "i8042.nopnp=1", "atkbd.reset"]
TESTS = {
    "test1": ("Keyboard test 1 - i8042 reset", BASE_PARAMS),
    "test2": ("Keyboard test 2 - plus ACPI PnP off", BASE_PARAMS + ["pnpacpi=off"]),
    "test3": ("Keyboard test 3 - plus dumbkbd", BASE_PARAMS + ["i8042.dumbkbd=1"]),
    "test4": (
        "Keyboard test 4 - ACPI PnP off and dumbkbd",
        BASE_PARAMS + ["pnpacpi=off", "i8042.dumbkbd=1"],
    ),
}
APP_PARAMS = set(BASE_PARAMS + ["pnpacpi=off", "i8042.dumbkbd=1"])
SAFE_ARG = re.compile(r"^[A-Za-z0-9_./=:+,@%-]+$")
SAFE_GRUB_PATH = re.compile(r"^/[A-Za-z0-9_./@+-]+$")
SAFE_MODULE = re.compile(r"^[A-Za-z0-9_]+$")


class PatchError(Exception):
    pass


def require_root() -> None:
    if os.geteuid() != 0:
        raise PatchError("This operation requires administrator access.")


def atomic_write(path: Path, content: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def read_state() -> dict | None:
    if not STATE_FILE.is_file():
        return None
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PatchError(f"The saved patch state is unreadable: {exc}") from exc
    if data.get("version") != 1 or data.get("phase") not in {"installing", "testing", "complete"}:
        raise PatchError("The saved patch state has an unknown format.")
    return data


def write_state(data: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(APP_DIR, 0o755)
    atomic_write(STATE_FILE, (json.dumps(data, indent=2) + "\n").encode(), 0o644)


def run_output(argv: list[str]) -> str:
    try:
        result = subprocess.run(argv, check=True, text=True, capture_output=True)
    except FileNotFoundError as exc:
        raise PatchError(f"Required system command was not found: {argv[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise PatchError(f"Command failed: {' '.join(argv)}\n{detail[-3000:]}") from exc
    return result.stdout.strip()


def grub_update_command() -> list[str]:
    if shutil.which("update-grub"):
        return ["update-grub"]
    if shutil.which("grub2-mkconfig"):
        for candidate in (
            Path("/boot/grub2/grub.cfg"),
            Path("/boot/grub/grub.cfg"),
        ):
            if candidate.parent.is_dir():
                return ["grub2-mkconfig", "-o", str(candidate)]
    if shutil.which("grub-mkconfig"):
        for candidate in (Path("/boot/grub/grub.cfg"), Path("/boot/grub2/grub.cfg")):
            if candidate.parent.is_dir():
                return ["grub-mkconfig", "-o", str(candidate)]
    raise PatchError("Could not find update-grub or grub2-mkconfig on this system.")


def update_grub() -> None:
    argv = grub_update_command()
    try:
        subprocess.run(argv, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise PatchError(f"GRUB update failed.\n{detail[-4000:]}") from exc


def set_simple_grub_value(text: str, key: str, value: str) -> str:
    lines = text.splitlines(keepends=True)
    pattern = re.compile(r"^\s*" + re.escape(key) + r"\s*=")
    matches = [i for i, line in enumerate(lines) if pattern.match(line)]
    if len(matches) > 1:
        raise PatchError(f"Found multiple {key} assignments in {GRUB_DEFAULT}.")
    if matches:
        i = matches[0]
        newline = "\n" if lines[i].endswith("\n") else ""
        lines[i] = f"{key}={value}{newline}"
    else:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"{key}={value}\n")
    return "".join(lines)


def shell_words(rhs: str) -> tuple[list[str], str]:
    """Parse a simple shell assignment and preserve a trailing comment."""
    quote = None
    escaped = False
    comment_at = len(rhs)
    for i, char in enumerate(rhs):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote != "'":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in "'\"":
            quote = char
        elif char == "#" and (i == 0 or rhs[i - 1].isspace()):
            comment_at = i
            break
    value = rhs[:comment_at].strip()
    comment = rhs[comment_at:].rstrip() if comment_at < len(rhs) else ""
    lexer = shlex.shlex(value, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        words = list(lexer)
    except ValueError as exc:
        raise PatchError(f"Could not parse GRUB_CMDLINE_LINUX_DEFAULT: {exc}") from exc
    if any(any(char in word for char in "$`\n\r") for word in words):
        raise PatchError(
            "GRUB_CMDLINE_LINUX_DEFAULT contains shell expansion; refusing to rewrite it."
        )
    return words, comment


def set_default_kernel_params(original: bytes, params: list[str]) -> bytes:
    text = original.decode("utf-8")
    lines = text.splitlines(keepends=True)
    pattern = re.compile(r"^\s*GRUB_CMDLINE_LINUX_DEFAULT\s*=")
    matches = [i for i, line in enumerate(lines) if pattern.match(line)]
    if len(matches) > 1:
        raise PatchError(
            f"Found multiple GRUB_CMDLINE_LINUX_DEFAULT assignments in {GRUB_DEFAULT}."
        )
    if matches:
        i = matches[0]
        line = lines[i]
        lhs, rhs = line.split("=", 1)
        newline = "\n" if line.endswith("\n") else ""
        words, comment = shell_words(rhs.rstrip("\r\n"))
        for param in params:
            if param not in words:
                words.append(param)
        new_rhs = shlex.quote(" ".join(words))
        if comment:
            new_rhs += " " + comment
        lines[i] = lhs + "=" + new_rhs + newline
    else:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append("GRUB_CMDLINE_LINUX_DEFAULT=" + shlex.quote(" ".join(params)) + "\n")
    return "".join(lines).encode("utf-8")


def grub_context() -> dict:
    release = os.uname().release
    kernel_candidates = (Path("/boot") / f"vmlinuz-{release}", Path("/boot/vmlinuz"))
    initrd_candidates = (
        Path("/boot") / f"initrd.img-{release}",
        Path("/boot") / f"initramfs-{release}.img",
        Path("/boot/initramfs.img"),
    )
    kernel = next((item for item in kernel_candidates if item.is_file()), kernel_candidates[0])
    initrd = next((item for item in initrd_candidates if item.is_file()), initrd_candidates[0])
    if not kernel.is_file() or not initrd.is_file():
        raise PatchError(f"Could not find the current kernel and initrd under /boot: {kernel}")
    kernel_path = run_output(["grub-mkrelpath", str(kernel)])
    initrd_path = run_output(["grub-mkrelpath", str(initrd)])
    boot_uuid = run_output(["grub-probe", "--target=fs_uuid", str(kernel)])
    for path in (kernel_path, initrd_path):
        if not SAFE_GRUB_PATH.fullmatch(path):
            raise PatchError(f"Unsafe path returned by grub-mkrelpath: {path}")
    if not re.fullmatch(r"[A-Za-z0-9-]+", boot_uuid):
        raise PatchError(f"Unsafe filesystem UUID returned by grub-probe: {boot_uuid}")

    modules: list[str] = ["search_fs_uuid"]
    for target in ("partmap_module", "fs_module", "abstraction_module"):
        try:
            output = run_output(["grub-probe", f"--target={target}", str(kernel)])
        except PatchError:
            output = ""
        for module in output.split():
            if not SAFE_MODULE.fullmatch(module):
                raise PatchError(f"Unsafe GRUB module returned by grub-probe: {module}")
            if module not in modules:
                modules.append(module)

    args = shlex.split(Path("/proc/cmdline").read_text())
    args = [arg for arg in args if not arg.startswith("BOOT_IMAGE=")]
    args = [arg for arg in args if arg not in APP_PARAMS]
    if not any(arg.startswith("root=") for arg in args):
        raise PatchError(
            "No root= parameter was found in /proc/cmdline; refusing to create boot entries."
        )
    for arg in args:
        if not SAFE_ARG.fullmatch(arg):
            raise PatchError(f"Unsupported kernel argument in /proc/cmdline: {arg}")
    return {
        "kernel_path": kernel_path,
        "initrd_path": initrd_path,
        "boot_uuid": boot_uuid,
        "modules": modules,
        "kernel_args": args,
    }


def render_custom_grub(context: dict) -> bytes:
    lines = [
        "#!/bin/sh",
        f"# {MARKER}",
        "cat <<'GRUB_ENTRIES'",
    ]
    for label, params in TESTS.values():
        menu_title = f"LINUX KEYBOARD PATCHER V 1.0 - {label}"
        lines.append(
            f"menuentry '{menu_title}' --class ubuntu --class gnu-linux "
            "--class gnu --class os {"
        )
        for module in context["modules"]:
            lines.append(f"    insmod {module}")
        lines.append(f"    search --no-floppy --fs-uuid --set=root {context['boot_uuid']}")
        argv = context["kernel_args"] + params
        lines.append(f"    linux {context['kernel_path']} {' '.join(argv)}")
        lines.append(f"    initrd {context['initrd_path']}")
        lines.append("}")
    lines.extend(["GRUB_ENTRIES", ""])
    return "\n".join(lines).encode("utf-8")


def backup_file(backup_dir: Path, source: Path, name: str) -> dict:
    if not source.exists():
        return {"exists": False, "backup": None}
    target = backup_dir / name
    shutil.copy2(source, target)
    return {"exists": True, "backup": str(target)}


def legacy_grub_backup() -> Path | None:
    candidates = list(Path("/var/backups").glob("codex-grub-keyboard-*/default-grub"))
    candidates = [item for item in candidates if item.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.stat().st_mtime)


def is_legacy_test_entry_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    required_labels = (
        "Keyboard test 1 - i8042 reset",
        "Keyboard test 2 - plus ACPI PnP off",
        "Keyboard test 3 - plus dumbkbd",
        "Keyboard test 4 - ACPI PnP off and dumbkbd",
    )
    return all(label in text for label in required_labels)


def adopt_legacy_test_entries() -> dict:
    previous = legacy_grub_backup()
    if previous is None:
        raise PatchError(
            "Four keyboard test entries already exist, but their original GRUB "
            "backup was not found. "
            "No files were changed."
        )
    backup_dir = APP_DIR / "backups" / f"adopted-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(backup_dir, 0o700)
    saved_original = backup_dir / "default-grub"
    shutil.copy2(previous, saved_original)
    state = {
        "version": 1,
        "phase": "testing",
        "backup_dir": str(backup_dir),
        "original_default": {"exists": True, "backup": str(saved_original)},
        "original_custom": {"exists": False, "backup": None},
        "started": time.time(),
        "adopted_existing_test_entries": True,
        "kernel_release": os.uname().release,
    }
    write_state(state)
    return state


def restore_originals(state: dict) -> None:
    original = state["original_default"]
    if original["exists"]:
        shutil.copy2(original["backup"], GRUB_DEFAULT)
    else:
        GRUB_DEFAULT.unlink(missing_ok=True)
    custom = state["original_custom"]
    if custom["exists"]:
        shutil.copy2(custom["backup"], CUSTOM_GRUB)
    else:
        CUSTOM_GRUB.unlink(missing_ok=True)


def begin() -> dict:
    require_root()
    current = read_state()
    if current and current["phase"] in {"testing", "complete"}:
        return current
    if current and current["phase"] == "installing":
        restore_originals(current)
        try:
            update_grub()
        finally:
            STATE_FILE.unlink(missing_ok=True)
        current = None

    if not GRUB_DEFAULT.is_file():
        raise PatchError(f"Could not find {GRUB_DEFAULT}.")
    if CUSTOM_GRUB.exists():
        if is_legacy_test_entry_file(CUSTOM_GRUB):
            return adopt_legacy_test_entries()
        raise PatchError(
            f"{CUSTOM_GRUB} already exists and is not owned by this patcher; leaving it unchanged."
        )
    context = grub_context()
    backup_dir = APP_DIR / "backups" / f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(backup_dir, 0o700)
    state = {
        "version": 1,
        "phase": "installing",
        "backup_dir": str(backup_dir),
        "original_default": backup_file(backup_dir, GRUB_DEFAULT, "default-grub"),
        "original_custom": backup_file(backup_dir, CUSTOM_GRUB, "custom-grub"),
        "started": time.time(),
    }
    write_state(state)
    try:
        original = GRUB_DEFAULT.read_bytes()
        text = original.decode("utf-8")
        text = set_simple_grub_value(text, "GRUB_TIMEOUT_STYLE", "menu")
        text = set_simple_grub_value(text, "GRUB_TIMEOUT", "10")
        atomic_write(GRUB_DEFAULT, text.encode("utf-8"), 0o644)
        atomic_write(CUSTOM_GRUB, render_custom_grub(context), 0o755)
        update_grub()
    except Exception:
        restore_originals(state)
        try:
            update_grub()
        except Exception:
            pass
        STATE_FILE.unlink(missing_ok=True)
        raise
    state["phase"] = "testing"
    state["kernel_release"] = os.uname().release
    write_state(state)
    return state


def finalize(test_id: str) -> dict:
    require_root()
    if test_id not in TESTS:
        raise PatchError("Unknown GRUB test entry.")
    state = read_state()
    if not state or state["phase"] != "testing":
        raise PatchError("The four GRUB test entries are not waiting for a selection.")
    _, params = TESTS[test_id]

    testing_default = GRUB_DEFAULT.read_bytes()
    testing_custom = CUSTOM_GRUB.read_bytes() if CUSTOM_GRUB.exists() else None
    if state["original_default"]["exists"]:
        original_bytes = Path(state["original_default"]["backup"]).read_bytes()
    else:
        original_bytes = b""
    try:
        final_default = set_default_kernel_params(original_bytes, params)
        atomic_write(GRUB_DEFAULT, final_default, 0o644)
        CUSTOM_GRUB.unlink(missing_ok=True)
        update_grub()
    except Exception:
        atomic_write(GRUB_DEFAULT, testing_default, 0o644)
        if testing_custom is not None:
            atomic_write(CUSTOM_GRUB, testing_custom, 0o755)
        try:
            update_grub()
        except Exception:
            pass
        raise

    state["phase"] = "complete"
    state["selected"] = test_id
    state["selected_label"] = TESTS[test_id][0]
    state["selected_params"] = params
    state["completed"] = time.time()
    write_state(state)
    return state


def cancel() -> None:
    require_root()
    state = read_state()
    if not state:
        return
    if state["phase"] in {"installing", "testing"}:
        restore_originals(state)
        update_grub()
    # Keep a completed keyboard fix when removing the application.
    STATE_FILE.unlink(missing_ok=True)


def main(argv: list[str]) -> int:
    if not argv:
        raise PatchError("Expected an operation: begin, finalize, or cancel.")
    action = argv[0]
    if action == "begin" and len(argv) == 1:
        state = begin()
    elif action == "finalize" and len(argv) == 2:
        state = finalize(argv[1])
    elif action == "cancel" and len(argv) == 1:
        cancel()
        print("OK")
        return 0
    else:
        raise PatchError("Invalid operation or arguments.")
    print(json.dumps({
        "phase": state["phase"],
        "selected": state.get("selected"),
        "adopted_existing_test_entries": state.get("adopted_existing_test_entries", False),
    }))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except PatchError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
