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
        self.elements.append(element)

    def addSubcircuit(self, circuitName, circuit):
        self.subcircuits[circuitName] = circuit

    def changeNodeID(self, nodeOld, nodeNew):
        pass

    def _addListOfElements(self, elementList):
        pass

    def flatten(self, bipolar_model, mosfet_model, depth):
        pass

    def to_ai_string(self):
        # currently a placeholder for debuging

        # print inner connecting nodes
        print("Connectionss:", self.outer_connecting_nodes)

        # print all elements
        print("Elements in Circuit")
        for element in self.elements:
            element.to_ai_string()

        # print all models
        if self.models:
            print("Models in Circuit")
            for name, model in self.models.items():
                print(name)
                model.to_ai_string()

        # print all subcircuits
        if self.subcircuits:  # only runs if there is at least one subcircuit
            print("Subcircuit in Circuit")
            for name, sub_ct in self.subcircuits.items():
                print(name)
                sub_ct.to_ai_string()
