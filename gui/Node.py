import dearpygui.dearpygui as dpg

BIPOLAR_MODELS = ["beta_with_r_be", "beta_with_r_be_G"]
MOSFET_MODELS = ["BSIM"]

class Node:
    def __init__(self, label, position=(100, 100)):
        self.label = label
        self.position = position
        # Add the editor to access the other nodes
        self.editor = None
        self.node_id = None

        # {pin_id: connected_node}
        self.connections = {}
        # {pin_id: variable}
        self.output_values = {}
        self.output_pins = []
        self.input_pins = []

    def setup(self, build_fn, parent):
        with dpg.node(label=self.label, pos=self.position, parent=parent) as self.node_id:
            build_fn()

            with self.add_static_attr():
                dpg.add_button(label="Debug Log", callback=self.debug_print)
            print("Output Pins: ", self.output_pins)

        print(f"node_id of node {self.label} with id: {self.node_id}")
        dpg.set_item_pos(self.node_id, self.position)

        return self.node_id
    
    def uuid(self, txt: str):
        return f"{self.node_id}_" + txt

    def add_input_attr(self):
        return dpg.node_attribute(parent=self.node_id, attribute_type=dpg.mvNode_Attr_Input)

    def add_static_attr(self):
        return dpg.node_attribute(parent=self.node_id, attribute_type=dpg.mvNode_Attr_Static)

    def add_output_attr(self):
        return dpg.node_attribute(parent=self.node_id, attribute_type=dpg.mvNode_Attr_Output)

    def add_output_value(self, pin_index, value):
        pin_id = self.output_pins[pin_index]
        self.output_values[pin_id] = value
        print("Output Values", self.output_values)

    def add_connection(self, pin_id, connected_node):
        self.connections[pin_id] = connected_node
        print("Connections in Node: ", self.connections)

    def onlink_callback(self):
        pass

    def delink_callback(self):
        pass

    def update(self):
        if len(self.output_pins) > 0:
            self.editor.propagate(self.output_pins[0])
        print("update was called!")

    def debug_print(self):
        print(f"Debug Output from Node: {self.label}")
        print("Label: ", self.label)
        print("Position: ", self.position)
        print("NodeID: ", self.node_id)
        print("Connections: ", self.connections)
        print("output Values: ", self.output_values)
        print("output pins: ", self.output_pins)


###################
#   NODE CLASSES  #
###################

class ImportCircuit(Node):
    def callback(self, sender, app_data):

        def format_feedback(feedback):
            message = ""
            for string in feedback:
                if string is not None:
                    message += "\n" + string
            return message

        from NetlistParser import NetlistParser

        parser = NetlistParser()
        parser.set_cir_file(app_data["file_path_name"])
        feedback = parser.pre_format()

        # when a file is selected create the output pin
        with self.add_output_attr() as output_pin:
            dpg.add_text("Selected file")
        self.output_pins.append(output_pin)

        self.add_output_value(0, app_data["file_path_name"])
        dpg.set_value(
            self.file_path_widget_id,
            f"Loaded file with following Feedback:\n{format_feedback(feedback)}",
        )



    def setup(self, parent):
        def build():
            with dpg.value_registry():
                dpg.add_string_value(
                    default_value="No file currently selected!", tag=f"{self.node_id}_file_path_string"
                )

            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self.callback,
                tag=f"{self.node_id}_file_dialog_id",
                width=700,
                height=400,
            ):
                dpg.add_file_extension(".cir")


            with self.add_static_attr():
                dpg.add_button(label="Open File Dialog", callback=lambda: dpg.show_item(f"{self.node_id}_file_dialog_id"))               
                self.file_path_widget_id = dpg.add_text(source=f"{self.node_id}_file_path_string")

        return super().setup(build, parent)


class NetlistParserNode(Node):
    def __init__(self, label, position=(100, 100)): 
        self.row_sources = []

        super().__init__(label, position)

    def setup(self, parent):
        def build():
            with dpg.value_registry():
                dpg.add_string_value(default_value="Circuit is not flattend yet!", tag=self.uuid("circuit_parser"))
                dpg.add_string_value(default_value="_", tag=self.uuid("separator"))
                dpg.add_string_value(default_value="beta_with_r_be", tag=self.uuid("bipolar_model"))
                dpg.add_string_value(default_value="BSIM", tag=self.uuid("mosfet_model"))

            with self.add_input_attr() as input_pin:
                self.file_path_widget_id = dpg.add_text(
                    default_value="Connect ImportNode here! [filepath]"
                )
            self.input_pins.append(input_pin)

            with self.add_static_attr():
                with dpg.group(horizontal=True):
                    dpg.add_text("Seperator Symbol")
                    dpg.add_combo(items=("_", ",", ".", ";"), width=50, source=self.uuid("separator"))

                with dpg.group(horizontal=True):
                    dpg.add_text("Default Bioplar model")
                    dpg.add_combo(items=BIPOLAR_MODELS, width=200, source=self.uuid("bipolar_model"))


                with dpg.group(horizontal=True):
                    dpg.add_text("Default Mosfet Model")
                    dpg.add_combo(items=MOSFET_MODELS, width=200, source=self.uuid("mosfet_model"))

                # create table to edit all subcircuits
                dpg.add_text("Select the default small signal models for the subcircuits")
                with dpg.table(header_row=True, policy=dpg.mvTable_SizingFixedFit, resizable=True, no_host_extendX=True,
                   borders_innerV=True, borders_outerV=True, borders_outerH=True, tag=self.uuid("subcircuit_table")):

                    # create the header of the table
                    dpg.add_table_column(label="name")
                    dpg.add_table_column(label="bpiolar_model")
                    dpg.add_table_column(label="mosfet_model")


                dpg.add_text("When nothing is selected the default value will be used!")

                # temperary update button
                dpg.add_button(label="Flatten Subcircuits", callback=self.update)

            """
            with self.add_output_attr() as ouput_pin:
                self.circuit_out_pin = dpg.add_text(source=self.uuid("circuit_parser"))
            self.output_pins.append(ouput_pin)
            """

        return super().setup(build, parent)

    def onlink_callback(self):
        input_pin = self.input_pins[0]
        from_pin = self.connections[input_pin]

        # traverse the connection to the connected node 
        # and get the object from there
        from_node_id = dpg.get_item_parent(from_pin)
        from_node = self.editor.node_dic[from_node_id]
        filepath = from_node.output_values.get(from_pin, "No value found")

        from NetlistParser import NetlistParser

        parser = NetlistParser()
        parser.set_cir_file(filepath)
        self.circuit = parser.parse_netlist()

        # populate the subcircuit table
        def add_cubcircuit_row(subct_name, bipolar_model, mosfet_model):
            with dpg.value_registry():
                bipolar_source_id = dpg.add_string_value(default_value="", tag=self.uuid(f"{subct_name}_bipolar_model"))
                self.row_sources.append(bipolar_source_id)
                mosfet_source_id = dpg.add_string_value(default_value="", tag=self.uuid(f"{subct_name}_mosfet_model"))
                self.row_sources.append(mosfet_source_id)

            row = dpg.add_table_row(parent=self.uuid("subcircuit_table"))
            dpg.add_text(subct_name, parent=row)
            dpg.add_combo(items=BIPOLAR_MODELS, source=self.uuid(f"{subct_name}_bipolar_model"), parent=row)
            dpg.add_combo(items=MOSFET_MODELS, source=self.uuid(f"{subct_name}_mosfet_model"), parent=row)

        subct_list = self.circuit.get_subcircuits()
        self.delete_table()
        for subct_name, subct_obj in subct_list.items():
            add_cubcircuit_row(subct_name, subct_obj.bipolar_model, subct_obj.mosfet_model)

        super().onlink_callback()

    def delete_table(self):
        dpg.delete_item(self.uuid("subcircuit_table"), children_only=True, slot=1)

        # delete the used sources of each cell
        for source in self.row_sources:
            dpg.delete_item(source)

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

        # create a output pin for the flattend circuit
        with self.add_output_attr() as output_pin:
            dpg.add_text("Flattend Circuit")
        self.output_pins.append(output_pin)

        self.add_output_value(0, flattend_circuit)

        flattend_circuit.to_ai_string()

        # apply it to UI
        dpg.set_value(f"{self.node_id}_circuit_parser", "Circuit with flattend Subcircuits")

        super().update()

class FlattenNode(Node):
    def __init__(self, label, position=(100, 100)): 
        self.row_sources = []

        super().__init__(label, position)

    def callback(self, sender, app_data):
        print(sender)
        print(app_data)
        self.out_file_path = app_data["file_path_name"]
        dpg.set_value(self.uuid("out_file_path"), f"Selected {self.out_file_path}")

    def setup(self, parent):
        def build():
            with dpg.value_registry():
                dpg.add_string_value(default_value="Circuit is not flattend yet!", tag=self.uuid("circuit_out"))
                dpg.add_string_value(default_value="No .out file currently selected!", tag=self.uuid("out_file_path"))

            with self.add_input_attr() as input_pin:
                self.file_path_widget_id = dpg.add_text(default_value="Connect Circuit here! [circuit]")
            self.input_pins.append(input_pin)

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

                dpg.add_button(label="Select .out File", callback=lambda: dpg.show_item(self.uuid("file_dialog_id")))
                dpg.add_text(source=self.uuid("out_file_path"))

                # create table to edit all subcircuits
                dpg.add_text("Select small signal models for every element")
                with dpg.table(header_row=True, policy=dpg.mvTable_SizingFixedFit, resizable=True, no_host_extendX=True,
                   borders_innerV=True, borders_outerV=True, borders_outerH=True, tag=self.uuid("element_table")):

                    # create the header of the table
                    dpg.add_table_column(label="name")
                    dpg.add_table_column(label="bpiolar_model")
                    dpg.add_table_column(label="mosfet_model")


                dpg.add_text("When nothing is selected the default value will be used!")

                # temperary update button
                dpg.add_button(label="Flatten Elements", callback=self.update)



        return super().setup(build, parent)

    def onlink_callback(self):
        input_pin = self.input_pins[0]
        from_pin = self.connections[input_pin]

        # traverse the connection to the connected node 
        # and get the object from there
        from_node_id = dpg.get_item_parent(from_pin)
        from_node = self.editor.node_dic[from_node_id]
        self.circuit = from_node.output_values.get(from_pin, "No value found")

        self.circuit.to_ai_string()

        # populate the subcircuit table
        def add_element_row(name, bipolar_model, mosfet_model):
            with dpg.value_registry():
                bipolar_source_id = dpg.add_string_value(default_value=bipolar_model, tag=self.uuid(f"{name}_bipolar_model"))
                self.row_sources.append(bipolar_source_id)
                mosfet_source_id = dpg.add_string_value(default_value=mosfet_model, tag=self.uuid(f"{name}_mosfet_model"))

                self.row_sources.append(mosfet_source_id)

            row = dpg.add_table_row(parent=self.uuid("element_table"))
            dpg.add_text(name, parent=row)
            dpg.add_combo(items=BIPOLAR_MODELS, source=self.uuid(f"{name}_bipolar_model"), parent=row, width=-1)
            dpg.add_combo(items=MOSFET_MODELS, source=self.uuid(f"{name}_mosfet_model"), parent=row, width=-1)

        # populate the table with all elements
        self.element_list = self.circuit.get_elements()
        print(self.element_list)
        self.delete_table()
        for item in self.element_list:
            if item.type == "Q":
                add_element_row(item.name, item.params["bipolar_model"], item.params["mosfet_model"]), 

        super().onlink_callback()

    def delete_table(self):
        dpg.delete_item(self.uuid("element_table"), children_only=True, slot=1)

        # delete the used sources of each cell
        for source in self.row_sources:
            dpg.delete_item(source)

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

        # output pin
        with self.add_output_attr() as ouput_pin:
            self.circuit_out_pin = dpg.add_text(source=self.uuid("circuit_out"))
        self.output_pins.append(ouput_pin)

        self.add_output_value(0, flattend_circuit)

        flattend_circuit.to_ai_string()

        # apply it to UI
        dpg.set_value(self.uuid("circuit_out"), "Circuit with flattend Models")

        super().update()

class BodePlot(Node):
    def setup(self, parent):
        def build():
            pass

        return super().setup(build, parent)

    def onlink_callback(self):
        super().onlink_callback()

    def update(self):
        super().update()

class ModifiedNodalAnalysis(Node):
    def setup(self, parent):
        def build():
            pass

        return super().setup(build, parent)

    def onlink_callback(self):
        super().onlink_callback()

    def update(self):
        super().update()
