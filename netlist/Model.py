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

        from netlist.Circuit import Circuit

        # Choose correct small signal model library
        if param_list["type"] in ("NPN", "PNP"):
            target_model = (
                "library/small_signal_models/bipolar_models/"
                + str(bipolar_model)
                + ".json"
            )
        elif param_list["type"] in ("MOS"):
            target_model = (
                "library/small_signal_models/mosfet_models/"
                + str(mosfet_model)
                + ".json"
            )
        else:
            print(f"Failed to load model! Type: {param_list['type']} is not known!")
            return None

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
