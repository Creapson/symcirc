from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Element(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: Optional[str] = None
    symbol: Optional[str] = None
    connections: List[str] = Field(default_factory=list)
    type: Optional[str] = None
    params: Dict[str, str] = Field(default_factory=dict)

    def set_type(self, newType: str):
        self.type = newType

    def get_symbol(self) -> str:
        if self.symbol is None:
            return self.name
        else:
            return self.symbol

    def add_param(self, paramSymbol: str, value):
        self.params[paramSymbol] = value

    def set_connections(self, connections: List[str]):
        self.connections = connections

    def get_connections(self) -> List[str]:
        return self.connections

    def remap_values(self, param_list: Dict[str, str]):
        # remap the str reference value to a numeric value
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
        print("\t" * indent, self.name, self.connections, self.type, param_string)

    def copy(self) -> "Element":
        return self.model_copy(deep=True)
