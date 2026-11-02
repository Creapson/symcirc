from parser.spice.Spice import Spice
from netlist.Element import Element 
from netlist.Circuit import Circuit
from parser.spice.SpiceParser import SpiceParser
from parser.ltspice.LtspiceParser import LtspiceParser

def detect_netlist_format(file_path: str) -> str:
    try:
        text = "".join(LtspiceParser._read_text_lines(file_path)).lower()
    except (OSError, UnicodeDecodeError):
        return "pspice"

    if ("schematics netlist" in text
            or "schematics version" in text
            or ".aliases" in text
            or ".probe" in text):
        return "pspice"

    return "ltspice"

def get_circuit_from_file(file_path : str = "") -> Circuit:
    if detect_netlist_format(file_path) == "ltspice":
        parser = LtspiceParser(file_path)
    else:
        parser = SpiceParser(file_path)

    circuit = parser._parse()
    circuit.remove_unused_models()
    circuit.resolve_controlled_sources()
    return circuit

def get_element_parameters_from_outfile(file_path : str, elements: list[Element]):
    parser = SpiceParser(file_path)
    parser.parse_element_params(file_path, elements)

def get_element_parameters_from_logfile(file_path : str, elements: list[Element]):
    parser = LtspiceParser(file_path)
    parser.parse_element_params(file_path, elements)

def get_pre_format_info(file_path : str) -> list[str]:
        parser = Spice()
        parser.set_cir_file(file_path)
        return parser.pre_format()
