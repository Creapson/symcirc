from __future__ import annotations

from typing import Dict, List
from pathlib import Path

from netlist.Circuit import Circuit
from netlist.Element import Element
from netlist.Model import Model


# Inspired by https://github.com/PySpice-org/PySpice/blob/master/PySpice/Spice/Parser.py

class SpiceParser:
    def __init__(self, path:str = "") -> None:
        self._path = str(Path(path).resolve()) if path else "" 
        self._raw_lines: List[str] = []
        self._libs: List[str] = []
        self.feedback: List[str] = []

        # self.lines
        if self._path:
            try:
                with open(self._path, 'r') as f:
                    self._raw_lines = f.readlines()
            except:
                self.feedback.append(f"Could not load file: {self._path}")
                print(f"Could not load file: {self._path}")

        self._add_includes()

        formatted_lines: List[str] = self._format_lines(self._raw_lines)
        self.lines: List[Line] = self._merge_lines(formatted_lines)

    def _add_includes(self):
        for idx, line in enumerate(self._raw_lines):
            if line.lower().startswith(".inc"):
                new_file_path = ""
                try:
                    import os
                    path = line.split()[1].strip("\"")
                    if path.endswith(".als"): return
                    dir_path = os.path.dirname(self._path)
                    new_file_path = os.path.join(dir_path, path)

                    inc_lines: List[str] = []
                    if path is not None:
                        with open(str(new_file_path), 'r') as f:
                            inc_lines = f.readlines()
                    self._raw_lines = (
                        self._raw_lines[:idx]
                        + inc_lines
                        + self._raw_lines[idx + 1 :]
                    )
                except:
                    self.feedback.append(f"Could not load file {new_file_path}")
                    print(Exception)

            if line.lower().startswith(".lib"):
                try:
                    import os
                    lib_path = line.split()[1].strip("\"")
                    # Convert relative library paths to absolute right away
                    if not os.path.isabs(lib_path):
                        lib_path = os.path.join(os.path.dirname(self._path), lib_path)
                    self._libs.append(lib_path)

                    self._libs.append(line.split()[1].strip("\""))
                except:
                    self.feedback.append(f"Could not get path from lib: {line}")
                    print(Exception)

    def _format_lines(self, raw_lines: list[str]):
        lines = [line.strip() for line in raw_lines if not line.lstrip().startswith("*")]
        return lines

    def _merge_lines(self, raw_lines: list[str]) -> List[Line]:
        lines = []
        current_line: Line = Line()
        for line_string in raw_lines:

            if line_string.startswith('+'):
                current_line.append(line_string[1:].strip('\r\n'))
            else:
                if line_string:
                    line = Line(line_string)
                    lines.append(line)
                    current_line = line

        # for line in lines:
        #     print(line._text)
        return lines

    def _parse(self) -> Circuit:
        base_circuit: Circuit = Circuit()
        tmp_subct: Circuit = Circuit()
        _scope = base_circuit

        used_models: List[str] = []
        used_subckts: List[str] = []

        for line in self.lines:
            line_str = line._text.lower()
            if line_str.startswith("."):

                if line_str.startswith(".ends"):
                    base_circuit.add_subcircuit(tmp_subct)
                    _scope = base_circuit

                if line_str.startswith(".subckt"):
                    tmp_subct = self._parse_subct(line)
                    tmp_subct.name = line.tokens[1]
                    _scope = tmp_subct
                    pass

                if line_str.startswith(".model"):
                    model = self._parse_model(line)
                    _scope.add_model(model)

                if line_str.startswith(".lib"):
                    pass

                if line_str.startswith(".inc"):
                    pass

                if line_str.startswith(".ac"):
                    log_space = self._parse_sweep(line)
                    _scope.add_param("sweep", log_space)
                    print("Added sweep")

                pass
            else:
                element = self._parse_element(line)
                _scope.add_element(element)
                if _scope == base_circuit:
                    if element.type in ("Q", "M"):
                        used_models.append(element.params.get("ref_model", ""))
                    if element.type == "X":
                        used_subckts.append(element.params.get("ref_cir", ""))

        # get all missing models and subckt from the libs
        for lib in self._libs:
            subcts: Dict[str, Circuit] = {}
            models: Dict[str, Model] = {}
            try:
                parser = SpiceParser(lib)
                lib_ct = parser._parse()
                subcts = lib_ct.get_subcircuits()
                models = lib_ct.get_models()
            except Exception as error:
                print(error.with_traceback(None))
                print(f"Could not parse lib: {lib}")

            for model_name in used_models:
                if model_name in models:
                    base_circuit.add_model(models.get(model_name, Model()))

            for subct_name in used_subckts:
                if subct_name in subcts:
                    base_circuit.add_subcircuit(subcts.get(subct_name, Circuit()))

        # base_circuit.to_ai_string()
        return base_circuit

    def _parse_element(self, line: Line) -> Element:
        """Parses the element from the given string.

        Args:
            line: str representing the Element

        Returns:
            The parsed Element
        """
        element: Element = Element()

        name = line.tokens[0]

        ele_type = name[0]
        element.set_type(ele_type)

        element.name = name
        element.historical_name = name
        element.remove_type_prefix()

        match element.type:
            # Admittance
            case "R" | "C" | "L" | "D":
                element.set_connections(line.tokens[1:-1])
                element.add_param("value_dc", line.tokens[-1])

            # Sources
            case "V" | "I":
                if line.token_cnd == 4:
                    element.set_connections(line.tokens[1:-1])
                    element.add_param("value_dc", line.tokens[-1])
                elif line.token_cnd > 4:
                    element.set_connections(line.tokens[1:3])

                    # parse all values from this token
                    def parse_token(index, token_str):
                        token_list = ["DC", "AC", "SIN(", "SIN", "PULSE", "EXP", "SFFM"]
                        token_list.remove(token_str)
                        param_token_str = "value_" + token_str.lower()
                        value = ""
                        index += 1
                        while (
                            index < line.token_cnd
                            and not line.tokens[index].upper().startswith(tuple(token_list))
                        ):
                            value += line.tokens[index]
                            index += 1
                        element.add_param(param_token_str, value)
                        return index

                    i = 3
                    while i < len(line.tokens):
                        token = line.tokens[i].upper()

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


            # Controlles Sources
            case "E" | "G" | "F" | "H":
                if line.token_cnd == 6:
                    element.set_connections(line.tokens[1:-1])
                    element.add_param("value", line.tokens[-1])

            # Transistors
            case "Q" | "M":
                if line.token_cnd <= 6:
                    element.set_connections(line.tokens[1:-1])
                    element.add_param("ref_model", line.tokens[-1])
                else:
                    element.set_connections(line.tokens[1:5])
                    element.add_param("ref_model", line.tokens[5])
                    element.add_param("area", line.tokens[6])
                
                # add params
                param_str = " ".join(line.tokens[7:])
                element.params.update(line.get_kwargs(param_str))

            # Subcircuits
            case "X":
                element.set_connections(line.tokens[1:-1])
                element.add_param("ref_cir", line.tokens[-1])
                # Fixme Subcircuits can have Params "PARAMS:"

            case _:
                return Element()

        return element

    def _parse_model(self, line: Line) -> Model:
        model: Model = Model()

        text = line.right_of('.model').strip()
        import re
        mtch = re.match("\s*([^ \t]+)\s*([^ \t(]+)(.*)", text)

        model.name = mtch[1]
        model.type = mtch[2]
        params = mtch[3]
        params = params.strip('() ')
        model.params = Line.get_kwargs(params)

        return model

    def _parse_subct(self, line: Line) -> Circuit:
        return Circuit()

    def to_spice_num(self, val : str) -> float:
        val = val.lower()
        val = val.removesuffix("hz")

        factors = {
            "t": 1e12,
            "meg": 1e6,
            "g": 1e9,
            "k": 1e3,
            "m": 1e-3,
            "u": 1e-6,
            "uf": 1e-6,
            "n": 1e-9,
            "p": 1e-12,
            "f": 1e-15
        }

        for suffix, multiplier in factors.items():
            if val.endswith(suffix):
                return float(val.replace(suffix, '')) * multiplier
        return float(val)

    def _parse_sweep(self, line: Line) -> str: 

        line_splits = line.tokens
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

    # this function needs cleanup
    def parse_element_params(self, out_filepath : str, elements : list[Element], is_bipol: bool = True):
        """
        text:     the full SPICE-like dump string
        elements: list of elements
        """
        def _parse_param_block(start_idx: int, elements: List[Element]):
            lookup = {(Element.get_normalised_name(el.historical_name)): el for el in elements}
            cur_names = []  # list of transistor names in the current block
            i = start_idx
            while i < n:
                line = lines[i].strip()

                # Detect "NAME Q201 Q202 ..."
                if line.startswith("NAME"):
                    parts = line.split()
                    cur_names = [Element.get_normalised_name(n) for n in parts[1:]]
                    i += 1
                    continue

                # check if the next line start with a Word
                # This is the name of the param
                if cur_names and re.match(r"^[A-Za-z0-9]+", line):
                    parts = line.split()
                    key = parts[0]
                    values = parts[1:]
                    if len(values) == len(cur_names):
                        for name, raw in zip(cur_names, values):
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

                if line.strip() == "" or line.startswith("JOB"):
                    cur_names = []

                i += 1

        import re

        with open(out_filepath, "r") as file:
            lines = [line.rstrip() for line in file]

        idx = 0
        bipol_param_start_index = 0
        mosfet_param_start_index = 0
        for line in lines:
            if "BIPOLAR JUNCTION TRANSISTORS" in line:
                bipol_param_start_index = idx
            elif "MOSFET" in line:
                mosfet_param_start_index = idx
            else:
                idx += 1

        # Build fast lookup
        

        if is_bipol:
            i = bipol_param_start_index
        else:
            i = mosfet_param_start_index
        n = len(lines)

        _parse_param_block(bipol_param_start_index, elements)
        _parse_param_block(mosfet_param_start_index, elements)

class Line:
    def __init__(self, line:str = "") -> None:
        self._text = line.strip()
        self.tokens = self._text.split()
        self.token_cnd = len(self.tokens)
    
    def append(self, line:str):
        self._text += " " + line

    def right_of(self, text):
        return self._text[len(text):].strip()

    @staticmethod
    def get_kwargs(text:str) -> Dict[str, str]:
        text = text.strip(" ;()")
        dict_parameters = {}

        parts = []
        for part in text.split():
            if '=' in part and part != '=':
                left, right = [x for x in part.split('=')]
                parts.append(left)
                parts.append('=')
                if right:
                    parts.append(right)
            else:
                parts.append(part)

        i = 0
        i_stop = len(parts)
        while i < i_stop:
            if i + 1 < i_stop and parts[i + 1] == '=':
                key, value = parts[i], parts[i + 2]
                dict_parameters[key] = value
                i += 3
            else:
                # print("Bad kwarg: {}".format(text))
                i += 3

        return dict_parameters
