import dearpygui.dearpygui as dpg

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

    def setup(self, build_fn):
        with dpg.node(label=self.label, pos=self.position) as self.node_id:
            build_fn()

            with self.add_static_attr():
                dpg.add_button(label="Debug Log", callback=self.debug_print)
            print("Output Pins: ", self.output_pins)


        print(f"node_id of node {self.label} with id: {self.node_id}")
        dpg.set_item_pos(self.node_id, self.position)

        return self.node_id

    def add_input_attr(self):
        return dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Input)

    def add_static_attr(self):
        return dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static)

    def add_output_attr(self):
        return dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output)

    def add_output_value(self, pin_index, value):
        pin_id = self.output_pins[pin_index]
        self.output_values[pin_id] = value
        print("Output Values", self.output_values)

    def add_connection(self, pin_id, connected_node):
        self.connections[pin_id] = connected_node
        print("Connections in Node: ", self.connections)

    def update(self):
        print("update was called!")

    def debug_print(self):
        print(f"Debug Output from Node: {self.label}")
        print("Label: ", self.label)
        print("Position: ", self.position)
        print("NodeID: ", self.node_id)
        print("Connections: ", self.connections)
        print("output Values: ", self.output_values)
        print("output pins: ", self.output_pins)


class ImportCircuit(Node):
    def callback(self, sender, app_data):
        self.add_output_value(0, app_data["file_path_name"])
        dpg.set_value(self.file_path_widget_id, f"Selected File Path:\n{app_data["file_path_name"]}")

    def cancel_callback(sender, app_data):
        print('Cancel was clicked.')

    def setup(self):
        def build():

            with dpg.value_registry():
                dpg.add_string_value(default_value="No file currently selected!", tag="file_path_string")

            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self.callback,
                cancel_callback=self.cancel_callback,
                tag="file_dialog_id",
                width=700,
                height=400
            ):
                dpg.add_file_extension(".cir")

            with self.add_output_attr() as output_pin:
                dpg.add_button(label="Open File Dialog",
                               callback=lambda: dpg.show_item("file_dialog_id"))
            self.output_pins.append(output_pin)

            with self.add_static_attr():
                self.file_path_widget_id = dpg.add_text(source="file_path_string")

        return super().setup(build)

class TextShowNode(Node):
    def setup(self):


        def build():

            with dpg.value_registry():
                dpg.add_string_value(default_value="Connect a input", tag="file_path_string_text")

            with self.add_input_attr() as input_pin:
                self.file_path_widget_id = dpg.add_text(source="file_path_string_text")
            self.input_pins.append(input_pin)

            with self.add_static_attr():
                dpg.add_button(label="Update", callback=self.update)

        return super().setup(build)


    def update(self):
        input_pin = self.input_pins[0]
        from_pin = self.connections[input_pin]

        # get parent node ID (dpg ID)
        from_node_id = dpg.get_item_parent(from_pin)

        # get actual python object
        from_node = self.editor.node_dic[from_node_id]

        # read the value
        value = from_node.output_values.get(from_pin, "No value found")

        # apply it to UI
        dpg.set_value("file_path_string_text", value)

        super().update()
