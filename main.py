from Circuit import Circuit
from NetlistParser import NetlistParser
from Equation_Formulator_WIP import ModifiedNodalAnalysis
circuit = Circuit()

parser = NetlistParser()

parser.set_netlist_file("testNetlist.cir")
circuit = parser.parse_netlist()
circuit.to_ai_string()
print("\n\n\nThe now flattend circuit with models")
circuit.flatten()
circuit.to_ai_string()
print("\n\n\nThe flattend circuit with small signal models")
circuit.flatten(True, "/home/nils/Downloads/beispiele/gm.out")
circuit.to_ai_string()
print(circuit.getNodes())
parser.parse_element_params("/home/nils/Downloads/beispiele/gm.out")
