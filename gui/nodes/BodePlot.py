import dearpygui.dearpygui as dpg

from gui.nodes.Node import Node


class BodePlot(Node):
    def setup(self, node_editor_tag):
        def build():
            # create pins for all nessary inputs
            with self.add_input_attr() as input_pin:
                dpg.add_text(
                    default_value="Connect freq_log here!",
                    tag=self.uuid("freq_log_pin"),
                )
            self.input_pins[self.uuid("freq_log_pin")] = input_pin

            with self.add_input_attr() as magn_pin:
                dpg.add_text(
                    default_value="Connect magnitude here!",
                    tag=self.uuid("magnitude_pin"),
                )
            self.input_pins[self.uuid("magnitude_pin")] = magn_pin

            with self.add_input_attr() as phase_pin:
                dpg.add_text(
                    default_value="Connect phase here!", tag=self.uuid("phase_pin")
                )
            self.input_pins[self.uuid("phase_pin")] = phase_pin

            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
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

    def onlink_callback(self):
        freq_log = self.get_input_pin_value(self.uuid("freq_log_pin"))
        magnitude = self.get_input_pin_value(self.uuid("magnitude_pin"))
        phase = self.get_input_pin_value(self.uuid("phase_pin"))
        print(freq_log)
        print(magnitude)
        print(phase)

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
