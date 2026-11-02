"""Runs LTspice headlessly to produce the ".op" log that flatten() needs.

LTspice only writes the "Semiconductor Device Operating Points" table (rpi, gm,
cbe, ...) into its ".log" when ".op" is the *active* simulation command. A
circuit netlisted for ".ac"/".tran" therefore ships a log without any transistor
data, and its small-signal placeholders would stay unresolved.

Doing that by hand means running LTspice twice and keeping the two logs apart,
since the second run overwrites the first one's log. Instead, this module
derives a ".op"-only *copy* of the netlist and runs LTspice on it in batch mode
("-b", no window, ~0.1 s) - the user's own schematic, netlist and log are never
touched.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from shutil import which
from typing import Iterable, List, Optional

from parser.ltspice.LtspiceParser import LtspiceParser


# LTspice 24 installs as ADI/LTspice, LTspice XVII as LTC/LTspiceXVII and
# LTspice IV as LTC/LTspiceIV.
_KNOWN_EXECUTABLES = (
    r"C:\Program Files\ADI\LTspice\LTspice.exe",
    r"C:\Program Files\LTC\LTspiceXVII\XVIIx64.exe",
    r"C:\Program Files (x86)\LTC\LTspiceXVII\XVIIx64.exe",
    r"C:\Program Files\LTC\LTspiceIV\scad3.exe",
)

# A netlist may only carry one active simulation command, so every other
# analysis directive is commented out before ".op" is added. ".step" goes with
# them: left in, it would repeat the .op point once per step value and produce
# one operating-point table per run.
_DISABLED_DIRECTIVES = (".ac", ".tran", ".dc", ".noise", ".tf", ".four", ".step", ".op")

# Distinctive enough that the generated files can never collide with the ".net"
# and ".log" LTspice writes for the user's own run.
_OP_SUFFIX = ".symcirc_op"


def find_ltspice(extra_paths: Iterable[str] = ()) -> Optional[str]:
    """Returns the path of an LTspice executable, or None if none was found."""
    for candidate in tuple(extra_paths) + _KNOWN_EXECUTABLES:
        if candidate and os.path.isfile(candidate):
            return candidate

    for name in ("LTspice.exe", "XVIIx64.exe", "scad3.exe", "ltspice"):
        found = which(name)
        if found:
            return found

    return None


def build_op_netlist(lines: Iterable[str]) -> List[str]:
    """Rewrites netlist lines into a ".op"-only version.

    Every analysis directive is commented out and a single ".op" is inserted
    just before ".end". Element, ".model", ".lib"/".inc" and comment lines are
    passed through untouched, so models and includes resolve exactly as they do
    in the original netlist.
    """
    result: List[str] = []
    op_inserted = False

    for raw_line in lines:
        stripped = raw_line.rstrip("\r\n")
        lowered = stripped.strip().lower()

        if lowered.startswith(_DISABLED_DIRECTIVES):
            result.append("* " + stripped.strip())
            continue

        # ".end" ends the netlist, ".ends" only ends a subcircuit.
        if lowered.startswith(".end") and not lowered.startswith(".ends"):
            if not op_inserted:
                result.append(".op")
                op_inserted = True
            result.append(stripped)
            continue

        result.append(stripped)

    if not op_inserted:
        result.append(".op")
        result.append(".end")

    return result


def generate_op_log(
    netlist_path: str,
    ltspice_exe: Optional[str] = None,
    timeout: int = 180,
) -> str:
    """Runs LTspice on a ".op"-only copy of `netlist_path`.

    Returns the path of the log LTspice produced ("<name>.symcirc_op.log", kept
    next to the netlist so it can be inspected and reused). The generated
    netlist and raw file are removed again; the original files are not touched.

    Raises FileNotFoundError if LTspice or the netlist is missing, and
    RuntimeError if LTspice ran but produced no log.
    """
    exe = ltspice_exe or find_ltspice()
    if exe is None:
        raise FileNotFoundError(
            "LTspice executable not found. Install LTspice, or pass its path "
            "as ltspice_exe."
        )

    source = Path(netlist_path)
    if not source.is_file():
        raise FileNotFoundError(f"Netlist not found: {netlist_path}")

    # The copy lives next to the original so relative .lib/.inc paths inside
    # the netlist still resolve.
    op_netlist = source.with_name(source.stem + _OP_SUFFIX + ".net")
    op_log = op_netlist.with_suffix(".log")
    op_raw = op_netlist.with_suffix(".raw")

    lines = LtspiceParser._read_text_lines(str(source))
    op_netlist.write_text(
        "\n".join(build_op_netlist(lines)) + "\n",
        encoding="latin-1",
        errors="replace",
    )

    try:
        completed = subprocess.run(
            [exe, "-b", str(op_netlist)],
            timeout=timeout,
            capture_output=True,
            check=False,
        )
    finally:
        # Keep the log, drop everything else that was generated.
        for temporary in (op_netlist, op_raw):
            try:
                temporary.unlink()
            except OSError:
                pass

    if not op_log.is_file():
        raise RuntimeError(
            f"LTspice ({exe}) produced no log for {source.name}. "
            f"Exit code {completed.returncode}."
        )

    return str(op_log)
