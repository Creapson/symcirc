import time as t

import matplotlib.pyplot as plt
import numpy as np
import sympy as sp

from Approximate import Approximation
from Modified_Node_Analysis import ModifiedNodalAnalysis
from netlist.Circuit import Circuit
from parser.NetlistParser import NetlistParser

circuit = Circuit()

parser = NetlistParser()

parser.set_cir_file("library/mosfet_models.lib")
circuit = parser.parse_netlist()
print(circuit.model_dump())
for name, subct in circuit.subcircuits.items():
    print(subct.model_dump())

circuit.to_ai_string()
print("\n\n\nThe now flattend subcircuits")
circuit.flatten()
circuit.to_ai_string()
print("\n\n\nThe flattend circuit with small signal models")
circuit.flatten(True, "test_circuits/labor10.out")
circuit.to_ai_string()
print(circuit.get_nodes())


mna = ModifiedNodalAnalysis(circuit)
mna.buildEquationsSystem()
row_sums = [sum(mna.A.row(i)) for i in range(mna.A.rows)]
print(row_sums)

mna_numerical = mna.toNumerical(mna.A, mna.value_dict)
mna_numerical = mna_numerical.subs(sp.symbols("s"), 1).evalf()

# sp.pprint(mna.A)


rank = np.linalg.matrix_rank(np.array(mna_numerical.tolist(), dtype=float))
print("Rank of the numerical A matrix:", rank, "out of", mna.A.rows)


x_syms = list(mna.get_unknowns())
print("Unknowns:")
print(x_syms)
idx_in = x_syms.index(sp.symbols("V_1"))
idx_out = x_syms.index(sp.symbols("V_3"))
w = np.logspace(-2, 9, 10000)

H_lambdified = mna.solveNumerical(mna.value_dict, w, idx_out)


print("\n\n\n\n\n\n")

# result = mna.solve()
# print("Symbolic result for V_10:")
# print(result)
# H = result[sp.symbols("V_10")] / result[sp.symbols("V_1")]
# print("Original transfer function:")
# print(H)

# H_numerical = H.subs(mna.value_dict)

# H_lambdified = sp.lambdify(sp.symbols("s"), H_numerical, "numpy")

print("\n\n\n\n\n\n")
print("Approximation results:")
ap = Approximation(mna)
t0 = t.perf_counter_ns()
# approximate(self, in_var, out_var, points/errors, term_removal_method, tolerance (tbt- rel_error; block - jmp_threshold), sorting_criterion, sorting_extra_var(column - col_num))
approx = ap.approximate(
    sp.symbols("V_1"), sp.symbols("V_3"), ((1e5, 0.05),), "tbt", 0.1, "max", 1
)
t1 = t.perf_counter_ns()
print(f"Time for approximation: {(t1 - t0) / 1e6} ms")
approx = sp.simplify(approx)

print(approx)

approx_num = approx.subs(mna.value_dict)

approx_H_lambdified = sp.lambdify(sp.symbols("s"), approx_num, "numpy")


# --- 1. Symbolische Übertragungsfunktion definieren ---
s = sp.symbols("s")
# Beispiel: Tiefpass 1. Ordnung: H(s) = 1 / (s + 1)


# --- 2. SymPy → numerische Funktion umwandeln ---

# --- 3. Frequenzachse definieren ---
# Kreisfrequenz
w = np.logspace(-2, 10, 10000)
jw = 1j * w

approx_eval = approx_H_lambdified(jw)

if np.isscalar(approx_eval):
    approx_eval = np.full_like(H_lambdified, approx_eval)

# print("\n\n\n\n\n\n", H_lambdified, "\n\n\n\n\n")
# --- 4. Bode-Plot erstellen ---
fig, (ax_mag, ax_phase) = plt.subplots(2, 1, figsize=(8, 6))

# Betrag (in dB)
ax_mag.semilogx(w, 20 * np.log10(abs(H_lambdified)), label="Original")
ax_mag.semilogx(w, 20 * np.log10(abs(approx_eval)), "r--", label="Approximiert")
ax_mag.set_title("Bode-Diagramm der Übertragungsfunktion")
ax_mag.set_ylabel("Betrag [dB]")
ax_mag.grid(True, which="both")
ax_mag.legend()

# Phase (in Grad)
ax_phase.semilogx(w, np.angle(H_lambdified, deg=True), label="Original")
ax_phase.semilogx(w, np.angle(approx_eval, deg=True), "r--", label="Approximiert")
ax_phase.set_ylabel("Phase [°]")
ax_phase.set_xlabel("Kreisfrequenz ω [rad/s]")
ax_phase.grid(True, which="both")
ax_phase.legend()


plt.tight_layout()
plt.show()
