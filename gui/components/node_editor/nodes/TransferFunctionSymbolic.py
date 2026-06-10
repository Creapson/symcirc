import dearpygui.dearpygui as dpg
from pydantic import Field

import sympy as sp
from sympy import init_printing
init_printing(use_unicode=True)

from netlist.Circuit import Circuit
from gui.components.node_editor.nodes.Node import Node, NodeType
from Modified_Node_Analysis import ModifiedNodalAnalysis
from typing import Literal, List

class TransferFunctionSymbolic(Node):
    node_type: Literal[NodeType.TRANSFER_FUNCTION_SYMBOLIC] = NodeType.TRANSFER_FUNCTION_SYMBOLIC

    mna: ModifiedNodalAnalysis = Field(default=None, exclude=True)
    sweep: str = Field(default="None", exclude=True)

    def build(self):
        with dpg.value_registry():
            dpg.add_string_value(
                default_value="Transfer Function not calculated yet!",
                tag=self.uuid("sym_tf_output"),
            )

        self.add_input_pin("num_results_input_pin", "Connect Circuit here")

        with self.add_static_attr():
            # add selection for the transfer-function
            with dpg.group(horizontal=True):
                dpg.add_text("Output Node")
                dpg.add_combo(items=[], tag=self.uuid("output_node"), width=100)
            dpg.add_button(label="Calculate Numeric Values", callback=self.update)

            dpg.add_text(default_value="Complexity Estimations", tag=self.uuid("compl_estimate"))

            with dpg.group(horizontal=True):
                dpg.add_text("Edit Sweep")
                dpg.add_input_text(default_value=self.sweep, tag=self.uuid("sweep"), width=200)

            dpg.add_input_text(source=self.uuid("sym_tf_output"), width=200)

        super().build()

    def get_possible_node_connections(self) -> List[str]:
        return ["solver_symbolic"]

    def onlink_callback(self):
        self.sweep, self.mna = self.get_input_pin_value("num_results_input_pin", ("None", None))
        dpg.configure_item(self.uuid("sweep"), default_value=self.sweep)

        A, _ = self.mna.get_equation_system()
        estimate_num_terms = self.mna.estimateTerms(A)
        print("Estimations: ", estimate_num_terms)
        dpg.configure_item(self.uuid("compl_estimate"), default_value="Complexity Estimations: " + str(estimate_num_terms))

        if self.mna is None:
            nodes = ["Update MNA"]
        else:
            nodes = self.mna.get_unknowns_as_strings()
            inputs = self.mna.get_System_Inputs()

            if dpg.does_item_exist(self.uuid("adv_settings")):
                dpg.delete_item(self.uuid("adv_settings"))

            with self.add_static_attr():
                with dpg.tree_node(label="Advanced Settings", tag=self.uuid("adv_settings")):
                    for name in inputs:
                        if name == "0": continue
                        with dpg.group(horizontal=True):
                            dpg.add_checkbox(label="Enabled", callback=lambda: dpg.configure_item(self.uuid(name), enabled=False))
                            dpg.add_text(name)
                            dpg.add_input_float(width=100)



        dpg.configure_item(self.uuid("output_node"), items=nodes)
        super().onlink_callback()

    def update(self):
        # get the sweep data from the ui
        sweep_str = dpg.get_value(self.uuid("sweep"))
        print(sweep_str)
        sweep = Circuit().get_sweep(sweep_str)        

        # use the selected nodes
        node_out = dpg.get_value(self.uuid("output_node"))

        H_sym = self.mna.solve(node_out)
        # smpl = H_sym
        # smpl = sp.cancel(H_sym)
        # smpl = sp.simplify(H_sym)
        # print(smpl)
        dpg.set_value(self.uuid("sym_tf_output"), sp.latex(H_sym))
        H_num = self.mna.solveNumerical(sweep, node_out)

        if not dpg.does_item_exist(self.uuid("h_out")):
            self.add_output_pin(tag="h_out", text="H")
        self.add_output_pin_value("h_out", (H_num.tolist(), sweep), is_persistence=False)
        super().update()
