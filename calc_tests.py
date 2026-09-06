import time as t


from netlist.Circuit import Circuit
from analysis_methoden.Modified_Node_Analysis import ModifiedNodalAnalysis
from parser.NetlistParser import get_circuit_from_file
from Approximate import Approximation 
import time as t

import sympy as sp
import sympy.physics.control.lti as tf
import numpy as np
import matplotlib.pyplot as plt

circuit = Circuit()

circuit = get_circuit_from_file("test_circuits/Emitteramp_deutsch.cir")
circuit.to_ai_string()
print("\n\n\nThe now flattend subcircuits")
circuit.flatten()
circuit.to_ai_string()

print("\n\n\nThe flattend circuit with small signal models")
circuit.flatten(True, "test_circuits/Emitteramp_deutsch.out")
circuit.to_ai_string()
print(circuit.get_nodes())

#x = input("Do you want to flatten the circuit with small signal models? (y/n): ")



mna = ModifiedNodalAnalysis(circuit)
mna.buildEquationsSystem()

sp.pprint(mna.A[0, :])

x_syms = list(mna.get_unknowns())
print("Unknowns:")
print(x_syms)
#idx_in = x_syms.index(sp.symbols("V_1"))
idx_out = x_syms.index(sp.symbols("V_3"))
f = np.logspace(0, 4, 400)


print("\n\n\n\n\n\n Value dict:\n")
sp.pprint(mna.value_dict)


H_lambdified = mna.solveNumerical(f, "V_3")


print("\n\n\n\n\n\n")

result = mna.solve("V_3") / mna.solve("V_1")
result = result.simplify()
print("Symbolic result for V_2:")
print(result)

numerator, denominator = sp.together(result).as_numer_denom()

print("\n\n\n\n\n\n")
#print("Degree of the numerator:", sp.degree(numerator, sp.symbols("s")))
print("\n")
#print("Degree of the denominator:", sp.degree(denominator, sp.symbols("s")))

numerator = numerator.subs(mna.value_dict)
denominator = denominator.subs(mna.value_dict)

print("\n\n\n\n\n\n")
print("Poles of the transfer function:")

print(sp.solve(denominator, sp.symbols("s")))

print("Zeros of the transfer function:")


print(sp.solve(numerator, sp.symbols("s")))


print("Original transfer function:")
#print(result)

# H_numerical = sp.lambdify(sp.symbols("s"), result.subs(mna.value_dict), "numpy")

# H_lambdified = np.array([H_numerical(1j * 2*np.pi *freq) for freq in f])

# print("\n\n\n\n\n\n")
# print("Approximation results:")
# ap = Approximation(mna)
# print("Available elimination methods:", ap.get_Elimination_Methods())
# print("Available sorting methods:", ap.get_Sorting_Methods())
# t0 = t.perf_counter_ns()
# #approximate(self, in_var, out_var, points/errors, term_removal_method, tolerance (tbt- rel_error; block - jmp_threshold), sorting_criterion, sorting_extra_var(column - col_num))
# approx = ap.approximate('V_2', ((1e5,0.1),(1e8,0.1)), "term-by-term",0.6, "max", 1)
# t1 = t.perf_counter_ns()
# print(f"Time for approximation: {(t1 - t0) / 1e6} ms")

# approx_H_lambdified = approx.solveNumerical(f, "V_3")

# approx_result = approx.solve("V_3") / approx.solve("V_1")
# print("Symbolic result for V_2:")
# print(approx_result.simplify())
# print("\n Numerical result for V_2:")
# print(approx_result.subs(mna.value_dict).simplify())

# print("\n\n\n\n\n\n")


# numerator, denominator = sp.together(approx_result).as_numer_denom()

# #numerator = numerator.subs(mna.value_dict)
# #denominator = denominator.subs(mna.value_dict)

# print("\n\n\n\n\n\n")
# print("Poles of the transfer function:")

# print(sp.solve(denominator.subs(mna.value_dict), sp.symbols("s")))

# print("Zeros of the transfer function:")


# print(sp.solve(numerator.subs(mna.value_dict), sp.symbols("s")))





# --- 1. Symbolische Übertragungsfunktion definieren ---
s = sp.symbols("s")

# --- 4. Bode-Plot erstellen ---
fig, (ax_mag, ax_phase) = plt.subplots(2, 1, figsize=(8, 6))

# Betrag (in dB)
ax_mag.semilogx(f, 20*np.log10(np.abs(H_lambdified)), label="Original") #
#ax_mag.semilogx(f, 20*np.log10(np.abs(approx_H_lambdified)), "r--", label="Approximiert")
ax_mag.set_title("Bode-Diagramm der Übertragungsfunktion")
ax_mag.set_ylabel("Betrag [dB]")
ax_mag.grid(True, which="both")
ax_mag.legend()

# Phase (in Grad)
ax_phase.semilogx(f, np.unwrap(np.angle(H_lambdified, deg=True), axis=0).flatten(), label="Original")
#ax_phase.semilogx(f, np.unwrap(np.angle(approx_H_lambdified, deg=True), axis=0).flatten(), "r--", label="Approximiert")
ax_phase.set_ylabel("Phase [°]")
ax_phase.set_xlabel("Kreisfrequenz ω [rad/s]")
ax_phase.grid(True, which="both")
ax_phase.legend()


plt.tight_layout()
plt.show()
