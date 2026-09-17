.. Copyright (c) 2008-2026 SmartEdit Studios, LLC
 (http://www.smarteditstudios.com). This file is part of
 SmartEdit Video Editor (http://www.smartedit.org), an open-source project
 dedicated to delivering high quality video editing and animation solutions
 to the world.

.. SmartEdit Video Editor is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public  as published by
 the Free Software Foundation, either version 3 of the , or
 (at your option) any later version.

.. SmartEdit Video Editor is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public  for more details.

.. You should have received a copy of the GNU General Public 
 along with SmartEdit Library.  If not, see <http://www.gnu.org/s/>.

.. _troubleshoot_ref:

Troubleshooting
===============

If you are experiencing an issue with SmartEdit, such as a freeze, crash, or error message, there are many different
techniques which can be useful for troubleshooting the issue.

Windows 11 Unresponsive
-----------------------

If you experience a freeze on Windows 11, this is a known issue with PyQt5 and Windows 11, related to the
accessibility features in Qt. This is triggered by pressing :kbd:`Ctrl+C` in SmartEdit (*only on Windows 11*).
SmartEdit will become unresponsive and a memory leak is also present (i.e. the longer SmartEdit is unresponsive,
the larger your memory leak will become until SmartEdit finally crashes or the user kills the process).

A simple work-around is to avoid :kbd:`Ctrl+C` on Windows 11, and instead use the right-click Copy/Paste menus. Another
work-around is to remap your "Copy" from :kbd:`Ctrl+C` to something else, for example :kbd:`Alt+C`. You can change
your keyboard mappings in the SmartEdit Preferences. See :ref:`preferences_keyboard_ref`.

Windows Debugging with GDB
--------------------------

If you are experiencing a crash or freeze with SmartEdit in Windows 10/11, the following step by step instructions
will help you determine the cause of the crash. These instructions will display a stack trace of SmartEdit's source code,
at the location of the crash. This information can be extremely useful for our development team, and very useful to
attach to bug reports (for a quicker resolution).

Install the Latest Daily Build
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before attaching a debugger, please download the **latest version** of SmartEdit: https://www.smartedit.org/download#daily.
Install this version of SmartEdit to the default location: ``C:\Program Files\SmartEdit Video Editor\``. For details
instructions on debugging SmartEdit on Windows, please see `this wiki <https://github.com/SmartEdit/smartedit-qt/wiki/Windows-Debugging-with-GDB>`_.

Install MSYS2
^^^^^^^^^^^^^

The Windows version of SmartEdit is compiled using an environment called MSYS2. In order to attach the GDB debugger
to our executable, ``smartedit-qt.exe``, you must first install MSYS2. This step is only required once.

1. Download & Install MSYS2: `<http://www.msys2.org/>`_
2. Run ``MSYS2 MinGW x64`` command prompt (for example: ``C:\msys64\msys2_shell.cmd -mingw64``)
3. Update all packages (*Copy/Paste the following command*):

   .. code-block:: shell

      pacman -Syu

4. Install GDB debugger (*Copy/Paste the following command*):

   .. code-block:: shell

      pacman -S --needed --disable-download-timeout mingw-w64-x86_64-toolchain

Launch SmartEdit with GDB Debugger
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run ``MSYS2 MinGW x64`` command prompt (for example: ``C:\msys64\msys2_shell.cmd -mingw64``)

Update the PATH (*Copy/Paste the following commands*):

.. code-block:: bash

    export PATH="/c/Program Files/SmartEdit Video Editor/lib:$PATH"
    export PATH="/c/Program Files/SmartEdit Video Editor/lib/PyQt5:$PATH"

Load SmartEdit into the GDB debugger (*Copy/Paste the following commands*):

.. code-block:: bash

    cd "/c/Program Files/SmartEdit Video Editor"/
    gdb smartedit-qt.exe

Launch SmartEdit from GDB prompt (*Copy/Paste the following command*):

.. code-block:: bash

    run --debug

Print Debugging Info
^^^^^^^^^^^^^^^^^^^^

Once SmartEdit has launched successfully with GDB attached, all you need to do is trigger a crash or freeze in SmartEdit.
When a crash occurs, switch back to the MSYS2 MinGW64 terminal and run one of the following commands
(by typing it and pressing ENTER). Usually, the first command to enter is ``bt``, which stands for ``backtrace``.
More commands are listed below.

.. code-block:: bash

    (gdb) run            (launch smartedit-qt.exe)
    (gdb) CTRL + C       (to manually break out   OR   wait for a crash / segmentation fault)
    (gdb) bt             (Print stack trace for the current thread #)
    (gdb) info threads   (to view all threads, and what they are doing. Look for `__lll_lock_wait` for Mutex/deadlocks)
    (gdb) thread 35      (Switch to thread number, for example thread 35)

High DPI / 4K Monitors
----------------------

SmartEdit Video Editor provides robust support for High DPI (Dots Per Inch)
monitors, ensuring that the interface looks sharp and is easily readable on
displays with various DPI settings. This support is particularly helpful on 4K
monitors and other high-resolution displays.

Per Monitor DPI Awareness
^^^^^^^^^^^^^^^^^^^^^^^^^

SmartEdit is DPI aware on a per-monitor basis, meaning it can adjust its scaling
dynamically depending on the DPI settings of each connected monitor. This helps
provide a consistent experience across different displays.

DPI Scaling on Windows
^^^^^^^^^^^^^^^^^^^^^^

On Windows, SmartEdit rounds the scaling factor to the nearest whole value to
maintain visual integrity. This helps avoid visual artifacts in the UI and
keeps interface elements crisp and well-aligned. Due to this rounding, some
scaling options can lead to larger fonts and UI elements than expected.

- **125% scaling** rounds to **100%**
- **150% scaling** rounds to **200%**

Workarounds for Fine-Grained Adjustment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

While rounding helps maintain a clean interface, there are workarounds for
users who require more precise control over scaling. These methods are **not
recommended** due to potential visual artifacts:

- **QT_SCALE_FACTOR_ROUNDING_POLICY=PassThrough**

  - Setting this environment variable can disable rounding and allow more precise scaling.
  - **Note:** This may cause visual artifacts, particularly in the timeline, and is not recommended.

- **QT_SCALE_FACTOR=1.25** (or similar value)

  - Manually setting the scale factor can provide finer adjustments to the font and UI scaling.
  - This can also be set via Preferences (User Interface Scale), but expect border/line issues on Windows with fractional scales.
  - **Note:** This method can also lead to visual artifacts and make SmartEdit harder to use.

For more info on adjusting these environment variables, please visit
https://github.com/SmartEdit/smartedit-qt/wiki/SmartEdit-UI-too-large.
