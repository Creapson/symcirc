"""Defines analyzing classes for EquationFormulator.
"""
import netlist.Circuit as Circuit
import sympy as sp
import logging
import Pspice_util as pu
logger = logging.getLogger(__name__)

class EquationFormulator:
    """_summary_.
    """
    
    def __init__(self):
        """_summary_.

        """
    
    def generateValueDict(self, ct:Circuit):

        value_dict = {}

        for element in self.ct.elements:
            symbol = element.get_symbol()
            match element.type:
                case "R" | "L" | "C": 
                    value_dict.update({sp.symbols(symbol): pu.pspice_to_float(element.params["value_dc"])})

                case "V" | "I": 
                    value_dict.update({sp.symbols(symbol): element.params.get("value_ac", 0)})
                
                case "H" | "F" | "E" | "G": 
                    value_dict.update({sp.symbols(symbol): pu.pspice_to_float(element.params["value"])})

        return value_dict
    
    def toNumerical(self, matrix, value_dict):
        """Convert symbolic matrix to numerical matrix based on the value dictionary.

        Args:
            matrix (matrix): symbolic matrix

        Returns:
            num_matrix (matrix): numerical matrix

        """
        num_matrix = matrix.subs(value_dict)
        return num_matrix

    def estimateTerms(self, matrix: sp.Matrix):
        """Estimate the terms of an equation system.

        Args:
            matrix (sp.Matrix): _Matrix of equation system.

        Raises:
            TypeError: Argument is not a sympy MatrixBase object.

        Returns:
            sympy.Expr: Determinant of the matrix with all symbols replaced by 1.

        """
        if not isinstance(matrix, sp.MatrixBase):
            raise TypeError(self.EXCEPTION_NOTAMATRIX)
        
       
        symbols = matrix.free_symbols
        
      
        subs_dict = {s: 1 for s in symbols}

        matrix_ones = matrix.subs(subs_dict)

        return sp.det(matrix_ones)    







