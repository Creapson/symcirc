import re
from Circuit import Circuit
from Element import Element
from Model import Model


class NetlistParser:
    netlist_lines = []

    def parse_netlist(self):
        """Parse the entire loaded Netlist. Load the netlist with
        NetlistParser.set_circuit_file()

        Returns:
            A Circuit with all Elements, Models and Subcircuit
        """
        self.pre_format()
        circuit = self.parse_lines()
        return circuit

    def set_netlist_file(self, file_path):
        """Set the filepath for file the will be parsed

        Args:
            file_path (str): Filepath to the netlist-File
        """
        self.file_path = file_path
        pass

    def pre_format(self):
        """Removes all Comments and empty lines from the loaded netlist"""
        # Remove Commands
        with open(self.file_path, "r") as file:
            lines = [line.strip() for line in file if not line.lstrip().startswith("*")]

        # Remove empty lines from the list
        self.netlist_lines = list(filter(None, lines))
        pass

    def print_parser_error(self, extra_string):
        """Print a error in red for a given line

        Args:
            extra_string (str): String with extra details to output
        """
        print(
            "\x1b[31m",
            "Unable to parse the following string: ",
            extra_string,
            "\x1b[0m",
        )

    def parse_lines(self, starting_index=0, end_index=None, circuit=None):
        """Parse all lines in the netlist-File

        Args:
            starting_index (int): Line-Index to start the parsing from
            end_index (int): Line-Index to end parsing at
            circuit (Cicuit): Circuit object where the Elements, Models
            and Subcircuits should be added to

        Returns:
            The fully populated Circuit
        """
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
        """Parses the element from the given string.

        Args:
            line: str representing the Elememt

        Returns:
            The parsed Element
        """
        line_splits = line.split()
        element = Element()
        # check if the element type is present twice e.g: CC32
        if len(line_splits[0]) >= 2:
            if line_splits[0][0] == line_splits[0][1]:
                # If Element Name starts with RR, CC, .. remove the first char
                element.name = line_splits[0].removeprefix(line_splits[0][0])
            element.name = line_splits[0]
        else:
            element.name = line_splits[0]

        element.set_type(line_splits[0][0])

        match line_splits[0].upper()[0]:
            # Admittance
            case "R" | "C" | "L":
                element.connections = line_splits[1:-1]
                element.add_param("value_dc", line_splits[3])
                return element

            # Sources
            case "V" | "I":
                if len(line_splits) == 4:
                    element.connections = line_splits[1:-1]
                    element.add_param("value_dc", line_splits[3])
                else:
                    self.print_parser_error("This line is too long or short!\t" + line)
                    return None
                return element

            # Controlles Sources
            case "E" | "G" | "F" | "H":
                if len(line_splits) == 6:
                    element.connections = line_splits[1:-1]
                    element.add_param("value", line_splits[5])
                else:
                    self.print_parser_error("This line is too long or short!" + line)
                return element

            # Transistors
            case "Q":
                if len(line_splits) == 5:
                    element.connections = line_splits[1:3]
                    element.add_param("ref_model", line_splits[4])
                elif len(line_splits) == 6:
                    element.connections = line_splits[1:4]
                    element.add_param("ref_model", line_splits[5])
                else:
                    element.connections = line_splits[1:4]
                    element.add_param("ref_model", line_splits[5])
                    element.add_param("area", line_splits[6])
                return element

            # Subcircuits
            case "X":
                if "PARAMS" in line:
                    self.print_parser_error("Cant parse this line! " + line)
                    return None
                element.connections = line_splits[1:-1]
                element.add_param("ref_cir", line_splits[-1])
                return element
            case _:
                self.print_parser_error(line)
                return None

    def find_subcircuit(self, subct_name):
        index = 0
        for i in range(0, len(self.netlist_lines)):
            if subct_name in self.netlist_lines[i]:
                index = i
                break
        return index

    def parse_subcircuit(self, index):
        """Searches througth the netlist to find the end of the subcircuit.
        Then it uses self.parse_lines() to parse a part of the whole file.

        Args:
            index (int): line-index where the start of the subcircuit definition startet

        Returns:
            end_index + 1: the line after the .ENDS
            ct_name: subcircuit name
            ct: independent Circuit object for this subcircuit
        """
        # Find where the subcircuit ends
        end_index = index + 1
        while not self.netlist_lines[end_index].startswith(
            (".ENDS", ".ends", ".END", ".end")
        ):
            end_index += 1
            if end_index >= len(self.netlist_lines):
                break

        # Parse only the lines inside this subcircuit, using a NEW Circuit instance
        ct = self.parse_lines(
            starting_index=index + 1, end_index=end_index, circuit=Circuit()
        )

        line_splits = self.netlist_lines[index].split()
        ct_name = line_splits[1]

        # Create a NEW Circuit object for this subcircuit
        ct.inner_connecting_nodes = line_splits[2:]

        # Return the line after the .ENDS, the name, and the subcircuit
        return end_index + 1, ct_name, ct

    def parse_model(self, index):
        """Parse the model

        Args:
            index (int): line-index there the model definiton starts

        Returns:
            index: line-index where the model definition ends
            model: Fully populated Model object
        """

        def parse_params(param_list):
            for param in param_list:
                # remove the brackets from the parameters
                param.removeprefix("(")
                param.removesuffix(")")
                param_split = param.split("=")
                model.add_param(param_split[0], param_split[1])

        # There are two different syntax for models
        # 1. .model name type (params)
        # 2. .model name
        #    + type
        #    + params ...

        line = self.netlist_lines[index]
        line_splits = line.split()
        model = Model()

        model.name = line_splits[1]

        # chech if is first Type
        if "(" in line:
            model.add_param("type", line_splits[2])
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
                model.add_param("type", "NPN")
                index += 1
                continue
            if "PNP" in param_line:
                model.add_param("type", "PNP")
                index += 1
                continue

            parse_params(param_line.split())

            if ")" in param_line:
                return index, model
            index += 1

        # return the line number where the model ends
        return index, model

    def parse_element_params(self, out_filepath, elements):
        """
        text:     the full SPICE-like dump string
        elements: list or dict of objects that have .name and .add_param(key, value)
        """
        with open(out_filepath, "r") as file:
            lines = [line.rstrip() for line in file]

        param_start_index = 0
        for line in lines:
            if "BIPOLAR JUNCTION TRANSISTORS" in line:
                param_start_index += 1
                break
            else:
                param_start_index += 1
        print(param_start_index)
        

        # Build fast lookup
        lookup = {el.name: el for el in elements}
        i = 0
        n = len(lines)

        current_names = []    # list of transistor names in the current block

        while i < n:
            line = lines[i].strip()

            # Detect "NAME Q201 Q202 ..."
            if line.startswith("NAME"):
                parts = line.split()
                current_names = parts[1:]  # all device names on that line
                row_index = 0
                i += 1
                continue

            # check if the next line start with a Word
            # This is the name of the param
            if current_names and re.match(r"^[A-Za-z0-9]+", line):
                parts = line.split()
                key = parts[0]
                values = parts[1:]

                # each value must have a element to whom
                # it belongs
                if len(values) != len(current_names):
                    # ERROR: mismatched count
                    print(f"Warning: key {key} has {len(values)} values but {len(current_names)} names.")
                else:
                    # Assign each value to the corresponding element
                    for name, raw in zip(current_names, values):

                        # convert str to float
                        try:
                            val = float(raw)
                        except ValueError:
                            val = raw

                        if name in lookup:
                            lookup[name].add_param(key, val)
                            print(f"Added {key} to {name}")
                        else:
                            print(f"Warning: element {name} not found in lookup.")

                i += 1
                continue

            # End of block or empty line resets current_names
            if line.strip() == "" or line.startswith("JOB"):
                current_names = []

            i += 1

            pass
