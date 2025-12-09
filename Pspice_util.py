def pspice_to_float(s: str):
    """Converts Pspice number to float.

    Args:
        s (str): Pspice number as string.

    Returns:
        float: Converted float value.
    """
    s = s.strip()
    s_upper = s.upper()

    multipliers = {
        "T": 1e12,
        "G": 1e9,
        "MEG": 1e6,
        "K": 1e3,
        "M": 1e-3,
        "U": 1e-6,
        "N": 1e-9,
        "P": 1e-12,
        "F": 1e-15
    }

    # Sort suffixes by length so "MEG" is matched before "M"
    for suf in sorted(multipliers.keys(), key=len, reverse=True):
        if s_upper.endswith(suf):
            number = float(s_upper[:-len(suf)])
            return number * multipliers[suf]

    # No suffix -> plain number
    return float(s)
