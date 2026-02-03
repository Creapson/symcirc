import dearpygui.dearpygui as dpg

from gui.nodes.Node import Node


class ModifiedNodalAnalysis(Node):
    def __init__(self, label, position=(100, 100)):
        self.nma = None

        super().__init__(label, position)

    def setup(self, node_editor_tag):
        def build():
            with self.add_input_attr() as magn_pin:
                dpg.add_text(
                    default_value="Connect Circuit here",
                    tag=self.uuid("circuit_input_pin"),
                )
            self.input_pins[self.uuid("circuit_input_pin")] = magn_pin

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
        self.circuit = self.get_input_pin_value(self.uuid("circuit_input_pin"))

        from Modified_Node_Analysis import ModifiedNodalAnalysis

        self.mna = ModifiedNodalAnalysis(self.circuit)
        # populate the from and to_node combo boxes
        # with the possible nodes
        nodes = list(self.mna.node_map.keys())
        dpg.configure_item(self.uuid("from_node"), items=nodes)
        dpg.configure_item(self.uuid("to_node"), items=nodes)

        dpg.set_value(self.uuid("circuit_input_pin"), "Circuit connected!")
        super().onlink_callback()

    def update(self):
        import sympy as sp

        self.mna.buildEquationsSystem()
        num_results = self.mna.solveNumerical(self.mna.value_dict)

        # use the selected nodes
        from_node = dpg.get_value(self.uuid("from_node"))
        to_node = dpg.get_value(self.uuid("to_node"))

        H = (
            num_results[sp.symbols(f"V_{to_node}")]
            / num_results[sp.symbols(f"V_{from_node}")]
        )

        self.delete_output_pins()

        # create output pins for those arrays

        with self.add_output_attr() as output_pin:
            dpg.add_text("H", tag=self.uuid("h_out"))
        self.output_pins[self.uuid("h_out")] = output_pin
        self.add_output_pin_value(self.uuid("h_out"), (H, self.mna))

        super().update()
