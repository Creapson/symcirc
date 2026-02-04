import dearpygui.dearpygui as dpg

from gui.nodes.Node import Node


class FlattenNode(Node):
    def __init__(self, label, position=(100, 100)):
        self.row_sources = []
        self.table_rows = {}
        self.out_file_path = None

        super().__init__(label, position)

    def callback(self, sender, app_data):
        print(sender)
        print(app_data)
        self.out_file_path = app_data["file_path_name"]
        dpg.set_value(self.uuid("out_file_path"), f"Selected {self.out_file_path}")

    def setup(self, node_editor_tag):
        def build():
            with dpg.value_registry():
                dpg.add_string_value(
                    default_value="Circuit is not flattend yet!",
                    tag=self.uuid("flattend_circuit_out"),
                )
                dpg.add_string_value(
                    default_value="No .out file currently selected!",
                    tag=self.uuid("out_file_path"),
                )

            with self.add_input_attr() as input_pin:
                dpg.add_text(
                    default_value="Connect Circuit here! [circuit]",
                    tag=self.uuid("file_path_pin"),
                )
            self.input_pins[self.uuid("file_path_pin")] = input_pin

            with self.add_static_attr():
                with dpg.file_dialog(
                    directory_selector=False,
                    show=False,
                    callback=self.callback,
                    tag=self.uuid("file_dialog_id"),
                    width=700,
                    height=400,
                ):
                    dpg.add_file_extension(".out")

                dpg.add_button(
                    label="Select .out File",
                    callback=lambda: dpg.show_item(self.uuid("file_dialog_id")),
                )
                dpg.add_text(source=self.uuid("out_file_path"))

                with dpg.group(horizontal=True):
                    dpg.add_text("Filter by element name:")
                    dpg.add_input_text(
                        width=200,
                        hint="type to filter...",
                        callback=self.filter_table,
                        tag=self.uuid("subckt_filter"),
                    )
                # create table to edit all subcircuits
                dpg.add_text("Select small signal models for every element")
                with dpg.table(
                    header_row=True,
                    policy=dpg.mvTable_SizingFixedFit,
                    resizable=True,
                    no_host_extendX=True,
                    borders_innerV=True,
                    borders_outerV=True,
                    borders_outerH=True,
                    tag=self.uuid("element_table"),
                ):
                    # create the header of the table
                    dpg.add_table_column(label="name")
                    dpg.add_table_column(label="bpiolar_model")
                    dpg.add_table_column(label="mosfet_model")

                dpg.add_text("When nothing is selected the default value will be used!")

                # temperary update button
                dpg.add_button(label="Flatten Elements", callback=self.update)

        return super().setup(build, node_editor_tag)

    def onlink_callback(self):
        self.circuit = self.get_input_pin_value(self.uuid("file_path_pin"))

        self.circuit.to_ai_string()

        # populate the subcircuit table
        def add_element_row(name, bipolar_model, mosfet_model):
            with dpg.value_registry():
                bipolar_source_id = dpg.add_string_value(
                    default_value=bipolar_model, tag=self.uuid(f"{name}_bipolar_model")
                )
                self.row_sources.append(bipolar_source_id)
                mosfet_source_id = dpg.add_string_value(
                    default_value=mosfet_model, tag=self.uuid(f"{name}_mosfet_model")
                )

                self.row_sources.append(mosfet_source_id)

            row = dpg.add_table_row(parent=self.uuid("element_table"))
            self.table_rows[name] = row

            dpg.add_text(name, parent=row)
            dpg.add_combo(
                items=self.BIPOLAR_MODELS,
                source=self.uuid(f"{name}_bipolar_model"),
                parent=row,
                width=-1,
            )
            dpg.add_combo(
                items=self.MOSFET_MODELS,
                source=self.uuid(f"{name}_mosfet_model"),
                parent=row,
                width=-1,
            )

        # populate the table with all elements
        self.element_list = self.circuit.get_elements()
        print(self.element_list)
        self.delete_table()
        for item in self.element_list:
            if item.type == "Q":
                (
                    add_element_row(
                        item.name,
                        item.params["bipolar_model"],
                        item.params["mosfet_model"],
                    ),
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
        # apply the changed small signal models to all elements
        for element in self.element_list:
            bipolar_model = dpg.get_value(self.uuid(f"{element.name}_bipolar_model"))
            mosfet_model = dpg.get_value(self.uuid(f"{element.name}_mosfet_model"))
            element.params["bipolar_model"] = bipolar_model
            element.params["mosfet_model"] = mosfet_model

        flattend_circuit = self.circuit.copy()
        flattend_circuit.flatten(True, self.out_file_path)

        if not dpg.does_item_exist(self.uuid("flattend_circuit_out")):
            with self.add_output_attr() as output_pin:
                dpg.add_text(source=self.uuid("flattend_circuit_out"))
            self.output_pins[self.uuid("flattend_circuit_out")] = output_pin
        self.add_output_pin_value(self.uuid("flattend_circuit_out"), flattend_circuit)

        flattend_circuit.to_ai_string()

        # apply it to UI
        dpg.set_value(self.uuid("flattend_circuit_out"), "Circuit with flattend Models")

        super().update()
