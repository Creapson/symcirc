from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: Optional[str] = None
    filename: str = ""
    params: Dict[str, str] = Field(default_factory=dict)

    def copy(self) -> "Model":
        return self.model_copy(deep=True)

    def add_param(self, paramSymbol: str, value):
        self.params[paramSymbol] = value

    def get_generated_subcircuit(
        self,
        element_params: Dict[str, str],
        bipolar_model: str,
        mosfet_model: str,
    ):
        # Merge model params and element params
        param_list = {k.lower(): v for k, v in (self.params | element_params).items()}

        import re

        from parser.NetlistParser import NetlistParser

        parser = NetlistParser()

        # Choose correct small signal model library
        if param_list["type"] in ("NPN", "PNP"):
            parser.set_cir_file("library/bipolar_models.lib")
            target_model = bipolar_model
        else:
            parser.set_cir_file("library/mosfet_models.lib")
            target_model = mosfet_model

        parser.pre_format()

        # Replace parameters in template
        regex = r"\b(" + "|".join(map(re.escape, param_list.keys())) + r")\b"

        new_netlist_lines = []
        for line in parser.netlist_lines:
            new_line = re.sub(
                regex,
                lambda m: str(param_list[m.group(1)]),
                line,
            )
            new_netlist_lines.append(new_line)

        parser.netlist_lines = new_netlist_lines

        # Parse generated subcircuit
        subct_start_index = parser.find_subcircuit(target_model)
        start_index, end_index, ct = parser.parse_subcircuit(subct_start_index)

        return ct

    def to_ai_string(self, indent: int):
        param_string = ", ".join(f'"{k}" -> {v}' for k, v in self.params.items())
        print("\t" * indent, self.name, self.filename, param_string)
