import dearpygui.dearpygui as dpg
from pydantic import Field
from typing import Literal, List, Union


from gui.components.OutputPin import PinType
from gui.components.node_editor.nodes.Node import Node, NodeType
from gui.windows.STAEditor import STAEditor
from netlist.Circuit import Circuit
from analysis_methoden.Modified_Node_Analysis import ModifiedNodalAnalysis
from analysis_methoden.Sparse_Tableau_Extended import SparseTableau
from analysis_methoden.Sparse_Tableau_Normal import SparseTableauNormal
from analysis_methoden.Analysis_Factory import create_analysis, available_methods, SPARSE_TABLEAU


class STA(Node):
    """Equation system node with a selectable formulation.

    A dropdown lets the user pick between the three formulations:
    ExtendedTableau, ModifiedNodal and SparseTableau. Internally this calls
    analysis_methoden.Analysis_Factory.create_analysis(). All three classes expose the same
    interface, so downstream nodes (TransferFunctionNumeric,
    TransferFunctionSymbolic, ApproximatorNode) work unchanged no matter
    which one was picked.
    """

    node_type: Literal[NodeType.STA] = NodeType.STA

    circuit: Circuit = Field(default=Circuit(), exclude=True)
    method: str = Field(default=SPARSE_TABLEAU)
    analysis: Union[
        ModifiedNodalAnalysis, SparseTableau, SparseTableauNormal, None
    ] = Field(default=None, exclude=True)

    def build(self):
        self.add_input_pin("circuit_input_pin", "Connect Circuit here")

        with self.add_static_attr():
            dpg.add_combo(
                items=available_methods(),
                default_value=self.method,
                label="Method",
                callback=self._on_method_changed,
                tag=self.uuid("method_combo"),
            )
            dpg.add_button(label="Calculate Numeric Values", callback=self.update)

        super().build()

    def _on_method_changed(self, sender, app_data):
        """Remember the formulation the user picked in the dropdown."""
        self.method = app_data

    def get_possible_node_connections(self) -> List[str]:
        return ["transfer_numeric", "transfer_symbolic", "approx"]

    def onlink_callback(self):
        circuit_dict = self.get_input_pin_value("circuit_input_pin", Circuit())
        self.circuit = Circuit.model_validate(circuit_dict)

        dpg.set_value(self.uuid("circuit_input_pin"), "Circuit connected!")
        super().onlink_callback()

    def open_editor(self):
        """Open the matrix view. STAEditor handles all three formulations."""
        editor = STAEditor(self.analysis, self.label)
        editor.setup()

    def update(self):
        self.analysis = create_analysis(self.circuit, method=self.method)
        self.analysis.buildEquationsSystem()

        # get the log_space from the circuit
        log_space = self.circuit.params.get("sweep", "")

        self.add_output_pin(
            tag="h_out",
            text="H",
            pintype=PinType.MNA_EDIT,
            button_callback=self.open_editor,
            button_text=f"Edit {self.method}",
        )
        self.add_output_pin_value("h_out", (log_space, self.analysis), is_persistence=False)

        super().update()
