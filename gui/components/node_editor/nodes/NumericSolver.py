import dearpygui.dearpygui as dpg

from gui.components.node_editor.nodes.Node import Node, NodeType
from typing import Literal, List
from pydantic import Field


class NumericSolver(Node):
    node_type: Literal[NodeType.NUMERIC_SOLVER] = NodeType.NUMERIC_SOLVER


    h: List[float] = Field(default_factory=list, exclude=True)
    sweep: List[float] = Field(default_factory=list, exclude=True)

    def build(self):
        self.add_input_pin("h_input_pin", "Connect H here")

        with self.add_static_attr():
            dpg.add_button(label="Calculate Numeric Values", callback=self.update)

        super().build()

    def get_possible_node_connections(self) -> List[str]:
        return ["bode_plot"]

    def onlink_callback(self):
        self.h, self.sweep = self.get_input_pin_value("h_input_pin", ([], []))

        super().onlink_callback()

    def update(self):
        import numpy as np

        # create solved arrays for later plotting
        magnitude = np.abs(self.h).flatten().tolist()
        phase_deg = np.unwrap(np.angle(self.h, deg=True), axis=0).flatten().tolist()

        self.add_output_pin(tag="line_out", text="Numeric Values for BodePlots")
        self.add_output_pin_value(
            "line_out", (self.sweep, magnitude, phase_deg),
            is_persistence=False
        )

        super().update()
