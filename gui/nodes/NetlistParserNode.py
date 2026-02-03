import dearpygui.dearpygui as dpg

from gui.nodes.Node import Node


class NetlistParserNode(Node):
    def __init__(self, label, position=(100, 100)):
        self.row_sources = []
        self.table_rows = {}

        super().__init__(label, position)

    def setup(self, node_editor_tag):
        def build():
            with dpg.value_registry():
                dpg.add_string_value(
                    default_value="Circuit is not flattend yet!",
                    tag=self.uuid("circuit_parser"),
                )
                dpg.add_string_value(default_value="_", tag=self.uuid("separator"))
                dpg.add_string_value(
                    default_value="beta_with_r_be", tag=self.uuid("bipolar_model")
                )
                dpg.add_string_value(
                    default_value="BSIM", tag=self.uuid("mosfet_model")
                )

            with self.add_input_attr() as input_pin:
                self.file_path_widget_id = dpg.add_text(
                    default_value="Connect ImportNode here! [filepath]",
                    tag=self.uuid("file_path_pin"),
                )
            self.input_pins[self.uuid("file_path_pin")] = input_pin

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
                        items=self.BIPOLAR_MODELS,
                        width=200,
                        source=self.uuid("bipolar_model"),
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("Default Mosfet Model")
                    dpg.add_combo(
                        items=self.MOSFET_MODELS,
                        width=200,
                        source=self.uuid("mosfet_model"),
                    )

                # create table to edit all subcircuits
                dpg.add_text(
                    "Select the default small signal models for the subcircuits"
                )

                # add a filter text-box above the table
                with dpg.group(horizontal=True):
                    dpg.add_text("Filter by subcircuit name:")
                    dpg.add_input_text(
                        width=200,
                        hint="type to filter...",
                        callback=self.filter_table,
                        tag=self.uuid("subckt_filter"),
                    )
                with dpg.table(
                    header_row=True,
                    policy=dpg.mvTable_SizingFixedFit,
                    resizable=True,
                    no_host_extendX=True,
                    borders_innerV=True,
                    borders_outerV=True,
                    borders_outerH=True,
                    tag=self.uuid("subcircuit_table"),
                ):
                    # create the header of the table
                    dpg.add_table_column(label="name")
                    dpg.add_table_column(label="bpiolar_model")
                    dpg.add_table_column(label="mosfet_model")

                dpg.add_text("When nothing is selected the default value will be used!")

                # temperary update button
                dpg.add_button(label="Flatten Subcircuits", callback=self.update)

        return super().setup(build, node_editor_tag)

    def onlink_callback(self):
        filepath = self.get_input_pin_value(self.uuid("file_path_pin"))

        from pathlib import Path

        from NetlistParser import NetlistParser

        parser = NetlistParser()
        parser.set_cir_file(filepath)
        self.circuit = parser.parse_netlist()

        # extract name and folder_path from the file_path
        p = Path(filepath)

        ct_name = p.stem
        ct_folder_path = str(p.parent) + "\\"

        self.circuit.set_name(ct_name)
        self.circuit.set_netlist_path(ct_folder_path)

        # populate the subcircuit table
        def add_cubcircuit_row(subct_name, bipolar_model, mosfet_model):
            with dpg.value_registry():
                bipolar_source_id = dpg.add_string_value(
                    default_value="", tag=self.uuid(f"{subct_name}_bipolar_model")
                )
                self.row_sources.append(bipolar_source_id)
                mosfet_source_id = dpg.add_string_value(
                    default_value="", tag=self.uuid(f"{subct_name}_mosfet_model")
                )
                self.row_sources.append(mosfet_source_id)

            row = dpg.add_table_row(parent=self.uuid("subcircuit_table"))
            self.table_rows[subct_name] = row

            dpg.add_text(subct_name, parent=row)
            dpg.add_combo(
                items=self.BIPOLAR_MODELS,
                source=self.uuid(f"{subct_name}_bipolar_model"),
                parent=row,
            )
            dpg.add_combo(
                items=self.MOSFET_MODELS,
                source=self.uuid(f"{subct_name}_mosfet_model"),
                parent=row,
            )

        subct_list = self.circuit.get_subcircuits()
        self.delete_table()
        for subct_name, subct_obj in subct_list.items():
            add_cubcircuit_row(
                subct_name, subct_obj.bipolar_model, subct_obj.mosfet_model
            )

        super().onlink_callback()

    def filter_table(self, sender, app_data):
        filter_text = app_data.lower()

        for subct_name, row_id in self.table_rows.items():
            visible = filter_text in subct_name.lower()
            dpg.configure_item(row_id, show=visible)

    def delete_table(self):
        dpg.delete_item(self.uuid("subcircuit_table"), children_only=True, slot=1)

        # delete the used sources of each cell
        for source in self.row_sources:
            dpg.delete_item(source)

        self.row_sources.clear()
        self.table_rows.clear()

    def delink_callback(self):
        self.delete_table()

        super().delink_callback()

    def update(self):
        # apply all options to the circuit
        # separator
        separator = dpg.get_value(self.uuid("separator"))
        self.circuit.set_separator(separator)
        # small signal models
        # circuit
        self.circuit.set_bipolar_model(dpg.get_value(self.uuid("bipolar_model")))
        self.circuit.set_mosfet_model(dpg.get_value(self.uuid("mosfet_model")))

        subct_list = self.circuit.get_subcircuits()
        for subct_name, subct_obj in subct_list.items():
            bipolar_model = dpg.get_value(self.uuid(f"{subct_name}_bipolar_model"))
            mosfet_model = dpg.get_value(self.uuid(f"{subct_name}_mosfet_model"))

            subct_obj.set_bipolar_model(bipolar_model)
            subct_obj.set_mosfet_model(mosfet_model)

            # if nothing was selected use the default values
            if bipolar_model == "":
                subct_obj.set_bipolar_model(dpg.get_value(self.uuid("bipolar_model")))

            if mosfet_model == "":
                subct_obj.set_mosfet_model(dpg.get_value(self.uuid("mosfet_model")))

        flattend_circuit = self.circuit.copy()
        flattend_circuit.flatten()

        # delte all output pins that already exist
        self.delete_output_pins()

        # create a output pin for the flattend circuit
        with self.add_output_attr() as output_pin:
            dpg.add_text("Flattend Circuit", tag=self.uuid("flattend_circuit"))
        self.output_pins[self.uuid("flattend_circuit")] = output_pin
        self.add_output_pin_value(self.uuid("flattend_circuit"), flattend_circuit)

        flattend_circuit.to_ai_string()

        # apply it to UI
        dpg.set_value(self.uuid("circuit_parser"), "Circuit with flattend Subcircuits")

        super().update()
