
import dearpygui.dearpygui as dpg
import uuid


# ------------------------------------------------------------
#  Utilities
# ------------------------------------------------------------

def uid():
    """Generate unique IDs for node attributes."""
    return str(uuid.uuid4())


# ------------------------------------------------------------
#  Base Node Class
# ------------------------------------------------------------

class Node:
    def __init__(self, label, position=(100, 100)):
        self.label = label
        self.position = position
        self.node_id = None

        self.input_attributes = []
        self.output_attributes = []

        self.input_widgets = {}   # <attr_id : widget_id>
        self.output_widgets = {}  # <attr_id : widget_id>

    def setup(self, build_fn):
        with dpg.node(label=self.label, pos=self.position) as self.node_id:
            build_fn()

        dpg.set_item_pos(self.node_id, self.position)

    def add_input_attr(self):
        attr_id = uid()
        self.input_attributes.append(attr_id)
        return dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Input, tag=attr_id)

    def add_output_attr(self):
        attr_id = uid()
        self.output_attributes.append(attr_id)
        return dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output, tag=attr_id)


# ------------------------------------------------------------
#  Example Node Types
# ------------------------------------------------------------

class SimpleNode(Node):
    def setup(self):
        def build():
            # Input
            with self.add_input_attr():
                dpg.add_input_float(label="Input", width=150)

            # Output
            with self.add_output_attr():
                dpg.add_input_float(label="Output", width=150)

        super().setup(build)


class AdvancedNode(Node):
    def setup(self):
        def build():
            with dpg.file_dialog(directory_selector=False, show=False, id="file_dialog_id",width=700 ,height=400):
                dpg.add_file_extension(".*")

            with self.add_output_attr():
                dpg.add_button(label="Open File Dialog",
                               callback=lambda: dpg.show_item("file_dialog_id"))

        super().setup(build)


class TextOutputNode(Node):
    def __init__(self, label, position):
        super().__init__(label, position)
        self.input_text_id = None

    def setup(self):
        def build():
            # Input
            with self.add_input_attr():
                self.inout_text_id = dpg.add_text("Filepath: ...")
                
        super().setup(build)

    def on_input(self, sender, app_data):
        dpg.set_value(self.input_text_id, f"Filepath: {app_data}")

    # Called by NodeEditor when a connected node changes
    def receive_value(self, value):
        dpg.set_value(self.input_text_id, value)
        dpg.set_value(self.output_text_id, f"Output: {value}")

# ------------------------------------------------------------
#  Node Editor
# ------------------------------------------------------------

class NodeEditor:
    def __init__(self):
        self.nodes = []
        self.links = []

    def add_node(self, node_cls, label, pos):
        node = node_cls(label, pos)
        self.nodes.append(node)
        return node

    def render(self):
        with dpg.window(label="Node Editor", width=1200, height=800):
            with dpg.node_editor(tag="node_editor",
                                 callback=self.on_link,
                                 delink_callback=self.on_delink):
                for node in self.nodes:
                    node.setup()

    # -------- LINK HANDLING --------
    def on_link(self, sender, app_data):
        output_attr, input_attr = app_data

        dpg.add_node_link(output_attr, input_attr, parent="node_editor")
        self.links.append((output_attr, input_attr))

        self.propagate_values()

    def on_delink(self, sender, link_id):
        dpg.delete_item(link_id)

        # clean links list
        self.links = [(o, i) for (o, i) in self.links if dpg.does_item_exist(o)]
        self.propagate_values()


    def propagate_values(self):

        # Build quick lookup tables
        attr_to_node = {}
        for node in self.nodes:
            for attr in node.output_attributes:
                attr_to_node[attr] = node
            for attr in node.input_attributes:
                attr_to_node[attr] = node

        # For each link
        for output_attr, input_attr in self.links:

            sender = attr_to_node[output_attr]
            receiver = attr_to_node[input_attr]

            # find the widget inside the sender that generates the value
            if output_attr in sender.output_widgets:
                widget_id = sender.output_widgets[output_attr]
                value = dpg.get_value(widget_id)
            else:
                continue

            # deliver value to receiver
            if hasattr(receiver, "receive_value"):
                receiver.receive_value(value)

# ------------------------------------------------------------
#  Main App
# ------------------------------------------------------------

def main():
    dpg.create_context()
    dpg.create_viewport(title="OOP Node Editor Example", width=1200, height=800)

    editor = NodeEditor()

    # Add nodes
    editor.add_node(SimpleNode, "Simple Node", (100, 100))
    editor.add_node(AdvancedNode, "Advanced Node", (350, 100))
    editor.add_node(TextOutputNode, "Text Output Node", (600, 100))

    editor.render()

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
