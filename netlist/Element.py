from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Element(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: Optional[str] = None
    connections: List[str] = Field(default_factory=list)
    type: Optional[str] = None
    params: Dict[str, str] = Field(default_factory=dict)

    def set_type(self, newType: str):
        self.type = newType

    def add_param(self, paramSymbol: str, value):
        self.params[paramSymbol] = value

    def set_connections(self, connections: List[str]):
        self.connections = connections

    def get_connections(self) -> List[str]:
        return self.connections

    def to_ai_string(self, indent: int):
        param_string = ", ".join(f'"{k}" -> {v}' for k, v in self.params.items())
        print("\t" * indent, self.name, self.connections, self.type, param_string)

    def copy(self) -> "Element":
        return self.model_copy(deep=True)
