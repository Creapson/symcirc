import dearpygui.dearpygui as dpg
from pydantic import Field
from typing import List, Dict, Literal

from gui.windows.CircuitEditor import CircuitEditor

from gui.components.node_editor.nodes.Node import Node, NodeType
from gui.components.Table import Table, Widget_Type
from netlist.Circuit import Circuit

class NetlistParserNode(Node):
    node_type: Literal[NodeType.NETLIST_PARSER] = NodeType.NETLIST_PARSER

    circuit: Circuit = Field(default=Circuit(), exclude=True)
    table: Table = Field(default=Table())

    def build(self):
        with dpg.value_registry():

            dpg.add_string_value(
                default_value="Circuit is not flattend yet!",
                tag=self.uuid("circuit_parser"),
            )

            dpg.add_string_value(
                    default_value=self.data.get("separator", "_"), 
                    tag=self.uuid("separator")
            )

            dpg.add_string_value(
                default_value=self.data.get("bipolar_model", "beta_with_r_be"), 
                tag=self.uuid("bipolar_model")
            )

            dpg.add_string_value(
                default_value=self.data.get("mosfet_model", "BSIM"), 
                tag=self.uuid("mosfet_model")
            )

        self.add_input_pin("file_path_pin", "Connect ImportNode fere! [filepath]")

        with self.add_static_attr():
            with dpg.group(horizontal=True):
                dpg.add_text("Seperator Symbol")
                dpg.add_combo(
                    items=("_", ",", ".", ";"),
                    width=50,
                    source=self.uuid("separator"),
                )

            with dpg.group(horizontal=True):
                dpg.add_text("Default Bioplar model")
                dpg.add_combo(
                    items=self.editor.application.bipolar_models,
                    width=200,
                    source=self.uuid("bipolar_model"),
                )

            with dpg.group(horizontal=True):
                dpg.add_text("Default Mosfet Model")
                dpg.add_combo(
                    items=self.editor.application.mosfet_models,
                    width=200,
                    source=self.uuid("mosfet_model"),
                )

            # create table to edit all subcircuits
            dpg.add_text(
                "Select the default small signal models for the subcircuits"
            )

            self.table.setup()
            self.table.add_column("name", Widget_Type.TEXT)
            self.table.add_column("bipolar_model", Widget_Type.COMBO, items=self.editor.application.bipolar_models)
            self.table.add_column("mosfet_model", Widget_Type.COMBO, items=self.editor.application.mosfet_models)
            self.table.build()

            dpg.add_text("When nothing is selected the default value will be used!")

            # temperary update button
            dpg.add_button(label="Flatten Subcircuits", callback=self.update)

        super().build()

    def get_possible_node_connections(self) -> List[str]:
        return ["flatten"]

    def onlink_callback(self):
        filepath = self.get_input_pin_value("file_path_pin", "")

        from pathlib import Path
        from parser.NetlistParser import get_circuit_from_file 

        self.circuit = get_circuit_from_file(filepath)

        # extract name and folder_path from the file_path
        p = Path(filepath)

        ct_name = p.stem
        ct_folder_path = str(p.parent) + "\\"

        self.circuit.set_name(ct_name)
        self.circuit.set_netlist_path(ct_folder_path)

        subct_list = self.circuit.get_subcircuits()

        self.table.clear()
        for subct_name, subct_obj in subct_list.items():
            row_dict = {
                    "name": subct_name,
                    "bipolar_model": subct_obj.bipolar_model,
                "mosfet_model": subct_obj.mosfet_model
                    }
            self.table.add_row(subct_name,  row_dict)
        self.table.build()

        super().onlink_callback()

    def delink_callback(self):
        self.table.delete()

        super().delink_callback()

    def update(self):
        # apply all options to the circuit
        # separator
        self.data["separator"] = dpg.get_value(self.uuid("separator"))
        self.data["bipolar_model"] = dpg.get_value(self.uuid("bipolar_model"))
        self.data["mosfet_model"] = dpg.get_value(self.uuid("mosfet_model"))

        self.circuit.set_separator(self.data.get("seperator", "_"))
        self.circuit.set_bipolar_model(self.data.get("bipolar_model", ""))
        self.circuit.set_mosfet_model(self.data.get("mosfet_model", ""))

        # apply settings from the table
        subct_list = self.circuit.get_subcircuits()
        for subct_name, subct_obj in subct_list.items():
            bipolar_model = self.table.get_value(subct_name, "bipolar_model", "beta_with_r_be")
            mosfet_model = self.table.get_value(subct_name, "mosfet_model", "BSIM")

            subct_obj.set_bipolar_model(bipolar_model)
            subct_obj.set_mosfet_model(mosfet_model)

        flattend_circuit = self.circuit.copy()
        flattend_circuit.flatten()

        # create a output pin for the flattend circuit
        self.add_output_pin(
                tag="flattend_circuit", 
                text="Flattend Circuit", 
                button_callback=self.open_circuit_edit, 
                button_text="Edit Circuit"
                            )
        self.add_output_pin_value("flattend_circuit", flattend_circuit)

        flattend_circuit.to_ai_string()

        # apply it to UI
        dpg.set_value(self.uuid("circuit_parser"), "Circuit with flattend Subcircuits")

        super().update()

    def save(self):
        self.data["separator"] = dpg.get_value(self.uuid("separator"))
        self.data["bipolar_model"] = dpg.get_value(self.uuid("bipolar_model"))
        self.data["mosfet_model"] = dpg.get_value(self.uuid("mosfet_model"))

        super().save()

    def open_circuit_edit(self):
        ct_editor = CircuitEditor(self.circuit, self.label)
        ct_editor.setup()
