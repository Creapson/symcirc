import dearpygui.dearpygui as dpg

from gui.windows.Window import Window

import analysis_methoden.insydes_naming as ins

from typing import Dict

# dearpygui tables are limited to 64 columns. Beyond that the matrix is drawn
# with the older group layout, which scrolls instead of fitting on screen.
MAX_TABLE_COLUMNS = 64


class STAEditor(Window):
    """Matrix view for any of the three equation system formulations.

    MNAEditor cannot be reused because it treats `mna.n` as the side length of
    the system matrix. That only holds when the circuit has no voltage
    sources: MNA grows its matrix per source, and both tableau formulations
    are larger still (n + 2b for the extended form, 2b for the normal form).
    This window reads the real matrix dimensions instead, so it never
    truncates rows.

    When the object is a normal sparse tableau it additionally labels the
    row blocks (KCL / KVL / element equations) and shows the spanning tree.

    The "Analog Insydes names" switch relabels everything the way Insydes
    prints it (V_RPI_Q1, gm_Q1, CS_VCS_Q1) so the two matrices can be read
    side by side. It only changes the text on screen, see insydes_naming.
    """

    def __init__(self, analysis, parent_tag: str):
        self.analysis = analysis
        self.tables: Dict[str, object] = {}
        self.insydes_names = True

        super().__init__(title=str(parent_tag + ":EquationSystemEditor"), autosize=False)

    def setup(self, show_menu_bar=False):
        """Open the window, replacing an older one with the same title.

        Window.setup() uses the title as the dearpygui tag. Pressing "Edit" a
        second time, or switching the formulation and pressing it again, would
        otherwise fail with "alias already exists" and no window would appear.
        """
        if dpg.does_item_exist(self.title):
            dpg.delete_item(self.title)

        return super().setup(show_menu_bar=show_menu_bar)

    def build(self):
        if self.analysis is None:
            dpg.add_text("No system yet. Press 'Calculate Numeric Values' first.")
            return

        self.build_summary()

        dpg.add_checkbox(
            label="Analog Insydes names (V_RPI_Q1, gm_Q1, CS_VCS_Q1)",
            default_value=self.insydes_names,
            callback=self._on_naming_changed,
            tag=self.uuid("insydes_names"),
        )
        dpg.add_separator()

        with dpg.child_window(autosize_x=True, horizontal_scrollbar=True,
                              tag=self.uuid("matrix_area")):
            self.build_matrix()

        with dpg.group(horizontal=True):
            dpg.add_button(label="Close", callback=self.on_close)

    def _on_naming_changed(self, sender, app_data):
        """Redraw the matrix with the other set of names."""
        self.insydes_names = app_data

        area = self.uuid("matrix_area")
        if not dpg.does_item_exist(area):
            return

        dpg.delete_item(area, children_only=True)
        dpg.push_container_stack(area)
        self.build_matrix()
        dpg.pop_container_stack()

    def _is_normal_tableau(self):
        """True when the analysis object exposes the A/B/P/Q block structure."""
        return hasattr(self.analysis, "get_blocks") and hasattr(self.analysis, "l")

    def build_summary(self):
        """Show the sizes so the structure can be checked at a glance."""
        matrix, _ = self.analysis.get_equation_system()

        dpg.add_text(f"formulation  : {type(self.analysis).__name__}")
        dpg.add_text(f"system size  : {matrix.rows} x {matrix.cols}")

        if self._is_normal_tableau():
            dpg.add_text(f"nodes without ground (n-1) = {self.analysis.n}")
            dpg.add_text(f"branches (b)               = {self.analysis.m}")
            dpg.add_text(f"independent loops (b-n+1)  = {self.analysis.l}")
            dpg.add_text(f"tree branches : {', '.join(self.analysis.get_tree_branches())}")
            dpg.add_text(f"link branches : {', '.join(self.analysis.get_link_branches())}")

        dpg.add_separator()

    def _plain_row_label(self, index):
        """Name the equation a row belongs to, when that is known.

        Row order is [KVL | KCL | element eqs.], matching Analog Insydes.
        """
        if not self._is_normal_tableau():
            return str(index + 1)

        n, l = self.analysis.n, self.analysis.l
        if index < l:
            return f"KVL {index + 1}"
        if index < l + n:
            return f"KCL {index - l + 1}"
        return self.analysis.branches[index - n - l].symbol

    def _labels(self, rows):
        """Row labels, column labels and the cell rename map for one redraw."""
        if not self.insydes_names:
            unknowns = self.analysis.get_unknowns_as_strings()
            return ([self._plain_row_label(i) for i in range(rows)], unknowns, {})

        try:
            return (ins.row_labels(self.analysis),
                    ins.unknown_labels(self.analysis),
                    ins.symbol_map(self.analysis))
        except Exception:
            # never let a naming problem hide the matrix itself
            unknowns = self.analysis.get_unknowns_as_strings()
            return ([self._plain_row_label(i) for i in range(rows)], unknowns, {})

    def build_matrix(self):
        """Render the system as [A] x [unknowns] = [rhs], Insydes-style."""
        matrix, rhs = self.analysis.get_equation_system()

        row_labels, unknowns, mapping = self._labels(matrix.rows)
        if len(unknowns) < matrix.cols:
            unknowns = unknowns + [""] * (matrix.cols - len(unknowns))

        cells = [[ins.render(matrix[i, j], mapping) for j in range(matrix.cols)]
                 for i in range(matrix.rows)]
        rhs_cells = [ins.render(rhs[i], mapping) for i in range(matrix.rows)]

        if matrix.cols + 4 <= MAX_TABLE_COLUMNS:
            self._build_matrix_table(cells, rhs_cells, row_labels, unknowns)
        else:
            self._build_matrix_groups(cells, rhs_cells, row_labels, unknowns)

    def _build_matrix_table(self, cells, rhs_cells, row_labels, unknowns):
        """Compact grid: label | A | x | unknowns | = | rhs, all in one table.

        One table keeps the unknown next to its own row without any manual
        height matching, and sizes every column to its content the way Insydes
        prints the system.
        """
        with dpg.table(header_row=True, policy=dpg.mvTable_SizingFixedFit,
                       borders_innerV=True, borders_outerV=True,
                       borders_outerH=True, scrollX=True, scrollY=True,
                       freeze_columns=1, freeze_rows=1,
                       height=-1, width=-1):

            dpg.add_table_column(label="A")
            for j in range(len(cells[0]) if cells else 0):
                dpg.add_table_column(label=str(j + 1))
            dpg.add_table_column(label="x")
            dpg.add_table_column(label="unknowns")
            dpg.add_table_column(label="=")
            dpg.add_table_column(label="RHS")

            for i, row in enumerate(cells):
                with dpg.table_row():
                    dpg.add_text(row_labels[i] if i < len(row_labels) else str(i + 1))
                    for value in row:
                        dpg.add_text(value)
                    dpg.add_text("x" if i == 0 else "")
                    dpg.add_text(unknowns[i] if i < len(unknowns) else "")
                    dpg.add_text("=" if i == 0 else "")
                    dpg.add_text(rhs_cells[i])

    def _build_matrix_groups(self, cells, rhs_cells, row_labels, unknowns):
        """Fallback for systems too wide for a dearpygui table."""
        with dpg.group(horizontal=True):
            with dpg.group():
                dpg.add_text("A".ljust(12))
                for i, row in enumerate(cells):
                    with dpg.group(horizontal=True):
                        label = row_labels[i] if i < len(row_labels) else str(i + 1)
                        dpg.add_text(label.ljust(12))
                        for value in row:
                            dpg.add_input_text(default_value=value, width=70,
                                               readonly=True)

            dpg.add_text("   x   ")

            with dpg.group():
                dpg.add_text("unknowns")
                for name in unknowns:
                    dpg.add_input_text(default_value=name, width=160, readonly=True)

            dpg.add_text("   =   ")

            with dpg.group():
                dpg.add_text("RHS")
                for value in rhs_cells:
                    dpg.add_input_text(default_value=value, width=90, readonly=True)
