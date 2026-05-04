from typing import Dict, Any
import dearpygui.dearpygui as dpg
from numpy import frexp
from pydantic import BaseModel, Field

class BodePlot(BaseModel):
    id: int = Field(default=0, exclude=True)

    mag_plot_id: int = Field(default=0, exclude=True)
    mag_x_id: int = Field(default=0, exclude=True)
    mag_y_id: int = Field(default=0, exclude=True)

    phase_plot_id: int = Field(default=0, exclude=True)
    phase_x_id: int = Field(default=0, exclude=True)
    phase_y_id: int = Field(default=0, exclude=True)

    line_dic: Dict[str, Any] = Field(default_factory=dict, exclude=True)

    def uuid(self, text: str) -> str:
        return str(self.id) + "_" + text

    def setup(self, width=-1, height=600):
        with dpg.subplots(
            2, 1, label="", link_all_x=True, 
            width=width,
            height=height
        ) as self.id:
            # -------- Magnitude Plot --------
            with dpg.plot(label="Betrag (dB)") as self.mag_plot_id:
                dpg.add_plot_legend()
                with dpg.plot_axis(dpg.mvXAxis,label="Frequency (Hz)", scale=dpg.mvPlotScale_Log10) as self.mag_x_id:
                    pass
                with dpg.plot_axis(dpg.mvYAxis, label="Betrag [dB]") as self.mag_y_id:
                    pass

            # -------- Phase Plot --------
            with dpg.plot(label="Phase (°)") as self.phase_plot_id:
                dpg.add_plot_legend()
                with dpg.plot_axis(dpg.mvXAxis, label="Frequency (Hz)", scale=dpg.mvPlotScale_Log10) as self.phase_x_id:
                    pass
                with dpg.plot_axis(dpg.mvYAxis, label="Phase [°]") as self.phase_y_id:
                    pass

    def clear_plot(self):
        dpg.delete_item(self.mag_y_id, children_only=True)
        dpg.delete_item(self.phase_y_id, children_only=True)

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
