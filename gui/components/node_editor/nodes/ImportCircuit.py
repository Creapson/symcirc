import dearpygui.dearpygui as dpg

from gui.components.node_editor.nodes.Node import Node, NodeType
from typing import Literal


class ImportCircuit(Node):
    node_type: Literal[NodeType.IMPORT_CIRCUIT] = NodeType.IMPORT_CIRCUIT

    def callback(self, sender, app_data):
        def format_feedback(feedback):
            message = ""
            for string in feedback:
                if string is not None:
                    message += "\n" + string
            return message

        from parser.NetlistParser import get_pre_format_info 

        feedback = get_pre_format_info(app_data["file_path_name"])

        # when a file is selected create the output pin
        self.add_output_pin(tag="file_path_out", text="Selected file")

        self.add_output_pin_value(
            "file_path_out", app_data["file_path_name"]
        )

        dpg.set_value(
            self.uuid("file_path_string"),
            f"Loaded file with following Feedback:\n{format_feedback(feedback)}",
        )

    def build(self):
        if not dpg.does_item_exist(self.uuid("file_dialog_id")):
            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self.callback,
                tag=self.uuid("file_dialog_id"),
                width=700,
                height=400,
            ):
                dpg.add_file_extension(".cir", parent=self.uuid("file_dialog_id"))
                dpg.add_file_extension(".net", parent=self.uuid("file_dialog_id"))

        with self.add_static_attr():
            dpg.add_button(
                label="Open File Dialog",
                callback=lambda: dpg.show_item(self.uuid("file_dialog_id")),
            )
            dpg.add_text(
                    label="No file currently selected",
                    tag=self.uuid("file_path_string")
            )
        super().build()
