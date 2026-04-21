import time as t


from netlist.Circuit import Circuit
from Modified_Node_Analysis import ModifiedNodalAnalysis
from parser.NetlistParser import get_circuit_from_file
from Approximate import Approximation 
import time as t

import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

circuit = Circuit()

circuit = get_circuit_from_file("test_circuits/Conrad2st.cir")
circuit.to_ai_string()
print("\n\n\nThe now flattend subcircuits")
circuit.flatten()
circuit.to_ai_string()
print("\n\n\nThe flattend circuit with small signal models")
circuit.flatten(True, "test_circuits/Conrad2st.out")
circuit.to_ai_string()
print(circuit.get_nodes())



mna = ModifiedNodalAnalysis(circuit)
mna.buildEquationsSystem()



x_syms = list(mna.get_unknowns())
print("Unknowns:")
print(x_syms)
idx_in = x_syms.index(sp.symbols("V_1"))
idx_out = x_syms.index(sp.symbols("V_10"))
f = np.logspace(0, 7, 800)

H_lambdified = mna.solveNumerical(mna.value_dict, f, idx_out, idx_in)


print("\n\n\n\n\n\n")

result = mna.solve()
# print("Symbolic result for V_10:")
# print(result)
H = result[sp.symbols("V_10")] / result[sp.symbols("V_1")]
print("Original transfer function:")
#print(H)

# H_numerical = H.subs(mna.value_dict)

# H_lambdified = sp.lambdify(sp.symbols("s"), H_numerical, "numpy")

print("\n\n\n\n\n\n")
print("Approximation results:")
ap = Approximation(mna)
print("Available elimination methods:", ap.get_Elimination_Methods())
print("Available sorting methods:", ap.get_Sorting_Methods())
t0 = t.perf_counter_ns()
#approximate(self, in_var, out_var, points/errors, term_removal_method, tolerance (tbt- rel_error; block - jmp_threshold), sorting_criterion, sorting_extra_var(column - col_num))
approx = ap.approximate(sp.symbols('V_1'), sp.symbols('V_10'), ((1e5,0.05),), "term-by-term",0.6, "max", 1)
t1 = t.perf_counter_ns()
print(f"Time for approximation: {(t1 - t0) / 1e6} ms")

approx_H_lambdified = approx.solveNumerical(mna.value_dict, f, idx_out, idx_in)






# --- 1. Symbolische Übertragungsfunktion definieren ---
s = sp.symbols("s")
# Beispiel: Tiefpass 1. Ordnung: H(s) = 1 / (s + 1)




# --- 2. SymPy → numerische Funktion umwandeln ---

# --- 3. Frequenzachse definieren ---
  # Kreisfrequenz
# w = np.logspace(-2, 10, 10000)
# jw = 1j * 2* np.pi* f

# approx_eval = approx_H_lambdified(jw)


# if np.isscalar(approx_eval):
#     approx_eval = np.full_like(H_lambdified, approx_eval)

#print("\n\n\n\n\n\n", H_lambdified, "\n\n\n\n\n")
# --- 4. Bode-Plot erstellen ---
fig, (ax_mag, ax_phase) = plt.subplots(2, 1, figsize=(8, 6))

# Betrag (in dB)
ax_mag.semilogx(f, abs(H_lambdified), label="Original")
ax_mag.semilogx(f, abs(approx_H_lambdified), "r--", label="Approximiert")
ax_mag.set_title("Bode-Diagramm der Übertragungsfunktion")
ax_mag.set_ylabel("Betrag [dB]")
ax_mag.grid(True, which="both")
ax_mag.legend()

# Phase (in Grad)
ax_phase.semilogx(f, np.angle(H_lambdified, deg=True), label="Original")
ax_phase.semilogx(f, np.angle(approx_H_lambdified, deg=True), "r--", label="Approximiert")
ax_phase.set_ylabel("Phase [°]")
ax_phase.set_xlabel("Kreisfrequenz ω [rad/s]")
ax_phase.grid(True, which="both")
ax_phase.legend()


plt.tight_layout()
plt.show()
