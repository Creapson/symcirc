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
        "MA": 1e-3, # Some use "MA" for milliampere
        "K": 1e3,
        "M": 1e-3,
        "U": 1e-6,
        "UF": 1e-6,  # Some use "uF" for microfarads
        "N": 1e-9,
        "P": 1e-12,
        "F": 1e-15,
        "A": 1.0,  # No multiplier for plain numbers
        "V": 1.0,
    }

    # Sort suffixes by length so "MEG" is matched before "M"
    for suf in sorted(multipliers.keys(), key=len, reverse=True):
        if s_upper.endswith(suf):
            
            s_upper = s_upper[:-len(suf)].strip()  # Remove suffix and any trailing spaces
            
            number = float(s_upper)
            return number * multipliers[suf]

    # No suffix -> plain number
    return float(s)
