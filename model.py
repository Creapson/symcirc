class Model():
    name: str
    filename: str
    params: dict[str, str] = {}

    def addParam(self, paramSymbol, value):
        self.params[paramSymbol] = value

    def generateSubcircuit(self, connections, element_params, bipolar_model, mosfet_model):
        pass
