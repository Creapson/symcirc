import numpy as np

from typing import List

from netlist.Circuit import Circuit
from netlist.Element import Element
from netlist.Model import Model


class Spice:
    netlist_lines: list[str] = []
    netlist_lines_source: list[str] = []
    file_path: str = ""
    def parse_netlist(self) -> Circuit:
        """Parse the entire loaded Netlist. Load the netlist with
        NetlistParser.set_circuit_file()

        Returns:
            A Circuit with all Elements, Models and Subcircuit
        """
        self.pre_format()
        circuit = self.parse_lines()
        return circuit

    def set_cir_file(self, file_path : str):
        """Set the filepath for file the will be parsed

        Args:
            file_path (str): Filepath to the netlist-File
        """
        self.file_path = file_path
        pass

    def print_parser_error(self, extra_string : str, index:int = 0):
        """Print a error in red for a given line

        Args:
            extra_string (str): String with extra details to output
        """
        if index == 0:
            print(
                "\x1b[31m",
                "Unable to parse the following string: ",
                extra_string,
                "\x1b[0m",
            )
        else:
            print(
                "\x1b[31m",
                "Unable to parse the following string: ",
                extra_string,
                "\tFrom file:",
                self.netlist_lines_source[index],
                "\x1b[0m",
            )


    def pre_format(self) -> list[str]:
        """Removes all Comments and empty lines from the loaded netlist"""
        feedback = []
        # Remove Commands
        with open(self.file_path, "r") as file:
            lines = [line.strip() for line in file if not line.lstrip().startswith("*")]

        # Remove empty lines from the list
        self.netlist_lines = list(filter(None, lines))
        self.netlist_lines_source = [f"{self.file_path}_{x}]" for x in range(len(self.netlist_lines))]

        # resolve missing includes / librarys
        index = 0
        end_index = len(self.netlist_lines)
        while index < end_index:
            line = self.netlist_lines[index]
            if line.startswith((".inc", ".INC")):
                feedback.append(self.parse_inc(index))
                end_index = len(self.netlist_lines)
                index += 1
                continue

            if line.startswith((".lib", ".LIB")):
                feedback.append(self.parse_lib(index))
                end_index = len(self.netlist_lines)
                index += 1
                continue
            index += 1

        return feedback

    def parse_lines(self, starting_index : int=0, end_index : int=0, circuit : Circuit | None = None) -> Circuit:
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
        if end_index == 0:
            end_index = len(self.netlist_lines)
        index = starting_index
        while index < end_index:
            line = self.netlist_lines[index]
            try:
                if line.startswith("."):

                    # start of subcircuit definition
                    if line.startswith((".SUBCKT", ".subckt")):
                        index, ct_name, sub_ct = self.parse_subcircuit(index)
                        circuit.add_subcircuit(ct_name, sub_ct)
                        continue

                    # start of model definition
                    if line.startswith((".model", ".MODEL")):
                        index, model = self.parse_model(index)
                        if model is not None:
                            circuit.add_model(model)
                        continue

                    if line.startswith((".AC", ".ac")): 
                        log_space = self.parse_sweep(index)
                        circuit.add_param("sweep", log_space)
                        index += 1 
                        continue

                    if line.lower().startswith((".inc", ".lib")):
                        index += 1 
                        continue

                    # output currently not parsable lines
                    self.print_parser_error(line, index)

                # skip those lines
                elif line.startswith("+"):
                    index += 1
                    continue

                else:
                    element, index = self.parse_element(index, circuit)
                    if element is not None:
                        circuit.add_element(element)
                index += 1

            except:
                self.print_parser_error("Unable to parse the following string: " + line, index)
                index += 1

        return circuit 

    def to_spice_num(self, val : str) -> float:
        factors = {'k': 1e3, 'meg': 1e6, 'g': 1e9, 'm': 1e-3, 'u': 1e-6, 'n': 1e-9}
        val = val.lower()
        for suffix, multiplier in factors.items():
            if val.endswith(suffix):
                return float(val.replace(suffix, '')) * multiplier
        return float(val)

    def parse_sweep(self, index : int) -> str: 

        line_splits = self.netlist_lines[index].split()
        sweep_type = line_splits[1]

        num_of_points = int(self.to_spice_num(line_splits[2]))

        match sweep_type:
            case "LIN" | "DEC" | "OCT": 
                start = self.to_spice_num(line_splits[3])
                stop = self.to_spice_num(line_splits[4])
                return sweep_type + " " + str(num_of_points) + " " + str(start) + " " + str(stop)

            case "POI": 
                points_of_interest = [str(self.to_spice_num(point)) for point in line_splits[3:]]
                return sweep_type + " ".join(points_of_interest)

            case _:
                return ""

    def parse_inc(self, index: int) -> str:
        line_splits = self.netlist_lines[index].split()
        # try leading the file
        file_path = line_splits[1].replace('"', "")

        if file_path.endswith(".als"): return ""

        import os

        dir_path = os.path.dirname(self.file_path)
        new_file_path = os.path.join(dir_path, file_path)

        lines = []
        try:
            with open(new_file_path, "r") as file:
                lines = [
                    line.strip() for line in file if not line.lstrip().startswith("*")
                ]
                # Remove empty lines from the list
                include_lines = list(filter(None, lines))
                include_line_source = [new_file_path for x in range(len(include_lines))]
                # squeeze the includes lines into the main line array
                self.netlist_lines = (
                    self.netlist_lines[:index]
                    + include_lines
                    + self.netlist_lines[index + 1 :]
                )
                self.netlist_lines_source = (
                    self.netlist_lines_source[:index]
                    + include_line_source
                    + self.netlist_lines_source[index + 1 :]
                )

            print(f"Succesfully loaded {file_path}!")
            return ""
        except FileNotFoundError:
            return f"The file: {file_path} could not be found!\n"

    def parse_lib(self, index: int) -> str:
        line_splits = self.netlist_lines[index].split()
        # try leading the file
        file_path = line_splits[1].replace('"', "")

        import os

        dir_path = os.path.dirname(self.file_path)
        new_file_path = os.path.join(dir_path, file_path)

        lines = []
        try:
            with open(new_file_path, "r") as file:
                lines = [
                    line.strip() for line in file if not line.lstrip().startswith("*")
                ]
                # Remove empty lines from the list
                include_lines = list(filter(None, lines))
                include_line_source = [new_file_path for x in range(len(include_lines))]

                # squeeze the includes lines into the main line array
                self.netlist_lines = (
                    self.netlist_lines[:index]
                    + include_lines
                    + self.netlist_lines[index + 1 :]
                )

                self.netlist_lines_source = (
                    self.netlist_lines_source[:index]
                    + include_line_source
                    + self.netlist_lines_source[index + 1 :]
                )

            print(f"Succesfully loaded {file_path}!")
            return ""
        except FileNotFoundError:
            return f"The file: {file_path} could not be found!\n"
        except PermissionError:
            return f"Unable to open the file {file_path}!\n"

    def parse_element(self, index:int, circuit : Circuit) -> tuple[Element, int]:
        """Parses the element from the given string.

        Args:
            line: str representing the Element

        Returns:
            The parsed Element
        """
        line = self.netlist_lines[index]
        line_splits = line.split()
        element = Element()

        element.set_type(line_splits[0].upper()[0])

        element.name = line_splits[0]
        element.remove_type_prefix()


        match element.type:
            # Admittance
            case "R" | "C" | "L" | "D":
                return self.parse_admittance(element, index)

            # Sources
            case "V" | "I":
                return self.parse_souces(element, index)


            # Controlles Sources
            case "E" | "G" | "F" | "H":
                return self.parse_controlled_sources(element, index, circuit)

            # Transistors
            case "Q" | "M":
                return self.parse_transistor(element, index)

            # Subcircuits
            case "X":
                return self.parse_subcircuit_element(element, index)

            case _:
                self.print_parser_error(line, index)
                return (Element(), index)

    def parse_admittance(self, element : Element, index:int) -> tuple[Element, int]:
        line_splits = self.netlist_lines[index].split()
        element.connections = line_splits[1:-1]
        element.add_param("value_dc", line_splits[3])
        return element, index

    def parse_souces(self, element : Element, index:int) -> tuple[Element, int]:
        line_splits = self.netlist_lines[index].split()
        if len(line_splits) == 4:
            element.connections = line_splits[1:-1]
            element.add_param("value_dc", line_splits[3])
        elif len(line_splits) > 4:
            element.connections = line_splits[1:3]

            # parse all values from this token
            def parse_token(index, token_str):
                token_list = ["DC", "AC", "SIN(", "SIN", "PULSE", "EXP", "SFFM"]
                token_list.remove(token_str)
                param_token_str = "value_" + token_str.lower()
                value = ""
                index += 1
                while (
                    index < len(line_splits)
                    and line_splits[index].upper() not in token_list
                ):
                    value += line_splits[index]
                    index += 1
                element.add_param(param_token_str, value)
                return index

            i = 3
            while i < len(line_splits):
                token = line_splits[i].upper()

                if token == "DC":
                    i = parse_token(i, "DC")
                    continue

                elif token == "AC":
                    i = parse_token(i, "AC")
                    continue

                elif token.startswith("SIN"):
                    i += 1
                    continue

                elif token == "PULSE":
                    i += 1
                    continue

                elif token == "EXP":
                    i += 1
                    continue

                elif token == "SFFM":
                    i += 1
                    continue

                else:
                    i += 1
        return (element, index)

    def parse_controlled_sources(self, element : Element, index, circuit : Circuit) -> tuple[Element, int]:
        line_splits = self.netlist_lines[index].split()

        if len(line_splits) == 6:
            element.connections = line_splits[1:-1]
            element.add_param("value", line_splits[5])

        # Special Case connctions refernces another element
        elif len(line_splits) == 5:
            ref_element = circuit.get_element(line_splits[3])
            if ref_element is None:
                self.print_parser_error("Could not find Element to resolve the connections: " + str(self.netlist_lines[index]), index)
                return (element, index)

            element.connections = line_splits[1:-2] + ref_element.connections
            element.add_param("value", line_splits[4])
        else:
            self.print_parser_error("This line is too long or short! " + str(self.netlist_lines[index]), index)
        return (element, index)

    def parse_transistor(self, element : Element, index: int) -> tuple[Element, int]:
        def parse_params(param_list: List[str], element: Element):
            for param in param_list:
                param = param.removeprefix("(")
                param = param.removesuffix(")")

                if "=" in param:
                    key, val = param.split("=", 1)
                    element.add_param(key.upper(), val)

        line_splits = self.netlist_lines[index].split()
        if len(line_splits) == 5:
            element.connections = line_splits[1:4]
            element.add_param("ref_model", line_splits[4])
        elif len(line_splits) == 6:
            element.connections = line_splits[1:5]
            element.add_param("ref_model", line_splits[5])
        else:
            element.connections = line_splits[1:5]
            element.add_param("ref_model", line_splits[5])
            element.add_param("area", line_splits[6])

        # check for aditional parameter
        while index < len(self.netlist_lines) - 2:
            if not self.netlist_lines[index+1].strip().startswith("+"):
                return (element, index)

            # parse the model Parameters
            param_line = self.netlist_lines[index+1].removeprefix("+").strip()
            parse_params(param_line.split(), element)

            index += 1

        return (element, index)

    def parse_subcircuit_element(self, element : Element, index:int) -> tuple[Element, int]:
        line_splits = self.netlist_lines[index].split()
        # find param start
        params_index = None
        for i, tok in enumerate(line_splits):
            if tok.startswith("PARAMS:"):
                params_index = i
                break

        # without PARAMS
        if params_index is None:
            element.connections = line_splits[1:-1]
            element.add_param("ref_cir", line_splits[-1])
            return (element, index)

        # with PARAMS
        element.connections = line_splits[1 : params_index - 1]
        element.add_param("ref_cir", line_splits[params_index - 1])

        # parse params
        params = line_splits[params_index][len("PARAMS:") :]
        for p in params.split():
            key, val = p.split("=")
            element.add_param(key.lower(), val)

        return (element, index)


    def find_subcircuit(self, subct_name : str) -> int:
        index = 0
        for i in range(0, len(self.netlist_lines)):
            if subct_name in self.netlist_lines[i]:
                index = i
                break
        return index

    def parse_subcircuit(self, index : int) -> tuple[int , str, Circuit]:
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
        ct.name = ct_name

        # Create a NEW Circuit object for this subcircuit
        ct.inner_connecting_nodes = line_splits[2:]

        # Return the line after the .ENDS, the name, and the subcircuit
        return end_index + 1, ct_name, ct

    def parse_model(self, index : int) -> tuple[int, Model | None]:
        def parse_params(param_list: List[str], model: Model):
            for param in param_list:
                param = param.removeprefix("(")
                param = param.removesuffix(")")

                if "NPN" in param:
                    model.add_param("type", "NPN")
                if "PNP" in param:
                    model.add_param("type", "PNP")

                if "=" in param:
                    key, val = param.split("=", 1)
                    model.add_param(key.upper(), val)

        # 1. .model name type (params)
        # 1. .model name type (param
        #    + ...
        #    + param=value param=value)
        # 2. .model name
        #    + type
        #    + params ...
        # 3. .model name type param=value
        #    + param=value param=value

        line = self.netlist_lines[index]
        line_splits = line.split()

        model = Model()


        model.name = line_splits[1]
        match len(line_splits):
            # 2nd Type
            case 2:
                pass
            case 3:
                model.add_param("type", line_splits[2])
            case _ if len(line_splits) > 3:
                model.add_param("type", line_splits[2])
                parse_params(line_splits[3:], model)
            case _:
                self.print_parser_error(f"Failed to parse this Model: {line}\t", index)
                return index, None

        if ")" in line:
            index += 1
            return index, model

        index += 1
        # Check for params after the model name
        # Loop over all lines with "+" at the start
        while index < len(self.netlist_lines) - 1:
            if not self.netlist_lines[index].strip().startswith("+"):
                return index, model

            # parse the model Parameters
            param_line = self.netlist_lines[index].removeprefix("+").strip()
            parse_params(param_line.split(), model)

            index += 1

        return index, model

    def parse_element_params(self, out_filepath : str, elements : list[Element]):
        """
        text:     the full SPICE-like dump string
        elements: list of elements
        """

        import re
        def normalize_name(name: str) -> str:
            """
            Normalize element names so different separators map to the same key.
            Examples:
                X1.Q1  -> X1.Q1
                X1_Q1  -> X1.Q1
                X1,Q1  -> X1.Q1
            """

            # Replace any separator with a dot
            name = re.sub(r"[,_]", ".", name)

            type:str = name[0]
            # remove type_prefix
            if name.startswith(f"{type}.{type}"):
                name = name.removeprefix(f"{type}.")
            if name.startswith(f"{type}{type}"):
                name = name.removeprefix(type)

            return name.strip()

        with open(out_filepath, "r") as file:
            lines = [line.rstrip() for line in file]

        param_start_index = 0
        for line in lines:
            if any(
                s in line
                for s in ("BIPOLAR JUNCTION TRANSISTORS", "BJT MODEL PARAMETERS")
            ):
                param_start_index += 1
                break
            else:
                param_start_index += 1

        # Build fast lookup
        lookup = {normalize_name(el.historical_name): el for el in elements}
        i = 0
        n = len(lines)

        current_names = []  # list of transistor names in the current block

        while i < n:
            line = lines[i].strip()

            # Detect "NAME Q201 Q202 ..."
            if line.startswith("NAME"):
                parts = line.split()
                # all device names on that line
                current_names = [normalize_name(n) for n in parts[1:]]
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
                    print(
                        f"Warning: key {key} has {len(values)} values but {
                            len(current_names)
                        } names."
                    )
                else:
                    # Assign each value to the corresponding element
                    for name, raw in zip(current_names, values):
                        # convert str to float
                        try:
                            val = float(raw)
                        except ValueError:
                            val = raw

                        if name in lookup:
                            lookup[name].add_param(key, str(val))
                        else:
                            print(f"Warning: element {name} not found in lookup.")

                i += 1
                continue

            # End of block or empty line resets current_names
            if line.strip() == "" or line.startswith("JOB"):
                current_names = []

            i += 1
