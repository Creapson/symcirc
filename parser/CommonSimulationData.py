import re

import pandas as pd

NAME_RE = re.compile(r"'([^']+)'")

DATA_RE = re.compile(
    r"(?P<real>[+-]?\d+\.\d+E[+-]\d+)/"
    r"(?P<imag>[+-]?\d+\.\d+E[+-]\d+):"
    r"(?P<index>[0-9A-Fa-f]+)"
)


def parse_csd(path):
    signal_names = []
    rows = []
    current_freq = None
    reading_names = False
    reading_header = False

    with open(path, "r") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if line.startswith("#H"):
                reading_header = True
                continue

            # End of file
            if line.startswith("#;"):
                break

            if line.startswith("#N"):
                reading_header = False
                reading_names = True
                continue

            # Frequency block starts → stop reading names
            if line.startswith("#C"):
                reading_names = False
                reading_header = False
                _, freq, _ = line.split()
                current_freq = float(freq)
                continue

            if reading_header:
                continue

            # Parse signal names (before first #C)
            if reading_names:
                signal_names.extend(NAME_RE.findall(line))
                continue

            # Parse data entries
            for value_str in line.split():
                values = value_str.split("/")
                val_re = values[0]
                val_im = values[1].split(":")[0]
                index = values[1].split(":")[1]

                rows.append(
                    {
                        "frequency_hz": current_freq,
                        "index": int(index, 16),
                        "value": float(val_re) + 1j * float(val_im),
                    }
                )

    # Build DataFrame
    df = pd.DataFrame(rows)

    return df, signal_names
