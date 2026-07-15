import dearpygui.dearpygui as dpg
from Modified_Node_Analysis import ModifiedNodalAnalysis
from gui.windows.Window import Window
from netlist.Circuit import Circuit
from gui.components.Table import Table, Widget_Type

from typing import Dict

class MNAEditor(Window):
    def __init__(self, mna : ModifiedNodalAnalysis, parent_tag:str):
        self.mna: ModifiedNodalAnalysis = mna

        self.tables: Dict[str,  Table] = {}

        super().__init__(title=str(parent_tag + ":CircuitEditor"), autosize=False)
        pass

    def build(self):
        with dpg.child_window(
                autosize_x=True,
                horizontal_scrollbar=True
            ):
            self.build_matrix()

        with dpg.group(horizontal=True):
            dpg.add_button(label="Save", callback=self.on_save)
            dpg.add_button(label="Close", callback=self.on_close)

    def on_save(self):
        pass

    def build_matrix(self):
        A, z = self.mna.get_equation_system()
        n = self.mna.n

        # Loop over rows and columns of Matrix A
        for i in range(n):
            with dpg.group(horizontal=True):
                for j in range(n):
                    dpg.add_input_text(
                            default_value=A[i, j],
                            width=200
                    )

        # Loop over the rows of Column Vector z
        # for i in range(n):
        #     z[i, 0] = i * 2  
