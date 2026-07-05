from parser.spice.Spice import Spice
from netlist.Element import Element 
from netlist.Circuit import Circuit
from parser.spice.SpiceParser import SpiceParser

def get_circuit_from_file(file_path : str = "") -> Circuit:
    # add logic to check what file format the file has

    # only type suported is PSpice
    # spice_parser = Spice()
    # spice_parser.set_cir_file(file_path)
    # circuit = spice_parser.parse_netlist()
    spice_parser = SpiceParser(file_path)
    circuit = spice_parser._parse()
    circuit.remove_unused_models()
    circuit.resolve_controlled_sources()
    return circuit

def get_element_parameters_from_outfile(file_path : str, elements: list[Element]): 
    parser = SpiceParser(file_path)
    parser.parse_element_params(file_path, elements)

def get_pre_format_info(file_path : str) -> list[str]:
        parser = Spice()
        parser.set_cir_file(file_path)
        return parser.pre_format()
