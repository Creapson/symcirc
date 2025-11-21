from typing import List

from Element import Element
from Model import Model


class Circuit:
    def __init__(self):
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

    def flatten_subcircuit(
        self, subcircuit_name, element_name, subct_element_connections
    ):
        if len(self.subcircuits) == 0:
            return
        subct = self.subcircuits[subcircuit_name]
        subct_connections = subct.inner_connecting_nodes

        # If this node is in connection use the nodeID of the root circuit
        def new_nodeIDs(nodeID):
            seperator = "_"

            new_IDs = []
            for node in nodeID:
                if node == "0":
                    new_IDs.append("0")
                if node in subct_connections:
                    position = subct.inner_connecting_nodes.index(node)
                    new_IDs.append(subct_element_connections[position])
                else:
                    new_IDs.append(subcircuit_name + seperator + node)
            # if list is empty
            return new_IDs

        subct_elements = []
        for element in subct.elements:
            element_connections = element.connections
            new_ele_connections = new_nodeIDs(element_connections)
            new_ele = element.copy()
            new_ele.name = element_name + "_" + new_ele.name
            new_ele.connections = new_ele_connections
            subct_elements.append(new_ele)
            pass
        for model in subct.models:
            self.addModel(model)
        return subct_elements

    def flatten(self, flatten_models=False):
        # Make sure all circuits are already flattend
        for name, subct in self.subcircuits.items():
            subct.flatten()

        new_elements = []
        for element in self.elements:
            if element.type == "X" and not flatten_models:
                element_connections = element.connections
                subcircuit_name = element.params["ref_cir"]
                subct_elements = self.flatten_subcircuit(
                    subcircuit_name, element.name, element_connections
                )
                new_elements += subct_elements
                continue

            # Create a subcircuit for each element where this is needed
            # then flatten those normaly
            # there are other models like D
            if element.type == "Q" and flatten_models:
                # create subcircuit with params for each element
                # then flatten those subcircuits
                model_name = element.params["ref_model"]
                model = self.models[model_name]
                subct_name = element.name + "_" + model_name
                model_subct = model.get_generated_subcircuit(element.params)
                self.addSubcircuit(subct_name, model_subct)
                subct_elements = self.flatten_subcircuit(
                    subct_name, element.name, element.connections
                )
                new_elements += subct_elements

                continue

            new_elements.append(element)

        # every subcircuit has been flattend. no need to store them
        # anymore
        self.subcircuits = {}
        self.elements = new_elements

    def to_ai_string(self, indent=0):
        # currently a placeholder for debuging
        # print inner connecting nodes
        print("\t" * indent + "Connectionss:", self.inner_connecting_nodes)

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
