from typing import Dict, Any
import dearpygui.dearpygui as dpg
from pydantic import BaseModel, Field

class Plot(BaseModel):
    label: str

    plot_id: int = Field(default=0, exclude=True) 
    x_axis_ids: list[int | str] = Field(default_factory=list, exclude=True)
    y_axis_ids: list[int | str] = Field(default_factory=list, exclude=True)

    def uuid(self, text: str) -> str:
        return str(self.plot_id) + "_" + text

    def apply_settings(self, sender, app_data, user_data):
        widget_id, setting = user_data

        match setting:
            case "log":
                dpg.configure_item(widget_id, scale=dpg.mvPlotScale_Log10)
            case _:
                print("Cant apply setting: ", setting)
        pass

    def setup(self):
        self.plot_id = int(dpg.generate_uuid())

        with dpg.tree_node(label="Settings"):
            dpg.add_button(label="fit_view", callback=self.fit_view)

        dpg.add_plot(
                label=self.label, 
                tag=self.plot_id,
                width=-1,
                height=-1
        )

    def add_x_axis(
            self, 
            label, 
            tag=None,
            ):
        if tag is None:
            tag = dpg.generate_uuid()
        else:
            tag=self.uuid(tag)
        axis_id = dpg.add_plot_axis(
                dpg.mvXAxis,
                label=label,
                scale=dpg.mvPlotScale_Linear,
                parent=self.plot_id,
                tag=tag
                )
        self.x_axis_ids.append(axis_id)
        return axis_id

    def add_y_axis(
            self, 
            label, 
            tag=None,
                   ):
        if tag is None:
            tag = dpg.generate_uuid()
        else:
            tag = self.uuid(tag)
        axis_id = dpg.add_plot_axis(
                dpg.mvYAxis, 
                label=label,
                scale=dpg.mvPlotScale_Linear,
                parent=self.plot_id,
                tag=tag
                )
        dpg.set_axis_limits_auto(axis_id)
        self.y_axis_ids.append(axis_id)
        return axis_id

    def remove_x_axis(self, tag):
        self.x_axis_ids.remove(self.uuid(tag))
        dpg.delete_item(self.uuid(tag))

    def remove_y_axis(self, tag):
        self.y_axis_ids.remove(self.uuid(tag))
        dpg.delete_item(self.uuid(tag))

    def clear_plot(self):
        dpg.delete_item(self.y_axis_id, children_only=True)

    def fit_view(self):
        dpg.fit_axis_data(self.x_axis_ids[0])
        dpg.fit_axis_data(self.y_axis_ids[0])

    def add_line_series(
            self, 
            name:str, 
            x_values: list[float],
            y_values: list[float],
            axis_id
            ):

        print("Adding line seires")
        dpg.add_line_series(
            x_values, y_values, label=name, 
            tag=self.uuid(name),
            parent=axis_id
        )
        self.fit_view()

    def add_candlestick_series(
            self, 
            name:str,
            dates, 
            opens, 
            closes, 
            lows, 
            highs,
            axis_id
            ):
        print("Adding candlestick seires")
        dpg.add_candle_series(
            dates, 
            opens, 
            closes, 
            lows, 
            highs, 
            label=name,
            parent=axis_id,
            tag=self.uuid(name)
        )
        self.fit_view()

    def add_bar_series(
            self,
            name,
            dates,
            values,
            axis_id
            ):
        dpg.add_bar_series(
                x=dates,
                y=values,
                parent=axis_id,
                tag=self.uuid(name)
                )
