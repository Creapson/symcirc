import dearpygui.dearpygui as dpg
from pydantic import Field
from typing import Literal


from gui.components.node_editor.nodes.Node import Node, NodeType
from netlist.Circuit import Circuit
from Modified_Node_Analysis import ModifiedNodalAnalysis



class ModifiedNodalAnalysisNode(Node):
    node_type: Literal[NodeType.MNA] = NodeType.MNA

    circuit: Circuit = Field(default=Circuit(), exclude=True)

    def build(self):
        self.add_input_pin("circuit_input_pin", "Connect Circuit here")

        with self.add_static_attr():
            dpg.add_button(label="Calculate Numeric Values", callback=self.update)

        super().build()

    def onlink_callback(self):
        self.circuit = self.get_input_pin_value("circuit_input_pin")

        dpg.set_value(self.uuid("circuit_input_pin"), "Circuit connected!")
        super().onlink_callback()

    def update(self):
        mna = ModifiedNodalAnalysis(self.circuit)
        mna.buildEquationsSystem()

        # get the log_space from the circuit
        log_space = self.circuit.get_sweep().tolist()

        self.add_output_pin(tag="h_out", text="H")
        self.add_output_pin_value("h_out", (log_space, mna), is_persistence=False)

        super().update()
