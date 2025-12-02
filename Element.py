from typing import List


class Element:
    def __init__(self):
        self.name: str = ""
        self.connections: List[str] = []
        self.type: str = ""
        self.params: dict[str, str] = {}

    def set_type(self, newType: str):
        self.type = newType

    def add_param(self, paramSymbol, value):
        self.params[paramSymbol] = value

    def set_connections(self, connections):
        self.connections = connections

    def get_connections(self):
        return self.connections

    def to_ai_string(self, indent):
        # All value_* und Symbolic_* müssen zusammen behandelt werden.
        param_string = ", ".join(f'"{k}" -> {v}' for k, v in self.params.items())
        print("\t" * indent, self.name, self.connections, self.type, param_string)
        return

    # --- COPY CONSTRUCTOR ---
    def copy(self) -> "Element":
        new = Element()
        new.name = self.name
        new.type = self.type
        new.connections = list(self.connections)  # copy list
        new.params = dict(self.params)  # copy dict
        return new

    # {"V1", {"1", "2"}, Type -> VoltageSource, Value -> {AC -> 1., DC | Transient -> 0}, Symbolic -> {AC -> V1}}
