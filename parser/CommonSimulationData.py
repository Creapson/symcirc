import re
from pathlib import Path

import pandas as pd

NAME_RE = re.compile(r"'([^']+)'")

DATA_RE = re.compile(
    r"(?P<real>[+-]?\d+\.\d+E[+-]\d+)/"
    r"(?P<imag>[+-]?\d+\.\d+E[+-]\d+):"
    r"(?P<index>[0-9A-Fa-f]+)"
)


def parse_csd(path: str | Path) -> pd.DataFrame:
    signal_names = []
    rows = []
    current_freq = None
    reading_names = True

    with open(path, "r") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            # End of file
            if line.startswith("#;"):
                break

            # Frequency block starts → stop reading names
            if line.startswith("#C"):
                reading_names = False
                _, freq, _ = line.split()
                current_freq = float(freq)
                continue

            # Parse signal names (before first #C)
            if reading_names:
                signal_names.extend(NAME_RE.findall(line))
                continue

            # Parse data entries
            for m in DATA_RE.finditer(line):
                rows.append(
                    {
                        "frequency_hz": current_freq,
                        "index": int(m.group("index"), 16),
                        "value": float(m.group("real")) + 1j * float(m.group("imag")),
                    }
                )

    # Build DataFrame
    df = pd.DataFrame(rows)
    print(df)
    print(signal_names)

    # Map index → signal name
    name_map = dict(enumerate(signal_names))
    df["signal"] = df["index"].map(name_map)

    # Safety check
    if df["signal"].isna().any():
        missing = df[df["signal"].isna()]["index"].unique()
        raise ValueError(f"Unmapped indices found: {missing}")

    # Pivot to one column per signal
    wide_df = df.pivot(index="frequency_hz", columns="signal", values="value")

    return wide_df.sort_index()

