import re

def pspice_to_float(s: str):
    s = s.strip().replace("µ", "u").replace("μ", "u")
    m = re.match(r"^([+-]?[0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?)\s*([a-zA-Z]*)", s)
    if not m:
        return float(s)
    number = float(m.group(1))
    unit = m.group(2).lower()

    multipliers = {
        "meg": 1e6, "mil": 25.4e-6,
        "t": 1e12, "g": 1e9, "k": 1e3,
        "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15,
    }
    for suf in ("meg", "mil", "t", "g", "k", "m", "u", "n", "p", "f"):  # "meg"/"mil" önce
        if unit.startswith(suf):
            return number * multipliers[suf]
    return number