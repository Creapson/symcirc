import dearpygui.dearpygui as dpg

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
                        dpg.plot_axis(dpg.mvXAxis, label="log10(ω) [rad/s]")
                        with dpg.plot_axis(dpg.mvYAxis, label="Betrag [dB]"):
                            dpg.add_line_series(
                                [], [], label="|H(jω)|", tag=self.uuid("mag_series")
                            )

                    # -------- Phase Plot --------
                    with dpg.plot(label="Phase (°)"):
                        dpg.add_plot_legend()
                        dpg.plot_axis(dpg.mvXAxis, label="log10(ω) [rad/s]")
                        with dpg.plot_axis(dpg.mvYAxis, label="Phase [°]"):
                            dpg.add_line_series(
                                [], [], label="∠H(jω)", tag=self.uuid("phase_series")
                            )

        return super().setup(build, node_editor_tag)

    def csd_select_callback(self, sender, app_data):
        import parser.CommonSimulationData as csd

        filepath = app_data["file_path_name"]
        print(filepath)
        csd.parse_csd(filepath)

        pass

    def onlink_callback(self):
        freq_log, magnitude, phase = self.get_input_pin_value(self.uuid("line_pin"))

        # update the plots with the new values
        if freq_log is not None and magnitude is not None:
            dpg.set_value(
                self.uuid("mag_series"), [freq_log.tolist(), magnitude.tolist()]
            )

        if freq_log is not None and phase is not None:
            dpg.set_value(
                self.uuid("phase_series"), [freq_log.tolist(), phase.tolist()]
            )

        super().onlink_callback()

    def update(self):
        super().update()
