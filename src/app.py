"""Zenity and terminal interfaces for Linux Keyboard Patcher."""
# Copyright (C) 2026 Blek
# SPDX-License-Identifier: GPL-3.0-only

import html
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT_HELPER_SOURCE = __ROOT_HELPER_SOURCE__
ROOT_OPS = {"__name__": "linux_keyboard_patcher_ops"}
exec(compile(ROOT_HELPER_SOURCE, "root-helper.py", "exec"), ROOT_OPS)
PatchError = ROOT_OPS["PatchError"]

APP_TITLE = "Linux Keyboard Patcher"
PRODUCT_TITLE = "LINUX KEYBOARD PATCHER V 1.0"
APP_ID = "com.farhanperdana.linuxkeyboardpatcher"
SUBTITLE = "Fixing unusable keyboard after GRUB"
BYLINE = 'by Blek "<a href="https://www.farhanperdana.com">www.farhanperdana.com</a>"'
HEADER = f"<b>{PRODUCT_TITLE}</b>\n{SUBTITLE}\n{BYLINE}"
ENTRIES = [
    ("test1", "Keyboard test 1 - i8042 reset"),
    ("test2", "Keyboard test 2 - plus ACPI PnP off"),
    ("test3", "Keyboard test 3 - plus dumbkbd"),
    ("test4", "Keyboard test 4 - ACPI PnP off and dumbkbd"),
]
ENTRY_LABELS = dict(ENTRIES)
DONE_TEXT = "Patching GRUB complete. Please reboot and try, which entry works."
BASE_TEST_PARAMS = frozenset(
    {"i8042.reset", "i8042.nomux=1", "i8042.nopnp=1", "atkbd.reset"}
)
_ZENITY_HAS_APP_ID: bool | None = None
_TERMINAL_MODE = False


class AppError(Exception):
    pass


def run_zenity(args: list[str]) -> subprocess.CompletedProcess:
    """Run Zenity, adding the application identity when supported."""
    global _ZENITY_HAS_APP_ID
    try:
        zenity = shutil.which("zenity")
        if zenity is None:
            raise AppError("Zenity is required to display this application.")
        if _ZENITY_HAS_APP_ID is None:
            probe = subprocess.run([zenity, "--help-all"], text=True, capture_output=True)
            _ZENITY_HAS_APP_ID = "--app-id" in (probe.stdout + probe.stderr)
        identity = [f"--app-id={APP_ID}"] if _ZENITY_HAS_APP_ID else []
        return subprocess.run([zenity, *identity, *args], text=True, capture_output=True)
    except FileNotFoundError as exc:
        raise AppError("Zenity is required to display this application.") from exc


def show_error(message: str) -> None:
    if _TERMINAL_MODE or not shutil.which("zenity"):
        print(f"{APP_TITLE}: {message}", file=sys.stderr)
        return
    text = f"{HEADER}\n\n{html.escape(message)}"
    run_zenity(["--error", f"--title={APP_TITLE}", f"--text={text}", "--width=520"])


def entry_lines() -> str:
    return "\n".join(f"{index}. {label}" for index, (_, label) in enumerate(ENTRIES, 1))


def instructions_text() -> str:
    return (
        f"{HEADER}\n\n<b>{DONE_TEXT}</b>\n\n"
        "Reboot and test the four GRUB entries one at a time. If one does not work, "
        "reboot and try the next. After you find an entry that works, reopen this "
        "application and choose it.\n\n"
        f"{entry_lines()}"
    )


def show_instructions(adopted: bool) -> None:
    """Show reboot instructions and, when requested, the permanent-entry chooser."""
    if adopted:
        text = (
            instructions_text()
            + "\n\nThe four test entries were already present. Choose now only if "
            "you have already tested an entry."
        )
        result = run_zenity([
            "--question", f"--title={APP_TITLE}", f"--text={text}",
            "--ok-label=Choose the entry that worked", "--cancel-label=Close and test",
            "--width=560",
        ])
        if result.returncode == 0:
            choose_entry()
        return

    result = run_zenity([
        "--info", f"--title={APP_TITLE}", f"--text={instructions_text()}",
        "--ok-label=Close", "--extra-button=Show the 4 GRUB entries", "--width=560",
    ])
    # Zenity reports an extra button's label on stdout and uses exit status 1,
    # so identify this action by its output rather than returncode.
    if result.stdout.strip() == "Show the 4 GRUB entries":
        choose_entry()


def current_test_id() -> str | None:
    """Return the test entry whose kernel parameters are active in this boot."""
    try:
        args = set(shlex.split(Path("/proc/cmdline").read_text()))
    except OSError:
        return None
    if not BASE_TEST_PARAMS.issubset(args):
        return None
    if "pnpacpi=off" in args and "i8042.dumbkbd=1" in args:
        return "test4"
    if "pnpacpi=off" in args:
        return "test2"
    if "i8042.dumbkbd=1" in args:
        return "test3"
    return "test1"


def choose_entry() -> None:
    """Let the user make a tested GRUB entry the permanent default."""
    current_id = current_test_id()
    current_label = ENTRY_LABELS.get(current_id) if current_id else None
    boot_note = (
        f"Current boot: {html.escape(current_label)} (preselected)."
        if current_label
        else (
            "Select the entry you tested successfully. It will become the "
            "permanent GRUB default."
        )
    )
    text = f"{HEADER}\n\n<b>{DONE_TEXT}</b>\n\n{boot_note}"
    args = [
        "--list", "--radiolist", f"--title={APP_TITLE}", f"--text={text}",
        "--column=Select", "--column=GRUB entry", "--column=ID",
        "--hide-column=3", "--print-column=3",
        "--ok-label=Make selected entry permanent", "--cancel-label=Cancel",
        "--width=560", "--height=520",
    ]
    for test_id, label in ENTRIES:
        is_current = current_id is not None and test_id == current_id
        args.extend(["TRUE" if is_current else "FALSE", label, test_id])
    result = run_zenity(args)
    selected = result.stdout.strip()
    if result.returncode != 0 or selected not in ENTRY_LABELS:
        return

    try:
        run_root_action(binary_path(), "finalize", selected)
    except (AppError, PatchError) as exc:
        show_error(str(exc))
        return
    result = run_zenity([
        "--info", f"--title={APP_TITLE}",
        f"--text={HEADER}\n\nPatching GRUB complete. The selected keyboard entry is "
        "now the permanent default. The original GRUB timeout and other settings "
        "have been restored.",
        "--width=560",
    ])


def cli_header() -> None:
    print(f"{PRODUCT_TITLE}\n{SUBTITLE}\nby Blek \"www.farhanperdana.com\"\n")


def cli_entry_lines(current_id: str | None = None) -> None:
    for index, (test_id, label) in enumerate(ENTRIES, 1):
        marker = "  [current boot]" if test_id == current_id else ""
        print(f"  {index}. {label}{marker}")


def pause_cli() -> None:
    try:
        input("\nPress Enter to close this window... ")
    except EOFError:
        pass


def choose_entry_cli(current_id: str) -> int:
    """Ask for a terminal selection and confirm before finalizing GRUB."""
    current_number = [test_id for test_id, _ in ENTRIES].index(current_id) + 1
    print(f"\nCurrent boot detected: {ENTRY_LABELS[current_id]}")
    print("Choose the entry you tested successfully:")
    cli_entry_lines(current_id)
    while True:
        try:
            value = input(f"\nEntry number [{current_number}], or q to cancel: ").strip().lower()
        except EOFError:
            return 0
        if value == "q":
            return 0
        if not value:
            selected_number = current_number
        elif value in {"1", "2", "3", "4"}:
            selected_number = int(value)
        else:
            print("Enter a number from 1 to 4, or q to cancel.")
            continue

        selected_id, selected_label = ENTRIES[selected_number - 1]
        try:
            confirmation = input(
                f"Make '{selected_label}' the permanent default? Type y to confirm: "
            ).strip().lower()
        except EOFError:
            return 0
        if confirmation != "y":
            print("Selection cancelled; GRUB was not finalized.")
            return 0
        try:
            run_root_action(binary_path(), "finalize", selected_id)
        except (AppError, PatchError) as exc:
            show_error(str(exc))
            return 1
        print("\nPatching GRUB complete.")
        print(f"Permanent keyboard entry: {selected_label}")
        print("The original GRUB timeout and other settings have been restored.")
        return 0


def show_cli_instructions(adopted: bool = False) -> None:
    print(DONE_TEXT)
    if adopted:
        print("The four GRUB test entries were already present.")
    print(
        "Reboot and test the four GRUB entries one at a time. If one does not work, "
        "reboot and try the next. After you find an entry that works, reopen this "
        "application and choose it.\n"
    )
    cli_entry_lines()


def run_cli() -> int:
    """Run the application flow in an interactive terminal."""
    cli_header()
    try:
        state = ROOT_OPS["read_state"]()
    except PatchError as exc:
        show_error(str(exc))
        return 1

    if not state:
        try:
            state = run_root_action(binary_path(), "begin")
        except (AppError, PatchError) as exc:
            show_error(str(exc))
            return 1
        adopted = bool(state.get("adopted_existing_test_entries"))
        show_cli_instructions(adopted)
        current_id = current_test_id()
        if adopted and current_id is not None:
            print("\nA test entry is active in this boot.")
            return choose_entry_cli(current_id)
        pause_cli()
        return 0

    phase = state.get("phase")
    if phase == "testing":
        current_id = current_test_id()
        if current_id is None:
            show_cli_instructions()
            print(
                "\nNo keyboard test entry is active in this boot. Reboot and "
                "choose a test entry first."
            )
            pause_cli()
            return 0
        print(DONE_TEXT)
        return choose_entry_cli(current_id)

    if phase == "complete":
        print("The permanent keyboard patch is already installed.")
        print(f"Selected entry: {state.get('selected_label', '')}")
        pause_cli()
        return 0

    show_error("The saved patch state is incomplete. No GRUB changes were made.")
    return 1


_BINARY_PATH: str | None = None


def binary_path() -> str:
    """Return the executable path passed by the native ELF launcher."""
    if _BINARY_PATH:
        return _BINARY_PATH
    raise AppError("Could not determine the application binary path.")


def run_root_action(executable: str, action: str, *args: str) -> dict:
    """Run one privileged operation directly or through sudo/Polkit."""
    if os.geteuid() == 0:
        if action == "begin":
            state = ROOT_OPS["begin"]()
        elif action == "finalize" and len(args) == 1:
            state = ROOT_OPS["finalize"](args[0])
        else:
            raise AppError("Invalid privileged operation.")
        return state

    command: list[str]
    if _TERMINAL_MODE and shutil.which("sudo"):
        command = ["sudo", executable, "--root", action, *args]
    elif shutil.which("pkexec"):
        command = ["pkexec", executable, "--root", action, *args]
    else:
        raise AppError("Administrator authorization requires sudo or Polkit (pkexec).")

    try:
        if _TERMINAL_MODE:
            # Keep the terminal available for sudo's password prompt while capturing
            # the helper's JSON response for the parent process.
            with tempfile.TemporaryFile(mode="w+t") as output:
                result = subprocess.run(command, stdout=output, text=True)
                output.seek(0)
                stdout = output.read()
            stderr = ""
        else:
            result = subprocess.run(command, text=True, capture_output=True)
            stdout = result.stdout
            stderr = result.stderr
    except FileNotFoundError as exc:
        raise AppError("Could not start the administrator authorization tool.") from exc
    if result.returncode != 0:
        detail = (stderr or stdout).strip()
        if not detail:
            detail = "Administrator authorization was cancelled or denied."
        raise AppError(detail)
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise AppError("The privileged GRUB operation returned an invalid result.") from exc


def run_as_root(action: str, *args: str) -> int:
    try:
        state = run_root_action(binary_path(), action, *args)
    except (AppError, PatchError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "phase": state.get("phase"),
                "selected": state.get("selected"),
                "adopted_existing_test_entries": state.get(
                    "adopted_existing_test_entries", False
                ),
            }
        )
    )
    return 0


def run_ui() -> int:
    """Run the application flow with Zenity dialogs."""
    if not shutil.which("zenity"):
        show_error(
            "Zenity is not installed. Install Zenity or run this program from a "
            "terminal."
        )
        return 1
    try:
        state = ROOT_OPS["read_state"]()
    except PatchError as exc:
        show_error(str(exc))
        return 1

    if not state:
        try:
            state = run_root_action(binary_path(), "begin")
        except (AppError, PatchError) as exc:
            show_error(str(exc))
            return 1
        show_instructions(bool(state.get("adopted_existing_test_entries")))
        return 0

    phase = state.get("phase")
    if phase == "testing":
        choose_entry()
        return 0
    if phase == "complete":
        selected = html.escape(state.get("selected_label", ""))
        run_zenity([
            "--info", f"--title={APP_TITLE}",
            f"--text={HEADER}\n\nThe permanent keyboard patch is already installed.\n\n"
            f"Selected entry: {selected}",
            "--width=540",
        ])
        return 0
    show_error("The saved patch state is incomplete. No GRUB changes were made.")
    return 1


def main() -> int:
    """Parse launcher options and choose GUI or terminal mode."""
    global _BINARY_PATH, _TERMINAL_MODE
    argv = sys.argv[1:]
    if len(argv) < 2 or argv[0] != "--binary-path":
        show_error("Launch this program through its binary file.")
        return 1
    _BINARY_PATH = argv[1]
    tail = argv[2:]
    if tail and tail[0] == "--root":
        if len(tail) < 2:
            print("Missing privileged operation.", file=sys.stderr)
            return 1
        return run_as_root(tail[1], *tail[2:])
    if "--terminal" in tail and "--gui" in tail:
        show_error("Choose either --terminal or --gui, not both.")
        return 2
    unknown = [arg for arg in tail if arg not in {"--terminal", "--gui"}]
    if unknown:
        show_error(f"Unknown option: {unknown[0]}")
        return 2
    if "--terminal" in tail:
        _TERMINAL_MODE = True
    elif "--gui" not in tail:
        _TERMINAL_MODE = sys.stdin.isatty() and sys.stdout.isatty()
    if _TERMINAL_MODE and not (sys.stdin.isatty() and sys.stdout.isatty()):
        show_error(
            "Terminal mode needs an interactive terminal. Run the program from a "
            "terminal window."
        )
        return 2
    return run_cli() if _TERMINAL_MODE else run_ui()


if __name__ == "__main__":
    raise SystemExit(main())
