from copy import deepcopy
import time as t
from netlist.Circuit import Circuit
<<<<<<< HEAD
from Modified_Node_Analysis import ModifiedNodalAnalysis
from Sparse_Tableau_Extended import SparseTableau
=======
from analysis_methoden.Modified_Node_Analysis import ModifiedNodalAnalysis
>>>>>>> 10542b174aa42979f296c9c931ef1079639efa8f
from parser.NetlistParser import get_circuit_from_file
from Approximate import Approximation 
import tracemalloc
import sympy as sp
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import ApproximateEigenvalue as ae
import compress_matrix as cm


circuit = Circuit()

circuit = get_circuit_from_file("test_circuits/Basisschaltung_2N2222.cir")
circuit.to_ai_string()
print("\n\n\nThe now flattend subcircuits")
circuit.flatten()
circuit.to_ai_string()

print("\n\n\nThe flattend circuit with small signal models")
circuit.flatten(True, "test_circuits/Basisschaltung_2N2222.out")
circuit.elements = [
    element
    for element in circuit.elements
    if element.type.upper() != "Q"
]
circuit.to_ai_string()
print(circuit.get_nodes())







mna = ModifiedNodalAnalysis(circuit)
mna.buildEquationsSystem()

st = SparseTableau(circuit)
st.buildEquationsSystem()



s = sp.Symbol("s")



print("\n compressing matrix:")
print(st.unknowns)

mna_compressed = deepcopy(mna)

T_compressed_num, rhs_comressed_num, new_indice, mna_compressed.A, mna_compressed.z, mna_compressed.unknowns = cm.CompressMatrix(st.T, st.get_unknowns(), st.RHS, list(st.get_unknowns()).index(sp.Symbol("V_ua")), st.value_dict, True)



ap = Approximation(mna_compressed)



result_ap = ap.approximate("V_ua", ((1e5, 0.14),), "block", 2.0, "max", 5)


print("Result: ")
print(sp.simplify(result_ap.solve("V_ua")))


print("Eigenwertberechnung für die Matrix A(s):")

eigenvalues, S, W, Q, Z = ae.get_eigenvalues(st.T.subs(st.value_dict), s)

print(eigenvalues)

# print("\n\n\nLeft eigenvector: ")


# v = ae.left_eigenvector_from_qz(S, T, eigenvalues[3], 3, Q)

# print(v)

# print("\n\n\nRight eigenvector: ")

# u = ae.right_eigenvector_from_qz(S, T, eigenvalues[3], 3, Z)

# print(u)

# print("\n\n\nModal Assurance Criterion:")

# mac = ae.modal_assurance_criterion(u, v)

# print(mac)






# T = deepcopy(mna.A)



# A0_sym = T.subs(s, 0)

# B_sym = -T.diff(s)


# A0_num = A0_sym.subs(mna.value_dict)
# B_num = B_sym.subs(mna.value_dict)

# lambda_test, y, residual_norm, iteration = ae.JacobiCorrection(A0_num, 
#                      B_num, 
#                      -67531278.0, 
#                      u, 
#                      u, 
#                      v, 
#                      10e-8, 
#                      0.98, 
#                      10)

# print("\n\n\nThe corrected eigenvalue is:")
# print(lambda_test)
# print("\n\n\nThe corrected right eigenvector is:")
# print(y)
# print("\n\n\nThe residual norm is:")
# print(residual_norm)
# print("\n\n\nThe number of iterations is:")
# print(iteration)

# print("\n\n\nModal Assurance Criterion:")

# mac = ae.modal_assurance_criterion(y, u)

# print(mac)

f = list(np.logspace(1, 9, 1000))

sols = st.solveNumerical(f, "V_ua")
# print("\n\n\nThe solution is:")
# print(sols)

fig, (ax_mag, ax_phase) = plt.subplots(2, 1, sharex=True, figsize=(8, 6))

ax_mag.semilogx(f, 20 * np.log10(np.abs(sols)))
ax_mag.set_ylabel("Magnitude [dB]")
ax_mag.grid(True, which="both", linestyle="--")
ax_mag.set_title("Bode Plot")

ax_phase.semilogx(f, np.angle(sols, deg=True))
ax_phase.set_xlabel("Frequency [rad/s]")
ax_phase.set_ylabel("Phase [degrees]")
ax_phase.grid(True, which="both", linestyle="--")

plt.tight_layout()
#plt.show()



info, ranking, determinant, roots= ae.eigenvalue_term_ranking(st.T, s, st, 6, 0.1, 10e-8, 0.98, 3, "relative", "norm", 3, True)



print("\n\n\nDeterminante:")
print(sp.simplify(determinant))


print("\n\n\nWurzeln:")
print(roots)

print("\nWurzeln numerisch:")
for root in roots:
    print(root.subs(st.value_dict))


# print("\n compressing matrix:")
#print(list(mna.get_unknowns()))
# T_compressed_num, rhs_comressed_num, new_indice, T_compressed_sym, rhs_compressed_sym, unknowns_compressed = cm.CompressMatrix(st.T, st.unknowns, st.RHS, 35, st.value_dict, True)

# print("\n\n\nThe compressed matrix is:")
# print(T_compressed_sym)

# print("result ")

# result = st.T.LUsolve(st.RHS)#T_compressed_sym.LUsolve(rhs_compressed_sym)

# print(sp.simplify(result[new_indice]))


