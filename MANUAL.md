# Linux Keyboard Patcher — User Manual

**Version:** 1.0  
**Subtitle:** Fixing unusable keyboard after GRUB  
**Author:** Blek — [www.farhanperdana.com](https://www.farhanperdana.com)

## 1. What the application does

Linux Keyboard Patcher adds four temporary GRUB entries that test common
parameters for a built-in keyboard that stops responding after Linux starts.
After you find an entry that works, the application can make that entry's
kernel parameters permanent.

The application backs up the original GRUB settings before it changes them.
While testing, it makes the GRUB menu visible and sets a 10-second timeout.
When you make an entry permanent, it restores the original timeout and removes
the temporary entries. Only the selected entry's keyboard parameters are kept
in the default kernel command line.

The four entries are:

1. **Keyboard test 1 — i8042 reset**  
   `i8042.reset i8042.nomux=1 i8042.nopnp=1 atkbd.reset`
2. **Keyboard test 2 — plus ACPI PnP off**  
   Entry 1 plus `pnpacpi=off`.
3. **Keyboard test 3 — plus dumbkbd**  
   Entry 1 plus `i8042.dumbkbd=1`.
4. **Keyboard test 4 — ACPI PnP off and dumbkbd**  
   Entry 1 plus both `pnpacpi=off` and `i8042.dumbkbd=1`.

The `dumbkbd` options may prevent the Caps Lock indicator from updating even
when the keyboard itself works. Test typing as well as the indicator.

## 2. Requirements

- x86_64 Linux or 32-bit x86 Linux with GRUB.
- Python 3 and the GRUB utilities provided by the distribution.
- Zenity for the graphical interface.
- `pkexec` and a Polkit authentication agent for graphical administrator
  prompts.
- An interactive terminal for terminal mode. When available, terminal mode
  uses `sudo` for administrator authentication; otherwise it uses `pkexec`.

The `.deb` and `.rpm` packages declare their runtime dependencies. For a
portable `.tgz` installation, install the corresponding dependencies with the
distribution's package manager first.

## 3. Install the application

### Debian and Ubuntu

Install the package that matches the system architecture with APT so it can
resolve package dependencies.

For 64-bit x86:

```sh
sudo apt install ./linux-keyboard-patcher_1.0-8_amd64.deb
```

For 32-bit x86:

```sh
sudo apt install ./linux-keyboard-patcher_1.0-8_i386.deb
```

On a 64-bit Debian or Ubuntu system, installing an i386 package requires i386
multiarch support and the 32-bit runtime dependencies. Replace the example
filename with the package you downloaded.

### Fedora and other RPM distributions

Install the architecture-matched RPM using the distribution's package
manager. For example, use the `x86_64` RPM on a 64-bit system:

```sh
sudo dnf install ./linux-keyboard-patcher-1.0-5.x86_64.rpm
```

For a 32-bit x86 system, use the `i686` RPM instead. The exact RPM filename
can vary by distribution and release.

### Portable tarball

Download the tarball matching your architecture: `x86_64` for 64-bit x86 or
`i386` for 32-bit x86. Extract it into a new directory and run its installer:

```sh
mkdir linux-keyboard-patcher
tar -xzf linux-keyboard-patcher-1.0-i386.tgz -C linux-keyboard-patcher
cd linux-keyboard-patcher
sudo ./install.sh
```

For a 64-bit installation, replace `i386` in the archive filename with
`x86_64`.

The installer copies the application files into `/usr`. To remove a tarball
installation later, run `sudo ./uninstall.sh` from the extracted directory.

## 4. Use the graphical interface

### First launch

1. Open **Linux Keyboard Patcher** from the Applications menu. The application
   requests administrator authorization before changing GRUB.
2. On the first run, it saves the original GRUB settings, adds the four test
   entries, and regenerates the GRUB menu.
3. The application displays **“Patching GRUB complete. Please reboot and try,
   which entry works.”** Read the instructions and entry names.
4. Choose **Close** to close the message and proceed to reboot and test. The
   **Show 4 GRUB Entries** button opens the entry-selection window with the
   **Make selected entry permanent** action. Use that action only after you
   have tested an entry and confirmed that it works. If you have not tested
   one yet, cancel the selection window.

### Test the entries

1. Reboot the computer.
2. In GRUB, choose **LINUX KEYBOARD PATCHER V 1.0** and then one of the four
   numbered keyboard test entries.
3. After Linux starts, try typing in a text field. Check whether Caps Lock
   responds, keeping in mind the `dumbkbd` note above.
4. If the keyboard still does not work, reboot and try another test entry.
   Test each entry in a separate boot.

### Make the working entry permanent

1. After booting with an entry that works, launch **Linux Keyboard Patcher**
   again. During the testing phase, the application opens the selection window.
2. The entry used for the current boot is selected automatically when the
   application can identify it. Choose another entry only if you tested it
   successfully as well.
3. Select **Make selected entry permanent** and authorize the administrator
   operation if prompted.
4. The application reports when the permanent patch is complete. The original
   GRUB timeout and temporary entries are restored; the selected keyboard
   parameters remain on the default Linux boot entry.

Canceling the selection window does not remove the temporary test entries.
They remain available until you choose a permanent entry or uninstall the
application while it is still in the testing phase.

## 5. Use the terminal interface

Open a terminal and run:

```sh
linux-keyboard-patcher --terminal
```

The application displays the instructions and the four entry names. On the
first run, press Enter when prompted to close the terminal view, then reboot
and test the entries from GRUB as described above.

After you find a working entry, boot that entry and run the same command again.
The terminal menu marks the current boot and lists entries 1 through 4:

- Press **Enter** to select the entry used for the current boot.
- Type **1**, **2**, **3**, or **4** to select another entry you already tested.
- Type **q** to leave the selection without making GRUB changes permanent.
- Type **y** when asked to confirm the permanent selection.

If no test entry is active in the current boot, terminal mode displays the
reboot instructions instead of offering to finalize an entry. Reboot using a
test entry, then run the command again.

### Choose a launch mode

```sh
linux-keyboard-patcher --terminal
linux-keyboard-patcher --gui
```

Use `--terminal` for the interactive text menu or `--gui` to open Zenity even
when starting from a terminal. With no option, the application uses terminal
mode when both standard input and output are connected to a terminal;
otherwise it opens the GUI.

The application requests administrator access itself. Do not prefix the
command with `sudo` unless your system specifically requires that workflow.

## 6. GRUB files and application state

During testing, the application uses:

- `/etc/default/grub` for the menu visibility and timeout settings.
- `/etc/grub.d/49_keyboard_tests` for the temporary test entries.
- `/var/lib/linux-keyboard-patcher/` for backups and workflow state.

The application regenerates GRUB after each change. If GRUB generation fails,
it restores the files from before that operation and attempts to regenerate
the menu again.

If you uninstall the application while it is still in the testing phase, the
package removal script restores the original GRUB settings and removes the
temporary entries. A completed keyboard fix remains active after the
application is uninstalled.

## 7. Troubleshooting

### The GUI does not open

Install Zenity and a Polkit authentication agent for your desktop environment.
You can use terminal mode while troubleshooting the GUI:

```sh
linux-keyboard-patcher --terminal
```

### Administrator authentication fails

Confirm that `pkexec` is installed and that your desktop session has a Polkit
authentication agent. In terminal mode, the application uses `sudo` when it is
available.

### The keyboard still does not work with a test entry

Reboot, select another numbered test entry, and check the keyboard again. Do
not make an entry permanent until you have confirmed that it works.

### GRUB reports an error

Read the error shown by the application. The patcher attempts to restore the
settings from before the failed operation. Do not manually delete the saved
state or backup directory while a test is in progress.

## 8. Build from source

From the project directory, run:

```sh
packaging/build-packages.sh x86_64
packaging/build-packages.sh i386
```

The build host must be x86_64 and have Python 3, GNU `as` and `ld`, `dpkg-deb`,
and `tar`. GNU `as` and `ld` provide the 32-bit i386 output mode, so a 32-bit C
library is not needed to build the launcher. `rpmbuild` is optional; without
it, the script still creates the RPM specification and source archive. Set
`OUTPUT_DIR=/path/to/output` to choose where package artifacts are written.

Build either standalone launcher inside the project with:

```sh
mkdir -p build
src/build-binary.sh --arch x86_64 build/linux-keyboard-patcher
src/build-binary.sh --arch i386 build/linux-keyboard-patcher-i386
```

You can launch either resulting binary directly:

```sh
build/linux-keyboard-patcher --terminal
build/linux-keyboard-patcher-i386 --terminal
# Add `--gui` to either command to open the graphical interface.
build/linux-keyboard-patcher-i386 --gui
```

## 9. License

Linux Keyboard Patcher is licensed under the GNU General Public License,
version 3 only (GPL-3.0-only). The complete license text is included in the
project's `LICENSE` file and in the distributed packages.

To create the 32-bit packages and RPM source files, run:

```sh
packaging/build-packages.sh i386
```

This creates a Debian `i386` package, an `i386` tarball, and an RPM source
archive for `i686`. The 32-bit launcher requires an x86 Linux kernel capable of
running 32-bit ELF programs. Its Python, Zenity, Polkit, and GRUB runtime
dependencies must also be available for the installed system.

The package builder also creates the architecture-independent project source
archive `linux-keyboard-patcher-source-1.0.tar.gz`. It includes both launcher
assembly files, the Python sources, packaging files, and this manual. The
application source contains the clickable `https://www.farhanperdana.com` URL.
