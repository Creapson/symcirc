from typing import List


class Element:
    name: str
    connections: List[str] = {}
    type: str
    params: dict[str, str] = {}

    def setType(self, newType: str):
        self.type = newType

    def addParam(self, paramSymbol, value):
        self.params[paramSymbol] = value

    def setConnections(self, connections):
        self.connections = connections

    def getConnections(self):
        return self.connections

    def to_ai_string(self):
        # All value_* und Symbolic_* müssen zusammen behandelt werden.
        param_string = ", ".join(f'"{k}" -> {v}' for k, v in self.params.items())
        print(self.name, self.connections, self.type, param_string)
        return

    # {"V1", {"1", "2"}, Type -> VoltageSource, Value -> {AC -> 1., DC | Transient -> 0}, Symbolic -> {AC -> V1}}
