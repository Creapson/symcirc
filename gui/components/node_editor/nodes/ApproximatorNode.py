import dearpygui.dearpygui as dpg

from gui.components.node_editor.nodes.Node import Node, NodeType
from gui.windows.ApproximatorWindow import ApproximatorWindow

from typing import Literal


class ApproximatorNode(Node):
    node_type: Literal[NodeType.APPROXIMATOR] = NodeType.APPROXIMATOR

    def build(self):
        self.add_input_pin("h_input", "Connect h here")

        with self.add_static_attr():
            dpg.add_button(
                label="Configure/Settings", callback=self.open_settings_window
            )

        super().build()

    def open_settings_window(self):
        if self.h is not None:
            self.settings_window = ApproximatorWindow(self.h, self.mna, self.node_id)
            self.settings_window.setup()

    def onlink_callback(self):
        self.h, self.mna = self.get_input_pin_value("h_input")

        super().onlink_callback()

    def update(self):
        super().update()
