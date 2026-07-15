import dearpygui.dearpygui as dpg
from pydantic import Field
from typing import Literal, List


from gui.components.OutputPin import PinType
from gui.components.node_editor.nodes.Node import Node, NodeType
from gui.windows.MNAEditor import MNAEditor
from netlist.Circuit import Circuit
from Modified_Node_Analysis import ModifiedNodalAnalysis


class MNA(Node):
    node_type: Literal[NodeType.MNA] = NodeType.MNA

    circuit: Circuit = Field(default=Circuit(), exclude=True)
    mna: ModifiedNodalAnalysis|None = Field(default=None, exclude=True)

    def build(self):
        self.add_input_pin("circuit_input_pin", "Connect Circuit here")

        with self.add_static_attr():
            dpg.add_button(label="Calculate Numeric Values", callback=self.update)

        super().build()

    def get_possible_node_connections(self) -> List[str]:
        return ["transfer_numeric", "transfer_symbolic", "approx"]

    def onlink_callback(self):
        circuit_dict = self.get_input_pin_value("circuit_input_pin", Circuit())
        self.circuit = Circuit.model_validate(circuit_dict)

        dpg.set_value(self.uuid("circuit_input_pin"), "Circuit connected!")
        super().onlink_callback()

    def open_mna_edit(self):
        mna_editor = MNAEditor(self.mna, self.label)
        mna_editor.setup()
        pass

    def update(self):
        self.mna = ModifiedNodalAnalysis(self.circuit)
        self.mna.buildEquationsSystem()

        # get the log_space from the circuit
        log_space = self.circuit.params.get("sweep", "")

        self.add_output_pin(
                tag="h_out", 
                text="H", 
                pintype=PinType.MNA_EDIT, 
                button_callback=self.open_mna_edit, 
                button_text="Edit MNA"
        )
        self.add_output_pin_value("h_out", (log_space, self.mna), is_persistence=False)

        super().update()
