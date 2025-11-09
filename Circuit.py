from typing import List

from Element import Element
from Model import Model


class Circuit:
    def __init__(self):
        self.outer_connecting_nodes: List[str] = []
        self.inner_connecting_nodes: List[str] = []

        self.nodes: List[str] = []

        self.elements: List[Element] = []

        self.models: dict[str, Model] = {}
        self.subcircuits: dict[str, "Circuit"] = {}

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
        if element is not None:
            self.elements.append(element)

    def addSubcircuit(self, circuitName, circuit):
        self.subcircuits[circuitName] = circuit

    def changeNodeID(self, nodeOld, nodeNew):
        pass

    def _addListOfElements(self, elementList):
        pass

    def flatten(self, bipolar_model, mosfet_model, depth):
        pass

    def to_ai_string(self, indent=0):
        # currently a placeholder for debuging
        # print inner connecting nodes
        print("\t" * indent + "Connectionss:", self.outer_connecting_nodes)

        # print all elements
        print("\t" * indent + "Elements in Circuit")
        for element in self.elements:
            element.to_ai_string(indent + 1)

        # print all models
        if self.models:
            print("\t" * indent + "Models in Circuit")
            for name, model in self.models.items():
                print("\t" * (indent + 1) + name)
                model.to_ai_string(indent + 1)

        # print all subcircuits
        if self.subcircuits:  # only runs if there is at least one subcircuit
            print("\t" * indent + "Subcircuit in Circuit")
            for name, sub_ct in self.subcircuits.items():
                print("\t" * indent + "Name of the subcircuit", name)
                sub_ct.to_ai_string(indent + 1)
