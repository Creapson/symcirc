from __future__ import annotations
from typing import Dict, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict
import os
from pathlib import Path

if TYPE_CHECKING:
    from netlist.Circuit import Circuit


class Model(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = ""
    filename: str = ""
    params: Dict[str, str] = {} 

    def add_param(self, paramSymbol: str, value):
        self.params[paramSymbol] = value

    def get_generated_subcircuit(
        self,
        element_params: Dict[str, str],
        bipolar_model: str,
        mosfet_model: str,
    ) -> Circuit | None:
        # Merge model params and element params
        param_list = {k.lower(): v for k, v in (self.params | element_params).items()}

        from netlist.Circuit import Circuit

        current_file_dir = Path(__file__).resolve().parent
        project_root = current_file_dir.parent

        # 3. Choose correct small signal model library sub-path
        if param_list["type"] in ("NPN", "PNP"):
            sub_path = Path("library/small_signal_models/bipolar_models") / f"{bipolar_model}.json"
        elif param_list["type"] in ("MOS", "NMOS"):
            sub_path = Path("library/small_signal_models/mosfet_models") / f"{mosfet_model}.json"
        else:
            print(f"Failed to load model! Type: {param_list['type']} is not known!")
            return None

        target_model = project_root / sub_path

        # load small signal model from library
        with open(target_model, "r", encoding="utf-8") as f:
            json_string = f.read()
        circuit = Circuit.model_validate_json(json_string)

        # replace the str in the value slot with the numeric values
        for element in circuit.elements:
            element.remap_values(param_list)

        return circuit

    def to_ai_string(self, indent: int):
        param_string = ", ".join(f'"{k}" -> {v}' for k, v in self.params.items())
        print("\t" * indent, self.name, self.filename, param_string)
