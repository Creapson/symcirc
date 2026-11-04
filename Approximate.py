import sympy as sp
import math
from sympy.matrices.exceptions import NonInvertibleMatrixError
import numpy as np
import time
import scipy.linalg as scipy
import warnings
import copy

from Modified_Node_Analysis import ModifiedNodalAnalysis
import compress_matrix as cm




class Approximation:

    def __init__(self, equation_formulator):
        self.analysis = copy.deepcopy(equation_formulator)
        warnings.filterwarnings("error", category=scipy.LinAlgWarning)
        
    @staticmethod
    def get_Elimination_Methods():
        return list(("term-by-term",))
    
    @staticmethod
    def get_Sorting_Methods():
        return list(("max", "avg", "column"))


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
                    term_list.append(((i, j), t, []))  # Placeholder for numerical value
        return term_list

    def generate_relevance_coefficients(
        self,
        output_potential,
        approx_points,
        sysMatrix
    ):
        t0 = time.perf_counter_ns()
        term_list = self.generate_term_list(sysMatrix)
       

        x_syms = list(self.analysis.get_unknowns())
        
        idx_out = x_syms.index(output_potential)


        s = sp.symbols('s')

        
        
        sysMatrix = sysMatrix.subs(self.analysis.value_dict)
        z_num = self.analysis.z.subs(self.analysis.value_dict)

          
        print("Computing reference solution for sensitivity calculation...") 

        f_terms = []

        t_all = [t.subs(self.analysis.value_dict) for (_, t, _) in term_list]
        f_all = sp.lambdify(s, t_all, 'numpy')

        i_idx = np.array([i for ((i, j), _, _) in term_list])
        j_idx = np.array([j for ((i, j), _, _) in term_list])
        

        
        
        

        for ap in approx_points:
            sysMatrix_num = sysMatrix.subs(s, 1j*2*np.pi*ap)
            
            t1 = time.perf_counter_ns()
            A_inv = sysMatrix_num.inv()
            t2 = time.perf_counter_ns()
            print(f"Matrix inversion took {(t2 - t1) / 1e6} ms")

            A_inv_np = np.array(A_inv, dtype=complex)


            x = A_inv_np * z_num
            x_np = np.array(x, dtype=complex).flatten()
            ref_result_k = x_np[idx_out]

            print("Term list length: ", len(term_list))

            t4 = time.perf_counter_ns()

            t_vals = f_all(1j*2*np.pi*ap)
            t_vals = np.array(t_vals, dtype=np.complex128)

            A_out_i = A_inv_np[idx_out, i_idx]
            A_j_i = A_inv_np[j_idx, i_idx]
            x_j = x_np[j_idx]

            dx_k_all = (t_vals * A_out_i) / (1 - t_vals * A_j_i) * x_j

            se_all = np.abs(dx_k_all) / abs(ref_result_k)

            for idx, se in enumerate(se_all):
             
                term_list[idx][2].append(float(se))

            

            
            t5 = time.perf_counter_ns()
            print(f"Sensitivity evaluation for one frequency point took {(t5 - t4) / 1e6} ms")
                

        
        t3 = time.perf_counter_ns()
        print(f"Sensitivity calculation took {(t3 - t0) / 1e6} ms")
       
        
        

        return term_list




    
    def generate_relevance_coefficients_LU(self, output_potential, approx_points, sysMatrix):
        """Generate relevance coefficients for each term in the term list.

        Args:
            term_list (list): list of terms in the form ((i, j), term, relevance coefficient)
            mna (ModifiedNodalAnalysis): MNA instance with numerical solution
            input_potential (sp.Expr): dictionary key for input potential
            output_potential (sp.Expr): dictionary key for output potential

        Returns:
            list: updated term list with relevance coefficients
        """
        t0 = time.perf_counter_ns()
        

        term_list = self.generate_term_list(sysMatrix)

       

    
        s = sp.symbols('s')
        approx_points = np.atleast_1d(approx_points)
        jw = 1j * 2* np.pi* approx_points

    
        x_syms = list(self.analysis.get_unknowns())
        
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

            H = x[idx_out] 
            abs_H_ref[k] = np.abs(H)

            A_base.append(A_num)
            lu_cache.append((lu, piv))
            z_num_cache.append(z_num)
            x_ref_cache.append(x)

        for idx, ((i, j), term, _) in enumerate(term_list):

            
            

            term_num = sp.lambdify(s, term.subs(self.analysis.value_dict), "numpy")

           

            abs_H_mod = np.empty(n_freq)

            failed = False

            for k, w in enumerate(jw):
            
                A_mod = A_base[k].copy()
                A_mod[i, j] -= complex(term_num(w))


                try:
                    lu, piv = scipy.lu_factor(A_mod)
                    x_mod = scipy.lu_solve((lu, piv), z_num_cache[k])

                    H_mod = x_mod[idx_out] 
                    abs_H_mod[k] = np.abs(H_mod)
                    

                except Exception:
                    term_list[idx] = ((i, j), term, float("inf"))
                    failed = True
                    break

            if failed:
                continue

            relative_error = np.abs((abs_H_ref - abs_H_mod) / abs_H_ref)
            term_list[idx] = ((i, j), term, relative_error) 

        t1 = time.perf_counter_ns()
        print(f"Relevance coefficient generation took {(t1 - t0) / 1e6} ms")

        
        return term_list

    
    def approximate(
        self,
        output_potential_str,
        reference_points,
        elimination_method,
        rel_error_threshold,
        sorting_method,
        influenceJumpPosition = None,
        column=0,
        
        
    ):
        #Initialize
        approx_points = [a for a, _ in reference_points]
        approx_points_errors = [b for _, b in reference_points]

        print("Approximation points:", approx_points)

        #----------------------------------------------------------
        # Determine maximum allowed error

        max_error = max(approx_points_errors)

        
        #----------------------------------------------------------
        #get potential indices
        x_syms = list(self.analysis.get_unknowns())


        output_potential = sp.symbols(output_potential_str)

        
        if output_potential not in self.analysis.unknowns:
            raise ValueError("Unknown variable "" + output_potential_str + "" not in the system")
        



        idx_out = x_syms.index(output_potential)

        

        #z numeric function
        z_num = self.analysis.z.subs(self.analysis.value_dict)
        z_num_func = sp.lambdify(sp.symbols('s'), z_num, "numpy")
        
        #Compute sensitivities
        term_list_sym = self.generate_relevance_coefficients( 
                                                         
                                                         output_potential, 
                                                         approx_points, 
                                                         self.analysis.A)

        print("Unsorted term list:")
        for ((i, j), t, rel) in term_list_sym:
            print(f"Term at position ({i}, {j}): {t}, Relevance Coefficient: {rel}")
      

        
        
        term_list_sym = [entry for entry in term_list_sym if not np.isnan(entry[2]).any()]
        

        
        # Sort term list by relevance coefficient --------------------------------------------------

        
        

        term_list_sym = self.sort_term_list(term_list_sym, sorting_method, column)
        
        
        term_list_sym.sort(key=lambda x: x[2].real)

        print("Sorted term list:")
        for ((i, j), t, rel) in term_list_sym:
            print(f"Term at position ({i}, {j}): {t}, Relevance Coefficient: {rel}")
        

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
        H_ref, _ = self.compute_transfer_function_numeric(
            A0,
            A1,
            z_num_func,
            approx_points,
            idx_out
        )
        abs_H_ref = np.abs(H_ref)

        
        print("Reference transfer function magnitude:")
        print(abs_H_ref)
        
        

        #Initialize error trackers and removed terms list
        accumulated_relevance_error = 0.0
        true_error = 0.0
        removed_terms = []   


        match elimination_method:
            case "block":

                if influenceJumpPosition is not None:
                    for n in range(influenceJumpPosition + 1):
                        (i, j), term, influence = term_list_sym.pop(0)
                        A_reduced[i, j] -= term   


                A_reduced_comp_num, z_comp_num, new_indice, A_reduced_comp, z_comp, unknowns_comp = cm.CompressMatrix(A_reduced, self.analysis.get_unknowns(), self.analysis.z, idx_out, self.analysis.value_dict, True)

                z_num_func_comp = sp.lambdify(sp.symbols('s'), z_comp_num, "numpy")


                term_list_sym = [((i, j), term, infl) for (i, j), term, infl in term_list_sym
                if i < A_reduced_comp.rows and j < A_reduced_comp.cols]

                A0_comp, A1_comp, term_list = self.split_linear_s_dependence(
                            A_reduced_comp,
                            term_list_sym,
                            s
                        )

                count = 0
                no_terms = True

                for safty_counter in range(3):
               
                    removable_terms = self.find_removable_block_terms(
                    A_matrix=A_reduced_comp,
                    term_list_sym=term_list_sym,
                    term_list_split=term_list,
                    A0=A0_comp,
                    A1=A1_comp,
                    z_num_func=z_num_func_comp,
                    approx_points=approx_points,
                    idx_out=new_indice,
                    max_error=max_error,
                    has_phase_sign_jump=self.has_phase_sign_jump,
                    )

                    count += 1

                    if removable_terms:
                        for (i,j), term, _ in removable_terms:
                            A_reduced_comp[i, j] -= term

                        A_reduced_comp_num, z_comp_num, new_indice, A_reduced_comp, z_comp, unknowns_comp = cm.CompressMatrix(A_reduced, self.analysis.get_unknowns(), self.analysis.z, idx_out, self.analysis.value_dict, True)
                        
                        z_num_func_comp = sp.lambdify(sp.symbols('s'), z_comp_num, "numpy")
                        
                        
                        term_list_sym = [((i, j), term, infl) for (i, j), term, infl in term_list_sym
                        if i < A_reduced_comp.rows and j < A_reduced_comp.cols]
                        
                        A0_comp, A1_comp, term_list = self.split_linear_s_dependence(
                            A_reduced_comp,
                            term_list_sym,
                            s
                        )

                        no_terms = False

                    if no_terms or count != 1:
                        analysis_comp = ModifiedNodalAnalysis(self.analysis.ct)

                        analysis_comp.A = A_reduced_comp
                        analysis_comp.z = z_comp
                        analysis_comp.unknowns = unknowns_comp
                        analysis_comp.value_dict = self.analysis.value_dict

                        approx_compressed = Approximation(analysis_comp)

                        return approx_compressed.approximate(
                                output_potential_str,
                                reference_points,
                                "term-by-term",
                                rel_error_threshold,
                                sorting_method,
                                influenceJumpPosition,
                                column)    

                
                    
                    

                    
                       
            
            case "term-by-term":
               
                while term_list:

                  
                    
                    #get next, least relevant, term
            
                    
                    (i, j), t0, t1, rel_coeff = term_list.pop(0) #get least relevant numeric term
                    
                    (i_sym, j_sym), term, rel_coeff_sym = term_list_sym.pop(0) # get least relevant symbolic term for record keeping
                   

                    #print(f"Trying to remove term {term} at position ({i}, {j}) with relevance coefficient {rel_coeff}")

                    #-------------------------------------------------------------------------------
                    # create trial matrices


                    A0_trial = A0.copy()
                    A1_trial = A1.copy()

                    A0_trial[i, j] -= t0
                    A1_trial[i, j] -= t1

                    #-------------------------------------------------------------------------------
                    # compute trial transfer function

                    
                        
                    H_trial, is_singular = self.compute_transfer_function_numeric(
                                A0_trial,
                                A1_trial,
                                z_num_func,
                                approx_points,
                                idx_out
                            )
                        
                        

                    if is_singular:
                        continue
                    

                    if self.has_phase_sign_jump(H_ref, H_trial):# check for phase jumps 
                        continue

                
                    abs_H_trial= np.abs(H_trial)


                    #-------------------------------------------------------------------------------
                    # calculate true error
                    
                    
                    true_error = np.max(
                        np.abs(abs_H_ref - abs_H_trial) / abs_H_ref
                    )
                    accumulated_relevance_error += rel_coeff

                    print("True error: ",true_error, " Accumulated error: ",accumulated_relevance_error)
                    
                    
                    #check if true error is acceptable
                    if (true_error > max_error) or (np.isnan(true_error) and (accumulated_relevance_error > max_error)): 
                        print("Error too high, ending approximation...\n number of remaining terms: ", len(term_list))
                        return self.calc_End_Result(removed_terms)


                    #-------------------------------------------------------------------------------
                
                    #accept removal
                    A0 = A0_trial.copy()
                    A1 = A1_trial.copy()
                    

                    removed_terms.append(((i_sym, j_sym), term, rel_coeff_sym)) # record keeping

                    #-------------------------------------------------------------------------------
                    rel_diff = np.abs(true_error - accumulated_relevance_error) # difference check
                    print("Difference Error: ", rel_diff)
                    print("-----------------\n")

                    #-------------------------------------------------------------------------------
                    # calculate new relevance coefficients if necessary

                    if rel_diff > rel_error_threshold:
                        print("Updating relevance coefficients...")
                        t3_extra = time.perf_counter_ns()

                        term_list_sym = self.update_remaining_terms(
                            removed_terms,
                            term_list_sym,
                            output_potential,
                            approx_points,
                            sorting_method,
                            column
                        )
                        t4_extra = time.perf_counter_ns()
                        print(f"Update took {(t4_extra - t3_extra) / 1e6} ms")
                        _, _, term_list = self.split_linear_s_dependence(
                            self.get_reduced_matrix(removed_terms),
                            term_list_sym,
                            s
                        )
                        t5_extra = time.perf_counter_ns()
                        print(f"Splitting took {(t5_extra - t4_extra) / 1e6} ms")

                        #term_list_sym.sort(key=lambda x: x[2].any())
                        term_list.sort(key=lambda x: x[2].real)
                        accumulated_relevance_error = 0.0

                

         
        
        
        return self.calc_End_Result(removed_terms)

        
    def calc_End_Result(self, rem_terms): 

        """Generate new MNA object with reduced system matrix

        Returns:
            ModifiedNodalAnalysis: new MNA object with reduced system matrix
        """
        analysis_reduced = copy.deepcopy(self.analysis)

        analysis_reduced.A = self.get_reduced_matrix(rem_terms)

        
        return analysis_reduced
    
    def get_reduced_matrix(self, rem_terms):
       

        
        A_sym = self.analysis.A.copy()

        for (i, j), term_sym, _ in rem_terms:
            A_sym[i, j] -= term_sym

        
        return A_sym

    def compute_transfer_function_numeric(self, A0, A1, z_func ,approx_points, output_potential):

        
        #s = sp.symbols("s")
        approx_points = np.atleast_1d(approx_points)
        jw = 1j * 2*np.pi* approx_points

 

        H = np.empty(len(jw))
        n = A0.shape[0]

        is_singular = False

        for k, w in enumerate(jw):
            #A_num = np.array(A_func(w), dtype=complex)
            z_num = np.array(z_func(w), dtype=complex).reshape(n)

            A = A0 + w * A1

            # try:

            #     lu, piv = scipy.lu_factor(A)

            # except RuntimeWarning:
            #     is_singular = True
            #     return None, is_singular

            try:
            
                lu, piv = scipy.lu_factor(A)

                x = scipy.lu_solve((lu, piv), z_num)
            
            except scipy.LinAlgWarning:
                is_singular = True
                H[k] = np.nan
                continue
                
            
            #print(x[output_potential])
            

            

            

            H[k] = x[output_potential] #/ x[input_potential]

        return H, is_singular

    def has_phase_sign_jump(self, H_ref, H_trial, threshold=np.pi):
        phi_ref   = np.unwrap(np.angle(H_ref))
        phi_trial = np.unwrap(np.angle(H_trial))

        dphi = phi_trial - phi_ref

        return np.any(np.abs(dphi) > threshold)

    def update_remaining_terms(
        self,
        rem_terms,
        remaining_terms,
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
       
        t0 = time.perf_counter_ns()

        updated = self.generate_relevance_coefficients(
            output_potential,
            approx_points,
            A_current
        )

        t1 = time.perf_counter_ns()
        print(f"Relevance coefficient generation took {(t1 - t0) / 1e6} ms")

        
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
                    relative_error = np.atleast_1d(relative_error)

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
    


    def _block_influence_exceeds(self, influence, max_error):
        """
        Prüft, ob mindestens ein Einflusswert max_error überschreitet.
        Nicht-endliche Einflusswerte führen ebenfalls zum Abbruch.
        """
        values = np.asarray(influence).reshape(-1)

        if values.size == 0:
            return False

        try:
            values = values.astype(float)
        except (TypeError, ValueError):
            values = np.array(
                [float(sp.N(value)) for value in values],
                dtype=float,
            )

        return bool(
            np.any(~np.isfinite(values))
            or np.any(values > max_error)
        )


    def _is_symbolically_nonzero(self, value):
        """
        Zählt symbolisch und numerisch von null verschiedene Einträge.
        """
        value = sp.simplify(value)

        if value.is_zero is True:
            return False

        if value.is_zero is False:
            return True

        # Bei einem vollständig numerischen Ausdruck nachprüfen.
        if not value.free_symbols:
            try:
                return complex(sp.N(value)) != 0
            except (TypeError, ValueError):
                return True

        # Ein nicht entscheidbarer symbolischer Ausdruck wird
        # konservativ als potenziell ungleich null behandelt.
        return True


    def find_block_candidate_indices(
            self,
        A_matrix,
        term_list_sym,
        max_error,
        include_last_candidate=False,
    ):
        """
        Identifiziert Blockkandidaten gemäß dem ersten Algorithmus.

        Parameters
        ----------
        A_matrix : sympy.Matrix
            Symbolische Ausgangsmatrix.
        term_list_sym : list
            Liste der Form ((i, j), term, rel_coeff).
        max_error : float
            Maximal zulässiger Einfluss.
        include_last_candidate : bool
            False bildet die ursprüngliche Mathematica-Schleife
            r < Length[Einflußliste] nach. Dabei wird der letzte
            Eintrag ausgelassen.

        Returns
        -------
        list[int]
            Indizes der erkannten Blockkandidaten in term_list_sym.
        """
        AL = sp.Matrix(A_matrix)
        block_indices = []

        if include_last_candidate:
            entries = term_list_sym
        else:
            entries = term_list_sym[:-1]

        for index, ((i, j), term, influence) in enumerate(entries):

            # Die Einträge sind nach Relevanz sortiert.
            # Beim ersten überschrittenen Grenzwert wird abgebrochen.
            if self._block_influence_exceeds(influence, max_error):
                break

            # Kandidat aus der Arbeitsmatrix entfernen.
            AL[i, j] = sp.simplify(AL[i, j] - term)

            # Anzahl von Nichtnull-Einträgen in Zeile i.
            row_count = sum(
                self._is_symbolically_nonzero(AL[i, k])
                for k in range(AL.cols)
            )

            # Anzahl von Nichtnull-Einträgen in Spalte j.
            col_count = sum(
                self._is_symbolically_nonzero(AL[k, j])
                for k in range(AL.rows)
            )

            # Blockelement identifizieren.
            if row_count == 1 or col_count == 1:
                block_indices.append(index)

        return block_indices


    def _compute_complex_transfer_function(
      self,
        A0,
        A1,
        z_num_func,
        approx_points,
        idx_out,
    ):
        """
        Berechnet H(s) für alle Approximationspunkte.

        Die Funktion verwendet komplexe Arrays und np.linalg.solve,
        ohne die bestehenden Klassenmethoden zu verändern.

        Returns
        -------
        H : np.ndarray oder None
            Komplexe Transferfunktionswerte.
        is_singular : bool
            True, falls mindestens ein System nicht gelöst werden kann.
        """
        A0 = np.asarray(A0, dtype=complex)
        A1 = np.asarray(A1, dtype=complex)

        if (
            A0.ndim != 2
            or A1.ndim != 2
            or A0.shape != A1.shape
            or A0.shape[0] != A0.shape[1]
        ):
            return None, True

        points = np.atleast_1d(
            np.asarray(approx_points, dtype=float)
        )

        H = np.empty(len(points), dtype=complex)
        n = A0.shape[0]

        for k, frequency in enumerate(points):
            s_value = 1j * 2 * np.pi * frequency

            A_num = A0 + s_value * A1

            try:
                z_num = np.asarray(
                    z_num_func(s_value),
                    dtype=complex,
                ).reshape(n)

                if (
                    not np.all(np.isfinite(A_num))
                    or not np.all(np.isfinite(z_num))
                ):
                    return None, True

                # Direkte Lösung statt expliziter Matrixinversion.
                x = np.linalg.solve(A_num, z_num)

                if not np.all(np.isfinite(x)):
                    return None, True

                H[k] = x[idx_out]

            except (
                np.linalg.LinAlgError,
                ValueError,
                TypeError,
                OverflowError,
            ):
                return None, True

        return H, False


    def _calculate_relative_magnitude_error(self, H_ref, H_trial):
        """
        Berechnet den maximalen relativen Fehler der Beträge
        über alle Approximationspunkte.

        e = max(| |H_ref| - |H_trial| | / |H_ref|)

        Ist ein Referenzbetrag null, wird der Fehler für diesen
        Punkt als 0 oder unendlich behandelt.
        """
        H_ref = np.asarray(H_ref, dtype=complex)
        H_trial = np.asarray(H_trial, dtype=complex)

        if (
            H_ref.shape != H_trial.shape
            or H_ref.size == 0
            or not np.all(np.isfinite(H_ref))
            or not np.all(np.isfinite(H_trial))
        ):
            return np.inf

        abs_ref = np.abs(H_ref)
        abs_trial = np.abs(H_trial)
        difference = np.abs(abs_ref - abs_trial)

        errors = np.empty_like(abs_ref, dtype=float)
        nonzero = abs_ref > 0

        errors[nonzero] = (
            difference[nonzero] / abs_ref[nonzero]
        )

        zero = ~nonzero
        errors[zero] = np.where(
            difference[zero] == 0,
            0.0,
            np.inf,
        )

        if not np.all(np.isfinite(errors)):
            return np.inf

        return float(np.max(errors))


    def find_removable_block_terms(
        self,
        A_matrix,
        term_list_sym,
        term_list_split,
        A0,
        A1,
        z_num_func,
        approx_points,
        idx_out,
        max_error,
        has_phase_sign_jump,
        include_last_candidate=True,
    ):
        """
        Bestimmt die maximal entfernbaren Blockkandidaten.

        Die Funktion ist auf die Datenstrukturen der vorhandenen
        Approximation-Klasse abgestimmt.

        Parameters
        ----------
        A_matrix : sympy.Matrix
            Symbolische Ausgangsmatrix, z. B. A_reduced.
        term_list_sym : list
            Symbolische Terme: ((i, j), term, rel_coeff).
        term_list_split : list
            Zerlegte Terme: ((i, j), term0, term1, rel_coeff).
        A0, A1 : np.ndarray
            Numerische Matrizen mit A(s) = A0 + s*A1.
        z_num_func : callable
            Numerische rechte Seite als Funktion von s.
        approx_points : array-like
            Frequenzen, an denen die Approximation geprüft wird.
        idx_out : int
            Index der Ausgangsvariablen.
        max_error : float
            Maximal zulässiger relativer Fehler.
        has_phase_sign_jump : callable
            Bestehende Klassenmethode zur Phasensprungprüfung.
        include_last_candidate : bool
            Ob der letzte Eintrag bei der Blockidentifikation
            berücksichtigt werden soll.

        Returns
        -------
        list
            Entfernte Terme in der Form
            ((i, j), term, rel_coeff), kompatibel mit
            get_reduced_matrix() und calc_End_Result().
        """

        # ---------------------------------------------------------
        # 1. Eingaben überprüfen
        # ---------------------------------------------------------

        if len(term_list_sym) != len(term_list_split):
            raise ValueError(
                "term_list_sym und term_list_split müssen "
                "gleich lang sein."
            )

        for index, (symbolic, numeric) in enumerate(
            zip(term_list_sym, term_list_split)
        ):
            if symbolic[0] != numeric[0]:
                raise ValueError(
                    f"Die Termlisten sind bei Index {index} "
                    "nicht synchronisiert."
                )

        # ---------------------------------------------------------
        # 2. Blockkandidaten erkennen
        # ---------------------------------------------------------

        block_indices = self.find_block_candidate_indices(
            A_matrix=A_matrix,
            term_list_sym=term_list_sym,
            max_error=max_error,
            include_last_candidate=include_last_candidate,
        )

        number_of_blocks = len(block_indices)

        print(f"Gefundene Blockkandidaten: {number_of_blocks}")

        if number_of_blocks == 0:
            return []

        # ---------------------------------------------------------
        # 3. Referenztransferfunktion komplex berechnen
        # ---------------------------------------------------------

        H_ref, is_singular = self._compute_complex_transfer_function(
            A0=A0,
            A1=A1,
            z_num_func=z_num_func,
            approx_points=approx_points,
            idx_out=idx_out,
        )

        if is_singular:
            raise ValueError(
                "Das Referenzsystem ist an mindestens einem "
                "Approximationspunkt singulär oder ungültig."
            )

        # ---------------------------------------------------------
        # 4. Binäre Suche initialisieren
        # ---------------------------------------------------------

        # Anzahl akzeptierter Blockkandidaten.
        yO = 0

        # Obere exklusive Grenze. Damit wird auch die Entfernung
        # sämtlicher Blockkandidaten überprüft.
        y = number_of_blocks + 1

        # ---------------------------------------------------------
        # 5. Maximale Anzahl entfernbarer Kandidaten suchen
        # ---------------------------------------------------------

        while y - yO > 1:

            yk = (yO + y) // 2

            print(
                f"\nPrüfe Entfernung der ersten {yk} "
                f"von {number_of_blocks} Blockkandidaten."
            )

            # Ausgangssystem für diesen Versuch kopieren.
            A0_trial = np.array(A0, dtype=complex, copy=True)
            A1_trial = np.array(A1, dtype=complex, copy=True)

            # Die ersten yk Blockkandidaten entfernen.
            for index in block_indices[:yk]:

                ((i, j), term0, term1, rel_coeff) = (
                    term_list_split[index]
                )

                A0_trial[i, j] -= term0
                A1_trial[i, j] -= term1

            # -----------------------------------------------------
            # 6. Invertierbarkeit überprüfen und Lösung bestimmen
            # -----------------------------------------------------

            H_trial, is_singular = (
                self._compute_complex_transfer_function(
                    A0=A0_trial,
                    A1=A1_trial,
                    z_num_func=z_num_func,
                    approx_points=approx_points,
                    idx_out=idx_out,
                )
            )

            if is_singular:
                y = yk

                print(
                    "Nicht akzeptiert: Mindestens ein reduziertes "
                    "System ist singulär oder ungültig."
                )
                continue

            # -----------------------------------------------------
            # 7. Phasensprung überprüfen
            # -----------------------------------------------------

            if has_phase_sign_jump(H_ref, H_trial):
                y = yk

                print(
                    "Nicht akzeptiert: Phasensprung erkannt."
                )
                continue

            # -----------------------------------------------------
            # 8. Relativen Fehler überprüfen
            # -----------------------------------------------------

            rel_error = self._calculate_relative_magnitude_error(
                H_ref,
                H_trial,
            )

            if rel_error > max_error:
                # Zu viele entfernte Kandidaten: Intervall verkleinern.
                y = yk

                print(
                    f"Nicht akzeptiert: Relativer Fehler "
                    f"{rel_error:.6g} > {max_error:.6g}."
                )

            else:
                # Versuch akzeptieren und mehr Kandidaten testen.
                yO = yk

                print(
                    f"Akzeptiert: Relativer Fehler "
                    f"{rel_error:.6g} <= {max_error:.6g}."
                )

            print(f"Aktuelles Suchintervall: [{yO}, {y}]")

        # ---------------------------------------------------------
        # 9. Akzeptierte Blockkandidaten zurückgeben
        # ---------------------------------------------------------

        removable_indices = block_indices[:yO]

        removed_terms = [
            term_list_sym[index]
            for index in removable_indices
        ]

        print(
            f"\nBlocksuche abgeschlossen: "
            f"{len(removed_terms)} von {number_of_blocks} "
            "Blockkandidaten können entfernt werden."
        )

        return removed_terms