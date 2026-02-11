import sympy as sp
from sympy.matrices.exceptions import NonInvertibleMatrixError
import numexpr
import numpy as np
import time
import scipy.linalg as scipy
from Modified_Node_Analysis import ModifiedNodalAnalysis


class Approximation:

    def __init__(self, equation_formulator):
        self.analysis = equation_formulator
        pass


    def generate_term_list(self, matrix):
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

    def generate_relevance_coefficients(self, input_potential,  output_potential, approx_points, sysMatrix):
        """Generate relevance coefficients for each term in the term list.

        Args:
            term_list (list): list of terms in the form ((i, j), term, relevance coefficient)
            mna (ModifiedNodalAnalysis): MNA instance with numerical solution
            input_potential (sp.Expr): dictionary key for input potential
            output_potential (sp.Expr): dictionary key for output potential

        Returns:
            list: updated term list with relevance coefficients
        """
        term_list = self.generate_term_list(sysMatrix)

    
        s = sp.symbols('s')
        approx_points = np.atleast_1d(approx_points)
        jw = 1j * approx_points

    
        x_syms = list(self.analysis.get_unknowns())
        idx_in = x_syms.index(input_potential)
        idx_out = x_syms.index(output_potential)

    
        A_sym = sysMatrix.subs(self.analysis.value_dict)
        z_sym = self.analysis.z.subs(self.analysis.value_dict)

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

            term_num = sp.lambdify(s, term.subs(self.analysis.value_dict), "numpy")

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
            term_list[idx] = ((i, j), term, relative_error) 

        
        return term_list


    def approximate(
        self,
        input_potential,
        output_potential,
        reference_points,
        rel_error_threshold,
        sorting_method,
        column=0
    ):
        #Initialize
        approx_points = [a for a, _ in reference_points]
        approx_points_errors = [b for _, b in reference_points]

        #----------------------------------------------------------
        # Determine maximum allowed error

        max_error = max(approx_points_errors)

        
        #----------------------------------------------------------
        #get potential indices
        x_syms = list(self.analysis.get_unknowns())
        idx_in = x_syms.index(input_potential)
        idx_out = x_syms.index(output_potential)

        #z numeric function
        z_num = self.analysis.z.subs(self.analysis.value_dict)
        z_num_func = sp.lambdify(sp.symbols('s'), z_num, "numpy")

        #Compute sensitivities
        term_list_sym = self.generate_relevance_coefficients( 
                                                         input_potential, 
                                                         output_potential, 
                                                         approx_points, 
                                                         self.analysis.A)
        term_list_sym = [entry for entry in term_list_sym if not np.isnan(entry[2]).any()]


        # Sort term list by relevance coefficient --------------------------------------------------

        term_list_sym = self.sort_term_list(term_list_sym, sorting_method, column)
        term_list_sym.sort(key=lambda x: x[2].real)

        print("Initial term list:")
        print(term_list_sym)

        # ------------------------------------------------------------------------------------------


        # Matrix init
        A_reduced = self.analysis.A.copy()

        #split linear s-dependence
        s = sp.symbols('s')

        A0, A1, term_list = self.split_linear_s_dependence(
            A_reduced,
            term_list_sym,
            s
        )



        # Compute reference transfer function
        H_ref = self.compute_transfer_function_numeric(
            A0,
            A1,
            z_num_func,
            approx_points,
            idx_in,
            idx_out
        )
        abs_H_ref = np.abs(H_ref)
        

        #Initialize error trackers an removed terms list
        accumulated_relevance_error = 0.0
        true_error = 0.0
        removed_terms = []   

        
        
        while term_list:
            
            #get next, least relevant, term
            

            (i, j), t0, t1, rel_coeff = term_list.pop(0) #get least relevant numeric term


            (i_sym, j_sym), term, rel_coeff_sym = term_list_sym.pop(0) # get least relevant symbolic term for record keeping

            print(f"Trying to remove term {term} at position ({i}, {j}) with relevance coefficient {rel_coeff}")

            #-------------------------------------------------------------------------------
            # create trial matrices


            A0_trial = A0.copy()
            A1_trial = A1.copy()

            A0_trial[i, j] -= t0
            A1_trial[i, j] -= t1

            #-------------------------------------------------------------------------------
            # compute trial transfer function

            try:
                
                H_trial = self.compute_transfer_function_numeric(
                        A0_trial,
                        A1_trial,
                        z_num_func,
                        approx_points,
                        idx_in,
                        idx_out
                    )
                

            except NonInvertibleMatrixError:
                continue
            

            if self.has_phase_sign_jump(H_ref, H_trial):# check for phase jumps 
                continue

        
            abs_H_trial= np.abs(H_trial)


            #-------------------------------------------------------------------------------
            # calculate true error
            
            
            true_error = np.max(
                np.abs(abs_H_ref - abs_H_trial) / abs_H_ref
            )
            
            
            #check if true error is acceptable
            if true_error > max_error: #TODO: max_error per frequency point
                break


            #-------------------------------------------------------------------------------
           
            #accept removal
            A0 = A0_trial.copy()
            A1 = A1_trial.copy()
            accumulated_relevance_error += rel_coeff

            removed_terms.append(((i_sym, j_sym), term, rel_coeff_sym)) # record keeping

            #-------------------------------------------------------------------------------
            rel_diff = np.abs(true_error - accumulated_relevance_error) # difference check
            print("True error: ",true_error, " Accumulated error: ",accumulated_relevance_error, " Difference: ", rel_diff)
            print("-----------------\n")

            #-------------------------------------------------------------------------------
            # calculate new relevance coefficients if necessary

            if rel_diff > rel_error_threshold:
                print("Updating relevance coefficients...")
                t3_extra = time.perf_counter_ns()

                term_list_sym = self.update_remaining_terms(
                    removed_terms,
                    term_list_sym,
                    input_potential,
                    output_potential,
                    approx_points,
                    sorting_method,
                    column
                )
                _, _, term_list = self.split_linear_s_dependence(
                    self.get_reduced_matrix(removed_terms),
                    term_list_sym,
                    s
                )

                term_list_sym.sort(key=lambda x: x[2].any())
                term_list.sort(key=lambda x: x[2].real)
                accumulated_relevance_error = 0.0

                t4_extra = time.perf_counter_ns()
                print(f"Update took {(t4_extra - t3_extra) / 1e6} ms")

            
        
        
        return self.calc_End_Result(removed_terms, input_potential, output_potential)

        
    def calc_End_Result(self, rem_terms, input_potential, output_potential):

        A_sym = self.get_reduced_matrix(rem_terms)


        x = self.analysis.get_unknowns()

        solutions = sp.solve(A_sym * x - self.analysis.z, x, dict=True)

        

        result_approx = solutions[0]

        result = result_approx[output_potential] / result_approx[input_potential]

        return result
    
    def get_reduced_matrix(self, rem_terms):

        A_sym = self.analysis.A.copy()

        for (i, j), term_sym, _ in rem_terms:
            A_sym[i, j] -= term_sym

        return A_sym

    def compute_transfer_function_numeric(self, A0, A1, z_func ,approx_points, input_potential, output_potential):

        
        #s = sp.symbols("s")
        approx_points = np.atleast_1d(approx_points)
        jw = 1j * approx_points

 

        H = np.empty(len(jw))
        n = A0.shape[0]

        

        for k, w in enumerate(jw):
            #A_num = np.array(A_func(w), dtype=complex)
            z_num = np.array(z_func(w), dtype=complex).reshape(n)

            A = A0 + w * A1

            lu, piv = scipy.lu_factor(A)

            x = scipy.lu_solve((lu, piv), z_num)
            

            

            

            H[k] = x[output_potential] / x[input_potential]

        return H

    def has_phase_sign_jump(self, H_ref, H_trial, threshold=np.pi):
        phi_ref   = np.unwrap(np.angle(H_ref))
        phi_trial = np.unwrap(np.angle(H_trial))

        dphi = phi_trial - phi_ref

        return np.any(np.abs(np.diff(dphi)) > threshold)

    def update_remaining_terms(
        self,
        rem_terms,
        remaining_terms,
        input_potential,
        output_potential,
        approx_points,
        sorting_method,
        column
    ):
        """
        Recompute relevance coefficients for remaining terms
        based on the current reduced matrix A_current.
        """
        A_current = self.get_reduced_matrix(rem_terms)
       

        updated = self.generate_relevance_coefficients(
            input_potential,
            output_potential,
            approx_points,
            A_current
        )


    
        # updated = new_list
        updated = self.sort_term_list(updated, sorting_method, column)

        updated.sort(key=lambda x: x[2])

        # nur verbleibende Terme übernehmen
        updated_dict = {
            (i, j): coeff
            for ((i, j), _,coeff) in updated
        }

       

        new_term_list = []
        for (i, j), term, _ in remaining_terms:
            new_term_list.append(
                ((i, j), term, updated_dict[(i, j)])
            )


        new_term_list = [entry for entry in new_term_list if not np.isnan(entry[2]).any()]
        

        return new_term_list

    def split_linear_s_dependence(self, A_sym, term_list, s_sym):
        """
        Zerlegt A(s) = A0 + s*A1 und ebenso alle Terme in term_list.

        Parameters
        ----------
        A_sym : sympy.Matrix
            Symbolische Matrix mit linearer s-Abhängigkeit
        term_list : list
            [((i, j), term_sym, rel_coeff), ...]
        s_sym : sympy.Symbol
            Das Symbol für s (z.B. sp.symbols('s'))

        Returns
        -------
        A0 : np.ndarray (complex)
        A1 : np.ndarray (complex)
        term_list_split : list
            [((i, j), term0, term1, rel_coeff), ...]
        """

        # --- Matrix zerlegen ---
        A_sym = A_sym.subs(self.analysis.value_dict)
        A0_sym = A_sym.subs(s_sym, 0)
        A1_sym = sp.diff(A_sym, s_sym)

        A0 = np.array(A0_sym, dtype=complex)
        A1 = np.array(A1_sym, dtype=complex)

        # --- Terme zerlegen ---
        term_list_split = []

        for (i, j), term_sym, rel_coeff in term_list:
            # Sicherheit: Linearität prüfen
            if sp.degree(term_sym, s_sym) > 1:
                raise ValueError(
                    f"Term ({i},{j}) ist nicht linear in s: {term_sym}"
                )

            term_sym = term_sym.subs(self.analysis.value_dict)
            term0 = complex(term_sym.subs(s_sym, 0))
            term1 = complex(sp.diff(term_sym, s_sym))

            term_list_split.append(((i, j), term0, term1, rel_coeff))

        return A0, A1, term_list_split
    

    def sort_term_list(self, term_list, method, column):
        """Sort term list by relevance coefficient.

        Args:
            term_list (list): list of terms in the form ((i, j), term, relevance coefficient)
            method (str): sorting method ("max", "avg", etc.)

        Returns:
            list: sorted term list
        """
        new_list = []
        match method:
            case "max":
                for (i, j), term, relative_error in term_list:
                    max_error = max(relative_error)
                    new_list.append(((i, j), term, max_error))
            case "avg":
                for (i, j), term, relative_error in term_list:
                    max_error = np.average(relative_error)
                    new_list.append(((i, j), term, max_error))
            case "column":
                for (i, j), term, relative_error in term_list:
                    col_error = relative_error[column]
                    new_list.append(((i, j), term, col_error))
            case _:
                raise ValueError(f"Unknown sorting method: {method}")
            
        term_list = new_list

        return term_list