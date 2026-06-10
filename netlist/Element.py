from typing import Dict, List
from pydantic import BaseModel, ConfigDict, Field
        
import re


class Element(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = ""
    historical_name: str = ""
    symbol: str = ""
    connections: List[str] = []
    type: str = "None"
    params: Dict[str, str] = {} 

    def set_type(self, newType: str):
        self.type = newType

    def remove_type_prefix(self):
        if self.name.startswith(f"{self.type}_{self.type}"):
            self.name = self.name.removeprefix(f"{self.type}_")
        if self.name.startswith(f"{self.type}{self.type}"):
            self.name = self.name.removeprefix(self.type)

    @staticmethod
    def get_normalised_name(name: str = "") -> str:
        return re.sub(r"[,_]", ".", name)

    def get_symbol(self) -> str:
        return self.name
        # if self.symbol == "":
        #     return self.name
        # else:
        #     return self.symbol

    def get_name_reversed(self, seperator:str = ".") -> str:
        parts = self.name.split(seperator)
        reversed_parts = [parts[-1]] + parts[:-1]
        return seperator.join(reversed_parts)

    def add_param(self, paramSymbol: str, value : str):
        self.params[paramSymbol] = value

    def set_connections(self, connections: List[str]):
        self.connections = connections

    def get_connections(self) -> List[str]:
        return self.connections

    def remap_values(self, param_list: Dict[str, str]):
        # remap the str reference value to a numeric value
        # example turn "betaac" into 2e^-10
        for key, value in param_list.items():
            if self.type in ("E", "G", "F", "H"):
                value_str = "value"
            else:
                value_str = "value_dc"

            current_value = self.params.get(value_str, None)
            if current_value == key:
                self.params[value_str] = str(value)
                print(key, current_value, value)
                return

    def to_ai_string(self, indent: int):
        param_string = ", ".join(f'"{k}" -> {v}' for k, v in self.params.items())
        print("\t" * indent, self.name, self.historical_name, self.symbol, self.connections, self.type, param_string)
