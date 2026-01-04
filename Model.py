class Model:
    def __init__(self):
        self.name: str
        self.filename: str = ""
        self.params: dict[str, str] = {}

   # --- COPY METHOD ---
    def copy(self) -> "Model":
        new = Model()
        new.name = self.name
        new.filename = self.filename
        new.params = dict(self.params)  # copy the dictionary
        return new

    def add_param(self, paramSymbol, value):
        self.params[paramSymbol] = value

    def get_generated_subcircuit(self, element_params, bipolar_model, mosfet_model):

        # convert all params to lowercase
        param_list = {k.lower(): v for k, v in (self.params | element_params).items()}

        import re

        from NetlistParser import NetlistParser

        parser = NetlistParser()

        # chose the correct small signal model
        # todo for those types: NPN, PNP, LPNP, D, ...
        if param_list["type"] == "NPN":
            parser.set_cir_file("library/bipolar_models.lib")
        else:
            parser.set_cir_file("library/mosfet_models.lib")
        parser.pre_format()

        # loop over all lines and replace the param_name with
        # the respecting value
        new_netlist_lines = []
        regex = r"\b(" + "|".join(map(re.escape, param_list.keys())) + r")\b"
        for line in parser.netlist_lines:
            new_line = re.sub(regex, lambda m: str(param_list[m.group(1)]), line)
            new_netlist_lines.append(new_line)
        parser.netlist_lines = new_netlist_lines

        # parse the replaced subcircuit normaly
        subct_start_index = parser.find_subcircuit(bipolar_model)
        start_index, end_index, ct = parser.parse_subcircuit(subct_start_index)
        return ct

    def to_ai_string(self, indent):
        param_string = ", ".join(f'"{k}" -> {v}' for k, v in self.params.items())
        print("\t" * indent, self.name, self.filename, param_string)
        return
