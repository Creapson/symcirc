from Circuit import Circuit
from Modified_Node_Analysis import ModifiedNodalAnalysis
from gui.NodeEditor import NodeEditor
from NetlistParser import NetlistParser

import sympy as sp
import numpy as np
import matplotlib.pyplot as plt
import dearpygui.dearpygui as dpg

nodeEditor = NodeEditor()
nodeEditor.start()

"""
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
results = mna.solve()
print("Matrix:")
print(mna.A)
print("Rechte Seite:")
print(mna.z)

estimation = mna.estimateTerms(mna.A)
print("Estimation of A matrix terms:")
print(estimation)

num_results = mna.solveNumerical(mna.value_dict)
print("Numerical Results:")
print(num_results)


# --- 1. Symbolische Übertragungsfunktion definieren ---
s = sp.symbols('s')
# Beispiel: Tiefpass 1. Ordnung: H(s) = 1 / (s + 1)
H = num_results[sp.symbols('V_2')] / num_results[sp.symbols('V_1')]

# --- 2. SymPy → numerische Funktion umwandeln ---
H_lambdified = sp.lambdify(s, H, 'numpy')
# --- 3. Frequenzachse definieren ---
w = np.logspace(-2, 8, 10000)         # Kreisfrequenz
jw = 1j * w
H_eval = H_lambdified(jw)

print("\n\n\n\n\n\n", H_eval, "\n\n\n\n\n")
# --- 4. Bode-Plot erstellen ---
fig, (ax_mag, ax_phase) = plt.subplots(2, 1, figsize=(8, 6))

# Betrag (in dB)
ax_mag.semilogx(w, 20 * np.log10(abs(H_eval)))
ax_mag.set_title("Bode-Diagramm der Übertragungsfunktion")
ax_mag.set_ylabel("Betrag [dB]")
ax_mag.grid(True, which="both")

# Phase (in Grad)
ax_phase.semilogx(w, np.angle(H_eval, deg=True))
ax_phase.set_ylabel("Phase [°]")
ax_phase.set_xlabel("Kreisfrequenz ω [rad/s]")
ax_phase.grid(True, which="both")

plt.tight_layout()
plt.show()

# --- 4. Bode-Plot mit DearPyGui ---

# Daten vorbereiten
freq_log = np.log10(w)
magnitude_db = 20 * np.log10(np.abs(H_eval))
phase_deg = np.angle(H_eval, deg=True)

# DearPyGui Setup
dpg.create_context()

# Viewport
with dpg.window(label="Bode-Diagramm", width=900, height=700):

    # -------- Magnitude Plot --------
    with dpg.plot(label="Betrag (dB)", height=300):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="log10(ω) [rad/s]")
        y_axis_mag = dpg.add_plot_axis(dpg.mvYAxis, label="Betrag [dB]")
        dpg.add_line_series(
            freq_log.tolist(),
            magnitude_db.tolist(),
            label="|H(jω)|",
            parent=y_axis_mag
        )

    # -------- Phase Plot --------
    with dpg.plot(label="Phase (°)", height=300, width=-1):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="log10(ω) [rad/s]")
        y_axis_phase = dpg.add_plot_axis(dpg.mvYAxis, label="Phase [°]")
        dpg.add_line_series(
            freq_log.tolist(),
            phase_deg.tolist(),
            label="∠H(jω)",
            parent=y_axis_phase
        )

dpg.create_viewport(title="Bode Plot", width=920, height=760)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
"""
