import dearpygui.dearpygui as dpg

from Approximate import Approximation
from gui.windows.Window import Window
from gui.components.BodePlot import BodePlot


class ApproximatorWindow(Window):
    def __init__(self, sweep, mna, par_node, parent_id=None):
        if parent_id is not None:
            self.title = f"{parent_id}_approx_settings_window"
        else:
            self.title = "approx_settings_window"

        self.par_node = par_node
        self.sweep = sweep
        self.mna = mna
        self.approximation_points = []
        self.drag_lines = []
        self.row_sources = {}
        self.drag_to_inputs = {}
        self.mna_approx = None

        self.approx_mag = None
        self.approx_phase = None

        self.bode_plot = BodePlot()

        super().__init__(title=self.title, autosize=False)

    def update(self):
        import sympy as sp

        from Approximate import Approximation

        ap = Approximation(self.mna)
        print(self.approximation_points)

        to_node = dpg.get_value(self.uuid("to_node"))

        elimination_method = dpg.get_value(self.uuid("elim_mothod"))
        rel_error_threshold = dpg.get_value(self.uuid("rel_error_threshold"))
        sorting_method = dpg.get_value(self.uuid("sorting_method"))
        column = dpg.get_value(self.uuid("column"))

        self.mna_approx = ap.approximate(
            to_node,
            self.approximation_points,
            elimination_method,
            rel_error_threshold,
            sorting_method,
            column,
        )

        numeric_values = self.mna_approx.solveNumerical(self.sweep, to_node)

        # calculate numeric values and plot them
        freq_log, magnitude_db, phase_deg = self.calculate_numeric_values(numeric_values)
        self.add_plot_line(freq_log, magnitude_db, phase_deg, "Approximation")

        self.par_node.update()
        super().update()

    def add_plot_line(self, freq_log, magnitude_db, phase_deg, label="None"):
        self.bode_plot.add_line_series(label, freq_log, magnitude_db, phase_deg)

    def build(self):
        # add selection for the transfer-function
        nodes = self.mna.get_unknowns_as_strings()
        with dpg.group(horizontal=True):
            dpg.add_text("To Node:")
            dpg.add_combo(items=nodes, tag=self.uuid("to_node"))

        dpg.add_button(label="Confirm TransferFunction", callback=self.tf_selected)

        self.bode_plot.setup()
        with dpg.handler_registry():
            dpg.add_mouse_release_handler(
                button=dpg.mvMouseButton_Left, callback=self.add_approx_point
            )
            dpg.add_mouse_release_handler(
                button=dpg.mvMouseButton_Right, callback=self.remove_approx_point
            )

        # create table
        with dpg.table(
            tag=self.uuid("approx_points_table"),
            header_row=True,
        ):
            dpg.add_table_column(label="Frequency")
            dpg.add_table_column(label="Error")
        pass

        sort_methods = Approximation.get_Sorting_Methods()
        with dpg.group(horizontal=True):
            dpg.add_text("Sorting Method")
            dpg.add_combo(items=sort_methods, tag=self.uuid("sorting_method"), default_value=sort_methods[0])

        with dpg.group(horizontal=True):
            dpg.add_text("Reletive error threshold")
            dpg.add_input_float(default_value=0.6, tag=self.uuid("rel_error_threshold"))

        elim_methods = Approximation.get_Elimination_Methods()
        with dpg.group(horizontal=True):
            dpg.add_text("Elimination Method")
            dpg.add_combo(items=elim_methods, tag=self.uuid("elim_mothod"), default_value=elim_methods[0])

        with dpg.group(horizontal=True):
            dpg.add_text("Column")
            dpg.add_input_int(default_value=0, tag=self.uuid("column"))

        dpg.add_text(
            default_value="Not Calculated yet!", tag=self.uuid("approx_func_txt")
        )

        dpg.add_button(label="Calculate Approx", callback=self.update)

        super().build()

    def tf_selected(self, sender, app_data):
        to_node = dpg.get_value(self.uuid("to_node"))

        print(self.sweep)
        print(to_node)
        h = self.mna.solveNumerical(self.sweep, to_node)

        freq_log, magnitude_db, phase_deg = self.calculate_numeric_values(h)
        self.add_plot_line(freq_log, magnitude_db, phase_deg, "Numeric Calculation")

    def calculate_numeric_values(self, h):
        import numpy as np
        freq_log = self.sweep
        magnitude_db = 20 * np.log10(np.abs(h)).flatten().tolist()
        phase_deg = np.unwrap(np.angle(h, deg=True), axis=0).flatten().tolist()

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

        if not dpg.is_item_hovered(self.bode_plot.mag_plot_id):
            return

        # Mouse position in plot coordinates
        x, y = dpg.get_plot_mouse_pos()

        # add value regestriys for the drag_lines
        row_index = len(self.approximation_points)
        print("row_index", row_index)

        # Add vertical drag line two both Plots
        # Bode Plot
        mag_drag_line = dpg.add_drag_line(
            parent=self.bode_plot.mag_plot_id,
            color=(0, 255, 0, 255),
            default_value=x,
            callback=self.on_drag,
            vertical=True,
        )
        # Phase Plot
        phase_line = dpg.add_drag_line(
            parent=self.bode_plot.phase_plot_id,
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

        if not dpg.is_item_hovered(self.bode_plot.mag_plot_id):
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

    def on_close(self, sender, app_data, user_data):
        super().on_close(sender=sender, app_data=app_data, user_data=user_data)
