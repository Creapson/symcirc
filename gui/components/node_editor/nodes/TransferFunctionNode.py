import dearpygui.dearpygui as dpg
from pydantic import Field

from gui.components.node_editor.nodes.Node import Node, NodeType
from Modified_Node_Analysis import ModifiedNodalAnalysis
from typing import Literal, List

class TransferFunctionNode(Node):
    node_type: Literal[NodeType.TRANSFER_FUNCTION] = NodeType.TRANSFER_FUNCTION

    mna: ModifiedNodalAnalysis = Field(default=None, exclude=True)
    sweep: List[float] = Field(default_factory=list, exclude=True)

    def build(self):
        self.add_input_pin("num_results_input_pin", "Connect Circuit here")


        with self.add_static_attr():
            # add selection for the transfer-function
            with dpg.group(horizontal=True):
                dpg.add_text("Output Node")
                dpg.add_combo(items=[], tag=self.uuid("output_node"), width=100)
            dpg.add_button(label="Calculate Numeric Values", callback=self.update)

        super().build()


    def onlink_callback(self):
        self.sweep, self.mna = self.get_input_pin_value("num_results_input_pin", ([], None))

        if self.mna is None:
            nodes = ["Update MNA"]
        else:
            nodes = self.mna.get_unknowns_as_strings()
            inputs = self.mna.get_System_Inputs()

            with self.add_static_attr():
                with dpg.tree_node(label="Advanced Settings"):
                    for name in inputs:
                        if name == "0": continue
                        with dpg.group(horizontal=True):
                            dpg.add_checkbox(label="Enabled", callback=lambda: dpg.configure_item(self.uuid(name), enabled=False))
                            dpg.add_text(name)
                            dpg.add_input_float(width=100)



        dpg.configure_item(self.uuid("output_node"), items=nodes)
        super().onlink_callback()

    def update(self):
        # use the selected nodes
        node_out = dpg.get_value(self.uuid("output_node"))

        H = self.mna.solveNumerical(self.sweep, node_out, )

        self.add_output_pin(tag="h_out", text="H")
        self.add_output_pin_value("h_out", (H.tolist(), self.sweep), is_persistence=False)
        super().update()
