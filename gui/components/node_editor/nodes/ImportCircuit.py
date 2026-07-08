import dearpygui.dearpygui as dpg

from gui.components.node_editor.nodes.Node import Node, NodeType
from typing import Literal, List


class ImportCircuit(Node):
    node_type: Literal[NodeType.IMPORT_CIRCUIT] = NodeType.IMPORT_CIRCUIT

    def callback(self, sender, app_data):
        def format_feedback(feedback):
            message = ""
            for string in feedback:
                if string is not None:
                    message += string
            return message

        from parser.NetlistParser import get_pre_format_info 

        file_path = self.open_file_dialog("Select Ciruit file", [("Circuit File","*.cir")])
        if len(file_path) > 0:
            feedback = get_pre_format_info(file_path[0])

        # when a file is selected create the output pin
        self.add_output_pin(tag="file_path_out", text="Selected file")

        self.add_output_pin_value(
            "file_path_out", file_path[0]
        )

        dpg.set_value(
            self.uuid("file_path_string"),
            f"Loaded file with following Feedback:\n{format_feedback(feedback)}",
        )    

    def get_possible_node_connections(self) -> List[str]:
        return ["parser"]

    def build(self):
        with self.add_static_attr():
            dpg.add_button(
                label="Open File Dialog",
                callback=self.callback,
            )
            dpg.add_text(
                    label="No file currently selected",
                    tag=self.uuid("file_path_string")
            )
        super().build()
