import dearpygui.dearpygui as dpg

from gui.nodes.Node import Node
from netlist.Circuit import Circuit


class ModifiedNodalAnalysis(Node):
    def __init__(self, node_editor, label, position=(100, 100)):
        self.nma = None

        super().__init__(node_editor, label, position)

    def setup(self, node_editor_tag):
        def build():
            with self.add_input_attr() as magn_pin:
                dpg.add_text(
                    default_value="Connect Circuit here",
                    tag=self.uuid("circuit_input_pin"),
                )
            self.input_pins[self.uuid("circuit_input_pin")] = magn_pin

            with self.add_static_attr():
                dpg.add_button(label="Calculate Numeric Values", callback=self.update)

        return super().setup(build, node_editor_tag)

    def onlink_callback(self):
        self.circuit : Circuit = self.get_input_pin_value(self.uuid("circuit_input_pin"))

        from Modified_Node_Analysis import ModifiedNodalAnalysis

        self.mna = ModifiedNodalAnalysis(self.circuit)

        dpg.set_value(self.uuid("circuit_input_pin"), "Circuit connected!")
        super().onlink_callback()

    def update(self):
        self.mna.buildEquationsSystem()

        # get the log_space from the circuit
        log_space = self.circuit.get_sweep()
        print(log_space)

        if not dpg.does_item_exist(self.uuid("h_out")):
            with self.add_output_attr() as output_pin:
                dpg.add_text("H", tag=self.uuid("h_out"))
            self.output_pins[self.uuid("h_out")] = output_pin
        self.add_output_pin_value(self.uuid("h_out"), (log_space, self.mna))

        super().update()
