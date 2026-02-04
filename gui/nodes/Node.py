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
        self.output_pins = {}
        self.input_pins = {}

        # enable if self.update() should be called
        # when the inputs change
        self.do_propagation = False

        self.BIPOLAR_MODELS = ["beta_with_r_be", "beta_with_r_be_G"]
        self.MOSFET_MODELS = ["BSIM"]

    def setup(self, build_fn, node_editor_tag):
        with dpg.node(
            label=self.label, pos=self.position, parent=node_editor_tag
        ) as self.node_id:
            build_fn()

            with self.add_static_attr():
                dpg.add_button(label="Debug Log", callback=self.debug_print)
            print("Output Pins: ", self.output_pins)

        print(f"node_id of node {self.label} with id: {self.node_id}")
        dpg.set_item_pos(self.node_id, self.position)

        return self.node_id

    def delete_output_pins(self):
        for pin_tag, attr_id in list(self.output_pins.items()):
            if dpg.does_item_exist(attr_id):
                dpg.delete_item(attr_id)

            self.output_values.pop(attr_id, None)

        self.output_pins.clear()

    def uuid(self, txt: str):
        return f"{self.node_id}_" + txt

    def add_input_attr(self):
        return dpg.node_attribute(
            parent=self.node_id, attribute_type=dpg.mvNode_Attr_Input
        )

    def add_static_attr(self):
        return dpg.node_attribute(
            parent=self.node_id, attribute_type=dpg.mvNode_Attr_Static
        )

    def add_output_attr(self):
        return dpg.node_attribute(
            parent=self.node_id, attribute_type=dpg.mvNode_Attr_Output
        )

    def add_output_pin_value(self, output_pin_tag, value):
        output_pin = self.output_pins.get(output_pin_tag, None)
        self.output_values[output_pin] = value

        self.editor.propagate(output_pin)
        print("Output Values", self.output_values)

    def add_connection(self, pin_id, connected_node):
        self.connections[pin_id] = connected_node
        print("Connections in Node: ", self.connections)

    def onlink_callback(self):
        if self.do_propagation:
            self.update()
        pass

    def delink_callback(self):
        pass

    def get_input_pin_value(self, input_pin_tag):
        if input_pin_tag in self.input_pins:
            input_pin = self.input_pins.get(input_pin_tag, None)
            from_pin = self.connections.get(input_pin, None)

            if from_pin is None:
                return None

            # traverse the connection to the connected node
            # and get the object from there
            from_node_id = dpg.get_item_parent(from_pin)
            from_node = self.editor.node_dic[from_node_id]
            return from_node.output_values.get(from_pin, None)

        else:
            return None

    def update(self):
        # when update is called all settings should be set
        self.do_propagation = True

    def debug_print(self):
        print(f"\n\nDebug Output from Node: {self.label}")
        print("Label: ", self.label)
        print("Position: ", self.position)
        print("NodeID: ", self.node_id)
        print("Connections: ", self.connections)
        print("Input Pins", self.input_pins)
        print("output Values: ", self.output_values)
        print("output pins: ", self.output_pins)


"""
class Copy(Node):
    def setup(self, node_editor_tag):
        def build():
            pass

        return super().setup(build, node_editor_tag)

    def onlink_callback(self):
        super().onlink_callback()

    def update(self):
        super().update()
"""
