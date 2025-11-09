from Circuit import Circuit
from Element import Element
from Model import Model


class NetlistParser:
    netlist_lines = []

    def parse_netlist(self):
        self.pre_format()
        circuit = self.parse_lines()
        return circuit

    def set_circuit_file(self, file_path):
        self.file_path = file_path
        pass

    def pre_format(self):
        # Remove Commands
        with open(self.file_path, "r") as file:
            lines = [line.strip() for line in file if not line.lstrip().startswith("*")]

        # Remove empty lines from the list
        self.netlist_lines = list(filter(None, lines))
        pass

    def print_parser_error(self, extra_string):
        print(
            "\x1b[31m",
            "Unable to parse the following string: ",
            extra_string,
            "\x1b[0m",
        )

    def parse_lines(self, starting_index=0, end_index=None, circuit=None):
        # Recognice what this line does(e.x descripe element or subcircuit)
        # and call the acording functions
        if circuit is None:
            circuit = Circuit()
        if end_index is None:
            end_index = len(self.netlist_lines)
        index = starting_index
        while index < end_index:
            line = self.netlist_lines[index]
            if line.startswith("."):
                # chech if subcircuit is starting
                if line.startswith((".SUBCKT", ".subckt")):
                    index, ct_name, sub_ct = self.parse_subcircuit(index)
                    circuit.addSubcircuit(ct_name, sub_ct)
                    continue

                # check if a model declaration is starting
                if line.startswith((".model", ".MODEL")):
                    index, model = self.parse_model(index)
                    circuit.addModel(model)
                    index += 1
                    continue

                # output currently not parsable lines
                self.print_parser_error(line)
            else:
                element = self.parse_element(line)
                circuit.addElement(element)
            index += 1
        return circuit

    def parse_element(self, line: str):
        line_splits = line.split(" ")
        element = Element()
        # check if the element type is present twice e.g: CC32
        if len(line_splits[0]) >= 2:
            if line_splits[0][0] == line_splits[0][1]:
                # If Element Name starts with RR, CC, .. remove the first char
                element.name = line_splits[0].removeprefix(line_splits[0][0])
            element.name = line_splits[0]
        else:
            element.name = line_splits[0]

        element.setType(line_splits[0][0])

        match line_splits[0].upper()[0]:
            # Admittance
            case "R" | "C" | "L":
                element.connections = line_splits[1:-1]
                element.addParam("value_dc", line_splits[3])
                return element

            # Sources
            case "V" | "I":
                if len(line_splits) == 4:
                    element.connections = line_splits[1:-1]
                    element.addParam("value_dc", line_splits[3])
                else:
                    self.print_parser_error("This line is too long or short!\t" + line)
                    return None
                return element

            # Controlles Sources
            case "E" | "G" | "F" | "H":
                if len(line_splits) == 6:
                    element.connections = line_splits[1:-1]
                    element.addParam("value", line_splits[5])
                else:
                    self.print_parser_error("This line is too long or short!" + line)
                return element

            # Transistors
            case "Q":
                if len(line_splits) == 5:
                    element.connections = line_splits[1:3]
                    element.addParam("ref_model", line_splits[4])
                elif len(line_splits) == 6:
                    element.connections = line_splits[1:4]
                    element.addParam("ref_model", line_splits[5])
                else:
                    element.connections = line_splits[1:4]
                    element.addParam("ref_model", line_splits[5])
                    element.addParam("area", line_splits[6])
                return element

            # Subcircuits
            case "X":
                element.connections = line_splits[1:-1]
                return element
            case _:
                self.print_parser_error(line)
                return None

    def parse_subcircuit(self, index):
        """
        Parse a subcircuit definition in the netlist.
        Returns:
            end_index + 1: the line after the .ENDS
            ct_name: subcircuit name
            ct: independent Circuit object for this subcircuit
        """
        # Find where the subcircuit ends
        end_index = index + 1
        while not self.netlist_lines[end_index].startswith((".ENDS", ".ends")):
            end_index += 1

        # Parse only the lines inside this subcircuit, using a NEW Circuit instance
        ct = self.parse_lines(
            starting_index=index + 1, end_index=end_index, circuit=Circuit()
        )

        line_splits = self.netlist_lines[index].split()
        ct_name = line_splits[1]

        # Create a NEW Circuit object for this subcircuit
        ct.outer_connecting_nodes = line_splits[2:]

        # Return the line after the .ENDS, the name, and the subcircuit
        return end_index + 1, ct_name, ct

    def parse_model(self, index):
        def parse_params(param_list):
            for param in param_list:
                # remove the brackets from the parameters
                param.removeprefix("(")
                param.removesuffix(")")
                param_split = param.split("=")
                model.addParam(param_split[0], param_split[1])

        # There are two different syntax for models
        # 1. .model name type (params)
        # 2. .model name
        #    + type
        #    + params ...

        line = self.netlist_lines[index]
        line_splits = line.split(" ")
        model = Model()

        model.name = line_splits[1]

        # chech if is first Type
        if "(" in line:
            model.addParam("type", line_splits[2])
            parse_params(line_splits[3:])

        # If a ')' is in this line all params are parsed
        if ")" in line:
            return index, model

        # Check for params after the model name
        index += 1
        # Loop over all lines with "+" at the start
        while index < len(self.netlist_lines) - 1:
            if not self.netlist_lines[index].strip().startswith("+"):
                return index, model

            # parse the model Parameters
            param_line = self.netlist_lines[index].removeprefix("+").strip()
            if "NPN" in param_line:
                model.addParam("type", "NPN")
                index += 1
                continue
            if "PNP" in param_line:
                model.addParam("type", "PNP")
                index += 1
                continue

            parse_params(param_line.split(" "))

            if ")" in param_line:
                return index, model
            index += 1

        # return the line number where the model ends
        return index, model
