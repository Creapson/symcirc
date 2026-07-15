import dearpygui.dearpygui as dpg
from typing import List, Dict, Literal

from pydantic import Field

from gui.components.node_editor.nodes.Node import Node, NodeType
from gui.components.OutputPin import OutputPin, PinType
from gui.components.Table import Table, Widget_Type
from gui.windows.CircuitEditor import CircuitEditor
from netlist.Circuit import Circuit
from netlist.Element import Element


class FlattenNode(Node):
    node_type: Literal[NodeType.FLATTEN] = NodeType.FLATTEN

    out_file_path : str = Field(default="")

    circuit : Circuit = Field(default=Circuit(), exclude=True)
    element_list: List[Element] = []

    table: Table = Field(default=Table())


    flattend_circuit : Circuit = Field(default=Circuit(), exclude=True)

    def callback(self, sender, app_data):
        file_path = self.open_file_dialog("Select Output File", [("Output Files","*.out")])
        if len(file_path) ==  0:
            self.data["out_file_path"] = file_path[0]
        dpg.set_value(self.uuid("out_file_path"), f"Selected {self.data["out_file_path"]}")

    def get_possible_node_connections(self) -> List[str]:
        return ["mna"]

    def build(self):
        with dpg.value_registry():
            dpg.add_string_value(
                default_value="Circuit is not flattend yet!",
                tag=self.uuid("flattend_circuit_out"),
            )
            dpg.add_string_value(
                default_value="No .out file currently selected!",
                tag=self.uuid("out_file_path"),
            )

        self.add_input_pin("parsed_circuit", "Connect Circuit here! [circuit]")

        with self.add_static_attr():
            dpg.add_button(
                label="Select .out File",
                callback=self.callback,
            )
            dpg.add_text(source=self.uuid("out_file_path"))

            # create table to edit all subcircuits
            dpg.add_text("Select small signal models for every element")

            self.table.setup()
            self.table.add_column("Name", Widget_Type.TEXT)
            self.table.add_column("Bipolar Model", Widget_Type.COMBO, items=self.editor.application.bipolar_models)
            self.table.add_column("Mosfet Model", Widget_Type.COMBO, items=self.editor.application.mosfet_models)
            self.table.build()

            dpg.add_text("When nothing is selected the default value will be used!")

            # temperary update button
            dpg.add_button(label="Flatten Elements", callback=self.update)
        super().build()

    def onlink_callback(self):
        circuit_dict = self.get_input_pin_value("parsed_circuit", None)
        print("circuit_dict", circuit_dict)

        self.circuit = Circuit.model_validate(circuit_dict)

        self.circuit.to_ai_string()

        self.table.clear()
        if not self.table.is_setup: self.table.setup()
        for item in self.circuit.get_elements():
            if item.type == "Q":
                row_dict = {
                        "Name": item.name,
                        "Bipolar Model": item.params.get("bipolar_model", "beta_with_r_be"),
                        "Mosfet Model": item.params.get("mosfet_model", "BSIM"),
                        }
                self.table.add_row(item.name, row_dict)
        self.table.build()

        super().onlink_callback()

    def delink_callback(self):
        self.table.delete()
        super().delink_callback()

    def update(self):
        # apply the changed small signal models to all elements
        for element in self.element_list:
            bipolar_model = self.table.get_value(element.name, "Bipolar Model", "beta_with_r_be")
            mosfet_model = self.table.get_value(element.name, "Mosfet Model", "BSIM")
            element.params["bipolar_model"] = bipolar_model
            element.params["mosfet_model"] = mosfet_model

        self.flattend_circuit = self.circuit.copy()
        self.circuit.to_ai_string()
        default_out_path = self.circuit.netlist_file_path + self.circuit.name + ".out"
        self.flattend_circuit.flatten(True, self.data.get("out_file_path", default_out_path))


        self.add_output_pin(
                tag="flattend_circuit_out_pin",
                text="Circuit with flattend Models",
                pintype=PinType.CIRCUIT_EDIT,
                button_callback=self.open_circuit_edit,
                button_text="Edit Circuit"
        )
        self.add_output_pin_value("flattend_circuit_out_pin", self.flattend_circuit)

        self.flattend_circuit.to_ai_string()
        super().update()

    def open_circuit_edit(self):
        ct_editor = CircuitEditor(self.flattend_circuit, self.label)
        ct_editor.setup()
