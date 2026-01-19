
from Circuit import Circuit
from Modified_Node_Analysis import ModifiedNodalAnalysis
from NetlistParser import NetlistParser
import Approximate as ap
import time as t

import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

circuit = Circuit()

parser = NetlistParser()

parser.set_cir_file("test_circuits/Emitteramp_deutsch.cir")
circuit = parser.parse_netlist()
circuit.to_ai_string()
print("\n\n\nThe now flattend subcircuits")
circuit.flatten()
circuit.to_ai_string()
print("\n\n\nThe flattend circuit with small signal models")
circuit.flatten(True, "test_circuits/Emitteramp_deutsch.out")
circuit.to_ai_string()
print(circuit.get_nodes())


#circuit.elements[0].connections.append("2")

mna = ModifiedNodalAnalysis(circuit)
mna.buildEquationsSystem()

estimation = mna.estimateTerms(mna.A)
print("Estimation of A matrix terms:")
print(estimation)

num_results = mna.solveNumerical(mna.value_dict)
print("Numerical Results:")
print(num_results)
print("Node map:")
print(mna.node_map)

print("Matrix:")
sp.pprint(mna.A)
print("Rechte Seite:")
sp.pprint(mna.z)

print("Unknown list:")
print(num_results)

print("\n\n\n\n\n\n")






result = mna.solve()
H = result[sp.symbols('V_2')] / result[sp.symbols('V_1')]
print("Original transfer function:")
print(H)

print("\n\n\n\n\n\n")
print("Approximation results:")
t0 = t.perf_counter_ns()
approx = ap.approximate(mna, 0.024, sp.symbols('V_1'), sp.symbols('V_2'), (1e5,), 46)
t1 = t.perf_counter_ns()
print(f"Time for approximation: {(t1 - t0) / 1e6} ms")

approx = sp.simplify(approx)

print(approx)

approx_num = approx.subs(mna.value_dict)

approx_H_lambdified = sp.lambdify(sp.symbols('s'), approx_num, 'numpy')


# --- 1. Symbolische Übertragungsfunktion definieren ---
s = sp.symbols('s')
# Beispiel: Tiefpass 1. Ordnung: H(s) = 1 / (s + 1)
H = num_results[sp.symbols('V_2') ] / num_results[sp.symbols('V_1')]

# --- 2. SymPy → numerische Funktion umwandeln ---
H_lambdified = sp.lambdify(s, H, 'numpy')
# --- 3. Frequenzachse definieren ---
w = np.logspace(-2, 10, 10000)         # Kreisfrequenz
jw = 1j * w
H_eval = H_lambdified(jw)
approx_eval = approx_H_lambdified(jw)

if np.isscalar(approx_eval):
    approx_eval = np.full_like(H_eval, approx_eval)

print("\n\n\n\n\n\n", H_eval, "\n\n\n\n\n")
# --- 4. Bode-Plot erstellen ---
fig, (ax_mag, ax_phase) = plt.subplots(2, 1, figsize=(8, 6))

# Betrag (in dB)
ax_mag.semilogx(w, 20 * np.log10(abs(H_eval)), label="Original")
ax_mag.semilogx(w, 20 * np.log10(abs(approx_eval)), 'r--', label="Approximiert")
ax_mag.set_title("Bode-Diagramm der Übertragungsfunktion")
ax_mag.set_ylabel("Betrag [dB]")
ax_mag.grid(True, which="both")
ax_mag.legend()

# Phase (in Grad)
ax_phase.semilogx(w, np.angle(H_eval, deg=True), label="Original")
ax_phase.semilogx(w, np.angle(approx_eval, deg=True), 'r--', label="Approximiert")
ax_phase.set_ylabel("Phase [°]")
ax_phase.set_xlabel("Kreisfrequenz ω [rad/s]")
ax_phase.grid(True, which="both")
ax_phase.legend()


plt.tight_layout()
plt.show()

# # --- 4. Bode-Plot mit DearPyGui ---

# # Daten vorbereiten
# freq_log = np.log10(w)
# magnitude_db = 20 * np.log10(np.abs(H_eval))
# phase_deg = np.angle(H_eval, deg=True)

# print(freq_log)
# print(magnitude_db)
# print(phase_deg)

# # DearPyGui Setup
# dpg.create_context()

# # Viewport
# with dpg.window(label="Bode-Diagramm", width=900, height=700):

#     # -------- Magnitude Plot --------
#     with dpg.plot(label="Betrag (dB)", height=300):
#         dpg.add_plot_legend()
#         dpg.add_plot_axis(dpg.mvXAxis, label="log10(ω) [rad/s]")
#         y_axis_mag = dpg.add_plot_axis(dpg.mvYAxis, label="Betrag [dB]")
#         dpg.add_line_series(
#             freq_log.tolist(),
#             magnitude_db.tolist(),
#             label="|H(jω)|",
#             parent=y_axis_mag
#         )

#     # -------- Phase Plot --------
#     with dpg.plot(label="Phase (°)", height=300, width=-1):
#         dpg.add_plot_legend()
#         dpg.add_plot_axis(dpg.mvXAxis, label="log10(ω) [rad/s]")
#         y_axis_phase = dpg.add_plot_axis(dpg.mvYAxis, label="Phase [°]")
#         dpg.add_line_series(
#             freq_log.tolist(),
#             phase_deg.tolist(),
#             label="∠H(jω)",
#             parent=y_axis_phase
#         )

# dpg.create_viewport(title="Bode Plot", width=920, height=760)
# dpg.setup_dearpygui()
# dpg.show_viewport()
# dpg.start_dearpygui()
# dpg.destroy_context()
