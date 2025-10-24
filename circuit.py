from typing import List

from element import Element
from model import Model

class Circuit():
    outer_connecting_nodes: List[str] = []
    inner_connecting_nodes: List[str] = []

    nodes: List[str] = []

    models: dict[str, Model] = {}
    elements: List[Element] = []

    subcircuits: List["Circuit"] = []
    
    def getNodes(self):
        return self.nodes.copy()


    def addNode(self, nodeID, alias):
        # if node doesnt exist add it
        if self.nodes.__contains__(nodeID) is False:
            self.nodes.append(nodeID)


    def addModel(self, model):
        model_name = model.name

        # Load subcircuit from library files before importing in dict
        #model.loadSubct()
        
        self.models[model_name] = model

    def addElement(self, element):
        self.elements.append(element)

    def addSubcircuit(self, subCt):
        pass

    def changeNodeID(self, nodeOld, nodeNew):
        pass

    def _addListOfElements(self, elementList):
        pass

    def flatten(self, bipolar_model, mosfet_model, depth):  # noqa: C901, PLR0912, PLR0915
        pass
