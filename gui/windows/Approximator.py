import dearpygui.dearpygui as dpg

from gui.windows.Window import Window


class ApproximatorWindow(Window):
    def __init__(self, h, mna, parent_id=None):
        if parent_id is not None:
            self.title = f"{parent_id}_approx_settings_window"
        else:
            self.title = "approx_settings_window"

        self.h = h
        self.mna = mna
        self.approximation_points = []
        self.drag_lines = []
        self.row_sources = {}
        # map mag_drag_line -> (freq_input, error_input)
        self.drag_to_inputs = {}

        self.approx_mag = None
        self.approx_phase = None
        super().__init__(title=self.title)
        pass

    def update(self):
        import sympy as sp

        import Approximate as ap

        self.approx = ap.approximate(
            self.mna, 0.024, sp.symbols("V_1"), sp.symbols("V_2"), (1e5,), 46
        )

        self.approx = sp.simplify(self.approx)

        approx_num = self.approx.subs(self.mna.value_dict)

        # calculate numeric values
        freq_log, magnitude_db, phase_deg = self.calculate_numeric_values(approx_num)
        # delete existing line_series
        if self.approx_mag is not None:
            dpg.delete_item(self.approx_mag)
            self.approx_mag = None
        if self.approx_phase is not None:
            dpg.delete_item(self.approx_phase)
            self.approx_phase = None

        # magnitude
        self.approx_mag = dpg.add_line_series(
            freq_log.tolist(),
            magnitude_db.tolist(),
            label="Approx",
            parent=self.uuid("y_axis_mag"),
        )
        # phase
        self.approx_phase = dpg.add_line_series(
            freq_log.tolist(),
            phase_deg.tolist(),
            label="Approx",
            parent=self.uuid("y_axis_phase"),
        )
        # show approx_func as Text
        dpg.configure_item(self.uuid("approx_func_txt"), label=str(self.approx))

        print(self.approx)

        super().update()

    def setup(self):
        def build():
            dpg.add_text(label="Test")
            self.setup_bode_plot()

            # create table
            with dpg.table(
                tag=self.uuid("approx_points_table"),
                header_row=True,
            ):
                dpg.add_table_column(label="Frequency")
                dpg.add_table_column(label="Error")
            pass

            dpg.add_text(
                default_value="Not Calculated yet!", tag=self.uuid("approx_func_txt")
            )
            dpg.add_button(label="Calculate Approx", callback=self.update)

        super().setup(build)

    def calculate_numeric_values(self, transfer_func):
        import numpy as np
        import sympy as sp

        s = sp.symbols("s")
        H_lambdified = sp.lambdify(s, transfer_func, "numpy")
        w = np.logspace(-2, 8, 10000)  # Kreisfrequenz
        jw = 1j * w

        H_eval = np.asarray(H_lambdified(jw), dtype=complex)

        if H_eval.shape == ():  # scalar → broadcast
            H_eval = np.full_like(w, H_eval, dtype=complex)

        # create solved arrays for later plotting
        freq_log = w
        magnitude_db = 20 * np.log10(np.abs(H_eval))
        phase_deg = np.angle(H_eval, deg=True)

        print("freq:\t", freq_log)
        print(type(freq_log))
        print("mag:\t", magnitude_db)
        print(type(magnitude_db))
        print("phase:\t", phase_deg)
        print(type(phase_deg))

        return freq_log, magnitude_db, phase_deg

    def on_drag(self, sender, app_data):
        """
        sender: drag line ID
        app_data: new x value (frequency in log axis)
        """
        x = float(dpg.get_value(sender))

        # find which point this drag line corresponds to
        for i, (mag_line, phase_line) in enumerate(self.drag_lines):
            if sender == mag_line:
                # update the table input
                freq_input = self.drag_to_inputs[sender]
                dpg.set_value(freq_input, x)

                # also update internal data
                _, error = self.approximation_points[i]
                self.approximation_points[i] = (x, error)
                break

    def add_approx_point(self, sender, app_data):
        # filter unwanted clicks

        if not (
            dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)
        ):
            return

        if not dpg.is_item_hovered(self.bode_plot_id):
            return

        # Mouse position in plot coordinates
        x, y = dpg.get_plot_mouse_pos()

        # add value regestriys for the drag_lines
        row_index = len(self.approximation_points)
        print("row_index", row_index)

        # Add vertical drag line two both Plots
        # Bode Plot
        mag_drag_line = dpg.add_drag_line(
            parent=self.bode_plot_id,
            color=(0, 255, 0, 255),
            default_value=x,
            callback=self.on_drag,
            vertical=True,
        )
        # Phase Plot
        phase_line = dpg.add_drag_line(
            parent=self.phase_plot_id,
            color=(0, 255, 0, 255),
            source=mag_drag_line,
            vertical=True,
        )

        self.approximation_points.append((x, 0.05))
        self.drag_lines.append((mag_drag_line, phase_line))
        self.setup_approx_point_table()

    def remove_approx_point(self, sender, app_data):
        # filter unwanted clicks

        if not (
            dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)
        ):
            return

        if not dpg.is_item_hovered(self.bode_plot_id):
            return

        # Mouse position in plot coordinates
        x, y = dpg.get_plot_mouse_pos()

        # check if list id empty
        if not self.drag_lines:
            return

        # get the neared drag_line to the click
        closest_index = min(
            range(len(self.drag_lines)),
            key=lambda i: abs(dpg.get_value(self.drag_lines[i][0]) - x),
        )

        mag_line, phase_line = self.drag_lines[closest_index]

        dpg.delete_item(mag_line)
        dpg.delete_item(phase_line)

        del self.approximation_points[closest_index]
        del self.drag_lines[closest_index]

        self.setup_approx_point_table()

    def on_freq_change(self, sender, app_data, user_data):
        mag_line, phase_line = user_data

        # update drag line position
        dpg.set_value(mag_line, app_data)

        # update internal data
        for i, (ml, pl) in enumerate(self.drag_lines):
            if ml == mag_line:
                _, error = self.approximation_points[i]
                self.approximation_points[i] = (app_data, error)
                break

    def on_error_change(self, sender, app_data, user_data):
        print("on_error_change", sender, app_data)
        # user_data is row_index
        freq, error = self.approximation_points[user_data]

        self.approximation_points[user_data] = (freq, app_data)
        pass

    def setup_approx_point_table(self):
        print("Creating table now")
        self.delete_table()

        # Add rows again
        row_index = 0
        for freq, error in self.approximation_points:
            with dpg.table_row(parent=self.uuid("approx_points_table")) as row:
                freq_input = dpg.add_input_float(
                    default_value=freq,
                    width=-1,
                    callback=self.on_freq_change,
                    # give the drag_line index that needs to be changed
                    user_data=self.drag_lines[row_index],
                )
                error_input = dpg.add_input_float(
                    default_value=error,
                    width=-1,
                    callback=self.on_error_change,
                    user_data=row_index,
                )

            self.drag_to_inputs[self.drag_lines[row_index][0]] = freq_input
            self.row_sources[row] = (freq_input, error_input)
            print(f"added row: {row}")
            row_index += 1

    def delete_table(self):
        dpg.delete_item(self.uuid("approx_points_table"), children_only=True, slot=1)

        # delete the used sources(value regestries) of each cell
        self.row_sources.clear()
        self.drag_to_inputs.clear()

    def setup_bode_plot(self):
        freq_log, magnitude_db, phase_deg = self.calculate_numeric_values(self.h)

        # Bode Plot
        with dpg.subplots(2, 1, label="", link_all_x=True, height=300):
            # -------- Magnitude Plot --------
            with dpg.plot(label="Betrag (dB)", no_menus=True) as self.bode_plot_id:
                dpg.add_plot_legend()
                dpg.plot_axis(
                    dpg.mvXAxis, label="log10(ω) [rad/s]", scale=dpg.mvPlotScale_Log10
                )
                with dpg.plot_axis(
                    dpg.mvYAxis, label="Betrag [dB]", tag=self.uuid("y_axis_mag")
                ):
                    dpg.add_line_series(
                        freq_log.tolist(),
                        magnitude_db.tolist(),
                        label="|H(jω)|",
                        tag=self.uuid("mag_series"),
                    )

            # -------- Phase Plot --------
            with dpg.plot(label="Phase (°)", no_menus=True) as self.phase_plot_id:
                dpg.add_plot_legend()
                dpg.plot_axis(
                    dpg.mvXAxis, label="log10(ω) [rad/s]", scale=dpg.mvPlotScale_Log10
                )
                with dpg.plot_axis(
                    dpg.mvYAxis, label="Phase [°]", tag=self.uuid("y_axis_phase")
                ):
                    dpg.add_line_series(
                        freq_log.tolist(),
                        phase_deg.tolist(),
                        label="∠H(jω)",
                        tag=self.uuid("phase_series"),
                    )

        # Create on_click callback for the plot

        with dpg.handler_registry():
            dpg.add_mouse_release_handler(
                button=dpg.mvMouseButton_Left, callback=self.add_approx_point
            )
            dpg.add_mouse_release_handler(
                button=dpg.mvMouseButton_Right, callback=self.remove_approx_point
            )
        """
        with dpg.handler_registry():
            dpg.add_mouse_click_handler(
                button=dpg.mvMouseButton_Left, callback=self.add_approx_point
            )
        """

        """
        with dpg.item_handler_registry() as handler:
            dpg.add_item_clicked_handler(callback=self.add_approx_point)

        dpg.bind_item_handler_registry(self.bode_plot_id, handler)
        """

    def on_close(self, sender, app_data, user_data):
        super().on_close(sender=sender, app_data=app_data, user_data=user_data)
