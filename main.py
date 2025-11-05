from NetlistParser import NetlistParser

parser = NetlistParser()

parser.set_circuit_file("testNetlist.cir")
parser.parse_netlist()
