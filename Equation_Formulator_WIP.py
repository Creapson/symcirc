"""Defines analyzing classes for EquationFormulator.
"""
import Circuit
import sympy as sp
import logging
logger = logging.getLogger(__name__)

class EquationFormulator():
    """_summary_.
    """
    
    def __init__(self):
        """_summary_.

        """







class ModifiedNodalAnalysis(EquationFormulator):
    """Class for modified nodal analysis method.


    """
    ct:Circuit
  

    def __init__(self, circuit:Circuit):
        """Innitialize the class.

        Args:
            circuit (Circuit): The Circuit to analyze.

        """

        self.ct = circuit
        self.n = len(self.ct.nodes) - 1  # Anzahl Knoten ohne Masse (0)
        self.A = sp.zeros(self.n, self.n)
        self.z = sp.zeros(self.n, 1)
        self.current_var_index = 0    # Gesamtanzahl von Stromvariablen

        #create mapping for node names to integer values for easy matrix handling
   
        node_map = {}
        used_values = set()
        
        for node in self.ct.nodes:
            if node.isdigit():
                val = int(node)
                if val not in used_values:
                    node_map[node] = val
                    used_values.add(val)
        
        for node in self.ct.nodes:
            if not node.isdigit():      
                # No number, assign next available starting from 1
                val = 1
                while val in used_values:
                    val += 1
                node_map[node] = val
                used_values.add(val)
        
     
                
    def expand_matrix(self):
        """Expand matrix in case of an additional voltage source by 1 row and 1 column.

        """
        rows, cols = self.A.shape
        last_row = sp.zeros(1, cols + 1)
        self.A = self.A.row_join(sp.zeros(rows, 1))   # rechte Spalte anhängen
        self.A = self.A.col_join(last_row)            # neue letzte Zeile

        self.z = self.z.col_join(sp.Matrix([0]))
        self.current_var_index += 1

    def add_admittance(self, node1, node2, value):
        """Add admittance to the matrix.

        Args:
            node1 (int): Node 1 of admittance
            node2 (int): Node 2 of admittance
            value (symbol): symbol of admittance (L, C, G, etc.)

        """

        if node1 != 0:
            self.A[node1 - 1, node1 - 1] += value
        if node2 != 0:
            self.A[node2 - 1, node2 - 1] += value
        if node1 != 0 and node2 != 0:
            self.A[node1 - 1, node2 - 1] -= value
            self.A[node2 - 1, node1 - 1] -= value

    def add_independent_current_source(self, node1, node2, value):
        """Add independent current source. 
        Direction of the current is from node1 to node2.

        Args:
            node1 (int): Node 1 of the current source.
            node2 (int): Node 2 of the current source.
            value (symbol): Symbol of the source.

        """
        if node1 != 0:
            self.z[node1 - 1] -= value
        if node2 != 0:
            self.z[node2 - 1] += value

    def add_independent_voltage_source(self, node1, node2, sym_value, num_value):  # noqa: D417
        """Add independent voltage source.

        Args:
            node1 (int): Node 1 of the voltage source (+).
            node2 (int): Node 2 of the voltage source (-).
            value (symbol): Symbol of the source.

        """
        self.expand_matrix()
        idx = self.A.rows - 1
        if node1 != 0:
            self.A[node1 - 1, idx] = 1
            self.A[idx, node1 - 1] = 1
        if node2 != 0:
            self.A[node2 - 1, idx] = -1
            self.A[idx, node2 - 1] = -1

        if num_value != 0:
            self.z[idx] = sym_value
        
        
    def add_vccs(self, node_out1, node_out2, node_ctrl1, node_ctrl2, gm):
        """Add voltage controlled current source.

        Args:
            node_out1 (int): node 1 of controlled element
            node_out2 (int): node 2 of controlled element
            node_ctrl1 (int): node 1 of controlling element
            node_ctrl2 (int): node 2 of controlling element
            gm (float): gain factor

        """
        if node_out1 != 0 and node_ctrl1 != 0:
            self.A[node_out1 - 1, node_ctrl1 - 1] += gm
        if node_out1 != 0 and node_ctrl2 != 0:
            self.A[node_out1 - 1, node_ctrl2 - 1] -= gm
        if node_out2 != 0 and node_ctrl1 != 0:
            self.A[node_out2 - 1, node_ctrl1 - 1] -= gm
        if node_out2 != 0 and node_ctrl2 != 0:
            self.A[node_out2 - 1, node_ctrl2 - 1] += gm

    def add_cccs(self, node_out1, node_out2, node_ctrl1, node_ctrl2, beta):  # noqa: C901, PLR0912
        """Add current controlled current source.

        Args:
            node_out1 (int): node 1 of controlled element
            node_out2 (int): node 2 of controlled element
            node_ctrl1 (int): node 1 of controlling element
            node_ctrl2 (int): node 2 of controlling element
            beta (float): gain factor

        """
        v_counter = 0
        proof_counter = 0

        for bipole in self.ct.bipoles:
            proof_counter += 1
            match bipole.tp:
                case "V" | "H" |  "E":            
                    if {self.result[bipole.node1], bipole.node2} == {node_ctrl1, node_ctrl2}:
                        idx = self.n + v_counter

                        if node_out1 != 0:
                            self.A[node_out1 - 1, idx] += beta

                        if node_out2 != 0:
                            self.A[node_out2 - 1, idx] += -beta
                        
                        break

                    v_counter += 1

                
                case  "R" | "C" | "L" | "I" | "F" | "G": 
                    if {bipole.node1, bipole.node2} == {node_ctrl1, node_ctrl2}:
                    
                        self.expand_matrix()
                        idx = self.A.rows - 1

                        if node_out1 != 0:
                            self.A[node_out1 - 1, idx] += beta

                        if node_out2 != 0:
                            self.A[node_out2 - 1, idx] += -beta
                        
                        if node_ctrl1 != 0:
                            self.A[idx, node_ctrl1 - 1] += 1
                            self.A[node_ctrl1 - 1, idx] += 1
                        
                        if node_ctrl2 != 0:
                            self.A[idx, node_ctrl2 - 1] += -1
                            self.A[node_ctrl2 - 1, idx] += -1
                        
                        self.z[idx] = 0
                        
                        break
        
        if proof_counter == len(self.ct.bipoles):
            self.expand_matrix()
            idx = self.A.rows - 1

            if node_out1 != 0:
                self.A[node_out1 - 1, idx] += beta

            if node_out2 != 0:
                self.A[node_out2 - 1, idx] += -beta
                        
            if node_ctrl1 != 0:
                self.A[idx, node_ctrl1 - 1] += 1
                self.A[node_ctrl1 - 1, idx] += 1
                        
            if node_ctrl2 != 0:
                self.A[idx, node_ctrl2 - 1] += -1
                self.A[node_ctrl2 - 1, idx] += -1

        
    def add_vcvs(self, node_out1, node_out2, node_ctrl1, node_ctrl2, gain):
        """Add voltage controlled voltage source.

        Args:
            node_out1 (int): node 1 of controlled element
            node_out2 (int): node 2 of controlled element
            node_ctrl1 (int): node 1 of controlling element
            node_ctrl2 (int): node 2 of controlling element
            gain (float): gain factor

        """
        self.expand_matrix()
        idx = self.A.rows - 1
        if node_out1 != 0:
            self.A[node_out1 - 1, idx] = 1
            self.A[idx, node_out1 - 1] = 1
        if node_out2 != 0:
            self.A[node_out2 - 1, idx] = -1
            self.A[idx, node_out2 - 1] = -1
        if node_ctrl1 != 0:
            self.A[idx, node_ctrl1 - 1] += gain
        if node_ctrl2 != 0:
            self.A[idx, node_ctrl2 - 1] -= gain
       
    def add_ccvs(self, node_out1, node_out2, node_ctrl1, node_ctrl2, r_m):  # noqa: C901, PLR0912, PLR0915
        """Add current controlled voltage source.

        Args:
            node_out1 (int): node 1 of controlled element
            node_out2 (int): node 2 of controlled element
            node_ctrl1 (int): node 1 of controlling element
            node_ctrl2 (int): node 2 of controlling element
            r_m (float): gain factor

        """
        v_counter = 0
        proof_counter = 0

        for element in self.ct.elements:
            proof_counter += 1
            match element.type:
                case "V" | "H" | "E":            
                    if {self.node_map[element.connections[0]], self.node_map[element.connections[1]]} == {node_ctrl1, node_ctrl2}:
                        ctrl_idx = self.n + v_counter

                        self.expand_matrix()
                        idx = self.A.rows - 1

                        if node_out1 != 0:
                            self.A[idx, node_out1 - 1] += 1
                            self.A[node_out1 - 1, idx] += 1
                        
                        if node_ctrl2 != 0:
                            self.A[idx, node_out2 - 1] += -1
                            self.A[node_out2 - 1, idx] += -1
                        
                        self.z[idx] = 0
                        
                        self.A[idx, ctrl_idx] = -r_m

                        
                        break

                    v_counter += 1

                
                case  "R" | "C" | "L" | "I" | "F" | "G": 
                    if {self.node_map[element.connections[0]], self.node_map[element.connections[1]]} == {node_ctrl1, node_ctrl2}:
                    
                        self.expand_matrix()
                        ctrl_idx = self.A.rows - 1

                        
                        if node_ctrl1 != 0:
                            self.A[idx, node_ctrl1 - 1] += 1
                            self.A[node_ctrl1 - 1, ctrl_idx] += 1
                        
                        if node_ctrl2 != 0:
                            self.A[idx, node_ctrl2 - 1] += -1
                            self.A[node_ctrl2 - 1, ctrl_idx] += -1
                        
                        self.z[ctrl_idx] = 0
                        
                        self.expand_matrix()
                        idx = self.A.rows - 1

                        if node_out1 != 0:
                            self.A[idx, node_out1 - 1] += 1
                            self.A[node_out1 - 1, idx] += 1
                        
                        if node_ctrl2 != 0:
                            self.A[idx, node_out2 - 1] += -1
                            self.A[node_out2 - 1, idx] += -1

                        self.z[idx] = 0
                        
                        self.A[idx, ctrl_idx] = -r_m
                        
                        break
        
        if proof_counter == len(self.ct.bipoles):
            self.expand_matrix()
            ctrl_idx = self.A.rows - 1

                        
            if node_ctrl1 != 0:
                self.A[idx, node_ctrl1 - 1] += 1
                self.A[node_ctrl1 - 1, ctrl_idx] += 1
                        
            if node_ctrl2 != 0:
                self.A[idx, node_ctrl2 - 1] += -1
                self.A[node_ctrl2 - 1, ctrl_idx] += -1
            
            self.z[ctrl_idx] = 0
                        
            self.expand_matrix()
            idx = self.A.rows - 1

            if node_out1 != 0:
                self.A[idx, node_out1 - 1] += 1
                self.A[node_out1 - 1, idx] += 1
                        
            if node_ctrl2 != 0:
                self.A[idx, node_out2 - 1] += -1
                self.A[node_out2 - 1, idx] += -1
            
            self.z[idx] = 0
                        
            self.A[idx, ctrl_idx] = -r_m


    def get_equation_system(self):
        """_summary_.

        Returns:
            A(matrix): Matrix table of the equation system.
            z(vector): solution vector of the equation system.

        """
        return self.A, self.z

    def get_unknowns(self):
        """Return vector with symbols of unknown node voltages and extra currents based
          on the size of the matrix.

        Returns:
            v(vector): vector with symbols of unknown node voltages and extra currents

        """
       
        #v = sp.Matrix(sp.symbols(f"V1:{self.n +1}"))
        potential_symbols_strings = [self.ct.getNodes()[k] for k in 
                                     sorted(self.ct.getNodes())]

        potential_symbols = sp.symbols(potential_symbols_strings[1:])

        v = sp.Matrix(potential_symbols)

        i = sp.Matrix(sp.symbols(f"I1:{self.current_var_index +1}"))

        return v.col_join(i)
    
    def get_unknowns_as_strings(self):
        """Return vector of unknowns as String for easy displaying.
    
        
        Returns:
            String (array): vector of unknowns as string.

        
        """
        result = [str(sym) for sym in self.get_unknowns()]

        print("Unknowns: ", result)
        return  result
     
    def buildEquationsSystem(self):  # noqa: C901
        """Build the equation system based on the circuit description.

        """
        print("Building equation system...")
        logger.debug("Building equation system...")

        s = sp.symbols('s')
         
        
        for element in self.ct.elements:
            
            

            match element.type:
                case "R": self.add_admittance(self.node_map[element.connections[0]], self.node_map[element.connections[1]],  # noqa: E701
                                              sp.symbols(element.name))

                case "L": self.add_admittance(self.node_map[element.connections[0]], self.node_map[element.connections[1]], # noqa: E701
                                              s*sp.symbols(element.name))

                case "C": self.add_admittance(self.node_map[element.connections[0]], self.node_map[element.connections[1]], # noqa: E701
                                              1/(s*sp.symbols(element.name)))

                case "V": self.add_independent_voltage_source(self.node_map[element.connections[0]], # noqa: E701
                                                self.node_map[element.connections[1]], sp.symbols(element.name), element.params["value_ac"])

                case "I": self.add_independent_current_source(self.node_map[element.connections[0]], # noqa: E701
                                                self.node_map[element.connections[1]], sp.symbols(element.name))
            
           
                    
        for bipole in self.ct.bipoles:

            
            match bipole.tp:
                
                case "H": 
                    self.add_ccvs(self.node_map[element.connections[0]], self.node_map[element.connections[1]], # noqa: E701
                        self.node_map[element.connections[3]], self.node_map[element.connections[4]], sp.symbols(element.name))

                case "F": 
                    self.add_cccs(self.node_map[element.connections[0]], self.node_map[element.connections[1]],
                        self.node_map[element.connections[3]], self.node_map[element.connections[4]], sp.symbols(element.name))

                case "E": 
                    self.add_vcvs(self.node_map[element.connections[0]], self.node_map[element.connections[1]], # noqa: E701
                        self.node_map[element.connections[3]], self.node_map[element.connections[4]], sp.symbols(element.name))

                case "G": 
                    self.add_vccs(self.node_map[element.connections[0]], self.node_map[element.connections[1]], # noqa: E701
                        self.node_map[element.connections[3]], self.node_map[element.connections[4]], sp.symbols(element.name))

        print("Finished building equation system!")
        logger.debug("Finished building equation system!")   
            
            

    def solve(self):
        """Return the solution of the equation system.
        
        Returns:
            sol(array): array with symbolic solutuions

        """
        x = self.get_unknowns()

        logger.debug(self.A)
        logger.debug(x)
        logger.debug(self.z)

        print("Solving equation system...")
        logger.debug("Solving equation system...")

        #result = sp.solve(self.A * x - self.z, x)
        result = self.A.LUsolve(self.z)

        result_dict = dict(zip(x, result))

        print("Finished solving equation system!")
        logger.debug("Finished solving equation system!")

        logger.debug(result_dict)

        return result_dict
    
         
