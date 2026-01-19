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

  
    s = sp.symbols('s')
    approx_points = np.atleast_1d(approx_points)
    jw = 1j * approx_points

   
    x_syms = list(analysis.get_unknowns())
    idx_in = x_syms.index(input_potential)
    idx_out = x_syms.index(output_potential)

   
    A_sym = analysis.A.subs(analysis.value_dict)
    z_sym = analysis.z.subs(analysis.value_dict)

    A_func = sp.lambdify(s, A_sym, "numpy")
    z_func = sp.lambdify(s, z_sym, "numpy")

    n_freq = len(jw)
    n = A_sym.rows

  
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
        abs_H_ref[k] = np.abs(H)

        A_base.append(A_num)
        lu_cache.append((lu, piv))
        z_num_cache.append(z_num)
        x_ref_cache.append(x)

    for idx, ((i, j), term, _) in enumerate(term_list):
        #print(f"Processing term {idx + 1} / {len(term_list)}")

        term_num = sp.lambdify(s, term.subs(analysis.value_dict), "numpy")

        abs_H_mod = np.empty(n_freq)

        failed = False

        for k, w in enumerate(jw):
          
            A_mod = A_base[k].copy()
            A_mod[i, j] -= complex(term_num(w))


            try:
                lu, piv = scipy.lu_factor(A_mod)
                x_mod = scipy.lu_solve((lu, piv), z_num_cache[k])

                H_mod = x_mod[idx_out] / x_mod[idx_in]
                abs_H_mod[k] = np.abs(H_mod)

            except Exception:
                term_list[idx] = ((i, j), term, float("inf"))
                failed = True
                break

        if failed:
            continue

        relative_error = np.abs((abs_H_ref - abs_H_mod) / abs_H_ref)
        term_list[idx] = ((i, j), term, np.max(relative_error)) 

    
    return term_list


def approximate(
    analysis,
    max_error,
    input_potential,
    output_potential,
    approx_points,
    rel_error_threshold
):
    term_list = generate_relevance_coefficients(analysis, input_potential, output_potential, approx_points)
    term_list = [entry for entry in term_list if not np.isnan(entry[2])]
  
    term_list.sort(key=lambda x: x[2])

    # 2. Originalmatrix
    A_reduced = analysis.A.copy()

    # 3. Referenz (Originalsystem)
    H_ref = compute_transfer_function_numeric(
        analysis,
        analysis.A,
        analysis.z,
        approx_points,
        input_potential,
        output_potential
    )
    abs_H_ref = np.abs(H_ref)
    

    
    accumulated_relevance_error = 0.0
    true_error = 0.0

    # 4. Terme iterativ entfernen
    while term_list:
        #remove terms with NaN error
        
        

        (i, j), term, rel_coeff = term_list.pop(0)

        A_trial = A_reduced.copy()
        A_trial[i, j] -= term

        try:
            H_trial = compute_transfer_function_numeric(
                    analysis,
                    A_trial,
                    analysis.z,
                    approx_points,
                    input_potential,
                    output_potential
                )
        
        except NonInvertibleMatrixError:
            continue
        

        if has_phase_sign_jump(H_ref, H_trial):
            continue

       
        abs_H_trial= np.abs(H_trial)
        mask = abs_H_ref > 1e-12
        
        true_error = np.max(
            np.abs(abs_H_ref[mask] - abs_H_trial[mask]) / abs_H_ref[mask]
        )
        
        

        if true_error > max_error:
            break



        # akzeptieren
        A_reduced = A_trial.copy()
        accumulated_relevance_error += rel_coeff

        rel_diff = np.abs(true_error - accumulated_relevance_error) / (true_error + 1e-12)
        print(rel_diff)

        if rel_diff > rel_error_threshold:
            print("Updating relevance coefficients...")
            H_ref = compute_transfer_function_numeric(
                analysis,
                A_reduced,
                analysis.z,
                approx_points,
                input_potential,
                output_potential
            )

            abs_H_ref = np.abs(H_ref)

            term_list = update_remaining_terms(
                analysis,
                A_reduced,
                term_list,
                input_potential,
                output_potential,
                approx_points
            )
            term_list = [entry for entry in term_list if not np.isnan(entry[2])]
            term_list.sort(key=lambda x: x[2])
            accumulated_relevance_error = 0.0

        

    x = analysis.get_unknowns()

    solutions = sp.solve(A_reduced * x - analysis.z, x, dict=True)

    

    result_approx = solutions[0]

    result = result_approx[output_potential] / result_approx[input_potential]

    return result

    

# def approximate(analysis:ModifiedNodalAnalysis, term_list, max_error, input_potential,  output_potential):
#     """
#     Remove terms from matrix A with smallest errors until max_error is reached.

#     Args:
#         A (sp.Matrix): original system matrix
#         term_list (list): [((i, j), term, error), ...]
#         max_error (float): allowed accumulated error

#     Returns:
#         A_reduced (sp.Matrix): modified matrix
#         removed_terms (list): removed entries
#         accumulated_error (float)
#     """

#     #remove terms with NaN error
#     term_list = [entry for entry in term_list if not np.isnan(entry[2])]
    
#     #sort terms by relevance coefficient (ascending)
#     sorted_terms = sorted(term_list, key=lambda x: x[2])
    
 
#     A_reduced = analysis.A.copy()

#     accumulated_error = 0.0
#     removed_terms = []

#     # 3. Remove terms until error limit reached
#     for (i, j), term, error in sorted_terms:

#         if accumulated_error + error > max_error:
#             break

#         A_reduced[i, j] -= term
#         accumulated_error += error
#         removed_terms.append(((i, j), term, error))
    
#     x = analysis.get_unknowns()

#     solutions = sp.solve(A_reduced * x - analysis.z, x, dict=True)

#     result_approx = solutions[0]

#     result = result_approx[output_potential] / result_approx[input_potential]

#     return result


def compute_transfer_function_numeric(analysis, A_sym, z_sym ,approx_points, input_potential, output_potential):

    s = sp.symbols("s")
    approx_points = np.atleast_1d(approx_points)
    jw = 1j * approx_points

    x_syms = list(analysis.get_unknowns())
    idx_in = x_syms.index(input_potential)
    idx_out = x_syms.index(output_potential)

    A_func = sp.lambdify(s, A_sym.subs(analysis.value_dict), "numpy")
    z_func = sp.lambdify(s, z_sym.subs(analysis.value_dict), "numpy")

    H = np.empty(len(jw))
    n = A_sym.rows

    for k, w in enumerate(jw):
        A_num = np.array(A_func(w), dtype=complex)
        z_num = np.array(z_func(w), dtype=complex).reshape(n)

        lu, piv = scipy.lu_factor(A_num)
        x = scipy.lu_solve((lu, piv), z_num)

        

        H[k] = x[idx_out] / x[idx_in]

    return H

def has_phase_sign_jump(H_ref, H_trial, threshold=np.pi):
    phi_ref   = np.unwrap(np.angle(H_ref))
    phi_trial = np.unwrap(np.angle(H_trial))

    dphi = phi_trial - phi_ref

    return np.any(np.abs(np.diff(dphi)) > threshold)


def update_remaining_terms(
    analysis,
    A_current,
    remaining_terms,
    input_potential,
    output_potential,
    approx_points
):
    """
    Recompute relevance coefficients for remaining terms
    based on the current reduced matrix A_current.
    """

    # temporär analysis.A ersetzen
    A_backup = analysis.A.copy()
    analysis.A = A_current.copy()

    updated = generate_relevance_coefficients(
        analysis,
        input_potential,
        output_potential,
        approx_points
    )

    # nur verbleibende Terme übernehmen
    updated_dict = {
        (i, j): coeff
        for ((i, j), _, coeff) in updated
    }

    new_term_list = []
    for (i, j), term, _ in remaining_terms:
        new_term_list.append(
            ((i, j), term, updated_dict[(i, j)])
        )

    # analysis.A zurücksetzen
    analysis.A = A_backup.copy()

   

    return new_term_list
