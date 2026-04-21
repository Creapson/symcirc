import dearpygui.dearpygui as dpg
import json

from gui.data.NodeEditor import NodeEditor


from gui.nodes.ApproximatorNode import ApproximatorNode
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
        self.node_editor_tag = "node_editor"
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
    def save_node_editor(self, sender, app_data):
        try:
            file_path:str = app_data.get("file_path_name")
            if not file_path:
                print("No file selected")
                return

            # Ensure .json extension
            if not file_path.endswith(".json"):
                file_path += ".json"

            # Dump Pydantic object to JSON
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.node_editor.model_dump_json(indent=4))

            print(f"Saved to {file_path}")

        except Exception as e:
            print("Error saving file:", e)
        print(self.node_editor.model_dump_json(indent=4))

    def load_node_editor(self, sender, app_data):
        try:
            file_path: str = app_data["file_path_name"]
            
            with open(file_path, "r", encoding="utf-8") as f:
                json_string = f.read()
            
            self.node_editor = NodeEditor.model_validate_json(json_string)
            self.node_editor.application = self
            self.setup_node_editor()

        except Exception as e:
            print(f"Error loading file: {e}")

    def onlink_callback(self, sender, app_data):
        self.node_editor.onlink_callback(sender=sender, app_data=app_data)

    # callback runs when user attempts to disconnect pins
    def delink_callback(self, sender, app_data):
        self.node_editor.delink_callback(sender=sender, app_data=app_data)

    def setup(self, build_func=None, show_menu_bar=False):
        def build():
            # ---------- MENU BAR ----------
            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self.save_node_editor,
                tag=self.uuid("file_save_dialog"),
                width=700,
                height=400,
            ):
                dpg.add_file_extension(".json")

            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self.load_node_editor,
                tag=self.uuid("file_load_dialog"),
                width=700,
                height=400,
            ):
                dpg.add_file_extension(".json")
            
            with dpg.menu_bar():
                with dpg.menu(label="File"):
                    dpg.add_menu_item(label="New", enabled=False)
                    dpg.add_menu_item(
                            label="Open", 
                            enabled=True, 
                            callback=lambda: dpg.show_item(self.uuid("file_load_dialog"))
                            )
                    dpg.add_menu_item(
                            label="Save", 
                            enabled=True, 
                            callback=lambda: dpg.show_item(self.uuid("file_save_dialog"))
                            )
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
            dpg.add_node_editor(
                tag=self.node_editor_tag,
                callback=self.onlink_callback,
                delink_callback=self.delink_callback,
                minimap=True,
                minimap_location=dpg.mvNodeMiniMap_Location_BottomRight)
            self.setup_node_editor()

        return super().setup(build, show_menu_bar=True)

    def setup_node_editor(self):
        for _, node in self.node_editor.node_dic.items():
            node.editor = self
            node.setup(self.node_editor_tag)
