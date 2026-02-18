import dearpygui.dearpygui as dpg
import numpy as np

from gui.nodes.Node import Node


class BodePlot(Node):
    def setup(self, node_editor_tag):
        def build():
            # create pins for all nessary inputs
            with self.add_input_attr() as input_pin:
                dpg.add_text(
                    default_value="Connect freq_log here!",
                    tag=self.uuid("line_pin"),
                )
            self.input_pins[self.uuid("line_pin")] = input_pin

            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self.csd_select_callback,
                tag=f"{self.node_id}_file_dialog_id",
                width=700,
                height=400,
            ):
                dpg.add_file_extension(".csd")

            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_button(
                    label="Open File Dialog",
                    callback=lambda: dpg.show_item(f"{self.node_id}_file_dialog_id"),
                )
                with dpg.subplots(
                    2, 1, label="", link_all_x=True, height=600
                ) as subplot_id:
                    # -------- Magnitude Plot --------
                    with dpg.plot(label="Betrag (dB)"):
                        dpg.add_plot_legend()
                        dpg.add_plot_axis(
                            dpg.mvXAxis,
                            label="Frequency (Hz)",
                            scale=dpg.mvPlotScale_Log10,
                        )
                        with dpg.plot_axis(dpg.mvYAxis, label="Betrag [dB]"):
                            dpg.add_line_series(
                                [], [], label="|H(jω)|", tag=self.uuid("mag_series")
                            )

                    # -------- Phase Plot --------
                    with dpg.plot(label="Phase (°)"):
                        dpg.add_plot_legend()

                        dpg.add_plot_axis(
                            dpg.mvXAxis,
                            label="Frequency (Hz)",
                            scale=dpg.mvPlotScale_Log10,
                        )
                        with dpg.plot_axis(dpg.mvYAxis, label="Phase [°]"):
                            dpg.add_line_series(
                                [], [], label="∠H(jω)", tag=self.uuid("phase_series")
                            )

        return super().setup(build, node_editor_tag)

    def csd_select_callback(self, sender, app_data):
        import parser.CommonSimulationData as csd

        filepath = app_data["file_path_name"]
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
        pass

    def onlink_callback(self):
        freq_log, magnitude, phase = self.get_input_pin_value(self.uuid("line_pin"))
        self.populate_plot(freq_log.tolist(), magnitude.tolist(), phase.tolist())
        super().onlink_callback()

    def populate_plot(self, freq, mag, phase):
        if freq is not None and mag is not None:
            dpg.set_value(self.uuid("mag_series"), [freq, mag])

        if freq is not None and phase is not None:
            dpg.set_value(self.uuid("phase_series"), [freq, phase])

    def update(self):
        super().update()
