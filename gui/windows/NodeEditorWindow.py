import dearpygui.dearpygui as dpg

from gui.components.node_editor.NodeEditor import NodeEditor


from gui.components.node_editor.nodes.ApproximatorNode import ApproximatorNode
from gui.components.node_editor.nodes.BodePlot import BodePlot
from gui.components.node_editor.nodes.Flatten import FlattenNode
from gui.components.node_editor.nodes.ImportCircuit import ImportCircuit
from gui.components.node_editor.nodes.ModifiedNodalAnalysis import ModifiedNodalAnalysisNode
from gui.components.node_editor.nodes.NetlistParserNode import NetlistParserNode
from gui.components.node_editor.nodes.NumericSolver import NumericSolver
from gui.components.node_editor.nodes.TransferFunctionNode import TransferFunctionNode
from gui.windows.Window import Window


class NodeEditorWindow(Window):
    def __init__(self, application):
        self.title = "Node Editor"
        self.node_editor_tag = "node_editor"
        self.application = application
        self.node_editor = NodeEditor(application=self.application)

        super().__init__(title=self.title)

    def add_node(self, node_constructor, label):
        mouse_pos = dpg.get_mouse_pos(local=False)
        editor_offset = [0, 0]
        self.node_editor.add_node(
                node_editor_tag=self.node_editor_tag, 
                node_constructor=node_constructor, 
                label=label, 
                pos=mouse_pos
                )
        dpg.configure_item(self.uuid("add_node_context_menu"), show=False)

    def save_node_editor(self, sender, app_data):
        try:
            file_path:str = app_data.get("file_path_name")
            if not file_path:
                print("No file selected")
                return

            # Ensure .json extension
            if not file_path.endswith(".json"):
                file_path += ".json"

            # save / update chaging variables like the position
            self.node_editor.save()
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
            self.node_editor.application = self.application
            self.setup_node_editor()

        except Exception as e:
            print(f"Error loading file: {e}")

    def onlink_callback(self, sender, app_data):
        self.node_editor.onlink_callback(sender=sender, app_data=app_data)

    # callback runs when user attempts to disconnect pins
    def delink_callback(self, sender, app_data):
        self.node_editor.delink_callback(sender=sender, app_data=app_data)

    def handle_click(self, sender, app_data):
        # right_click is '1'
        if app_data == 1:
            if dpg.is_item_hovered(self.node_editor_tag):
                mouse_pos = dpg.get_mouse_pos(local=False)
                dpg.set_item_pos(self.uuid("add_node_context_menu"), mouse_pos)
                dpg.configure_item(self.uuid("add_node_context_menu"), show=True)
            else:
                dpg.configure_item(self.uuid("add_node_context_menu"), show=False)

    def _menu_callback(self, sender, app_data, user_data):
        # user_data is the (node_class, desc) tuple we passed above
        node_constructor, label = user_data
        self.add_node(node_constructor, label)

    def build_add_node_menu(self):
        menu_structure = [
            {
                "Netlist": [
                        ("ImportCircuit", ImportCircuit, "Circuit import Node"),
                        ("NetlistParserNode", NetlistParserNode, "Netlist Parser Node"),
                        ("Flatten", FlattenNode, "Flatten Node")
                    ]
            },
            {
                "Numeric": [
                        ("ModifiedNodalAnalysis", ModifiedNodalAnalysisNode, "ModifiedNodalAnalysis Node"),
                        ("TransferFunction Node", TransferFunctionNode, "TransferFunction Node"),
                        ("NumericSolver", NumericSolver, "NumericSolver"),
                    ]
            },
            {
                "Display": [
                    ("BodeBlot", BodePlot, "BodePlot Node"),
                ]
            },
            ("ApproximatorNode", ApproximatorNode, "Approximate"),
        ]

        def _create_menu_recursive(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    with dpg.menu(label=key):
                        _create_menu_recursive(value)
            
            elif isinstance(data, list):
                for item in data:
                    _create_menu_recursive(item)

            elif isinstance(data, tuple):
                node_label, node_class, desc = data
                
                dpg.add_menu_item(
                    label=node_label,
                    callback=self._menu_callback,
                    user_data=(node_class, desc)
                )

        _create_menu_recursive(menu_structure)

    def build(self):
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

        with dpg.window(tag=self.uuid("add_node_context_menu"), show=False, popup=True):
            self.build_add_node_menu()
        
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
                    self.build_add_node_menu()

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

        with dpg.handler_registry():
            dpg.add_mouse_click_handler(callback=self.handle_click)

        self.setup_node_editor()

        super().build()

    def setup_node_editor(self):
        old_dic = self.node_editor.node_dic.copy()
        self.node_editor.node_dic = {}
        # Draw the node
        for _, node in old_dic.items():
            node.editor = self.node_editor
            new_id = node.setup(self.node_editor_tag)
            node.connections = {}
            self.node_editor.node_dic[new_id] = node

        # create big transition table
        trans_dic = {}
        for _,node in self.node_editor.node_dic.items():
            trans_dic.update(node.id_transition_table)
        print(trans_dic)

        # update the output_values pin ids
        for _,node in self.node_editor.node_dic.items():
            old_dic = node.output_values.copy()
            for pin_id,_ in old_dic.items():
                if pin_id in trans_dic:
                    node.output_values[trans_dic[pin_id]] = node.output_values[pin_id]
                    del node.output_values[pin_id]

        ### CREATE THE LINKS ###
        old_link_dic = self.node_editor.links.copy()
        self.node_editor.links = {}
        for _,(from_pin, to_pin) in old_link_dic.items():
            # update pin ids if nessesary
            if from_pin in trans_dic: 
                from_pin = trans_dic[from_pin]
            if to_pin in trans_dic:
                to_pin = trans_dic[to_pin]
            self.onlink_callback(sender=self.node_editor_tag, app_data=(from_pin, to_pin))
