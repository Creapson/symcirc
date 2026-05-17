import dearpygui.dearpygui as dpg
import numpy as np
import pandas as pd
from pydantic import Field

from gui.components.node_editor.nodes.Node import Node, NodeType
from gui.components.BodePlot import BodePlot
from typing import Literal, List


class BodePlotNode(Node):
    node_type: Literal[NodeType.BODE_PLOT] = NodeType.BODE_PLOT

    df: pd.DataFrame = Field(default=None, exclude=True)
    signal_names: List[str] = Field(default_factory=list, exclude=True)

    bode_plot: BodePlot = Field(default=BodePlot(), exclude=True)
    def build(self):
        # create pins for all nessary inputs
        self.add_input_pin("line_pin", "Connect freq_log here!")

        with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
            dpg.add_button(
                label="Open File Dialog",
                callback=self.csd_select_callback,
            )

            self.bode_plot.setup(width=400)

        super().build()

    def csd_select_callback(self, sender, app_data):
        import parser.CommonSimulationData as csd

        filepath = self.open_file_dialog("Select CSD File", [("CSD File", "*.csd")])[0]
        self.df, self.signal_names = csd.parse_csd(filepath)

        combo_tag = self.uuid("csd_select_combo")

        # If the combo box already exists, update items
        if dpg.does_item_exist(combo_tag):
            dpg.configure_item(combo_tag, items=self.signal_names)
        else:
            with self.add_static_attr():
                dpg.add_combo(
                    items=self.signal_names,
                    filter_key=True,  # This enables typing filter
                    width=150,
                    tag=combo_tag,
                    callback=self.csd_name_select_callback,
                )

    def csd_name_select_callback(self, sender, app_data):
        index = 0
        if app_data in self.signal_names:
            index = self.signal_names.index(app_data)

        subset = self.df[self.df["index"] == index]
        freqs = subset["frequency_hz"].tolist()

        values = subset["value"]

        magnitudes = np.abs(values).tolist()
        phases_rad = np.angle(values).tolist()
        phases_deg = np.degrees(np.angle(values)).tolist()

        self.populate_plot(freqs, magnitudes, phases_deg)
        print(subset)

    def onlink_callback(self):
        freq_log, magnitude, phase = self.get_input_pin_value("line_pin", ([], [], []))
        self.populate_plot(freq_log, magnitude, phase)
        super().onlink_callback()

    def populate_plot(self, freq, mag, phase):
        self.bode_plot.add_line_series("Test",freq, mag, phase)

    def update(self):
        super().update()
