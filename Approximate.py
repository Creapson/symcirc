import sympy as sp
from sympy.matrices.exceptions import NonInvertibleMatrixError
import numpy as np
import time
import scipy.linalg as scipy
from Modified_Node_Analysis import ModifiedNodalAnalysis


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

def generate_relevance_coefficients(analysis: ModifiedNodalAnalysis, input_potential,  output_potential, approx_points):
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

    # -----------------------------
    # Vorbereitung
    # -----------------------------
    s = sp.symbols('s')
    approx_points = np.atleast_1d(approx_points)
    jw = 1j * approx_points

    # Unbekannte → Liste
    x_syms = list(analysis.get_unknowns())
    idx_in = x_syms.index(input_potential)
    idx_out = x_syms.index(output_potential)

    # Symbolische Matrizen → numerische Funktionen (EINMAL!)
    A_sym = analysis.A.subs(analysis.value_dict)
    z_sym = analysis.z.subs(analysis.value_dict)

    A_func = sp.lambdify(s, A_sym, "numpy")
    z_func = sp.lambdify(s, z_sym, "numpy")

    n_freq = len(jw)
    n = A_sym.rows

    # -----------------------------
    # Referenzlösung + LU-Caching
    # -----------------------------
    abs_H_ref = np.empty(n_freq)

    A_base = []
    lu_cache = []
    z_num_cache = []
    x_ref_cache = []

    for k, w in enumerate(jw):
        A_num = np.array(A_func(w), dtype=complex)
        z_num = np.array(z_func(w), dtype=complex).reshape(n)

        lu, piv = scipy.lu_factor(A_num)
        x = scipy.lu_solve((lu, piv), z_num)

        H = x[idx_out] / x[idx_in]
        abs_H_ref[k] = 20 * np.log10(abs(H))

        A_base.append(A_num)
        lu_cache.append((lu, piv))
        z_num_cache.append(z_num)
        x_ref_cache.append(x)

    # -----------------------------
    # Schleife über Terme
    # -----------------------------
    for idx, ((i, j), term, _) in enumerate(term_list):
        print(f"Processing term {idx + 1} / {len(term_list)}")

        term_num = sp.lambdify(s, term.subs(analysis.value_dict), "numpy")

        abs_H_mod = np.empty(n_freq)

        failed = False

        for k, w in enumerate(jw):
            # Matrix kopieren (nur numerisch!)
            A_mod = A_base[k].copy()
            A_mod[i, j] -= complex(term_num(w))


            try:
                lu, piv = scipy.lu_factor(A_mod)
                x_mod = scipy.lu_solve((lu, piv), z_num_cache[k])

                H_mod = x_mod[idx_out] / x_mod[idx_in]
                abs_H_mod[k] = 20 * np.log10(abs(H_mod))

            except Exception:
                term_list[idx] = ((i, j), term, float("inf"))
                failed = True
                break

        if failed:
            continue

        relative_error = np.abs((abs_H_ref - abs_H_mod) / abs_H_ref)
        term_list[idx] = ((i, j), term, np.max(relative_error))

    # term_list = generate_term_list(analysis.A)

    # s = sp.symbols('s')

    # jw = 1j * np.asarray(approx_points)

    # A_sym = analysis.A
    # z_sym = analysis.z
    # x_sym = list(analysis.get_unknowns())

    # idx_in = x_sym.index(input_potential)
    # idx_out = x_sym.index(output_potential)

    # A_func = sp.lambdify(s, A_sym.subs(analysis.value_dict), "numpy")
    # z_func = sp.lambdify(s, z_sym.subs(analysis.value_dict), "numpy")

    # H_ref = np.empty(len(jw), dtype=complex)

    # for k, w in enumerate(jw):
    #     A_num = np.array(A_func(w), dtype=complex)
    #     z_num = np.array(z_func(w), dtype=complex).reshape(-1)

    #     x = np.linalg.solve(A_num, z_num)
    #     H_ref[k] = x[idx_out] / x[idx_in]

    # abs_H_ref = 20 * np.log10(np.abs(H_ref))

  

    # for idx, ((i, j), term, _) in enumerate(term_list):

        

        

    #     A_mod_sym = A_sym.copy()
    #     A_mod_sym[i, j] -= term

    #     A_mod_func = sp.lambdify(s, A_mod_sym.subs(analysis.value_dict), "numpy")

    #     H_mod = np.empty(len(jw), dtype=complex)

    #     failed = False

    #     for k, w in enumerate(jw):
    #         try:
    #             A_mod_num = np.array(A_mod_func(w), dtype=complex)
    #             z_num = np.array(z_func(w), dtype=complex).reshape(-1)

    #             x_mod = np.linalg.solve(A_mod_num, z_num)
    #             H_mod[k] = x_mod[idx_out] / x_mod[idx_in]

    #         except np.linalg.LinAlgError:
    #             term_list[idx] = ((i, j), term, float('inf'))
    #             failed = True
    #             break

    #     if failed:
    #         continue

    #     abs_H_mod = 20 * np.log10(np.abs(H_mod))
    #     relative_error = np.abs((abs_H_ref - abs_H_mod) / abs_H_ref)

    #     term_list[idx] = ((i, j), term, np.max(relative_error))

        
        
       
    
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
    term_list = [entry for entry in term_list if not np.isnan(entry[2])]
    
    sorted_terms = sorted(term_list, key=lambda x: x[2])
    
    # print("Sorted term list for approximation:")
    # for (i, j), term, error in sorted_terms:
    #     print(f"Term at position ({i}, {j}): {term}, Relevance Coefficient: {error}")

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
