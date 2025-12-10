from Circuit import Circuit
from Equation_Formulator import ModifiedNodalAnalysis
from gui.NodeEditor import NodeEditor
from NetlistParser import NetlistParser

#nodeEditor = NodeEditor()
#nodeEditor.start()

circuit = Circuit()

parser = NetlistParser()

parser.set_netlist_file("test_circuits/testNetlist.cir")
circuit = parser.parse_netlist()
circuit.to_ai_string()
print("\n\n\nThe now flattend circuit with models")
circuit.flatten()
circuit.to_ai_string()
print("\n\n\nThe flattend circuit with small signal models")
circuit.flatten(True, "test_circuits/gm.out")
circuit.to_ai_string()
print(circuit.getNodes())


#circuit.elements[0].connections.append("2")

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
