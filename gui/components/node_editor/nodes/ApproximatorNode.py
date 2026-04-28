import dearpygui.dearpygui as dpg

from gui.components.node_editor.nodes.Node import Node, NodeType
from gui.windows.ApproximatorWindow import ApproximatorWindow

from Modified_Node_Analysis import ModifiedNodalAnalysis

from typing import Literal, List
from pydantic import Field


class ApproximatorNode(Node):
    node_type: Literal[NodeType.APPROXIMATOR] = NodeType.APPROXIMATOR

    mna: ModifiedNodalAnalysis = Field(default=None, exclude=True)
    sweep: List[float] = Field(default_factory=list, exclude=True)
    settings_window: ApproximatorWindow = Field(default=None, exclude=True)

    def build(self):
        self.add_input_pin("h_input", "Connect h here")

        with self.add_static_attr():
            dpg.add_button(
                label="Configure/Settings", callback=self.open_settings_window
            )

        super().build()

    def open_settings_window(self):
        if self.sweep is not None:
            self.settings_window = ApproximatorWindow(self.sweep, self.mna, self, self.node_id)
            self.settings_window.setup()

    def onlink_callback(self):
        self.sweep, self.mna = self.get_input_pin_value("h_input")

        super().onlink_callback()

    def update(self):
        self.add_output_pin("approx_mna", "Approximated MNA")
        self.add_output_pin_value("approx_mna", (self.sweep, self.settings_window.mna_approx), is_persistence=False)
        super().update()
