"""The normal tableau must reproduce Analog Insydes' matrix cell for cell.

Analog Insydes is the reference implementation this project is checked against,
so its SparseTableau output for test_circuits/Basisschaltung_2N2222.cir is
pinned here. The reference was exported from Mathematica with

    eqs = CircuitEquations[netlist, Formulation -> SparseTableau];
    {c0, c1} = CoefficientArrays[eqs[[1]], eqs[[2]]];

and is stored sparsely: REFERENCE_ROWS[i][j] is the coefficient in row i,
column j, columns missing from a row are zero.

What is being pinned is the *formulation*, not the answer. Any spanning tree
gives a correct and equivalent tableau, but only the tree Insydes picks - grow
it in plain netlist order, see TestSpanningTreeOrder - reproduces this KVL
block. Sorting the branches into a "normal tree" first silently permutes and
re-signs nine of the eleven KVL rows, which is what this test caught.

Run from the project root:
    python -m unittest discover -s tests -t .
"""

import os
import unittest

import sympy as sp

import analysis_methoden.insydes_naming as ins
from analysis_methoden.Analysis_Factory import create_analysis
from parser.NetlistParser import get_circuit_from_file

CIRCUIT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "test_circuits")
CIRCUIT_NAME = "Basisschaltung_2N2222"
BIPOLAR_MODEL = "BJT_BasicModel"

# Insydes' unknown vector, [u_1..u_b | i_1..i_b]. Insydes spells the model's
# controlled source VC and prefixes the controlling port with C, this project
# spells it VCS; only the spelling differs, the branch is the same one.
REFERENCE_UNKNOWNS = [
    "V_CB", "V_C2", "V_RL", "V_VIN", "V_RPI_Q1", "V_RO_Q1", "V_CBC_Q1",
    "V_CBE_Q1", "V_VC_Q1", "VC_VC_Q1", "V_CBX_Q1", "V_R2", "V_RC", "V_RS",
    "V_C1", "V_VCC", "V_R1", "V_RE",
    "I_CB", "I_C2", "I_RL", "I_VIN", "I_RPI_Q1", "I_RO_Q1", "I_CBC_Q1",
    "I_CBE_Q1", "I_VC_Q1", "IC_VC_Q1", "I_CBX_Q1", "I_R2", "I_RC", "I_RS",
    "I_C1", "I_VCC", "I_R1", "I_RE",
]

# Insydes' name for the model's controlled source and its controlling port,
# translated into the spelling insydes_naming builds
CONTROLLED_SOURCE_SPELLING = {
    "V_VC_Q1": "V_VCS_Q1",
    "VC_VC_Q1": "V_CS_VCS_Q1",
    "I_VC_Q1": "I_VCS_Q1",
    "IC_VC_Q1": "I_CS_VCS_Q1",
}

# rows 0..10 are KVL (one per link), 11..17 KCL (one per node), 18..35 the
# element equations (one per branch, in branch order)
KVL_ROWS, KCL_ROWS, ELEMENT_ROWS = range(0, 11), range(11, 18), range(18, 36)

REFERENCE_ROWS = [
    {0: "1", 1: "-1", 2: "-1", 4: "-1", 5: "1"},
    {0: "-1", 1: "1", 2: "1", 6: "1"},
    {4: "-1", 7: "1"},
    {0: "1", 1: "-1", 2: "-1", 4: "-1", 8: "1"},
    {4: "-1", 9: "1"},
    {0: "-1", 1: "1", 2: "1", 10: "1"},
    {0: "-1", 11: "1"},
    {0: "1", 3: "-1", 4: "-1", 13: "1", 14: "1"},
    {1: "-1", 2: "-1", 12: "-1", 15: "1"},
    {0: "-1", 1: "1", 2: "1", 16: "1"},
    {0: "-1", 4: "1", 17: "1"},
    {21: "1", 31: "1"},
    {31: "-1", 32: "1"},
    {22: "-1", 23: "-1", 25: "-1", 26: "-1", 27: "-1", 32: "-1", 35: "1"},
    {19: "1", 23: "1", 24: "-1", 26: "1", 28: "-1", 30: "-1", 34: "-1"},
    {18: "1", 22: "1", 24: "1", 25: "1", 27: "1", 28: "1", 29: "1", 34: "1"},
    {30: "1", 33: "1"},
    {19: "-1", 20: "1"},
    {0: "CB*s", 18: "-1"},
    {1: "C2*s", 19: "-1"},
    {2: "-1", 20: "RL"},
    {3: "1"},
    {4: "-1", 22: "Rpi_Q1"},
    {5: "-1", 23: "Ro_Q1"},
    {6: "Cbc_Q1*s", 24: "-1"},
    {7: "Cbe_Q1*s", 25: "-1"},
    {9: "gm_Q1", 26: "-1"},
    {27: "1"},
    {10: "Cbx_Q1*s", 28: "-1"},
    {11: "-1", 29: "R2"},
    {12: "-1", 30: "RC"},
    {13: "-1", 31: "RS"},
    {14: "C1*s", 32: "-1"},
    {15: "1"},
    {16: "-1", 34: "R1"},
    {17: "-1", 35: "RE"},
]

# only the AC source drives the circuit
REFERENCE_RHS = {21: "VIN"}


def build_tableau():
    """Assemble the normal tableau for the reference circuit."""
    circuit = get_circuit_from_file(os.path.join(CIRCUIT_DIR, CIRCUIT_NAME + ".cir"))
    circuit.set_bipolar_model(BIPOLAR_MODEL)
    circuit.set_separator("_")
    circuit.flatten(flatten_models=True,
                    out_file_path=os.path.join(CIRCUIT_DIR, CIRCUIT_NAME + ".out"))

    tableau = create_analysis(circuit, method="SparseTableau")
    tableau.buildEquationsSystem()
    return tableau


def _fold(expression):
    """Upper case every symbol so both spellings of a name compare equal.

    Insydes capitalises a model parameter after the model (Rpi_Q1) where this
    project keeps the netlist spelling (rpi_Q1).
    """
    expression = sp.sympify(expression)
    return sp.expand(expression.subs(
        {symbol: sp.Symbol(str(symbol).upper()) for symbol in expression.free_symbols}))


class TestInsydesReferenceMatrix(unittest.TestCase):
    """Cell by cell diff against the Analog Insydes export."""

    @classmethod
    def setUpClass(cls):
        circuit = get_circuit_from_file(os.path.join(CIRCUIT_DIR, CIRCUIT_NAME + ".cir"))
        circuit.set_bipolar_model(BIPOLAR_MODEL)
        circuit.set_separator("_")
        circuit.flatten(flatten_models=True,
                        out_file_path=os.path.join(CIRCUIT_DIR, CIRCUIT_NAME + ".out"))

        cls.tableau = create_analysis(circuit, method="SparseTableau")
        cls.tableau.buildEquationsSystem()

        mapping = ins.symbol_map(cls.tableau)
        cls.ours = [[_fold(cls.tableau.T[row, column].subs(mapping)) for column in range(36)]
                    for row in range(36)]
        cls.ours_rhs = [_fold(cls.tableau.RHS[row].subs(mapping)) for row in range(36)]
        cls.theirs = [[_fold(REFERENCE_ROWS[row].get(column, "0")) for column in range(36)]
                      for row in range(36)]
        cls.theirs_rhs = [_fold(REFERENCE_RHS.get(row, "0")) for row in range(36)]

    def test_shape_matches(self):
        """Both tableaus are 36 x 36 with the same block split."""
        self.assertEqual(self.tableau.T.shape, (36, 36))
        self.assertEqual(self.tableau.l, len(KVL_ROWS))
        self.assertEqual(self.tableau.n, len(KCL_ROWS))
        self.assertEqual(self.tableau.m, len(ELEMENT_ROWS))

    def test_unknowns_line_up(self):
        """Our unknown vector is Insydes' one, column for column."""
        self.assertEqual(ins.unknown_labels(self.tableau),
                         [CONTROLLED_SOURCE_SPELLING.get(name, name)
                          for name in REFERENCE_UNKNOWNS])

    def test_every_row_matches(self):
        """No row of the 36 x 36 tableau differs from the reference.

        The rows are reported one by one because a wrong spanning tree shows up
        as a handful of permuted KVL rows, not as a scattering of single cells.
        """
        for row in range(36):
            with self.subTest(row=row, block=self.block_of(row)):
                self.assertEqual(self.ours[row], self.theirs[row])

    def test_right_hand_side_matches(self):
        """Only the AC source appears on the right hand side, with sign."""
        self.assertEqual(self.ours_rhs, self.theirs_rhs)

    @staticmethod
    def block_of(row):
        """Name of the row block a row index falls into."""
        if row in KVL_ROWS:
            return "KVL"
        return "KCL" if row in KCL_ROWS else "element"


if __name__ == "__main__":
    unittest.main()
