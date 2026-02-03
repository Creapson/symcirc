import dearpygui.dearpygui as dpg

from gui.nodes.Node import Node


class NumericSolver(Node):
    def setup(self, node_editor_tag):
        def build():
            with dpg.value_registry():
                dpg.add_int_value(default_value=2, tag=self.uuid("start_log_int"))
                dpg.add_int_value(default_value=8, tag=self.uuid("end_log_int"))
                dpg.add_int_value(default_value=10000, tag=self.uuid("points_in_log"))

            with self.add_input_attr() as input_pin:
                dpg.add_text(
                    default_value="Connect H here",
                    tag=self.uuid("h_input_pin"),
                )
            self.input_pins[self.uuid("h_input_pin")] = input_pin

            with self.add_static_attr():
                dpg.add_text("Configure the log-Space")

                with dpg.group(horizontal=True):
                    dpg.add_text("Start Frequenzy in 10^x")
                    dpg.add_input_int(
                        label="input int", source=self.uuid("start_log_int")
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("End Frequenzy in 10^x")
                    dpg.add_input_int(
                        label="input int", source=self.uuid("end_log_int")
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("Number of Points between start and end")
                    dpg.add_input_int(
                        label="input int", source=self.uuid("points_in_log")
                    )

                dpg.add_button(label="Calculate Numeric Values", callback=self.update)

        return super().setup(build, node_editor_tag)

    def onlink_callback(self):
        self.h, _ = self.get_input_pin_value(self.uuid("h_input_pin"))

        super().onlink_callback()

    def update(self):
        import numpy as np
        import sympy as sp

        s = sp.symbols("s")
        # --- 2. SymPy → numerische Funktion umwandeln ---
        H_lambdified = sp.lambdify(s, self.h, "numpy")
        # --- 3. Frequenzachse definieren ---
        w = np.logspace(-2, 8, 10000)  # Kreisfrequenz
        jw = 1j * w
        H_eval = H_lambdified(jw)

        # create solved arrays for later plotting
        freq_log = np.log10(w)
        magnitude_db = 20 * np.log10(np.abs(H_eval))
        phase_deg = np.angle(H_eval, deg=True)

        print(freq_log)
        print(magnitude_db)
        print(phase_deg)

        # freq_log
        with self.add_output_attr() as output_pin:
            dpg.add_text("fraq_log (x-Achse)", tag=self.uuid("freq_log_out"))
        self.output_pins[self.uuid("freq_log_out")] = output_pin
        self.add_output_pin_value(self.uuid("freq_log_out"), freq_log)

        # freq_log
        with self.add_output_attr() as output_pin:
            dpg.add_text("magnitude_db (y-Achse)", tag=self.uuid("magnitude_out"))
        self.output_pins[self.uuid("magnitude_out")] = output_pin
        self.add_output_pin_value(self.uuid("magnitude_out"), magnitude_db)

        # freq_log
        with self.add_output_attr() as output_pin:
            dpg.add_text("phase_deg (y-Achse)", tag=self.uuid("phase_out"))
        self.output_pins[self.uuid("phase_out")] = output_pin
        self.add_output_pin_value(self.uuid("phase_out"), phase_deg)
        super().update()
