import dearpygui.dearpygui as dpg

from gui.nodes.BodePlot import BodePlot
from gui.nodes.Flatten import FlattenNode
from gui.nodes.ImportCircuit import ImportCircuit
from gui.nodes.ModifiedNodalAnalysis import ModifiedNodalAnalysis
from gui.nodes.NetlistParserNode import NetlistParserNode
from gui.nodes.NumericSolver import NumericSolver
from gui.windows.Window import Window


class NodeEditor(Window):
    def __init__(self):
        self.title = "Node Editor"

        self.node_dic = {}
        self.nodes = []
        self.node_editor_tag = None
        self.links = {}

        super().__init__(title=self.title)

    def add_node(self, node_constructor, label, pos=(0, 100)):
        node = node_constructor(label, pos)
        node.editor = self
        self.nodes.append(node)

        # CREATE DearPyGui items immediately
        node_id = node.setup(node_editor_tag=self.node_editor_tag)
        self.node_dic[node_id] = node

        # debug
        print(self.node_dic)
        print("node rendered:", node_id)

        return node

    # callback runs when user attempts to connect attributes
    def onlink_callback(self, sender, app_data):
        from_pin, to_pin = app_data
        to_node_id = dpg.get_item_parent(to_pin)
        to_node = self.node_dic[to_node_id]

        # you can not connect multiple outputs to one input
        # check if the input pin already has a connection
        if to_pin not in to_node.connections:
            to_node.add_connection(to_pin, from_pin)
            try:
                to_node.onlink_callback()  # may raise
            except Exception as e:
                to_node.connections = {}
                print(f"Link rejected: {e}")
                return

            link_id = dpg.add_node_link(from_pin, to_pin, parent=sender)
            # store link metadata
            self.links[link_id] = (from_pin, to_pin)

            print("Added Connections: ", app_data)

    # callback runs when user attempts to disconnect attributes
    def delink_callback(self, sender, app_data):
        link_id = app_data

        if link_id not in self.links:
            return

        from_pin, to_pin = self.links[link_id]

        from_node_id = dpg.get_item_parent(from_pin)
        to_node_id = dpg.get_item_parent(to_pin)

        from_node = self.node_dic[from_node_id]
        to_node = self.node_dic[to_node_id]

        # remove logical connections
        from_node.connections.pop(from_pin, None)
        to_node.connections.pop(to_pin, None)

        to_node.delink_callback()

        # remove stored link
        del self.links[link_id]

        # remove visual link
        dpg.delete_item(link_id)

        print("Removed connection:", from_pin, "->", to_pin)

    # when the output changes run onlink_callback on
    # all connected nodes to update the value
    def propagate(self, output_pin_id):
        for link_id, (from_pin, to_pin) in self.links.items():
            if from_pin == output_pin_id:
                # get the node which should be
                # updated
                to_node_id = dpg.get_item_parent(to_pin)
                to_node = self.node_dic[to_node_id]
                to_node.onlink_callback()

    def setup(self):
        def build():
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
                        dpg.add_menu_item(
                            label="ImportCircuit",
                            callback=lambda: self.add_node(
                                ImportCircuit, "Circuit import Node", (000, 100)
                            ),
                        )
                        dpg.add_menu_item(
                            label="NetlistParserNode",
                            callback=lambda: self.add_node(
                                NetlistParserNode, "Netlist Parser Node", (600, 100)
                            ),
                        )
                        dpg.add_menu_item(
                            label="ModifiedNodalAnalysis",
                            callback=lambda: self.add_node(
                                ModifiedNodalAnalysis,
                                "ModifiedNodalAnalysis Node",
                                (000, 300),
                            ),
                        )
                        dpg.add_menu_item(
                            label="BodeBlot",
                            callback=lambda: self.add_node(
                                BodePlot, "BodePlot Node", (300, 300)
                            ),
                        )
                        dpg.add_menu_item(
                            label="Flatten",
                            callback=lambda: self.add_node(
                                FlattenNode, "Flatten Node", (600, 300)
                            ),
                        )

                        dpg.add_menu_item(
                            label="NumericSolver",
                            callback=lambda: self.add_node(
                                NumericSolver, "NumericSolver", (600, 300)
                            ),
                        )

                with dpg.menu(label="Settings"):
                    dpg.add_menu_item(
                        label="Style Editor", callback=lambda: dpg.show_style_editor()
                    )
                    dpg.add_menu_item(
                        label="Font Manager", callback=lambda: dpg.show_font_manager()
                    )

                with dpg.menu(label="Debug"):
                    dpg.add_menu_item(label="Debug", callback=lambda: dpg.show_debug())

                    dpg.add_menu_item(
                        label="Item Registry", callback=lambda: dpg.show_item_registry()
                    )

                    dpg.add_menu_item(
                        label="Metrics", callback=lambda: dpg.show_metrics()
                    )

            # ---------- NODE EDITOR ----------
            self.node_editor_tag = self.uuid("node_editor")

            with dpg.node_editor(
                tag=self.node_editor_tag,
                callback=self.onlink_callback,
                delink_callback=self.delink_callback,
                minimap=True,
                minimap_location=dpg.mvNodeMiniMap_Location_BottomRight,
            ):
                for node in self.nodes:
                    node_id = node.setup()
                    self.node_dic[node_id] = node
                print(self.node_dic)

        return super().setup(build, show_menu_bar=True)
