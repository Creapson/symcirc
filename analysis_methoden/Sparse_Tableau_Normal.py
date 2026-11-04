"""Normal sparse tableau analysis (STA) in the form used in the lecture.

The unknown vector holds branch quantities only, no node potentials. The
order of both the unknowns and the row blocks follows Analog Insydes'
SparseTableau.m (voltages before currents, KVL before KCL) so that this
tableau lines up column-for-column and row-for-row with Insydes' output:

    x = [ u_1 .. u_b | i_1 .. i_b ]^T          ->  2b unknowns

The tableau is built from the blocks A, B, P and Q:

    | B   0 |   | u |   | 0 |     <- (b-n+1) rows : KVL            B*u = 0
    | 0   A | * | i | = | 0 |     <- (n-1) rows   : KCL            A*i = 0
    | Q   P |           | s |     <-  b rows      : element eqs.   P*i + Q*u = s

Blocks
------
A : reduced incidence matrix, (n-1) x b.
    A[k,j] = +1 if branch j leaves node k, -1 if it enters, 0 otherwise.
    The ground row is dropped, which is the matrix form of choosing a
    reference node.

B : fundamental loop matrix, (b-n+1) x b.
    A spanning tree is chosen. Every branch outside the tree (a link) closes
    exactly one independent loop. B[k,j] is +1 / -1 / 0 depending on whether
    branch j runs with, against, or outside loop k. A * B^T = 0 always holds.

P, Q : current and voltage coefficients of the element equations, b x b.
    The rows are written the way Analog Insydes writes them: the element
    parameter (R, s*L, s*C, gain) carries the plus sign and the unit
    coefficient the minus sign, e.g. R*i - u = 0 for a resistor and
    s*C*u - i = 0 for a capacitor. Independent sources keep a positive unit
    coefficient so their entry in s keeps its sign.

s    : independent source vector, b x 1.

Relation to Modified_Node_Analysis
----------------------------------
This class deliberately follows the structure of ModifiedNodalAnalysis: the
same attribute names, the same netlist conventions, the same solver strategy
and one stamping method per element type. The mathematics differs because MNA
eliminates branch quantities in favour of node potentials, while the sparse
tableau keeps them and expresses KVL through loops instead of potentials.

Node potentials can still be recovered after solving by summing tree branch
voltages along the path from ground. That is a post processing step and is not
part of the tableau.
"""

import logging
from collections import deque

import numpy as np
import scipy.linalg as sla
import sympy as sp

import netlist.Circuit as Circuit
import Pspice_util as pu
from Equation_Formulator import EquationFormulator

logger = logging.getLogger(__name__)

GROUND_NAMES = ("0", "gnd", "GND", "ground", "Ground", "GROUND")

# element types that carry a second, controlling port
CONTROLLED_SOURCES = ("E", "G", "F", "H")


class Branch:
    """One branch of the tableau.

    A branch is not the same thing as an element: a controlled source occupies
    two branches, the output port and the controlling port.

    Attributes:
        element (Element): the netlist element this branch belongs to.
        node_p (str): name of the positive node.
        node_n (str): name of the negative node.
        is_control (bool): True for the controlling port of a controlled source.
        symbol (str): base name used to build the I_ and U_ symbols.

    """

    def __init__(self, element, node_p, node_n, is_control=False):
        """Initialize the branch.

        Args:
            element (Element): the netlist element this branch belongs to.
            node_p (str): name of the positive node.
            node_n (str): name of the negative node.
            is_control (bool): True for the controlling port.

        """
        self.element = element
        self.node_p = node_p
        self.node_n = node_n
        self.is_control = is_control
        self.symbol = f"{element.get_symbol()}_ctrl" if is_control else element.get_symbol()


class SparseTableauNormal(EquationFormulator):
    """Class for the normal sparse tableau method."""

    ct: Circuit
    value_dict: dict

    def __init__(self, circuit: Circuit):
        """Initialize the class.

        Args:
            circuit (Circuit): The Circuit to analyze. It has to be flattened,
                so it must not contain subcircuits or transistor models.

        """
        self.ct = circuit
        self.value_dict = self.generateValueDict(self.ct)
        self.s = sp.symbols("s")

        self._build_node_map()
        self._build_branches()

        # number of nodes without ground, written (n-1) in the lecture notes
        self.n = len(self.node_map) - 1
        # number of branches, written b in the lecture notes
        self.m = len(self.branches)

        self._build_spanning_tree()

        # number of independent loops, b - (n-1)
        self.l = self.m - self.n

        self.A = sp.SparseMatrix(self.n, self.m, {})
        self.B = sp.SparseMatrix(self.l, self.m, {})
        self.P = sp.SparseMatrix(self.m, self.m, {})
        self.Q = sp.SparseMatrix(self.m, self.m, {})
        self.s_vec = sp.SparseMatrix(self.m, 1, {})
        self.RHS = sp.SparseMatrix(2 * self.m, 1, {})
        self.T = sp.SparseMatrix(0, 0, {})

        self._build_unknowns()

        self.sym_result = {}
        self.num_result = {}

    # ------------------------------------------------------------------
    # setup helpers
    # ------------------------------------------------------------------

    def generateValueDict(self, ct: Circuit):
        """Map every element symbol to its numerical value.

        The parameter that carries the value depends on the element type, in
        the same way as in ModifiedNodalAnalysis: passive elements use
        "value_dc", independent sources use "value_ac" for the small signal
        analysis and controlled sources use "value".

        Args:
            ct (Circuit): the circuit whose elements are read.

        Returns:
            dict: mapping from sympy symbol to float or symbolic expression.

        """
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
        """Map node names to consecutive indices, ground always to 0.

        The index of a node is the position of its KCL equation in the
        tableau, so the order has to be the one Analog Insydes uses:
        numbered nodes first and ascending, named nets after them,
        alphabetically. Numbering the nodes in order of first appearance in
        the netlist instead permutes the whole KCL block against Insydes'
        matrix - still a correct system, but no longer comparable row by row.
        SparseTableau (extended) already sorted them this way.

        Raises:
            ValueError: if the circuit has no ground node.

        """
        self.node_map = {}
        self._has_ground = False
        self._ground_name = None

        for node in self.ct.nodes:
            if node in GROUND_NAMES:
                self.node_map[node] = 0
                self._has_ground = True
                if self._ground_name is None:
                    self._ground_name = node

        def _node_sort_key(name):
            # numeric node names sort as numbers (1, 2, ..., 10), everything
            # else (named nets like "ua") sorts alphabetically after them
            try:
                return (0, int(name), "")
            except ValueError:
                return (1, 0, name)

        non_ground_nodes = sorted(
            {node for node in self.ct.nodes if node not in self.node_map},
            key=_node_sort_key,
        )
        for index, node in enumerate(non_ground_nodes, start=1):
            self.node_map[node] = index

        if not self._has_ground:
            raise ValueError(
                "No ground node found. The normal sparse tableau needs a "
                "reference node (name it '0' or 'GND')."
            )

    def _build_branches(self):
        """Turn the element list into the branch list.

        The order of this list fixes the row and column order of the tableau.
        A controlled source appends its controlling port directly after its
        output port, which is what the j+1 indexing in the stamps relies on.

        Raises:
            ValueError: if an element has too few connections or refers to an
                unknown node.

        """
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

    def _build_spanning_tree(self):
        """Split the branches into tree branches and links.

        Union-Find is used: a branch that joins two so far separate parts of
        the graph is a tree branch, otherwise it closes a loop and is a link.

        The branches are offered in plain branch order, which is the order of
        the netlist. That is what Analog Insydes' SparseTableau.m does, and it
        is what makes the KVL block line up with Insydes' row for row. Sorting
        them into a "normal tree" first (voltage sources into the tree,
        current sources into the co-tree, storage elements in between) yields
        a different but equally valid tree: A * B^T = 0 and the solution are
        unchanged, only the printed KVL rows differ. Insydes does not do it,
        so neither does this.

        Raises:
            ValueError: if the circuit graph is not connected.

        """
        parent = {node: node for node in self.node_map}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra == rb:
                return False
            parent[ra] = rb
            return True

        self.twigs = []
        self.links = []

        for j, branch in enumerate(self.branches):
            if union(branch.node_p, branch.node_n):
                self.twigs.append(j)
            else:
                self.links.append(j)

        self.twigs.sort()
        self.links.sort()

        expected = len(self.node_map) - 1
        if len(self.twigs) != expected:
            raise ValueError(
                f"The circuit graph is not connected: found {len(self.twigs)} tree "
                f"branches but expected {expected}. Every node must be reachable "
                "from ground."
            )

        self._build_tree_potentials()

    def _build_tree_potentials(self):
        """Express every node potential through tree branch voltages.

        The tree is rooted at ground. For a tree branch j the relation
        u_j = e_p - e_n gives:

            walking from p to n:  e_n = e_p - u_j   ->  coefficient -1
            walking from n to p:  e_p = e_n + u_j   ->  coefficient +1

        The result is stored as node_potential_coeffs[node] = {branch: factor}
        and is used both for the loop matrix and for recovering node
        potentials after the solve.

        """
        adjacency = {node: [] for node in self.node_map}
        for j in self.twigs:
            branch = self.branches[j]
            adjacency[branch.node_p].append((branch.node_n, j, -1))
            adjacency[branch.node_n].append((branch.node_p, j, +1))

        self.node_potential_coeffs = {self._ground_name: {}}

        queue = deque([self._ground_name])
        while queue:
            current = queue.popleft()
            for neighbour, j, sign in adjacency[current]:
                if neighbour in self.node_potential_coeffs:
                    continue
                coeffs = dict(self.node_potential_coeffs[current])
                coeffs[j] = coeffs.get(j, 0) + sign
                self.node_potential_coeffs[neighbour] = coeffs
                queue.append(neighbour)

    def _build_unknowns(self):
        """Build the unknown vector [ u_1..u_b | i_1..i_b ], Insydes order."""
        current_symbols = [sp.Symbol(f"I_{branch.symbol}") for branch in self.branches]
        voltage_symbols = [sp.Symbol(f"U_{branch.symbol}") for branch in self.branches]

        self.unknowns = sp.Matrix(voltage_symbols + current_symbols)

    # ------------------------------------------------------------------
    # topology blocks
    # ------------------------------------------------------------------

    def buildIncidenceMatrix(self):
        """Build block A, the reduced incidence matrix.

        Returns:
            A (matrix): incidence matrix of shape (n-1) x b.

        """
        self.A = sp.SparseMatrix(self.n, self.m, {})

        for j, branch in enumerate(self.branches):
            index_p = self.node_map[branch.node_p]
            index_n = self.node_map[branch.node_n]

            if index_p != 0:
                self.A[index_p - 1, j] += 1
            if index_n != 0:
                self.A[index_n - 1, j] -= 1

        return self.A

    def buildLoopMatrix(self):
        """Build block B, the fundamental loop matrix.

        Every link closes exactly one loop. Walking that loop over the tree
        gives u_link = e_p - e_n = (c[p] - c[n]) . u, which rearranges into
        the loop equation u_link - (c[p] - c[n]) . u = 0.

        Returns:
            B (matrix): loop matrix of shape (b-n+1) x b.

        """
        self.B = sp.SparseMatrix(self.l, self.m, {})

        for k, j in enumerate(self.links):
            branch = self.branches[j]

            self.B[k, j] += 1

            for twig, coeff in self.node_potential_coeffs[branch.node_p].items():
                self.B[k, twig] -= coeff
            for twig, coeff in self.node_potential_coeffs[branch.node_n].items():
                self.B[k, twig] += coeff

        return self.B

    # ------------------------------------------------------------------
    # element stamps, one method per element type
    # ------------------------------------------------------------------

    def add_impedance(self, row, impedance):
        """Add an element described by its impedance: Z * i - u = 0.

        Used for R (Z = R) and L (Z = s*L). Writing the resistor in impedance
        form avoids the 1/R division that nodal analysis needs.

        The row is written the way Analog Insydes writes it: the element
        parameter carries the plus sign and the unit coefficient carries the
        minus sign. Multiplying the row by -1 would give the equivalent
        u - Z * i = 0; the solution is the same either way, because the right
        hand side of this row is zero.

        Args:
            row (int): branch index, which is also the equation row.
            impedance (symbol): symbolic impedance of the branch.

        """
        self.P[row, row] = impedance
        self.Q[row, row] = -1

    def add_admittance(self, row, admittance):
        """Add an element described by its admittance: Y * u - i = 0.

        Used for C (Y = s*C). The admittance form is chosen here so that no
        1/(s*C) term appears, which would be singular at s = 0.

        Sign convention as in add_impedance: parameter positive, unit
        coefficient negative, matching Analog Insydes.

        Args:
            row (int): branch index, which is also the equation row.
            admittance (symbol): symbolic admittance of the branch.

        """
        self.P[row, row] = -1
        self.Q[row, row] = admittance

    def add_independent_voltage_source(self, row, sym_value):
        """Add an independent voltage source: u = V.

        The polarity follows the netlist, connections[0] is the plus terminal.

        Args:
            row (int): branch index of the source.
            sym_value (symbol): symbol of the source.

        """
        self.Q[row, row] = 1
        self.s_vec[row] = sym_value

    def add_independent_current_source(self, row, sym_value):
        """Add an independent current source: i = I.

        The current flows from connections[0] to connections[1] through the
        element, the same direction convention as in ModifiedNodalAnalysis.

        Args:
            row (int): branch index of the source.
            sym_value (symbol): symbol of the source.

        """
        self.P[row, row] = 1
        self.s_vec[row] = sym_value

    def add_vcvs(self, row, ctrl_row, gain):
        """Add a voltage controlled voltage source: gain * u_ctrl - u_out = 0.

        Sign convention as in add_impedance: the gain carries the plus sign,
        the unit coefficient the minus sign, matching Analog Insydes.

        Args:
            row (int): branch index of the output port.
            ctrl_row (int): branch index of the controlling port.
            gain (symbol): gain factor.

        """
        self.Q[row, row] = -1
        self.Q[row, ctrl_row] = gain

    def add_vccs(self, row, ctrl_row, gm):
        """Add a voltage controlled current source: gm * u_ctrl - i_out = 0.

        Args:
            row (int): branch index of the output port.
            ctrl_row (int): branch index of the controlling port.
            gm (symbol): transconductance.

        """
        self.P[row, row] = -1
        self.Q[row, ctrl_row] = gm

    def add_cccs(self, row, ctrl_row, beta):
        """Add a current controlled current source: beta * i_ctrl - i_out = 0.

        Args:
            row (int): branch index of the output port.
            ctrl_row (int): branch index of the controlling port.
            beta (symbol): current gain.

        """
        self.P[row, row] = -1
        self.P[row, ctrl_row] = beta

    def add_ccvs(self, row, ctrl_row, r_m):
        """Add a current controlled voltage source: r_m * i_ctrl - u_out = 0.

        Args:
            row (int): branch index of the output port.
            ctrl_row (int): branch index of the controlling port.
            r_m (symbol): transresistance.

        """
        self.Q[row, row] = -1
        self.P[row, ctrl_row] = r_m

    def add_voltage_control_port(self, row):
        """Add the controlling port of a VCVS or VCCS: i_ctrl = 0.

        A port that senses a voltage must behave like a voltmeter and draw no
        current, so the port is an open circuit.

        Args:
            row (int): branch index of the controlling port.

        """
        self.P[row, row] = 1

    def add_current_control_port(self, row):
        """Add the controlling port of a CCCS or CCVS: u_ctrl = 0.

        A port that senses a current must behave like an ammeter and drop no
        voltage, so the port is a short circuit.

        Args:
            row (int): branch index of the controlling port.

        """
        self.Q[row, row] = 1

    # ------------------------------------------------------------------
    # element block
    # ------------------------------------------------------------------

    def buildElementMatrices(self):
        """Build blocks P and Q and the source vector s.

        Row j holds the element equation of branch j:

            P[j, :] . i  +  Q[j, :] . u  =  s[j]

        Returns:
            P (matrix): current coefficients, b x b.
            Q (matrix): voltage coefficients, b x b.

        Raises:
            ValueError: if an element type is not supported, which usually
                means the circuit has not been flattened.

        """
        s = self.s

        self.P = sp.SparseMatrix(self.m, self.m, {})
        self.Q = sp.SparseMatrix(self.m, self.m, {})
        self.s_vec = sp.SparseMatrix(self.m, 1, {})

        for j, branch in enumerate(self.branches):
            element = branch.element
            symbol = sp.symbols(element.get_symbol())
            element_type = element.type.upper()

            if branch.is_control:
                if element_type in ("E", "G"):
                    self.add_voltage_control_port(j)
                else:
                    self.add_current_control_port(j)
                continue

            match element_type:
                case "R":
                    self.add_impedance(j, symbol)
                case "L":
                    self.add_impedance(j, s * symbol)
                case "C":
                    self.add_admittance(j, s * symbol)
                case "V":
                    excitation = symbol if "value_ac" in element.params else sp.Integer(0)
                    self.add_independent_voltage_source(j, excitation)
                case "I":
                    excitation = symbol if "value_ac" in element.params else sp.Integer(0)
                    self.add_independent_current_source(j, excitation)
                case "E":
                    self.add_vcvs(j, j + 1, symbol)
                case "G":
                    self.add_vccs(j, j + 1, symbol)
                case "F":
                    self.add_cccs(j, j + 1, symbol)
                case "H":
                    self.add_ccvs(j, j + 1, symbol)
                case _:
                    raise ValueError(
                        f"Element type '{element.type}' of {element.get_symbol()} is not "
                        "supported. Flatten the circuit before running the analysis."
                    )

        return self.P, self.Q

    def buildRHS(self):
        """Build the right hand side: zeros for KCL and KVL, then s.

        Returns:
            RHS (vector): right hand side of length 2b.

        """
        top_zeros = sp.SparseMatrix(self.n + self.l, 1, {})
        self.RHS = top_zeros.col_join(self.s_vec)
        return self.RHS

    def buildTableau(self):
        """Assemble the blocks into the system matrix T.

        Column order is [u | i] and row order is [KVL | KCL | element eqs.],
        matching Analog Insydes' SparseTableau.m.

        Returns:
            T (matrix): system matrix of shape 2b x 2b.

        """
        top = self.B.row_join(sp.SparseMatrix(self.l, self.m, {}))
        middle = sp.SparseMatrix(self.n, self.m, {}).row_join(self.A)
        bottom = self.Q.row_join(self.P)

        self.T = top.col_join(middle).col_join(bottom)
        return self.T

    def buildEquationsSystem(self):
        """Build the equation system based on the circuit description.

        Returns:
            T (matrix): system matrix.
            RHS (vector): right hand side.

        """
        self.buildIncidenceMatrix()
        self.buildLoopMatrix()
        self.buildElementMatrices()
        self.buildRHS()
        self.buildTableau()

        logger.debug("Finished building equation system!")
        return self.T, self.RHS

    # ------------------------------------------------------------------
    # accessors
    # ------------------------------------------------------------------

    def get_equation_system(self):
        """Return the equation system.

        Returns:
            T (matrix): system matrix of the equation system.
            RHS (vector): right hand side of the equation system.

        """
        return self.T, self.RHS

    def get_blocks(self):
        """Return the blocks A, B, P, Q and s separately.

        Returns:
            tuple: (A, B, P, Q, s) as used in the lecture notes.

        """
        return self.A, self.B, self.P, self.Q, self.s_vec

    def get_unknowns(self):
        """Return the vector of unknown branch currents and branch voltages.

        Returns:
            x (vector): vector of unknowns, length 2b.

        """
        return self.unknowns

    def get_unknowns_as_strings(self):
        """Return the vector of unknowns as strings for easy displaying.

        Returns:
            String (array): vector of unknowns as string.

        """
        return [str(symbol) for symbol in self.get_unknowns()]

    def get_solvable_names(self):
        """Return every name that solve() accepts.

        On top of the real unknowns this adds the node potentials, which are
        not part of the tableau but can be recovered from it. The GUI uses
        this list to fill its output selection.

        Returns:
            String (array): unknowns followed by node potential names.

        """
        node_names = [
            f"V_{name}" for name, index in self.node_map.items() if index != 0
        ]
        return self.get_unknowns_as_strings() + node_names

    def get_tree_branches(self):
        """Return the symbol names of the tree branches.

        Returns:
            String (array): names of the branches inside the spanning tree.

        """
        return [self.branches[j].symbol for j in self.twigs]

    def get_link_branches(self):
        """Return the symbol names of the link branches.

        Returns:
            String (array): names of the branches outside the spanning tree.

        """
        return [self.branches[j].symbol for j in self.links]

    def get_System_Inputs(self):
        """Get the input variables of the system.

        Returns:
            inputs (array): array with input variables.

        """
        return [str(entry) for entry in self.RHS]

    def modify_Input(self, new_value: list):
        """Replace the right hand side entries by the given values.

        Args:
            new_value (list): one entry per row of the right hand side.

        Returns:
            RHS (vector): a modified copy, the original stays untouched.

        """
        rhs_modified = self.RHS.copy()
        for index, value in enumerate(new_value):
            rhs_modified[index] = sp.sympify(value)
        return rhs_modified

    def _index_of(self, unknown_variable: str):
        """Return the position of an unknown inside the solution vector.

        Args:
            unknown_variable (str): name of the unknown.

        Returns:
            int: index inside the solution vector.

        Raises:
            ValueError: if the name is not an unknown of the system.

        """
        symbol = sp.symbols(unknown_variable)
        unknown_list = list(self.get_unknowns())
        if symbol not in unknown_list:
            raise ValueError(f"Unknown variable '{unknown_variable}' is not in the system.")
        return unknown_list.index(symbol)

    def _resolve_rhs(self, input_modification):
        """Pick the right hand side to solve with.

        Args:
            input_modification (list): replacement values, may be empty.

        Returns:
            RHS (vector): modified copy if the length matches, else the original.

        """
        if len(input_modification) == len(self.RHS):
            return self.modify_Input(input_modification)
        if input_modification:
            logger.warning("Input modification has the wrong length, using the original RHS.")
        return self.RHS

    # ------------------------------------------------------------------
    # node potential recovery, post processing only
    # ------------------------------------------------------------------

    def _node_potential_expression(self, node_name: str, solution):
        """Sum the tree branch voltages on the path from ground to a node.

        Args:
            node_name (str): name of the node.
            solution (vector): solved unknown vector.

        Returns:
            sympy.Expr: the node potential.

        Raises:
            ValueError: if the node is not part of the circuit.

        """
        if node_name not in self.node_potential_coeffs:
            raise ValueError(f"Node '{node_name}' is not part of the circuit.")

        expression = sp.Integer(0)
        for twig, coeff in self.node_potential_coeffs[node_name].items():
            expression += coeff * solution[twig]
        return expression

    def _is_node_request(self, name: str):
        """Check whether a name asks for a node potential.

        Args:
            name (str): requested name, for example "V_2".

        Returns:
            str | None: the node name, or None if this is not a node request.

        """
        if not name.startswith("V_"):
            return None
        node_name = name[2:]
        return node_name if node_name in self.node_map else None

    # ------------------------------------------------------------------
    # solvers
    # ------------------------------------------------------------------

    def solve(self, unknown_variable: str, input_modification: list = None,
              simplify: bool = True):
        """Return the symbolic solution of the equation system.

        Args:
            unknown_variable (str): variable for which to solve the system.
                Branch quantities like "I_R1" and "U_R1" are read straight out
                of the solution vector, node potentials like "V_2" are
                recovered from the tree afterwards.
            input_modification (list): optional replacement right hand side.
            simplify (bool): cancel the result into a single fraction.

        Returns:
            sympy.Expr: symbolic solution.

        """
        if input_modification is None:
            input_modification = []

        if self.T.rows == 0:
            self.buildEquationsSystem()

        rhs = self._resolve_rhs(input_modification)
        solution = self.T.LUsolve(rhs)

        node_name = self._is_node_request(unknown_variable)
        if node_name is not None:
            result = self._node_potential_expression(node_name, solution)
        else:
            result = solution[self._index_of(unknown_variable)]

        return sp.cancel(sp.together(result)) if simplify else result

    def solveAll(self, input_modification: list = None, include_nodes: bool = True):
        """Solve the system for every unknown at once.

        Args:
            input_modification (list): optional replacement right hand side.
            include_nodes (bool): also add the recovered node potentials.

        Returns:
            dict: mapping from symbol to symbolic solution.

        """
        if input_modification is None:
            input_modification = []

        if self.T.rows == 0:
            self.buildEquationsSystem()

        solution = self.T.LUsolve(self._resolve_rhs(input_modification))

        self.sym_result = {
            symbol: sp.cancel(sp.together(value))
            for symbol, value in zip(self.get_unknowns(), solution)
        }

        if include_nodes:
            for node_name, index in self.node_map.items():
                if index == 0:
                    continue
                expression = self._node_potential_expression(node_name, solution)
                self.sym_result[sp.Symbol(f"V_{node_name}")] = sp.cancel(
                    sp.together(expression))

        return self.sym_result

    def solveNumerical(self, frequencies: list, unknown_variable: str,
                       input_modification: list = None):
        """Solve the equation system numerically over a list of frequencies.

        Args:
            frequencies (list): frequencies in Hz for which to solve.
            unknown_variable (str): variable for which to solve the system.
            input_modification (list): optional replacement right hand side.

        Returns:
            H (array): array with numerical solutions, one per frequency.

        """
        if input_modification is None:
            input_modification = []

        if self.T.rows == 0:
            self.buildEquationsSystem()

        rhs = self._resolve_rhs(input_modification)

        node_name = self._is_node_request(unknown_variable)
        if node_name is None:
            index = self._index_of(unknown_variable)
            coefficients = None
        else:
            index = None
            coefficients = self.node_potential_coeffs[node_name]

        T_num = self.toNumerical(sp.Matrix(self.T), self.value_dict)
        rhs_num = self.toNumerical(sp.Matrix(rhs), self.value_dict)

        T_func = sp.lambdify(self.s, T_num, "numpy", dummify=True)
        rhs_func = sp.lambdify(self.s, rhs_num, "numpy", dummify=True)

        def solve_freq(freq):
            jw = 1j * 2 * np.pi * freq
            try:
                x = sla.solve(
                    np.array(T_func(jw), dtype=complex),
                    np.array(rhs_func(jw), dtype=complex).reshape(-1),
                )
            except sla.LinAlgError:
                return np.nan

            if index is not None:
                return x[index]

            total = 0j
            for twig, coeff in coefficients.items():
                total += coeff * x[twig]
            return total

        self.num_result = np.array([solve_freq(freq) for freq in frequencies])
        return self.num_result
