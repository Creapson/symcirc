from Element import Element
from Model import Model


class NetlistParser:
    netlist_lines = []

    def parse_netlist(self):
        self.pre_format()
        self.parse_lines()
        pass

    def set_circuit_file(self, file_path):
        self.file_path = file_path
        pass

    def pre_format(self):
        # Remove Commands
        with open(self.file_path, "r") as file:
            lines = [line.strip() for line in file if not line.lstrip().startswith("*")]

        # Remove empty lines from the list
        self.netlist_lines = list(filter(None, lines))
        print(self.netlist_lines)
        print("Num of lines: ", len(self.netlist_lines))
        pass

    def parse_lines(self):
        # Recognice what this line does(e.x descripe element or subcircuit)
        # and call the acording functions
        index = 0
        while index < len(self.netlist_lines):
            line = self.netlist_lines[index]
            if line.startswith("."):
                print(line)
                if line.startswith((".SUBCKT", ".subckt")):
                    index = self.parse_subcircuit(index)
                    continue
                if line.startswith((".model", ".MODEL")):
                    print("Model Found")
                    index = self.parse_model(index + 1)
                    continue
                print(
                    "\x1b[31m",
                    "Unable to parse the following string: ",
                    line,
                    "\x1b[0m",
                )
            else:
                self.parse_element(line)
            index += 1

    def parse_element(self, line: str):
        line_splits = line.split(" ")
        element = Element()
        if line_splits[0][0] == line_splits[0][1]:
            # If Element Name starts with RR, CC, .. remove the first char
            element.name = line_splits[0].removeprefix(line_splits[0][0])
        else:
            element.name = line_splits[0]

        element.setType(line_splits[0][0])

        match line_splits[0].upper()[0]:
            # Admittance
            case "R" | "C" | "L":
                element.connections = {line_splits[1], line_splits[2]}
                element.addParam("value_dc", line_splits[3])
                element.to_ai_string()
                return

            # Sources
            case "V" | "I":
                element.connections = {line_splits[1], line_splits[2]}
                element.addParam("value_dc", line_splits[3])
                element.to_ai_string()
                return

            # Controlles Sources
            case "E" | "G" | "F" | "H":
                return

            # Transistors
            case "Q":
                element.connections = {
                    line_splits[1],
                    line_splits[2],
                    line_splits[3],
                    line_splits[4],
                }
                element.addParam("ref_model", line_splits[5])
                element.addParam("area", line_splits[6])
                element.to_ai_string()
                return

            # Subcircuits
            case "X":
                return

    def parse_subcircuit(self, index):
        print("subcircuit found")
        while not self.netlist_lines[index].startswith(".ENDS"):
            # Add recursive logic here
            index += 1

        # Return the line number where the subcircuit ends
        return index + 1

    def parse_model(self, index):
        line_splits = self.netlist_lines[index].split(" ")
        model = Model()
        model.name = line_splits[1]
        while index < len(self.netlist_lines) - 1:
            if not self.netlist_lines[index].startswith("+"):
                return index + 1

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

            # split params in the current line
            for param in param_line.split(" "):
                param_split = param.split("=")
                model.addParam(param_split[0], param_split[1])

            index += 1

        model.to_ai_string()
        # return the line number where the model ends
        return index + 1
