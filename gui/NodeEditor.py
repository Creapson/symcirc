import dearpygui.dearpygui as dpg

from gui.Node import ImportCircuit, NetlistParserNode


class NodeEditor:
    def __init__(self):
        self.node_dic = {}
        self.nodes = []

    def add_node(self, node_constructor, label, pos):
        node = node_constructor(label, pos)
        node.editor = self
        self.nodes.append(node)
        return node

    # callback runs when user attempts to connect attributes
    def link_callback(self, sender, app_data):
        print("Added Connections: ", app_data)
        from_pin, to_pin = app_data
        to_node_id = dpg.get_item_parent(to_pin)
        to_node = self.node_dic[to_node_id]

        to_node.add_connection(to_pin, from_pin)

        dpg.add_node_link(from_pin, to_pin, parent=sender)

    # callback runs when user attempts to disconnect attributes
    def delink_callback(self, sender, app_data):
        # app_data -> link_id
        dpg.delete_item(app_data)

    def render(self):
        with dpg.window(tag="Node Editor"):
            with dpg.node_editor(
                tag="node_editor",
                callback=self.link_callback,
                delink_callback=self.delink_callback,
            ):
                for node in self.nodes:
                    node_id = node.setup()
                    self.node_dic[node_id] = node
                print(self.node_dic)

    def start(self):
        dpg.create_context()

        # Viewport
        dpg.create_viewport(title="OOP Node Editor Example", width=1200, height=800)
        editor = NodeEditor()
        # Add nodes
        editor.add_node(ImportCircuit, "Circuit import Node", (000, 100))
        editor.add_node(NetlistParserNode, "Show the text", (600, 100))
        editor.render()
        dpg.setup_dearpygui()

        dpg.show_viewport()
        dpg.set_primary_window("Node Editor", True)

        # Render Loop
        dpg.start_dearpygui()
        dpg.destroy_context()
