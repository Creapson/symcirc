import sympy as sp
import Circuit
import logging as logger
import Pspice_util as pu
import numpy as np
from Equation_Formulator import EquationFormulator

class SparseTableau(EquationFormulator):
    """Class for sparse tableau analysis method.
    """
    ct:Circuit
    value_dict:dict
  

    def __init__(self, circuit:Circuit):
        """Constructor for SparseTableau class.

        Args:
            circuit (Circuit): Circuit object to analyze.

        """
        
        self.ct = circuit
        self.value_dict = self.generateValueDict(self.ct)

        self.n = len(self.ct.nodes) - 1  # Anzahl Knoten ohne Masse
        self.m = len(self.ct.elements)  # Anzahl der Zweige
        self.A = sp.zeros(self.n, self.m)
        self.G = sp.zeros(self.m, self.m)
        self.H = sp.zeros(self.m, self.m)
        self.RHS = sp.zeros(0, 0)
        self.CM_RHS = sp.zeros(0, 0)

        

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
    

    
    def buildIncidenceMatrix(self):
        """Builds the incidence matrix for the circuit.

        Returns:
            sp.Matrix: Incidence matrix.

        """
        

        for j, element in enumerate(self.ct.elements):

            

            i = self.node_map[element.connections[0]]

            if i != 0:  # Exclude ground node
                self.A[i-1, j] = 1
            
            i = self.node_map[element.connections[1]]
            if i != 0:  # Exclude ground node
                self.A[i-1, j] = -1
            
            if len(element.connections) < 4: #check for 4 terminal elements
                continue

            i = self.node_map[element.connections[2]]
            if i != 0:  # Exclude ground node
                self.A[i-1, j] = 1
            
            i = self.node_map[element.connections[3]]
            if i != 0:  # Exclude ground node
                self.A[i-1, j] = -1

    def buildComponentMatrices(self):
        """Builds the component matrices for the circuit.

        Returns:
            None

        """
        s = sp.symbols('s')
         
        
        for j, element in enumerate(self.ct.elements):
            symbol = element.get_symbol()
            match element.type:
                case "R": 
                    self.G[j, j] = sp.symbols(symbol)
                    self.H[j, j] = -1
                    self.CM_RHS = self.CM_RHS.row_insert(self.CM_RHS.rows, sp.Matrix([[0]]))

                case "L": 
                    self.G[j, j] = sp.symbols(symbol) * s
                    self.H[j, j] = -1
                    self.CM_RHS = self.CM_RHS.row_insert(self.CM_RHS.rows, sp.Matrix([[0]]))

                case "C": 
                    self.G[j, j] = -1
                    self.H[j, j] = 1 / (sp.symbols(symbol) * s)
                    self.CM_RHS = self.CM_RHS.row_insert(self.CM_RHS.rows, sp.Matrix([[0]]))

                case "V": 
                    self.G[j, j] = 0
                    self.H[j, j] = 1
                    self.CM_RHS = self.CM_RHS.row_insert(self.CM_RHS.rows, sp.Matrix([[sp.symbols(symbol)]]))
                    

                case "I": 
                    self.G[j, j] = 1
                    self.H[j, j] = 0
                    self.CM_RHS = self.CM_RHS.row_insert(self.CM_RHS.rows, sp.Matrix([[sp.symbols(symbol)]]))
                    
                
                case "H": # CCVS
                    self.G[j, j] = 0
                    self.H[j, j] = -1
                    controlled_Element_index = self.findControlledElement(element, j)
                    self.G[j, controlled_Element_index] = sp.symbols(symbol)
                    self.CM_RHS = self.CM_RHS.row_insert(self.CM_RHS.rows, sp.Matrix([[0]]))

                    
                    

                case "F": # CCCS
                    self.H[j, j] = 0
                    self.G[j, j] = -1
                    controlled_Element_index = self.findControlledElement(element, j)
                    self.G[j, controlled_Element_index] = sp.symbols(symbol)
                    self.CM_RHS = self.CM_RHS.row_insert(self.CM_RHS.rows, sp.Matrix([[0]]))
                    

                case "E": # VCVS
                    self.G[j, j] = 0
                    self.H[j, j] = -1
                    controlled_Element_index = self.findControlledElement(element, j)
                    self.H[j, controlled_Element_index] = sp.symbols(symbol)
                    self.CM_RHS = self.CM_RHS.row_insert(self.CM_RHS.rows, sp.Matrix([[0]]))

                case "G": # VCCS
                    self.G[j, j] = -1
                    self.H[j, j] = 0
                    controlled_Element_index = self.findControlledElement(element, j)
                    self.H[j, controlled_Element_index] = sp.symbols(symbol)
                    self.CM_RHS = self.CM_RHS.row_insert(self.CM_RHS.rows, sp.Matrix([[0]]))
    
    def findControlledElement(self, controlElement, control_index):
        """Finds the controlled element for a given control name.

        Args:
            control_name (str): Name of the controlling element.

        Returns:
            int: Index of the controlled element.
        """
        for current_index, element in enumerate(self.ct.elements):
            match element.type:
                case "V" | "I" | "R" | "L" | "C":
                    if {self.node_map[element.connections[0]], self.node_map[element.connections[1]]} == {self.node_map[controlElement.connections[0]], self.node_map[controlElement.connections[1]]}:
                        if current_index != control_index:
                            return current_index
                
                case "H" | "F" | "E" | "G":
                    if {self.node_map[element.connections[2]], self.node_map[element.connections[3]]} == {self.node_map[controlElement.connections[0]], self.node_map[controlElement.connections[1]]}:
                        if current_index != control_index:
                            return current_index
        
        raise ValueError("Controlled element not found.")

    def buildRHS(self):
        """Builds the right-hand side vector for the circuit.

        Returns:
            sp.Matrix: Right-hand side vector.

        """
        self.RHS = sp.Matrix([[0]] * (self.n+self.m)).col_join(self.CM_RHS)

    def buildEquationSystem(self):
        """Builds the complete equation system for the circuit.

        Returns:
            sp.Matrix: Complete equation system.

        """
        # n - number of nodes without ground
        # m - number of branches

        top = sp.Matrix.hstack(sp.zeros(self.n, self.n), self.A, sp.zeros(self.n, self.m))

        middle = sp.Matrix.hstack(self.A.T, sp.zeros(self.m, self.m), -sp.eye(self.m))

        bottom = sp.Matrix.hstack(sp.zeros(self.m,self.n), self.G, self.H)

        system_matrix = sp.Matrix.vstack(top, middle, bottom)
        return system_matrix
    
    def solve(self):
        """Solves the equation system for the circuit.

        Returns:
            sp.Matrix: Solution vector.

        """
        print("Solving Sparse Tableau System...")
        system_matrix = self.buildEquationSystem()
        solution = system_matrix.LUsolve(self.RHS)
        print("Sparse Tableau System solved.")
        return solution