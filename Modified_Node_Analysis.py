import sympy as sp
import netlist.Circuit as Circuit
import logging as logger
import Pspice_util as pu
import numpy as np
from Equation_Formulator import EquationFormulator

class ModifiedNodalAnalysis(EquationFormulator):
    """Class for modified nodal analysis method.


    """
    ct:Circuit
    value_dict:dict
  

    def __init__(self, circuit:Circuit):
        """Innitialize the class.

        Args:
            circuit (Circuit): The Circuit to analyze.

        """
        self.value_dict = {}
        self.ct = circuit
        self.n = len(self.ct.nodes) - 1  # Anzahl Knoten ohne Masse (0)
        self.A = sp.zeros(self.n, self.n)
        self.z = sp.zeros(self.n, 1)
        self.current_var_index = 0    # Gesamtanzahl von Stromvariablen

        self.sym_result = {}
        self.num_result = {}

        #create mapping for node names to integer values for easy matrix handling
   
        self.node_map = {}
        used_values = set()
        
        for node in self.ct.nodes:
            if node.isdigit():
                val = int(node)
                if val not in used_values:
                    self.node_map[node] = val
                    used_values.add(val)
        
        for node in self.ct.nodes:
            if not node.isdigit():      
                # No number, assign next available starting from 1
                val = 1
                while val in used_values:
                    val += 1
                self.node_map[node] = val
                used_values.add(val)
        
        size = len(self.node_map)
        self.unknowns = [None] * size

        for name, idx in self.node_map.items():
            if (name == "ground") | (name == "0") | (name == "GND") | (name == "gnd"):
                # Masseknoten bekommt kein Symbol (None bleibt stehen)
                continue
            self.unknowns[idx] = sp.Symbol(f"V_{name}")

        # Falls Masseknoten (oder andere fehlende Indizes) vorhanden sind:
        # setze Dummy-Symbole NICHT -> SymPy soll nur echte Variablen enthalten
        # hier entfernen wir leere Einträge
        self.unknowns = [s for s in self.unknowns if s is not None]
        self.unknowns = sp.Matrix(self.unknowns)
        
     
                
    def expand_matrix(self, symName):
        """Expand matrix in case of an additional voltage source by 1 row and 1 column.

        """
        rows, cols = self.A.shape
        last_row = sp.zeros(1, cols + 1)
        self.A = self.A.row_join(sp.zeros(rows, 1))   # rechte Spalte anhängen
        self.A = self.A.col_join(last_row)            # neue letzte Zeile

        self.z = self.z.col_join(sp.Matrix([0]))

        newsym = sp.Symbol("I_" + str(symName))
        self.unknowns = self.unknowns.col_join(sp.Matrix([newsym]))
                                               
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

    def add_independent_current_source(self, node1, node2, value, num_value):
        """Add independent current source. 
        Direction of the current is from node1 to node2.

        Args:
            node1 (int): Node 1 of the current source.
            node2 (int): Node 2 of the current source.
            value (symbol): Symbol of the source.

        """
        if num_value != 0:
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
        self.expand_matrix(sym_value)
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
        self.expand_matrix(beta)
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

        
    def add_vcvs(self, node_out1, node_out2, node_ctrl1, node_ctrl2, gain):
        """Add voltage controlled voltage source.

        Args:
            node_out1 (int): node 1 of controlled element
            node_out2 (int): node 2 of controlled element
            node_ctrl1 (int): node 1 of controlling element
            node_ctrl2 (int): node 2 of controlling element
            gain (float): gain factor

        """
        self.expand_matrix(gain)
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
        self.expand_matrix(r_m + "_ctrl")
        ctrl_idx = self.A.rows - 1

                        
        if node_ctrl1 != 0:
            self.A[ctrl_idx, node_ctrl1 - 1] += 1
            self.A[node_ctrl1 - 1, ctrl_idx] += 1
                        
        if node_ctrl2 != 0:
            self.A[ctrl_idx, node_ctrl2 - 1] += -1
            self.A[node_ctrl2 - 1, ctrl_idx] += -1
                        
        self.z[ctrl_idx] = 0
                        
        self.expand_matrix(r_m)
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
       
        

        return self.unknowns
    
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
                case "R": 
                    self.add_admittance(self.node_map[element.connections[0]], self.node_map[element.connections[1]],  # noqa: E701
                                              1/sp.symbols(element.name))
                    self.value_dict.update({sp.symbols(element.name): pu.pspice_to_float(element.params["value_dc"])})

                case "L": 
                    self.add_admittance(self.node_map[element.connections[0]], self.node_map[element.connections[1]], # noqa: E701
                                              1/s*sp.symbols(element.name))
                    self.value_dict.update({sp.symbols(element.name): pu.pspice_to_float(element.params["value_dc"])})

                case "C": 
                    self.add_admittance(self.node_map[element.connections[0]], self.node_map[element.connections[1]], # noqa: E701
                                              (s*sp.symbols(element.name)))
                    self.value_dict.update({sp.symbols(element.name): pu.pspice_to_float(element.params["value_dc"])})

                case "V": 
                    self.add_independent_voltage_source(self.node_map[element.connections[0]], # noqa: E701
                        self.node_map[element.connections[1]], sp.symbols(element.name), element.params.get("value_ac", 0))
                    self.value_dict.update({sp.symbols(element.name): element.params.get("value_ac", 0)})

                case "I": 
                    self.add_independent_current_source(self.node_map[element.connections[0]], # noqa: E701
                                                self.node_map[element.connections[1]], sp.symbols(element.name), element.params.get("value_ac", 0))
                    self.value_dict.update({sp.symbols(element.name): element.params.get("value_ac", 0)})
            
           
                    
        for element in self.ct.elements:

            
            match element.type:
                
                case "H": 
                    self.add_ccvs(self.node_map[element.connections[0]], self.node_map[element.connections[1]], # noqa: E701
                        self.node_map[element.connections[2]], self.node_map[element.connections[3]], sp.symbols(element.name))
                    self.value_dict.update({sp.symbols(element.name): pu.pspice_to_float(element.params["value"])})

                case "F": 
                    self.add_cccs(self.node_map[element.connections[0]], self.node_map[element.connections[1]],
                        self.node_map[element.connections[2]], self.node_map[element.connections[3]], sp.symbols(element.name))
                    self.value_dict.update({sp.symbols(element.name): pu.pspice_to_float(element.params["value"])})

                case "E": 
                    self.add_vcvs(self.node_map[element.connections[0]], self.node_map[element.connections[1]], # noqa: E701
                        self.node_map[element.connections[2]], self.node_map[element.connections[3]], sp.symbols(element.name))
                    self.value_dict.update({sp.symbols(element.name): pu.pspice_to_float(element.params["value"])})

                case "G": 
                    self.add_vccs(self.node_map[element.connections[0]], self.node_map[element.connections[1]], # noqa: E701
                        self.node_map[element.connections[2]], self.node_map[element.connections[3]], sp.symbols(element.name))
                    self.value_dict.update({sp.symbols(element.name): pu.pspice_to_float(element.params["value"])})

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

        self.sym_result = sp.solve(self.A * x - self.z, x)
        #result = self.A.LUsolve(self.z)

        #result_dict = dict(zip(x, result))

        print("Finished solving equation system!")
        logger.debug("Finished solving equation system!")

        #logger.debug(result_dict)
        

        return self.sym_result
    


    def solveNumerical(self, value_dict):

        """Solve the equation system numerically based on the value dictionary.

        Args:
            value_dict (dict): dictionary with numerical values for symbols

        Returns:
            sol(array): array with numerical solutions

        """
        x = self.get_unknowns()

        A_num = self.toNumerical(self.A, value_dict)
        z_num = self.toNumerical(self.z, value_dict)

        print("Solving numerical equation system...")
        logger.debug("Solving numerical equation system...")

        self.num_result = sp.solve(A_num * x - z_num, x)

        print("Finished solving numerical equation system!")
        logger.debug("Finished solving numerical equation system!")

        return self.num_result
    
