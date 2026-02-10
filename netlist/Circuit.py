from typing import List

from netlist.Element import Element
from netlist.Model import Model


class Circuit:
    def __init__(self):
        self.name = ""
        self.netlist_file_path = ""

        self.inner_connecting_nodes: List[str] = []

        self.bipolar_model = "beta_with_r_be_G"
        self.mosfet_model = "BSIM"

        self.nodes: List[str] = []

        self.elements: List[Element] = []

        self.models: dict[str, Model] = {}
        self.subcircuits: dict[str, "Circuit"] = {}

        self.separator = "."

    # --- COPY METHOD ---
    def copy(self) -> "Circuit":
        new = Circuit()
        new.name = self.name
        new.netlist_file_path = self.netlist_file_path

        new.inner_connecting_nodes = list(self.inner_connecting_nodes)
        new.bipolar_model = self.bipolar_model
        new.mosfet_model = self.mosfet_model
        new.nodes = list(self.nodes)

        # Copy elements
        new.elements = [element.copy() for element in self.elements]

        # Copy models (Model class must have a copy method)
        new.models = {name: model.copy() for name, model in self.models.items()}

        # Copy subcircuits recursively
        new.subcircuits = {
            name: sub_ct.copy() for name, sub_ct in self.subcircuits.items()
        }

        new.separator = self.separator
        return new

    def set_name(self, name):
        self.name = name

    def set_netlist_path(self, path):
        self.netlist_file_path = path

    def set_separator(self, separator):
        self.separator = separator

    def set_bipolar_model(self, new_model):
        self.bipolar_model = new_model

        # apply this to all elements
        for element in self.elements:
            if element.type == "Q":
                element.add_param("bipolar_model", self.bipolar_model)

    def set_mosfet_model(self, new_model):
        self.mosfet_model = new_model

        # apply this to all elements
        for element in self.elements:
            if element.type == "Q":
                element.add_param("mosfet_model", self.mosfet_model)

    def update_nodes(self):
        for element in self.elements:
            for node in element.connections:
                self.add_node(node)

    def get_nodes(self):
        return self.nodes.copy()

    def get_elements(self):
        return self.elements

    def get_element(self, element_name):
        for element in self.elements:
            if element.name == element_name:
                return element

    def get_subcircuits(self):
        return self.subcircuits

    def add_node(self, nodeID):
        # if node doesnt exist add it
        if self.nodes.__contains__(nodeID) is False:
            self.nodes.append(nodeID)

    def add_model(self, model):
        model_name = model.name
        self.models[model_name] = model

    def add_element(self, element):
        if element is not None:
            self.elements.append(element)
        for node in element.connections:
            self.add_node(node)

    def add_subcircuit(self, circuitName, circuit):
        self.subcircuits[circuitName] = circuit

    def change_node_ID(self, nodeOld, nodeNew):
        pass

    def flatten_subcircuit(
        self, subcircuit_name, element_name, subct_element_connections, subcircuits={}
    ):
        combined_subct_list = self.subcircuits | subcircuits

        subct = combined_subct_list[subcircuit_name]
        subct_connections = subct.inner_connecting_nodes

        # If this node is in connection use the nodeID of the root circuit
        def new_node_IDs(nodeID):
            new_IDs = []
            for node in nodeID:
                if node == "0":
                    new_IDs.append("0")
                elif node in subct_connections:
                    position = subct.inner_connecting_nodes.index(node)
                    new_IDs.append(subct_element_connections[position])
                else:
                    new_IDs.append(
                        subcircuit_name
                        + self.separator
                        + element_name
                        + self.separator
                        + node
                    )
            # if list is empty
            return new_IDs

        subct_elements = []
        for element in subct.elements:
            element_connections = element.connections
            new_ele_connections = new_node_IDs(element_connections)
            new_ele = element.copy()
            new_ele.name = element_name + self.separator + new_ele.name
            new_ele.connections = new_ele_connections
            if new_ele.type == ("Q"):
                new_ele.add_param("bipolar_model", subct.bipolar_model)
                new_ele.add_param("mosfet_model", subct.mosfet_model)
            subct_elements.append(new_ele)
            pass
        for model_name, model in subct.models.items():
            self.add_model(model)
        return subct_elements

    def flatten(self, flatten_models=False, out_file_path=None, subcircuits={}):
        # Make sure all subcircuits are already flattend
        for name, subct in self.subcircuits.items():
            subct.flatten(subcircuits=self.subcircuits)

        # parse the element params before creating
        # the small signal subcircuits
        if flatten_models:
            # add the missing element params from the .out file
            from parser.NetlistParser import NetlistParser

            parser = NetlistParser()
            # the elements get changed by reference

            if out_file_path is not None:
                parser.parse_element_params(out_file_path, self.elements)
            else:
                # build .out path
                out_file_path = self.netlist_file_path + self.name + ".out"
                parser.parse_element_params(out_file_path, self.elements)

        new_elements = []
        for element in self.elements:
            if element.type == "X" and not flatten_models:
                element_connections = element.connections
                subcircuit_name = element.params["ref_cir"]
                subct_elements = self.flatten_subcircuit(
                    subcircuit_name,
                    element.name,
                    element_connections,
                    subcircuits,
                )
                if subct_elements is not None:
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
                subct_name = element.name + "." + model_name

                bipolar_model = element.params.get("bipolar_model", self.bipolar_model)
                mosfet_model = element.params.get("mosfet_model", self.mosfet_model)
                model_subct = model.get_generated_subcircuit(
                    element.params, bipolar_model, mosfet_model
                )

                self.add_subcircuit(subct_name, model_subct)
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
        self.update_nodes()

    def to_ai_string(self, indent=0):
        # currently a placeholder for debuging
        # print inner connecting nodes
        print("\t" * indent + "Name:", self.name)
        print("\t" * indent + "Netlist_File_Path:", self.netlist_file_path)
        print("\t" * indent + "Connectionss:", self.inner_connecting_nodes)
        print("\t" * indent + "Nodes:", self.nodes)

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
