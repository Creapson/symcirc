from typing import Dict, Any
import dearpygui.dearpygui as dpg
from pydantic import BaseModel, Field
from sympy.strategies.core import switch

class BodePlot(BaseModel):
    id: int = Field(default=0, exclude=True)

    mag_plot_id: int = Field(default=0, exclude=True)
    mag_x_id: int = Field(default=0, exclude=True)
    mag_y_id: int = Field(default=0, exclude=True)

    phase_plot_id: int = Field(default=0, exclude=True)
    phase_x_id: int = Field(default=0, exclude=True)
    phase_y_id: int = Field(default=0, exclude=True)

    # Settings
    mag_x_log: bool = Field(default=True)
    mag_y_log: bool = Field(default=True)
    phase_x_log: bool = Field(default=False)
    phase_y_log: bool = Field(default=True)

    # View
    max_x_mag: float = Field(default=0)
    min_x_mag: float = Field(default=0)
    max_y_mag: float = Field(default=0)
    max_y_mag: float = Field(default=0)

    max_x_phase: float = Field(default=0)
    min_x_phase: float = Field(default=0)
    max_y_phase: float = Field(default=0)
    max_y_phase: float = Field(default=0)

    line_dic: Dict[str, Any] = Field(default_factory=dict, exclude=True)

    def uuid(self, text: str) -> str:
        return str(self.id) + "_" + text

    def apply_settings(self, sender, app_data, user_data):
        widget_id, setting = user_data

        match setting:
            case "log":
                if app_data:
                    dpg.configure_item(widget_id, scale=dpg.mvPlotScale_Log10)
                else:
                    dpg.configure_item(widget_id, scale=dpg.mvPlotScale_Linear)

            case _:
                print("Cant apply setting: ", setting)
        pass

    def setup(self, width=-1, height=600):
        if self.id == 0:
            self.id = int(dpg.generate_uuid())

        self.mag_plot_id = int(dpg.generate_uuid())
        self.mag_x_id = int(dpg.generate_uuid()) 
        self.mag_y_id = int(dpg.generate_uuid())

        self.phase_plot_id = int(dpg.generate_uuid()) 
        self.phase_x_id = int(dpg.generate_uuid()) 
        self.phase_y_id = int(dpg.generate_uuid()) 
        with dpg.tree_node(label="Settings"):
            with dpg.group(horizontal=True):
                dpg.add_checkbox(label="Log mag x", tag=self.uuid("mag_x_log"), default_value=self.mag_x_log, callback=self.apply_settings,user_data=(self.mag_x_id, "log")) 
                dpg.add_checkbox(label="Log mag y", tag=self.uuid("mag_y_log"), default_value=self.mag_y_log, callback=self.apply_settings, user_data=(self.mag_y_id, "log"))
                dpg.add_checkbox(label="Log phase x", tag=self.uuid("phase_x_log"), default_value=self.phase_x_log, callback=self.apply_settings, user_data=(self.phase_x_id, "log"))
                dpg.add_checkbox(label="Log phase y", tag=self.uuid("phase_y_log"), default_value=self.phase_y_log, callback=self.apply_settings, user_data=(self.phase_y_id, "log"))
            dpg.add_button(label="fit_view", callback=self.fit_view)

        with dpg.subplots(
            2, 1, label="", link_all_x=True, 
            width=width,
            height=height,
            tag=self.id
        ):
            # -------- Magnitude Plot --------
            with dpg.plot(label="Betrag (dB)", tag=self.mag_plot_id):
                dpg.add_plot_legend()
                with dpg.plot_axis(dpg.mvXAxis,label="Frequency (Hz)", scale=dpg.mvPlotScale_Log10, tag=self.mag_x_id):
                    pass
                with dpg.plot_axis(dpg.mvYAxis, label="Betrag [dB]", scale=dpg.mvPlotScale_Linear, tag=self.mag_y_id):
                    pass

            # -------- Phase Plot --------
            with dpg.plot(label="Phase (°)", tag=self.phase_plot_id):
                dpg.add_plot_legend()
                with dpg.plot_axis(dpg.mvXAxis, label="Frequency (Hz)", scale=dpg.mvPlotScale_Log10, tag=self.phase_x_id):
                    pass
                with dpg.plot_axis(dpg.mvYAxis, label="Phase [°]", tag=self.phase_y_id):
                    pass

    def clear_plot(self):
        dpg.delete_item(self.mag_y_id, children_only=True)
        dpg.delete_item(self.phase_y_id, children_only=True)

    def fit_view(self):
        dpg.fit_axis_data(self.mag_x_id)
        dpg.fit_axis_data(self.mag_y_id)
        dpg.fit_axis_data(self.phase_x_id)
        dpg.fit_axis_data(self.phase_y_id)

    def add_line_series(self, name:str, 
                        freq: list[float] = [], 
                        magnitude: list[float] = [], 
                        phase: list[float] = []):

        print("Adding line seires")
        if not dpg.does_item_exist(self.uuid(f"mag_{name}")):
            dpg.add_line_series(
                freq, magnitude, label=name, 
                tag=self.uuid(f"mag_{name}"),
                parent=self.mag_y_id
            )
        else:
            dpg.set_value(self.uuid(f"mag_{name}"), [list(freq), list(magnitude)])

        print("Adding 2nd line seires")
        if not dpg.does_item_exist(self.uuid(f"phase_{name}")):
            dpg.add_line_series(
                freq, phase, label=name, 
                tag=self.uuid(f"phase_{name}"),
                parent=self.phase_y_id
            )
        else:
            dpg.set_value(self.uuid(f"phase_{name}"), [list(freq), list(phase)])

        self.fit_view()
