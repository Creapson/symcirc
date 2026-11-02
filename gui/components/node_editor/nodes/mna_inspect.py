"""
mna_inspect.py -- symcirc MNA matrix inspector

WHY: once the pole/zero discrepancy has been shown not to be in the solver,
one possibility remains: the A(s) matrix is different. This tool makes the
matrix comparable ROW BY ROW against another tool (e.g. Analog Insydes).

If you keep working with different BJTs, this is the real checkpoint: a wrong
model library makes every circuit wrong, no matter how good the solver is.

USAGE
    from tools.mna_inspect import inspect_mna
    inspect_mna(mna_data)                    # full report
    inspect_mna(mna_data, symbolic=True)     # symbolic, no value substitution
"""

import numpy as np
import sympy as sp


def inspect_mna(mna_data, symbolic=False, max_print=14):
    s = sp.symbols('s')
    names = [str(u) for u in mna_data.get_unknowns()]
    n = len(names)

    A = mna_data.A if symbolic else mna_data.A.subs(mna_data.value_dict)
    z = mna_data.z if symbolic else mna_data.z.subs(mna_data.value_dict)

    print("=" * 76)
    print(f"MNA SYSTEM  n = {n}")
    print("=" * 76)
    print("Unknowns:", ", ".join(f"[{i}] {v}" for i, v in enumerate(names)))

    if symbolic:
        print("\nA(s) (symbolic):")
        sp.pprint(A)
        print("\nz(s) (symbolic):")
        sp.pprint(z.T)
        return

    free = A.free_symbols - {s}
    if free:
        print(f"\n!! UNRESOLVED SYMBOLS: {sorted(free, key=str)}")
        print("   value_dict is incomplete - the numeric report below is not reliable.")
        return

    G = np.array(A.subs(s, 0), dtype=complex)
    C = np.array(sp.diff(A, s).subs(s, 0), dtype=complex)

    print("\n" + "-" * 76)
    print("C_dyn (REACTIVE element matrix) -- non-zero entries")
    print("-" * 76)
    print("These show the capacitances (and inductance contributions) in your circuit.")
    print("They must match the reference tool's netlist expansion ONE FOR ONE.\n")
    ent = [(i, j, C[i, j]) for i in range(n) for j in range(n) if C[i, j] != 0]
    if not ent:
        print("   (empty - no reactive elements at all?)")
    for i, j, v in ent[:max_print * 2]:
        kind = "diagonal" if i == j else "off-diag "
        print(f"   C[{names[i]:>6},{names[j]:>6}] {kind} = {v.real:+.6e}")
    if len(ent) > max_print * 2:
        print(f"   ... ({len(ent) - max_print*2} more entries)")

    print("\n" + "-" * 76)
    print("TOTAL CAPACITANCE PER NODE (including ground)")
    print("-" * 76)
    print("If a node's row sum is zero, the capacitors at that node have no")
    print("connection to GROUND (a floating capacitor network).\n")
    for i in range(n):
        rs = C[i, :].sum().real
        tag = "  <- no connection to ground" if abs(rs) < 1e-18 * max(1.0, abs(C[i, i])) else ""
        print(f"   {names[i]:>8}: diagonal {C[i,i].real:+.4e}   row sum {rs:+.4e}{tag}")

    print("\n" + "-" * 76)
    print("STRUCTURAL SUMMARY")
    print("-" * 76)
    rk = np.linalg.matrix_rank(C)
    print(f"   rank(C_dyn) = {rk} / {n}   -> {rk} finite poles expected")
    print(f"   cond(G)     = {np.linalg.cond(G):.4e}")
    nzC = C[C != 0]
    if nzC.size:
        print(f"   |C| range   = {np.min(np.abs(nzC)):.3e} .. {np.max(np.abs(nzC)):.3e}"
              f"  ({np.max(np.abs(nzC))/np.min(np.abs(nzC)):.2e}x)")
    print(f"   is z(s) s-dependent: {'YES' if z.has(s) else 'no'}")
    nzz = [(i, z[i, 0]) for i in range(n) if z[i, 0] != 0]
    print(f"   source entries: " +
          (", ".join(f"{names[i]}={complex(v).real:+.3e}" for i, v in nzz) or "(none)"))

    print("\n" + "-" * 76)
    print("ASYMMETRIC G ENTRIES (controlled sources: gm, mu, ...)")
    print("-" * 76)
    print("Your BJT small-signal model's gm stamp shows up here.\n")
    asym = [(i, j, G[i, j], G[j, i]) for i in range(n) for j in range(i + 1, n)
            if abs(G[i, j] - G[j, i]) > 1e-15 * max(1.0, abs(G[i, j]))]
    if not asym:
        print("   (none - no controlled-source stamp found)")
    for i, j, a, b in asym[:max_print]:
        print(f"   G[{names[i]:>6},{names[j]:>6}] = {a.real:+.6e}   "
              f"G[{names[j]:>6},{names[i]:>6}] = {b.real:+.6e}   "
              f"diff = {(a-b).real:+.6e}")

    print("\n" + "=" * 76)
    print("COMPARISON CHECKLIST")
    print("=" * 76)
    print("  1. Which BJT model LEVEL is selected in the reference tool? (Analog")
    print("     Insydes offers three separate simplification levels for BJTs.)")
    print("  2. Are C_jc, C_je the same on both sides? They set the high-frequency")
    print("     poles EXACTLY.")
    print("  3. Does the reference model include r_b (base spreading resistance),")
    print("     r_o (Early), C_cs (collector-substrate)? Does yours?")
    print("  4. Are the source resistance and coupling capacitors the same?")
    print("  5. Is the output node the SAME on both sides? (zeros depend on it)")
    print("=" * 76)


def check_index_mapping(mna_data):
    """Is the ORDER of get_unknowns() the same as the COLUMN ORDER of A?

    Why it matters: idx_out = get_unknowns().index(node), and that index
    decides WHICH COLUMN is replaced in the Cramer/Rosenbrock step. If the
    order does not match, the POLES STAY CORRECT (det is permutation-invariant)
    but the ZEROS come out wrong. So this is exactly one of the causes of a
    "poles match, zeros don't" table.

    Test: in the MNA a branch-current unknown I_X's ROW is a voltage-source
    constraint; its entries should be +/-1 (and 0) - it must NOT contain a
    conductance value. Node-voltage rows are the opposite. This distinction
    can be checked mechanically.
    """
    s = sp.symbols('s')
    names = [str(u) for u in mna_data.get_unknowns()]
    A = mna_data.A.subs(mna_data.value_dict)
    G = np.array(A.subs(s, 0), dtype=complex)
    n = len(names)

    print("=" * 76)
    print("INDEX MAPPING CONSISTENCY TEST")
    print("=" * 76)
    if G.shape[0] != n:
        print(f"!! SIZE MISMATCH: A {G.shape[0]}x{G.shape[1]}, "
              f"get_unknowns() {n} elements. This alone is a bug.")
        return False

    ok = True
    for i, nm in enumerate(names):
        row = G[i, :]
        nz = row[row != 0]
        if nz.size == 0:
            continue
        looks_pm1 = bool(np.all(np.isclose(np.abs(nz), 1.0, rtol=1e-9)))
        is_current = nm.startswith("I_")
        if is_current and not looks_pm1:
            print(f"  !! {nm:<26} is a branch current but its row is NOT +/-1 "
                  f"(max |entry| = {np.max(np.abs(nz)):.3e})")
            ok = False
        elif (not is_current) and looks_pm1 and nz.size <= 2:
            print(f"  ?  {nm:<26} is a node voltage but its row looks like +/-1 "
                  f"- the ordering may be shifted")
            ok = False

    if ok:
        print("  All rows are of the expected type. The ordering looks CONSISTENT.")
        print("  (Still not conclusive; check the source test below too.)")
    print()
    z = mna_data.z.subs(mna_data.value_dict)
    zn = np.array(z.subs(s, 0), dtype=complex).ravel()
    nzi = [i for i in range(n) if zn[i] != 0]
    print("  Non-zero rows in the z vector:")
    for i in nzi:
        kind = "branch current (EXPECTED: voltage source)" if names[i].startswith("I_") \
               else "node voltage (EXPECTED: current source)"
        print(f"     [{i}] {names[i]:<26} = {zn[i].real:+.4e}   {kind}")
    if not nzi:
        print("     (none - is the source vector empty?)")
    print("=" * 76)
    return ok


def junction_caps(mna_data, device_hint="Q"):
    """Extract and list the capacitances touching a transistor's internal nodes.

    These values set the high-frequency poles EXACTLY. They must be compared
    one for one against the values the reference tool uses for the same
    transistor.

    NOTE (two often-missed points):
      * C_pi = C_je(depletion) + C_diff,  C_diff = TF * gm
        For a 2N2222 TF ~ 0.4 ns, gm ~ 0.04 S  ->  C_diff ~ 16 pF,
        i.e. the SAME ORDER as the depletion term. Dropping the diffusion
        term shifts the high-frequency poles significantly.
      * Junction capacitances are BIAS-DEPENDENT:
        C_jc(V) = CJC / (1 + V_CB/VJC)^MJC
        Using the zero-bias CJC directly is off by roughly 2x at V_CB=5V.
    If the two tools differ on either point, the LOW-frequency results still
    match exactly but the HIGH-frequency poles/zeros diverge.
    """
    s = sp.symbols('s')
    names = [str(u) for u in mna_data.get_unknowns()]
    C = np.array(sp.diff(mna_data.A.subs(mna_data.value_dict), s).subs(s, 0),
                 dtype=complex)
    n = len(names)
    dev = [i for i, nm in enumerate(names) if device_hint in nm]

    print("=" * 76)
    print("CAPACITANCES TOUCHING THE DEVICE INTERNAL NODES")
    print("=" * 76)
    if not dev:
        print(f"  No unknown containing '{device_hint}' found.")
    else:
        print("  Device internal nodes:", [names[i] for i in dev])
    print()
    seen = set()
    for i in range(n):
        for j in range(i + 1, n):
            if C[i, j] == 0:
                continue
            if i in dev or j in dev:
                key = (i, j)
                if key in seen:
                    continue
                seen.add(key)
                print(f"   {names[i]:>28} -- {names[j]:<28} C = {abs(C[i,j].real):.6e} F"
                      f"  ({abs(C[i,j].real)*1e12:.3f} pF)")
    print()
    print("  ALL off-diagonal capacitances (largest to smallest):")
    allc = sorted([(abs(C[i, j].real), i, j) for i in range(n) for j in range(i + 1, n)
                   if C[i, j] != 0], reverse=True)
    for v, i, j in allc[:12]:
        print(f"   {v:.6e} F  ({v*1e12:>12.3f} pF)   {names[i]} -- {names[j]}")
    print("=" * 76)
