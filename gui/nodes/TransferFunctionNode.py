import dearpygui.dearpygui as dpg

from gui.nodes.Node import Node, NodeType
from typing import Literal

class TransferFunctionNode(Node):
    node_type: Literal[NodeType.TRANSFER_FUNCTION] = NodeType.TRANSFER_FUNCTION

    def build(self):
        with self.add_input_attr() as magn_pin:
            dpg.add_text(
                default_value="Connect Circuit here",
                tag=self.uuid("num_results_input_pin"),
            )
        self.input_pins[self.uuid("num_results_input_pin")] = magn_pin

        with self.add_static_attr():
            # add selection for the transfer-function
            with dpg.group(horizontal=True):
                dpg.add_text("From Node:")
                dpg.add_combo(items=[], tag=self.uuid("from_node"), width=100)

            with dpg.group(horizontal=True):
                dpg.add_text("To Node:")
                dpg.add_combo(items=[], tag=self.uuid("to_node"), width=100)

            dpg.add_button(label="Calculate Numeric Values", callback=self.update)

        super().build()


    def onlink_callback(self):
        self.data["mna"] = self.get_input_pin_value(
            self.uuid("num_results_input_pin")
        )

        nodes = list(self.data["mna"].node_map.keys())
        dpg.configure_item(self.uuid("from_node"), items=nodes)
        dpg.configure_item(self.uuid("to_node"), items=nodes)
        super().onlink_callback()

    def update(self):
        import sympy as sp

        # use the selected nodes
        from_node = dpg.get_value(self.uuid("from_node"))
        to_node = dpg.get_value(self.uuid("to_node"))

        H = self.data["mna"].solveNumerical(self.data["mna"].value_dict, to_node, from_node)

        self.add_output_pin(tag="h_out", text="H")
        self.add_output_pin_value(self.uuid("h_out"), (sweep, H))
        super().update()
