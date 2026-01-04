import dearpygui.dearpygui as dpg

from gui.Node import ImportCircuit, NetlistParserNode


class NodeEditor:
    def __init__(self):
        self.node_dic = {}
        self.nodes = []
        self.node_editor_tag = "node_editor"

    def add_node(self, node_constructor, label, pos=(0, 100)):
        node = node_constructor(label, pos)
        node.editor = self
        self.nodes.append(node)

        # CREATE DearPyGui items immediately
        node_id = node.setup(parent=self.node_editor_tag)
        self.node_dic[node_id] = node

        # debug
        print(self.node_dic)
        print("node rendered:", node_id)

        return node

    # callback runs when user attempts to connect attributes
    def onlink_callback(self, sender, app_data):
        print("Added Connections: ", app_data)
        from_pin, to_pin = app_data
        to_node_id = dpg.get_item_parent(to_pin)
        to_node = self.node_dic[to_node_id]

        to_node.add_connection(to_pin, from_pin)
        to_node.onlink_callback()

        dpg.add_node_link(from_pin, to_pin, parent=sender)

    # callback runs when user attempts to disconnect attributes
    def delink_callback(self, sender, app_data):
        # app_data -> link_id
        dpg.delete_item(app_data)

    def render(self):
        
        with dpg.window(tag="Node Editor"):
           # ---------- MENU BAR ----------
            with dpg.menu_bar():
                with dpg.menu(label="File"):
                    dpg.add_menu_item(label="New", enabled=False)
                    dpg.add_menu_item(label="Open", enabled=False)
                    dpg.add_separator()
                    dpg.add_menu_item(label="Exit", enabled=False)

                with dpg.menu(label="Edit"):
                    dpg.add_menu_item(label="Undo", enabled=False)
                    dpg.add_menu_item(label="Redo", enabled=False)
                    # sub menu (dropdown with all node types
                    with dpg.menu(label="Add Node"):
                        dpg.add_menu_item(label="ImportCircuit", callback=lambda: self.add_node(ImportCircuit, "Circuit import Node", (000, 100)))
                        dpg.add_menu_item(label="NetlistParserNode", callback=lambda: self.add_node(NetlistParserNode, "Netlist Parser Node", (600, 100)))

            # ---------- NODE EDITOR ----------
            with dpg.node_editor(
                tag="node_editor",
                callback=self.onlink_callback,
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
        editor.render()
        dpg.setup_dearpygui()

        dpg.show_viewport()
        dpg.set_primary_window("Node Editor", True)

        # Render Loop
        dpg.start_dearpygui()
        dpg.destroy_context()
