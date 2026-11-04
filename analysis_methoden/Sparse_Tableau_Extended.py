"""Sparse Tableau Analysis (STA) for symbolic and numeric circuit analysis.

The order of the unknowns and of the row blocks follows Analog Insydes'
SparseTableau.m (ExtendedTableau variant): branch voltages and currents come
before node potentials, and the branch voltage definition comes before KCL.

The unknown vector is

    x = [ u_1 .. u_b | i_1 .. i_b | e_1 .. e_n ]

with `b` branch voltages, `b` branch currents and `n` non-ground node
potentials.  The resulting system reads

    |  I    0   -A^T |   | u |   | 0 |
    |  0    A    0   | * | i | = | 0 |
    |  H    G    0   |   | e |   | w |

    row block 1 : branch voltage definition  u - A^T * e     = 0
    row block 2 : KCL                        A * i           = 0
    row block 3 : element equations          H * u + G * i   = w
"""

import logging

import numpy as np
import sympy as sp

import netlist.Circuit as Circuit
import Pspice_util as pu
from Equation_Formulator import EquationFormulator

logger = logging.getLogger(__name__)

GROUND_NAMES = ("0", "gnd", "GND", "ground", "Ground", "GROUND")

# element types that own an additional controlling branch
CONTROLLED_SOURCES = ("E", "G", "F", "H")


class Branch:
    """A single branch of the tableau.

    Attributes:
        element: the netlist element this branch belongs to.
        node_p (str): positive node name.
        node_n (str): negative node name.
        is_control (bool): True if this is the controlling port of a
            controlled source, False for a normal / output branch.
        symbol (str): name used to build the I_ / U_ symbols.
    """

    def __init__(self, element, node_p, node_n, is_control=False):
        self.element = element
        self.node_p = node_p
        self.node_n = node_n
        self.is_control = is_control
        self.symbol = f"{element.get_symbol()}_ctrl" if is_control else element.get_symbol()


class SparseTableau(EquationFormulator):
    """Class for the sparse tableau analysis method."""

    ct: Circuit
    value_dict: dict

    def __init__(self, circuit: Circuit):
        """Initialize the class.

        Args:
            circuit (Circuit): the circuit to analyze. It has to be flattened,
                i.e. it must not contain subcircuits or transistor models.
        """
        self.ct = circuit
        self.value_dict = self.generateValueDict(self.ct)

        self.s = sp.symbols("s")

        self._build_node_map()
        self._build_branches()

        self.n = len(self.node_map) - 1 if self._has_ground else len(self.node_map)
        self.m = len(self.branches)

        # OPTIMIZATION 1: all matrices use SymPy's SparseMatrix structure
        self.A = sp.SparseMatrix(self.n, self.m, {})
        self.G = sp.SparseMatrix(self.m, self.m, {})
        self.H = sp.SparseMatrix(self.m, self.m, {})
        self.w = sp.SparseMatrix(self.m, 1, {})
        self.RHS = sp.SparseMatrix(self.n + 2 * self.m, 1, {})
        self.T = sp.SparseMatrix(0, 0, {})

        self._build_unknowns()

        self.sym_result = {}
        self.num_result = {}

    # ------------------------------------------------------------------
    # setup helpers
    # ------------------------------------------------------------------

    def generateValueDict(self, ct: Circuit):
        """Map every element symbol to its numeric value."""
        value_dict = {}

        for element in ct.elements:
            symbol = sp.symbols(element.get_symbol())
            element_type = element.type.upper()

            match element_type:
                case "R" | "L" | "C":
                    raw = element.params.get("value_dc")
                case "V" | "I":
                    raw = element.params.get("value_ac", "0")
                case "E" | "F" | "G" | "H":
                    raw = element.params.get("value")
                case _:
                    continue

            if raw is None:
                logger.warning("Element %s has no value, its symbol stays symbolic.",
                               element.get_symbol())
                continue

            try:
                value_dict[symbol] = pu.pspice_to_float(str(raw))
            except (ValueError, TypeError):
                value_dict[symbol] = sp.sympify(raw)

        return value_dict

    def _build_node_map(self):
        """Map every node name to a consecutive index, ground is always 0."""
        self.node_map = {}
        self._has_ground = False

        for node in self.ct.nodes:
            if node in GROUND_NAMES:
                self.node_map[node] = 0
                self._has_ground = True

        def _node_sort_key(name):
            # numeric node names sort as numbers (1, 2, ..., 10), everything
            # else (named nets like "ua") sorts alphabetically after them
            try:
                return (0, int(name))
            except ValueError:
                return (1, name)

        non_ground_nodes = sorted(
            {node for node in self.ct.nodes if node not in self.node_map},
            key=_node_sort_key,
        )
        for index, node in enumerate(non_ground_nodes, start=1):
            self.node_map[node] = index

        if not self._has_ground:
            logger.warning("No ground node found - the system may be singular.")

    def _build_branches(self):
        """Create the branch list."""
        self.branches = []

        for element in self.ct.elements:
            connections = element.connections

            if len(connections) < 2:
                raise ValueError(
                    f"Element {element.get_symbol()} has less than two connections."
                )

            for node in connections:
                if node not in self.node_map:
                    raise ValueError(
                        f"Node {node} of element {element.get_symbol()} is unknown. "
                        "Call circuit.update_nodes() first."
                    )

            self.branches.append(Branch(element, connections[0], connections[1]))

            if element.type.upper() in CONTROLLED_SOURCES:
                if len(connections) < 4:
                    raise ValueError(
                        f"Controlled source {element.get_symbol()} needs four connections."
                    )
                self.branches.append(
                    Branch(element, connections[2], connections[3], is_control=True)
                )

    def _build_unknowns(self):
        """Create the symbol vector of all unknowns, Insydes order [u | i | e]."""
        node_symbols = [None] * self.n
        for name, index in self.node_map.items():
            if index == 0:
                continue
            node_symbols[index - 1] = sp.Symbol(f"V_{name}")

        current_symbols = [sp.Symbol(f"I_{branch.symbol}") for branch in self.branches]
        voltage_symbols = [sp.Symbol(f"U_{branch.symbol}") for branch in self.branches]

        self.unknowns = sp.Matrix(voltage_symbols + current_symbols + node_symbols)

    # ------------------------------------------------------------------
    # matrix assembly
    # ------------------------------------------------------------------

    def buildIncidenceMatrix(self):
        """Build the reduced incidence matrix A (n x m)."""
        self.A = sp.SparseMatrix(self.n, self.m, {})

        for j, branch in enumerate(self.branches):
            index_p = self.node_map[branch.node_p]
            index_n = self.node_map[branch.node_n]

            if index_p != 0:
                self.A[index_p - 1, j] += 1
            if index_n != 0:
                self.A[index_n - 1, j] -= 1

        return self.A

    def buildComponentMatrices(self):  # noqa: C901
        """Build the element matrices G, H and the source vector w."""
        s = self.s

        self.G = sp.SparseMatrix(self.m, self.m, {})
        self.H = sp.SparseMatrix(self.m, self.m, {})
        self.w = sp.SparseMatrix(self.m, 1, {})

        for j, branch in enumerate(self.branches):
            element = branch.element
            symbol = sp.symbols(element.get_symbol())

            # netlist models may use lower case type names
            element_type = element.type.upper()

            # controlling port of a controlled source
            if branch.is_control:
                if element_type in ("E", "G"):
                    # voltage controlled -> open circuit, i_ctrl = 0
                    self.G[j, j] = 1
                else:
                    # current controlled -> short circuit, u_ctrl = 0
                    self.H[j, j] = 1
                continue

            # Sign convention follows Analog Insydes: the element parameter
            # (R, s*L, s*C, gain) carries the plus sign, the unit coefficient
            # the minus sign. Independent sources keep a positive unit
            # coefficient so their right hand side keeps its sign.
            match element_type:
                case "R":
                    self.G[j, j] = symbol
                    self.H[j, j] = -1
                case "L":
                    self.G[j, j] = symbol * s
                    self.H[j, j] = -1
                case "C":
                    self.G[j, j] = -1
                    self.H[j, j] = symbol * s
                case "V":
                    self.H[j, j] = 1
                    self.w[j] = symbol if "value_ac" in element.params else sp.Integer(0)
                case "I":
                    self.G[j, j] = 1
                    self.w[j] = symbol if "value_ac" in element.params else sp.Integer(0)
                case "E":
                    self.H[j, j] = -1
                    self.H[j, j + 1] = symbol
                case "G":
                    self.G[j, j] = -1
                    self.H[j, j + 1] = symbol
                case "F":
                    self.G[j, j] = -1
                    self.G[j, j + 1] = symbol
                case "H":
                    self.H[j, j] = -1
                    self.G[j, j + 1] = symbol
                case _:
                    raise ValueError(
                        f"Element type '{element.type}' of {element.get_symbol()} is not "
                        "supported. Flatten the circuit before running the analysis."
                    )

        return self.G, self.H

    def buildRHS(self):
        """Build the right hand side vector of the complete system."""
        top_zeros = sp.SparseMatrix(self.n + self.m, 1, {})
        self.RHS = top_zeros.col_join(self.w)
        return self.RHS

    def buildEquationSystem(self):
        """Assemble the tableau matrix T using sparse blocks.

        Column order is [u | i | e] and row order is [branch voltage
        definition | KCL | element eqs.], matching Analog Insydes'
        SparseTableau.m (ExtendedTableau variant).
        """
        # Top block (m rows): [ I | 0 | -A^T ]  ->  u - A^T * e = 0
        identity_m = sp.SparseMatrix(self.m, self.m, {(i, i): 1 for i in range(self.m)})
        zeros_m_m = sp.SparseMatrix(self.m, self.m, {})
        top = identity_m.row_join(zeros_m_m).row_join(-self.A.T)

        # Middle block (n rows): [ 0 | A | 0 ]  ->  A * i = 0
        zeros_n_m = sp.SparseMatrix(self.n, self.m, {})
        zeros_n_n = sp.SparseMatrix(self.n, self.n, {})
        middle = zeros_n_m.row_join(self.A).row_join(zeros_n_n)

        # Bottom block (m rows): [ H | G | 0 ]  ->  H * u + G * i = w
        zeros_m_n = sp.SparseMatrix(self.m, self.n, {})
        bottom = self.H.row_join(self.G).row_join(zeros_m_n)

        # Stack them vertically
        self.T = top.col_join(middle).col_join(bottom)
        return self.T

    def buildEquationsSystem(self):
        """Build the complete equation system in one call."""
        self.buildIncidenceMatrix()
        self.buildComponentMatrices()
        self.buildRHS()
        self.buildEquationSystem()
        return self.T, self.RHS

    # ------------------------------------------------------------------
    # accessors
    # ------------------------------------------------------------------

    def get_equation_system(self):
        return self.T, self.RHS

    def get_unknowns(self):
        return self.unknowns

    def get_unknowns_as_strings(self):
        return [str(symbol) for symbol in self.get_unknowns()]

    def get_System_Inputs(self):
        return [str(entry) for entry in self.RHS]

    def modify_Input(self, new_value: list):
        rhs_modified = self.RHS.copy()
        for index, value in enumerate(new_value):
            rhs_modified[index] = sp.sympify(value)
        return rhs_modified

    def _index_of(self, unknown_variable: str):
        symbol = sp.symbols(unknown_variable)
        unknown_list = list(self.get_unknowns())
        if symbol not in unknown_list:
            raise ValueError(f"Unknown variable '{unknown_variable}' is not in the system.")
        return unknown_list.index(symbol)

    def _resolve_rhs(self, input_modification):
        if len(input_modification) == len(self.RHS):
            return self.modify_Input(input_modification)
        if input_modification:
            logger.warning("Input modification has the wrong length, using the original RHS.")
        return self.RHS

    # ------------------------------------------------------------------
    # solvers
    # ------------------------------------------------------------------

    def solve(self, unknown_variable: str, input_modification: list = None,
              simplify: bool = True):
        """Solve the system symbolically for a single unknown."""
        if input_modification is None:
            input_modification = []

        if self.T.rows == 0:
            self.buildEquationsSystem()

        index = self._index_of(unknown_variable)
        rhs = self._resolve_rhs(input_modification)

        solution = self.T.LUsolve(rhs)
        result = solution[index]

        return sp.cancel(sp.together(result)) if simplify else result

    def solveAll(self, input_modification: list = None):
        """Solve the system symbolically for every unknown."""
        if input_modification is None:
            input_modification = []

        if self.T.rows == 0:
            self.buildEquationsSystem()

        solution = self.T.LUsolve(self._resolve_rhs(input_modification))
        self.sym_result = {
            symbol: sp.cancel(sp.together(value))
            for symbol, value in zip(self.get_unknowns(), solution)
        }
        return self.sym_result

    def solveNumerical(self, frequencies: list, unknown_variable: str,
                       input_modification: list = None):
        """Solve the system numerically over a list of frequencies."""
        if input_modification is None:
            input_modification = []

        if self.T.rows == 0:
            self.buildEquationsSystem()

        index = self._index_of(unknown_variable)
        rhs = self._resolve_rhs(input_modification)

        # OPTIMIZATION 3: cast SparseMatrix to a dense matrix here to avoid
        # errors in the numeric solver (Numpy lambdify)
        T_num = self.toNumerical(sp.Matrix(self.T), self.value_dict)
        rhs_num = self.toNumerical(sp.Matrix(rhs), self.value_dict)

        T_func = sp.lambdify(self.s, T_num, "numpy", dummify=True)
        rhs_func = sp.lambdify(self.s, rhs_num, "numpy", dummify=True)

        def solve_frequency(frequency):
            jw = 1j * 2 * np.pi * frequency
            try:
                x = np.linalg.solve(
                    np.array(T_func(jw), dtype=complex),
                    np.array(rhs_func(jw), dtype=complex).reshape(-1),
                )
            except np.linalg.LinAlgError:
                return np.nan
            return x[index]

        self.num_result = np.array([solve_frequency(f) for f in frequencies])
        return self.num_result