import dearpygui.dearpygui as dpg

from gui.nodes.Node import Node


class TransferFunctionNode(Node):
    def setup(self, node_editor_tag):
        def build():
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
                    dpg.add_combo(items=[], tag=self.uuid("from_node"))

                with dpg.group(horizontal=True):
                    dpg.add_text("To Node:")
                    dpg.add_combo(items=[], tag=self.uuid("to_node"))

                dpg.add_button(label="Calculate Numeric Values", callback=self.update)

        return super().setup(build, node_editor_tag)

    def onlink_callback(self):
        self.num_results, self.mna = self.get_input_pin_value(
            self.uuid("num_results_input_pin")
        )

        nodes = list(self.mna.node_map.keys())
        dpg.configure_item(self.uuid("from_node"), items=nodes)
        dpg.configure_item(self.uuid("to_node"), items=nodes)
        super().onlink_callback()

    def update(self):
        import sympy as sp

        # use the selected nodes
        from_node = dpg.get_value(self.uuid("from_node"))
        to_node = dpg.get_value(self.uuid("to_node"))

        H = (
            self.num_results[sp.symbols(f"V_{to_node}")]
            / self.num_results[sp.symbols(f"V_{from_node}")]
        )

        if not dpg.does_item_exist(self.uuid("h_out")):
            with self.add_output_attr() as output_pin:
                dpg.add_text("H", tag=self.uuid("h_out"))
            self.output_pins[self.uuid("h_out")] = output_pin
        self.add_output_pin_value(self.uuid("h_out"), H)
        super().update()
