class Model:
    name: str
    filename: str = ""
    params: dict[str, str] = {}

    def addParam(self, paramSymbol, value):
        self.params[paramSymbol] = value

    def generateSubcircuit(
        self, connections, element_params, bipolar_model, mosfet_model
    ):
        pass

    def to_ai_string(self):
        param_string = ", ".join(f'"{k}" -> {v}' for k, v in self.params.items())
        print(self.name, self.filename, param_string)
        return
