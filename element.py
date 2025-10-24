from typing import List

class Element():
    name : str
    connections: List[str] = {}
    type: str
    params: dict[str, str] = {}

    def setType(self, newType):
        self.type = newType

    def addParam(self, paramSymbol, value):
        self.params[paramSymbol] = value

    def setConnections(self, connections):
        self.connections = connections

    def getConnections(self):
        return self.connections