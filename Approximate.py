import sympy as sp
import numpy as np
from Modified_Node_Analysis import ModifiedNodalAnalysis
from Equation_Formulator import EquationFormulator
from Circuit import Circuit

def generate_term_list(matrix):
    """Generate term list of matrix.

    Args:
        matrix (sp.matrix): symbolic matrix

    Returns:
        list: list of terms in the form ((i, j), term, relevance coefficient (this is 0.0 for now))
    """
    term_list = []
    for i in range(matrix.rows):
        for j in range(matrix.cols):
            expr = matrix[i, j]
            if (expr == 0):
                continue
            terms = list(sp.Add.make_args(expr))
            for t in terms:
                term_list.append(((i, j), t, 0.0))  # Placeholder for numerical value
    return term_list

def generate_relevance_coefficients(analysis: ModifiedNodalAnalysis, input_potential,  output_potential, approx_ppoints):
    """Generate relevance coefficients for each term in the term list.

    Args:
        term_list (list): list of terms in the form ((i, j), term, relevance coefficient)
        mna (ModifiedNodalAnalysis): MNA instance with numerical solution
        input_potential (sp.Expr): dictionary key for input potential
        output_potential (sp.Expr): dictionary key for output potential

    Returns:
        list: updated term list with relevance coefficients
    """
    term_list = generate_term_list(analysis.A)

    s = sp.symbols('s')

    H = analysis.num_result[output_potential] / analysis.num_result[input_potential]

    H_lambdified = sp.lambdify(s, H, 'numpy')
    
    w = np.array(approx_ppoints)      
    jw = 1j * w

    H_eval = H_lambdified(jw)
    abs_H_eval = 20 * np.log10(abs(H_eval))
    

    idx = 0

    for (i, j), term, _ in term_list:
        print(f"Processing term {idx + 1} / {len(term_list)}")

        #Copy original A matrix and subtract the term
        mod_A = analysis.A.copy()

        mod_A[i, j] = mod_A[i, j] - term

        # Convert modified A matrix to numerical and solve

        mod_A_num = analysis.toNumerical(mod_A, analysis.value_dict)

        x = analysis.get_unknowns()

        z_num = analysis.toNumerical(analysis.z.copy(), analysis.value_dict)



        solutions = sp.solve(mod_A_num * x - z_num, x, dict=True)

        if not solutions:
            #If no solution found, set relevance coefficient to infinity
            term_list[idx] = ((i, j), term, float('inf'))
            idx += 1
            continue

        mod_num_result = solutions[0]

       
        
        

        mod_H_num = mod_num_result[output_potential] / mod_num_result[input_potential]

        mod_H_num = mod_H_num.subs(analysis.num_result)

        mod_H_num_lambdified = sp.lambdify(s, mod_H_num, 'numpy')

        mod_H_eval = mod_H_num_lambdified(jw)

        abs_mod_H_eval = 20 * np.log10(abs(mod_H_eval))

      

        #Calculate relative error between original and modified transfer function at approximation points

        relative_error = np.abs((abs_H_eval - abs_mod_H_eval) / abs_H_eval)



        relevance_coefficient = np.max(relative_error) #TODO: klären ob max, mean oder etwas anderes

        #Update term list with relevance coefficient
        term_list[idx] = ((i, j), term, relevance_coefficient)
        
        idx += 1
        del mod_A
        del mod_A_num

    return term_list

def approximate(analysis:ModifiedNodalAnalysis, term_list, max_error, input_potential,  output_potential):
    """
    Remove terms from matrix A with smallest errors until max_error is reached.

    Args:
        A (sp.Matrix): original system matrix
        term_list (list): [((i, j), term, error), ...]
        max_error (float): allowed accumulated error

    Returns:
        A_reduced (sp.Matrix): modified matrix
        removed_terms (list): removed entries
        accumulated_error (float)
    """

    # 1. Sort term list by error (ascending)
    sorted_terms = sorted(term_list, key=lambda x: x[2])

    # 2. Copy matrix (do NOT modify original)
    A_reduced = analysis.A.copy()

    accumulated_error = 0.0
    removed_terms = []

    # 3. Remove terms until error limit reached
    for (i, j), term, error in sorted_terms:

        if accumulated_error + error > max_error:
            break

        A_reduced[i, j] -= term
        accumulated_error += error
        removed_terms.append(((i, j), term, error))
    
    x = analysis.get_unknowns()

    solutions = sp.solve(A_reduced * x - analysis.z, x, dict=True)

    result_approx = solutions[0]

    result = result_approx[output_potential] / result_approx[input_potential]

    return result
