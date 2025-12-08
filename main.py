from Circuit import Circuit
from NetlistParser import NetlistParser
from Equation_Formulator import ModifiedNodalAnalysis
circuit = Circuit()

parser = NetlistParser()

parser.set_netlist_file("testNetlist.cir")
circuit = parser.parse_netlist()
circuit.to_ai_string()
print("\n\n\nThe now flattend circuit with models")
circuit.flatten()
circuit.to_ai_string()
print("\n\n\nThe flattend circuit with small signal models")
circuit.flatten(True, "gm.out")
circuit.to_ai_string()
print(circuit.getNodes())

circuit.elements[0].connections.append("2")

mna = ModifiedNodalAnalysis(circuit)
mna.buildEquationsSystem()
results = mna.solve()
print("Results:")
print(results)

estimation = mna.estimateTerms(mna.A)
print("Estimation of A matrix terms:")
print(estimation)

num_results = mna.solveNumerical(mna.value_dict)
print("Numerical Results:")
print(num_results)