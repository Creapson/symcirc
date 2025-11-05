from typing import List

from Element import Element
from Model import Model


class Circuit:
    outer_connecting_nodes: List[str] = []
    inner_connecting_nodes: List[str] = []

    nodes: List[str] = []

    elements: List[Element] = []

    models: dict[str, Model] = {}
    subcircuits: dict[str, "Circuit"] = {}

    def getNodes(self):
        return self.nodes.copy()

    def addNode(self, nodeID, alias):
        # if node doesnt exist add it
        if self.nodes.__contains__(nodeID) is False:
            self.nodes.append(nodeID)

    def addModel(self, model):
        model_name = model.name
        self.models[model_name] = model

    def addElement(self, element):
        self.elements.append(element)

    def addSubcircuit(self, circuitName, circuit):
        self.subcircuits[circuitName] = circuit

    def changeNodeID(self, nodeOld, nodeNew):
        pass

    def _addListOfElements(self, elementList):
        pass

    def flatten(self, bipolar_model, mosfet_model, depth):  # noqa: C901, PLR0912, PLR0915
        pass
