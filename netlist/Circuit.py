from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from netlist.Element import Element
from netlist.Model import Model


class Circuit(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = ""
    netlist_file_path: str = ""

    inner_connecting_nodes: List[str] = Field(default_factory=list)

    bipolar_model: str = "beta_with_r_be_G"
    mosfet_model: str = "BSIM"

    nodes: List[str] = Field(default_factory=list)

    elements: List[Element] = Field(default_factory=list)

    models: Dict[str, Model] = Field(default_factory=dict)
    subcircuits: Dict[str, "Circuit"] = Field(default_factory=dict)

    separator: str = "."

    # --- COPY METHOD ---
    def copy(self) -> "Circuit":
        return Circuit(
            name=self.name,
            netlist_file_path=self.netlist_file_path,
            inner_connecting_nodes=list(self.inner_connecting_nodes),
            bipolar_model=self.bipolar_model,
            mosfet_model=self.mosfet_model,
            nodes=list(self.nodes),
            elements=[element.copy() for element in self.elements],
            models={name: model.copy() for name, model in self.models.items()},
            subcircuits={
                name: sub_ct.copy() for name, sub_ct in self.subcircuits.items()
            },
            separator=self.separator,
        )

    def set_name(self, name: str):
        self.name = name

    def set_netlist_path(self, path: str):
        self.netlist_file_path = path

    def set_separator(self, separator: str):
        self.separator = separator

    def set_bipolar_model(self, new_model: str):
        self.bipolar_model = new_model
        for element in self.elements:
            if element.type == "Q":
                element.add_param("bipolar_model", self.bipolar_model)

    def set_mosfet_model(self, new_model: str):
        self.mosfet_model = new_model
        for element in self.elements:
            if element.type == "Q":
                element.add_param("mosfet_model", self.mosfet_model)

    def update_nodes(self):
        for element in self.elements:
            for node in element.connections:
                self.add_node(node)

    def get_nodes(self) -> List[str]:
        return list(self.nodes)

    def get_elements(self) -> List[Element]:
        return self.elements

    def get_element(self, element_name: str):
        for element in self.elements:
            if element.name == element_name:
                return element
        return None

    def get_subcircuits(self) -> Dict[str, "Circuit"]:
        return self.subcircuits

    def add_node(self, nodeID: str):
        if nodeID not in self.nodes:
            self.nodes.append(nodeID)

    def add_model(self, model: Model):
        self.models[model.name] = model

    def add_element(self, element: Element):
        if element is not None:
            self.elements.append(element)
            for node in element.connections:
                self.add_node(node)

    def add_subcircuit(self, circuitName: str, circuit: "Circuit"):
        self.subcircuits[circuitName] = circuit

    def flatten_subcircuit(
        self,
        subcircuit_name: str,
        element_name: str,
        subct_element_connections: List[str],
        subcircuits: Optional[Dict[str, "Circuit"]] = None,
    ) -> List[Element]:
        if subcircuits is None:
            subcircuits = {}

        combined_subct_list = self.subcircuits | subcircuits
        subct = combined_subct_list[subcircuit_name]

        subct_connections = subct.inner_connecting_nodes

        def new_node_ids(node_ids: List[str]) -> List[str]:
            new_ids = []

            for node in node_ids:
                if node == "0":
                    new_ids.append("0")

                elif node in subct_connections:
                    position = subct_connections.index(node)
                    new_ids.append(subct_element_connections[position])

                else:
                    new_ids.append(
                        f"{subcircuit_name}{self.separator}"
                        f"{element_name}{self.separator}{node}"
                    )

            return new_ids

        subct_elements: List[Element] = []

        for element in subct.elements:
            new_ele = element.copy()
            new_ele.name = f"{element_name}{self.separator}{new_ele.name}"
            new_ele.connections = new_node_ids(element.connections)

            if new_ele.type == "Q":
                new_ele.add_param("bipolar_model", subct.bipolar_model)
                new_ele.add_param("mosfet_model", subct.mosfet_model)

            subct_elements.append(new_ele)

        # copy models into root circuit
        for model in subct.models.values():
            self.add_model(model)

        return subct_elements

    def flatten(
        self,
        flatten_models: bool = False,
        out_file_path: Optional[str] = None,
        subcircuits: Optional[Dict[str, "Circuit"]] = None,
    ):
        if subcircuits is None:
            subcircuits = {}

        # ensure all subcircuits are flattened first
        for subct in self.subcircuits.values():
            subct.flatten(subcircuits=self.subcircuits)

        # --------------------------------------------------
        # Parse model parameters from .out file if required
        # --------------------------------------------------

        if flatten_models:
            from parser.NetlistParser import NetlistParser

            parser = NetlistParser()

            if out_file_path is None:
                out_file_path = self.netlist_file_path + self.name + ".out"

            parser.parse_element_params(out_file_path, self.elements)

        # --------------------------------------------------
        # Main flatten loop
        # --------------------------------------------------

        new_elements: List[Element] = []

        for element in self.elements:
            # Expand subcircuits
            if element.type == "X" and not flatten_models:
                subcircuit_name = element.params["ref_cir"]

                subct_elements = self.flatten_subcircuit(
                    subcircuit_name,
                    element.name,
                    element.connections,
                    subcircuits,
                )

                new_elements.extend(subct_elements)
                continue

            # Expand transistor models
            if element.type == "Q" and flatten_models:
                model_name = element.params["ref_model"]
                model = self.models[model_name]

                subct_name = f"{element.name}.{model_name}"

                bipolar_model = element.params.get("bipolar_model", self.bipolar_model)
                mosfet_model = element.params.get("mosfet_model", self.mosfet_model)

                model_subct = model.get_generated_subcircuit(
                    element.params,
                    bipolar_model,
                    mosfet_model,
                )

                self.add_subcircuit(subct_name, model_subct)

                subct_elements = self.flatten_subcircuit(
                    subct_name,
                    element.name,
                    element.connections,
                )

                new_elements.extend(subct_elements)
                continue

            # Normal element
            new_elements.append(element)

        # cleanup
        self.subcircuits = {}
        self.elements = new_elements
        self.update_nodes()

    # --------------------------------------------------
    # DEBUG STRING
    # --------------------------------------------------

    def to_ai_string(self, indent: int = 0):
        prefix = "\t" * indent

        print(prefix + "Name:", self.name)
        print(prefix + "Netlist_File_Path:", self.netlist_file_path)
        print(prefix + "Connections:", self.inner_connecting_nodes)
        print(prefix + "Nodes:", self.nodes)

        print(prefix + "Elements in Circuit")
        for element in self.elements:
            element.to_ai_string(indent + 1)

        if self.models:
            print(prefix + "Models in Circuit")
            for name, model in self.models.items():
                print("\t" * (indent + 1) + name)
                model.to_ai_string(indent + 1)

        if self.subcircuits:
            print(prefix + "Subcircuits in Circuit")
            for name, sub_ct in self.subcircuits.items():
                print(prefix + "Name of the subcircuit:", name)
                sub_ct.to_ai_string(indent + 1)


# Required for recursive Pydantic models
Circuit.model_rebuild()
