from Circuit import Circuit
from NetlistParser import NetlistParser

circuit = Circuit()

parser = NetlistParser()

parser.set_netlist_file("testNetlist.cir")
circuit = parser.parse_netlist()
print(circuit)
circuit.to_ai_string()

circuit.flatten()
circuit.to_ai_string()

circuit.flatten(True)
circuit.to_ai_string()
