from typing import Dict, Any
import dearpygui.dearpygui as dpg
from gui.components.plots.Plot import Plot
from pydantic import BaseModel, Field
import numpy as np


class PoleZeroPlot(BaseModel):
    plot_id: int = Field(default=0, exclude=True)

    x_axis: int = Field(default=0, exclude=True)
    y_axis: int = Field(default=0, exclude=True)

    # themes 
    zero_theme: int = Field(default=0, exclude=True)
    pole_theme: int = Field(default=0, exclude=True)

    line_dic: Dict[str, Any] = Field(default_factory=dict, exclude=True)

    def __init__(self, **data):
        super().__init__(**data)
        with dpg.theme() as self.zero_theme:
            with dpg.theme_component(dpg.mvScatterSeries):
                dpg.add_theme_style(
                    dpg.mvPlotStyleVar_Marker,
                    dpg.mvPlotMarker_Circle,
                    category=dpg.mvThemeCat_Plots,
                )
                dpg.add_theme_style(
                    dpg.mvPlotStyleVar_MarkerSize, 6, category=dpg.mvThemeCat_Plots
                )
                dpg.add_theme_color(
                    dpg.mvPlotCol_Line,
                    (0, 200, 255, 255),
                    category=dpg.mvThemeCat_Plots,
                )

        with dpg.theme() as self.pole_theme:
            with dpg.theme_component(dpg.mvScatterSeries):
                dpg.add_theme_style(
                    dpg.mvPlotStyleVar_Marker,
                    dpg.mvPlotMarker_Cross,
                    category=dpg.mvThemeCat_Plots,
                )
                dpg.add_theme_style(
                    dpg.mvPlotStyleVar_MarkerSize, 7, category=dpg.mvThemeCat_Plots
                )
                dpg.add_theme_color(
                    dpg.mvPlotCol_Line,
                    (255, 80, 80, 255),
                    category=dpg.mvThemeCat_Plots,
                )

    def uuid(self, text: str) -> str:
        return str(self.plot_id) + "_" + text

    def setup(self):
        if self.plot_id == 0:
            self.plot_id = int(dpg.generate_uuid())

        with dpg.window():
            with dpg.plot(label="Pole Zero Plot", tag=self.plot_id):
                dpg.add_plot_legend()

                with dpg.plot_axis(dpg.mvXAxis,label="Re()", scale=dpg.mvPlotScale_Linear) as self.x_axis:
                    pass
                with dpg.plot_axis(dpg.mvYAxis, label="Im()", scale=dpg.mvPlotScale_Linear) as self.y_axis:
                    pass

        zeros = np.array([0.5 + 0.5j, 0.5 - 0.5j])
        poles = np.array([-0.3 + 0.7j, -0.3 - 0.7j, 0.8 + 0.0j])
        self.add_poles(poles)
        self.add_zeros(zeros)

    def add_poles(self, poles):
        poles_real, poles_imag = poles.real, poles.imag
        poles_series = dpg.add_scatter_series(
            list(poles_real), list(poles_imag), label="Poles (X)", parent=self.y_axis
        )
        dpg.bind_item_theme(poles_series, self.pole_theme)


    def add_zeros(self, zeros):
        zeros_real, zeros_imag = zeros.real, zeros.imag
        zeros_series = dpg.add_scatter_series(
            list(zeros_real), list(zeros_imag), label="Zeros (0)", parent=self.y_axis
        )
        dpg.bind_item_theme(zeros_series, self.zero_theme)