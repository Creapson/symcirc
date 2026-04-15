import dearpygui.dearpygui as dpg

from gui.data.NodeEditor import NodeEditor


from gui.nodes.Approximator import ApproximatorNode
from gui.nodes.BodePlot import BodePlot
from gui.nodes.Flatten import FlattenNode
from gui.nodes.ImportCircuit import ImportCircuit
from gui.nodes.ModifiedNodalAnalysis import ModifiedNodalAnalysis
from gui.nodes.NetlistParserNode import NetlistParserNode
from gui.nodes.NumericSolver import NumericSolver
from gui.nodes.TransferFunctionNode import TransferFunctionNode
from gui.windows.Window import Window


class NodeEditorWindow(Window):
    def __init__(self, application):
        self.title = "Node Editor"
        self.node_editor_tag = None
        self.application = application
        self.node_editor = NodeEditor(application=self.application)

        super().__init__(title=self.title)

    def add_node(self, node_constructor, label, pos=(0, 100)):
        self.node_editor.add_node(
                node_editor_tag=self.node_editor_tag, 
                node_constructor=node_constructor, 
                label=label, 
                pos=pos
                )

    def onlink_callback(self, sender, app_data):
        self.node_editor.onlink_callback(sender=sender, app_data=app_data)

    # callback runs when user attempts to disconnect pins
    def delink_callback(self, sender, app_data):
        self.node_editor.delink_callback(sender=sender, app_data=app_data)

    def setup(self, build_func=None, show_menu_bar=False):
        def build():
            # ---------- MENU BAR ----------
            with dpg.menu_bar():
                with dpg.menu(label="File"):
                    dpg.add_menu_item(label="New", enabled=False)
                    dpg.add_menu_item(label="Open", enabled=False)
                    dpg.add_menu_item(label="Save", enabled=True, callback=lambda: print(self.node_editor.model_dump_json(indent=4)))
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
                            label="TransferFunction Node",
                            callback=lambda: self.add_node(
                                TransferFunctionNode,
                                "TransferFunction Node",
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

                        dpg.add_menu_item(
                            label="Approximator",
                            callback=lambda: self.add_node(
                                ApproximatorNode, "Approimate", (600, 300)
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

            dpg.add_node_editor(
                tag=self.node_editor_tag,
                callback=self.onlink_callback,
                delink_callback=self.delink_callback,
                minimap=True,
                minimap_location=dpg.mvNodeMiniMap_Location_BottomRight)

        return super().setup(build, show_menu_bar=True)
