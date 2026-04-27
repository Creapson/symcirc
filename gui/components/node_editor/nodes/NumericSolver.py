import dearpygui.dearpygui as dpg

from gui.components.node_editor.nodes.Node import Node, NodeType
from typing import Literal, List
from pydantic import Field


class NumericSolver(Node):
    node_type: Literal[NodeType.NUMERIC_SOLVER] = NodeType.NUMERIC_SOLVER


    h: List[float] = Field(default_factory=list, exclude=True)
    sweep: List[float] = Field(default_factory=list, exclude=True)

    def build(self):
        with dpg.value_registry():
            dpg.add_int_value(default_value=2, tag=self.uuid("start_log_int"))
            dpg.add_int_value(default_value=8, tag=self.uuid("end_log_int"))
            dpg.add_int_value(default_value=10000, tag=self.uuid("points_in_log"))

        self.add_input_pin("h_input_pin", "Connect H here")

        with self.add_static_attr():
            dpg.add_text("Configure the log-Space")

            with dpg.group(horizontal=True):
                dpg.add_text("Start Frequenzy in 10^x")
                dpg.add_input_int(
                    label="input int", 
                    source=self.uuid("start_log_int"),
                    width=100
                )

            with dpg.group(horizontal=True):
                dpg.add_text("End Frequenzy in 10^x")
                dpg.add_input_int(
                    label="input int", 
                    source=self.uuid("end_log_int"),
                    width=100
                )

            with dpg.group(horizontal=True):
                dpg.add_text("Number of Points between start and end")
                dpg.add_input_int(
                    label="input int", 
                    source=self.uuid("points_in_log"),
                    width=100
                )

            dpg.add_button(label="Calculate Numeric Values", callback=self.update)

        super().build()

    def onlink_callback(self):
        self.h, self.sweep = self.get_input_pin_value("h_input_pin")

        super().onlink_callback()

    def update(self):
        import numpy as np

        # create solved arrays for later plotting
        freq_log = self.sweep
        magnitude = np.abs(self.h)
        phase_deg = np.angle(self.h, deg=True)

        print(freq_log)
        print(magnitude)
        print(phase_deg)

        self.add_output_pin(tag="line_out", text="Numeric Values for BodePlots")
        self.add_output_pin_value(
            "line_out", (freq_log, magnitude, phase_deg),
            is_persistence=False
        )

        super().update()
