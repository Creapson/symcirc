"""
[TR] Pol-Nullstellen (kutup/sifir) dugumu.

Bir TransferFunction dugumune baglanir, ondan gelen MNA sistemini (A, z)
ve secilen cikis dugumunu alir ve transfer fonksiyonu H(s)'in kutup ve
sifirlarini hesaplar; sonuclari s-duzleminde cizer.

Iki hesap yolu:
  * Sayisal: descriptor (DAE) formulasyonu, A(s) = G + s*C_dyn. Kutuplar
    eig(G, -C_dyn); sifirlar Analog Insydes'in ZerosByQZ yontemiyle
    (cikis sutununu z ile degistirip sonlu ozdegerler). Buyuk/pF-uF
    olcek farki icin gamma-olcekleme + satir/sutun dengeleme.
  * Sembolik: H(s) = det(A_out) / det(A) tam rasyonel olarak (Berkowitz,
    bolmesiz determinant). s=0 kutuplari/sifirlari TAM cikar; sonuc
    carpanlarina ayrilmis H(s) metni olarak da gosterilir.

Mod (sayisal/sembolik) ve cikis dugumu bagli TransferFunction dugumunden
gelir - bu dugumde secilmez (arayuz akisi: MNA -> TF -> PoleZero).

[EN] Pole-Zero node.

Connects to a TransferFunction node, takes its MNA system (A, z) and the
selected output node, and computes the poles and zeros of the transfer
function H(s); plots them on the s-plane.

Two calculation paths:
  * Numeric: descriptor (DAE) form, A(s) = G + s*C_dyn. Poles from
    eig(G, -C_dyn); zeros via Analog Insydes' ZerosByQZ method (replace
    the output column with z, keep the finite eigenvalues). gamma scaling
    + row/column equilibration to cope with the pF-vs-uF spread.
  * Symbolic: H(s) = det(A_out) / det(A) as an exact rational (Berkowitz,
    division-free determinant). Poles/zeros at s=0 come out EXACT; the
    result is also shown as a factored H(s) string.

The mode (numeric/symbolic) and the output node come from the connected
TransferFunction node - they are not chosen here (UI flow: MNA -> TF ->
PoleZero).
"""

import dearpygui.dearpygui as dpg
import numpy as np
import sympy as sp
from pydantic import Field
from typing import Literal, List
import scipy.linalg as scipy
from gui.components.node_editor.nodes.Node import Node, NodeType

class PoleZeroNode(Node):
    node_type: Literal[NodeType.POLE_ZERO_PLOT] = NodeType.POLE_ZERO_PLOT

    zeros: List[complex] = Field(default_factory=list, exclude=True)
    poles: List[complex] = Field(default_factory=list, exclude=True)

    text_zeros_tag: str = Field(default="", exclude=True)
    text_poles_tag: str = Field(default="", exclude=True)
    scatter_zeros_tag: str = Field(default="", exclude=True)
    scatter_poles_tag: str = Field(default="", exclude=True)
    symbolic_tf_tag: str = Field(default="", exclude=True)
    source_info_tag: str = Field(default="", exclude=True)

    # [TR] Bagli TransferFunction dugumunden gelen baglam (link aninda doldurulur).
    # [EN] Context from the connected TransferFunction node (filled on link).
    src_mode: str = Field(default="", exclude=True)          # "numeric" | "symbolic"
    src_output_node: str = Field(default="", exclude=True)

    def build(self):
        # [TR] Tek giris pini; bir TransferFunction dugumunun cikisina baglanir.
        # [EN] Single input pin; wired to a TransferFunction node's output.
        self.add_input_pin("mna_pin", "Connect a TransferFunction node here!")

        with self.add_static_attr():
            dpg.add_button(label="Calculate & Plot", callback=self.calculate_callback)

            self.source_info_tag = self.uuid("source_info")
            dpg.add_text("Kaynak: bir TransferFunction dugumu baglayin.",
                         tag=self.source_info_tag, color=[150, 150, 150], wrap=340)
            dpg.add_text("Cikis dugumu ve sembolik/sayisal secimi bagli olan "
                         "TransferFunction dugumunden alinir.", color=[150, 150, 150],
                         wrap=340)
            dpg.add_separator()

            self.text_zeros_tag = self.uuid("zeros_text")
            self.text_poles_tag = self.uuid("poles_text")

            dpg.add_text("Zeros:", color=[100, 100, 255])
            dpg.add_text("N/A", tag=self.text_zeros_tag)

            dpg.add_text("Poles:", color=[255, 100, 100])
            dpg.add_text("N/A", tag=self.text_poles_tag)

            self.symbolic_tf_tag = self.uuid("symbolic_tf")
            dpg.add_text("", tag=self.symbolic_tf_tag, color=[160, 200, 160], wrap=340)
            dpg.add_separator()

            with dpg.plot(label="S-Plane Map", width=350, height=350):
                dpg.add_plot_legend()
                x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Real Part, Sigma")
                y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Imaginary Part, jw")

                self.scatter_zeros_tag = self.uuid("scatter_zeros")
                self.scatter_poles_tag = self.uuid("scatter_poles")

                dpg.add_scatter_series([], [], label="Zeros", parent=y_axis, tag=self.scatter_zeros_tag)
                dpg.add_scatter_series([], [], label="Poles", parent=y_axis, tag=self.scatter_poles_tag)

                dpg.bind_item_theme(self.scatter_zeros_tag, self.create_scatter_theme(dpg.mvPlotMarker_Circle, [100, 100, 255, 255]))
                dpg.bind_item_theme(self.scatter_poles_tag, self.create_scatter_theme(dpg.mvPlotMarker_Cross, [255, 100, 100, 255]))

        super().build()

    def create_scatter_theme(self, marker_style, color_rgba):
        theme = dpg.add_theme()
        with dpg.theme_component(dpg.mvScatterSeries, parent=theme):
            dpg.add_theme_color(dpg.mvPlotCol_Line, color_rgba, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, marker_style, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 6, category=dpg.mvThemeCat_Plots)
        return theme

    def get_possible_node_connections(self) -> List[str]:
        # [TR] Terminal goruntuleme dugumu: kendisinden sonra baska dugum gelmez,
        #      bu yuzden downstream ikon etiketi yok. (Bu dugumun ikonu, TF
        #      dugumleri "pole_zero" dondurdugu icin aktiflesir.)
        # [EN] Terminal display node: nothing comes after it, so no downstream
        #      icon tag. (This node's own icon lights up because the TF nodes
        #      return "pole_zero".)
        return []

    # ------------------------------------------------------------------
    # [TR] Yardimci fonksiyonlar: Descriptor (DAE) durum-uzayi / Rosenbrock
    #      sistem matrisi tabanli Polinom Ozdeger Problemi (PEP) cozucusu.
    # [EN] Helpers for the NUMERIC path: descriptor (DAE) state-space form and
    #      the Rosenbrock-system-matrix polynomial eigenvalue problem (PEP).
    # ------------------------------------------------------------------

    def _extract_poly_coeffs(self, A_mat, s):
        """
        [EN] Extract the EXACT polynomial coefficient matrices of A(s) in s:
             A(s) = A_0 + s*A_1 (+ higher orders s^2*A_2, ... if present).
             Standard MNA stamps inductor/capacitor branches as s*L / s*C (not
             1/(sL)), so A(s) is exactly affine: A(s) = G + s*C_dyn, and G, C_dyn
             are read off as the value at s=0 and the analytic s-derivative - no
             finite differences, no truncation. If some entry is rational in s
             (an upstream symbolic node reduction), the whole matrix is first
             cleared by its least common denominator and the denominator roots
             are returned so _filter_spurious_roots can drop them.
             Returns (list_of_np_coeff_matrices, max_degree, denom_lcm).

        --- Turkce aciklama / Turkish explanation ---

        A(s) matrisinin s'e gore TAM polinom katsayi matrislerini cikarir:
        A(s) = G + s*C_dyn (+ olasi daha yuksek dereceler: s^2*A_2, ...)

        Standart MNA'da endüktans dallari ayri bir akim degiskeniyle temsil
        edildiginden (yani 1/(sL) degil sL damgasi kullanildigindan), A(s)
        s'de TAM OLARAK AFINDIR: A(s) = G + s*C_dyn, ve bu ayristirma
        (s=0'daki deger ile s'e gore ANALITIK turev - sonlu fark degil)
        HICBIR YAKLAŞIKLIK ICERMEZ. Asagidaki kod bunu genel bir polinom
        katsayi cikarimi olarak yapar (k=1 ozel durumu G, C_dyn'e karsilik
        gelir); boylece olasi bir ust-akis sembolik indirgemesi A(s)'e daha
        yuksek dereceden terim katarsa (s^2, s^3, ...) bu da OTOMATIK ve
        DOGRU sekilde yakalanir - kirpma/truncation hicbir durumda olmaz.

        Sembolik LUsolve/ters alma gibi pahali islemlere hic girilmez;
        sadece her (i,j) elemaninin s'e gore katsayilari okunur - bu O(n^2)
        maliyetli, "expression swell" riski tasimayan ucuz bir islemdir.

        Eger bir eleman s cinsinden saf POLINOM degilse (rasyonel/kesirli ise
        - ornegin bu node'a gelmeden once bir yerde ic dugum sembolik olarak
        indirgenmisse), once tum matrisin ortak paydasini (LCD) bulup
        temizler. Bu durumda payda'nin kokleri "sahte" (spurious) kok olarak
        isaretlenip _filter_spurious_roots ile sonuclardan cikarilir.
        """
        n, m = A_mat.shape

        # [TR] Hizli yol: standart MNA'da A(s) neredeyse her zaman s'de afindir
        #      (A_0 + s*A_1). Bunu tek bir turev + s=0 degeriyle test et; tutuyorsa
        #      pahali eleman-bazli Poly/is_polynomial taramasini tamamen atla.
        # [EN] Fast path: for standard MNA A(s) is almost always affine in s
        #      (A_0 + s*A_1). Test that with one derivative + the value at s=0;
        #      if it holds, skip the per-entry Poly / is_polynomial scan entirely.
        try:
            A0 = A_mat.subs(s, 0)
            A1 = A_mat.diff(s)
            if (A_mat - A0 - s * A1).applyfunc(sp.expand).is_zero_matrix:
                G_arr = np.array(A0, dtype=complex)
                if A1.is_zero_matrix:            # purely resistive: degree 0
                    return [G_arr], 0, sp.Integer(1)
                return [G_arr, np.array(A1, dtype=complex)], 1, sp.Integer(1)
        except Exception:
            pass

        non_poly_found = any(
            A_mat[i, j] != 0 and not A_mat[i, j].is_polynomial(s)
            for i in range(n) for j in range(m)
        )

        denom_lcm = sp.Integer(1)
        if non_poly_found:
            print("Uyari: A(s) matrisinde rasyonel (paydali) elemanlar tespit edildi; "
                  "ortak payda ile temizleniyor. Payda kokleri sahte (spurious) kok "
                  "olarak isaretlenip sonuclardan cikarilacak.", flush=True)
            for i in range(n):
                for j in range(m):
                    _, denom = sp.fraction(sp.together(A_mat[i, j]))
                    denom_lcm = sp.lcm(denom_lcm, denom)
            A_mat = sp.expand(A_mat * denom_lcm)

        max_deg = 0
        for i in range(n):
            for j in range(m):
                expr = A_mat[i, j]
                if expr == 0 or s not in expr.free_symbols:
                    continue
                # NOT: sp.degree() Python int degil, sympy Integer donduruyor.
                # int()'e hemen sarmazsak asagida numpy/float aritmetigine
                # karisip her seyi sessizce (ve yavas) sympy nesnesine
                # cevirebilir (ornegin gamma hesaplamasinda).
                # sp.degree(0-poly) -> -oo; is_polynomial False -> PolynomialError:
                # ikisini de gecerli "sabit terim" (derece 0) gibi ele al.
                try:
                    deg = sp.degree(expr, gen=s)
                except sp.PolynomialError:
                    continue
                if not deg.is_finite:
                    continue
                max_deg = max(max_deg, int(deg))

        coeff_mats_sym = [sp.zeros(n, m) for _ in range(max_deg + 1)]
        for i in range(n):
            for j in range(m):
                expr = A_mat[i, j]
                if expr == 0:
                    continue
                try:
                    poly = sp.Poly(expr, s)
                except sp.PolynomialError:
                    # s cinsinden polinom degil (artik rasyonel terim); s=0
                    # degerini sabit terime koy - kalan sahte kokler zaten
                    # _filter_spurious_roots ile elenir.
                    coeff_mats_sym[0][i, j] = expr.subs(s, 0)
                    continue
                asc_coeffs = poly.all_coeffs()[::-1]  # index d -> s^d katsayisi
                for d, c in enumerate(asc_coeffs):
                    if d < len(coeff_mats_sym):
                        coeff_mats_sym[d][i, j] = c

        coeffs = [np.array(mat, dtype=complex) for mat in coeff_mats_sym]
        return coeffs, max_deg, denom_lcm

    def _compute_pencil_scaling(self, A_coeffs, k):
        """
        [EN] Scale factor gamma for the substitution s = gamma * s_hat, so that
             the constant term G (resistor / low-frequency scale) and the
             highest-order term (junction-capacitance / high-frequency scale)
             become comparable near s_hat ~ O(1):
                 gamma = (||A_0|| / ||A_k||)^(1/k)   (||G||/||C_dyn|| for k=1).
             This conditions the pencil before the QZ step.

        --- Turkce aciklama / Turkish explanation ---

        s = gamma * s_hat donusumu icin olcekleme katsayisini hesaplar, oyle ki
        G (dusuk frekans/direnc mertebesi) ve en yuksek dereceli katsayi
        (yuksek frekans/jonksiyon kapasitesi mertebesi) terimleri s_hat~O(1)
        civarinda karsilastirilabilir buyuklukte olsun:
        gamma = (||G|| / ||A_k||)^(1/k)  (k=1 icin ||G||/||C_dyn||)
        """
        norm_a0 = np.max(np.abs(A_coeffs[0])) if A_coeffs[0].size else 0.0
        norm_ak = np.max(np.abs(A_coeffs[k])) if A_coeffs[k].size else 0.0
        if norm_a0 > 0 and norm_ak > 0 and k > 0:
            gamma = (norm_a0 / norm_ak) ** (1.0 / k)
        else:
            gamma = 1.0
        return gamma

    def _equilibrate_pencil(self, A, B, iterations=2):
        """
        [EN] Balance the matrix pencil (A, B) by two-sided diagonal scaling.
             This does NOT change the eigenvalues: it is D*A*E and D*B*E with D,
             E diagonal invertible, and eigenvectors map as v -> E^-1 v. It only
             improves the numerical stability of scipy's QZ when pF-range
             junction caps and uF-range coupling caps sit in the same pencil
             (large cond(G)).

        --- Turkce aciklama / Turkish explanation ---

        (A, B) pencil'ini satir/sutun bazinda kosegen olcekleme ile dengeler.

        Bu islem OZDEGERLERI DEGISTIRMEZ: D*A*E ve D*B*E seklinde iki tarafli
        kosegen bir donusumdur (D, E kosegen ve tersinir), ve v -> E^-1*v ile
        ozdegerler birebir korunur - sadece scipy.linalg.eig'in QZ algoritmasinin
        sayisal kararliligini artirir. Bu, ozellikle pF mertebesindeki jonksiyon
        kapasiteleri ile uF mertebesindeki bypass/coupling kapasitelerinin AYNI
        pencil icinde bulunmasi durumunda onemlidir (cond(G) buyuk oldugunda).
        """
        n = A.shape[0]
        if n == 0:
            return A, B
        for _ in range(iterations):
            row_max = np.maximum(np.max(np.abs(A), axis=1), np.max(np.abs(B), axis=1))
            row_max[row_max == 0] = 1.0
            r = 1.0 / np.sqrt(row_max)
            A = A * r[:, None]
            B = B * r[:, None]

            col_max = np.maximum(np.max(np.abs(A), axis=0), np.max(np.abs(B), axis=0))
            col_max[col_max == 0] = 1.0
            c = 1.0 / np.sqrt(col_max)
            A = A * c[None, :]
            B = B * c[None, :]
        return A, B

    def _build_rosenbrock_coeffs(self, A_coeffs, B_coeffs, C_out, n):
        """
        [EN] Build the generalized Rosenbrock system-matrix polynomial
             P(s) = [[A(s), -B(s)], [C_out, 0]]  (size (n+1) x (n+1)),
             coefficient-wise:
                 P_0 = [[G, -B_0], [C_out, 0]],   P_i = [[A_i, -B_i], [0, 0]].
             B(s) is treated as a full polynomial too (Norton source transforms
             can make z depend on s). By the Schur-complement identity
             det(P(s)) = det(A(s)) * (C_out A(s)^-1 B(s)) equals the Cramer
             numerator (the transmission-zero numerator) exactly, but is solved
             by a single GEVP that never needs A(s) to be invertible.

        --- Turkce aciklama / Turkish explanation ---

        A(s) = sum_i s^i * A_coeffs[i] (n x n) ve B(s) = sum_i s^i * B_coeffs[i]
        (n x 1), C_out (1 x n) icin genellestirilmis ROSENBROCK SISTEM MATRISI
        polinomunu ((n+1) x (n+1)) kurar:

            P(s) = [[A(s), -B(s)], [C_out, 0]]

        Katsayi bazinda:
            P_0 = [[G, -B_0], [C_out, 0]],   P_i = [[A_i, -B_i], [0, 0]]

        ONEMLI: B(s)'in s'e BAGLI olabilecegi varsayilir. MNA'da z vektoru
        cogu zaman sabittir, ANCAK kaynak donusumu (Norton: Vin/Z(s) = Vin*s*C)
        yapan formulasyonlarda z(s) s icerebilir; bu durumda z'yi s=0'da
        dondurmak (eski davranis) sifirlari TAMAMEN yok edebilir. Bu yuzden
        B de tam polinom olarak islenir ve pencil derecesi
        k = max(deg A, deg B) olarak alinir.

        Schur tumleyeni ozdesligiyle det(P(s)) = det(A(s)) * (C_out A(s)^-1 B(s))
        = Cramer payi (transmission zero payi) ile BIREBIR AYNIDIR - ama
        A(s)'in herhangi bir noktada tersinir olmasina hic bagli olmayan,
        tek bir GEVP ile dogrudan cozulen, descriptor sistemler teorisindeki
        standart Rosenbrock formulasyonudur. k=1 ve sabit B durumunda dogrudan
        M0=[[G,-B],[C_out,0]], M1=[[C_dyn,0],[0,0]] pencil'ine esittir.
        """
        k = max(len(A_coeffs), len(B_coeffs)) - 1
        m = n + 1
        P_coeffs = [np.zeros((m, m), dtype=complex) for _ in range(k + 1)]
        for i, Ai in enumerate(A_coeffs):
            P_coeffs[i][:n, :n] = Ai
        for i, Bi in enumerate(B_coeffs):
            P_coeffs[i][:n, n] = -Bi[:, 0]
        P_coeffs[0][n, :n] = C_out
        return P_coeffs, m, k

    def _solve_polynomial_eigenproblem(self, A_coeffs, n, k, gamma, abs_mag_limit=1e18):
        """
        [EN] Solve the degree-k matrix polynomial P(s) = sum_i s^i * A_coeffs[i]
             by companion linearization into a kn x kn GEVP, then scipy.linalg.eig
             (LAPACK ggev = the QZ algorithm). For k=1 this is exactly the pencil
             eig(A_0, -A_1). Infinite / spurious eigenvalues are filtered in two
             stages: (1) a RELATIVE beta threshold max|beta|*1e-10 - because
             LAPACK's (alpha, beta) scale with the absolute size of the input
             pencil, a fixed threshold would be wrong after gamma scaling +
             equilibration; (2) an ABSOLUTE magnitude cap on the physical
             (gamma-undone) value - no real circuit pole/zero exceeds it.
             Returns the finite eigenvalues (physical units), unsorted.

        --- Turkce aciklama / Turkish explanation ---

        P(s) = sum_i s^i * A_coeffs[i] (derece k) icin companion linearization
        ile kn x kn boyutlu bir GEVP kurup scipy.linalg.eig ile cozer. k=1
        durumunda bu dogrudan G + s*C_dyn pencil'ine (eig(G,-C_dyn)) esittir.

        scipy.linalg.eig(a, b) - b verildiginde - LAPACK'in ggev rutinini
        cagirir; bu ZATEN QZ algoritmasidir (dogrulanmistir). ordqz/gges'in
        ek sundugu tek sey Schur-form uzerinde secili ozdeger kumelerini
        yeniden siralama/ayirma yetenegidir - burada oldugu gibi TUM sonlu
        ozdegerleri cikarip Python'da kendimiz siraladigimiz kullanimda bu,
        ggev'in verdigi dogruluga hicbir ek katki saglamaz.

        Sonsuzdaki/sahte ozdegerleri IKI ASAMALI filtreler:
          1) GORECELI beta esigi (max|beta|*1e-10): (alpha,beta) ciftlerinin
             LAPACK'ta girdi pencil'inin MUTLAK olcegiyle orantili ciktigi
             sayisal olarak dogrulanmistir (orn. pencil 1e6 ile carpilirsa
             beta da 1e6 ile carpilir) - yani SABIT bir beta esigi (ornegin
             1e-12), gamma-olcekleme ve equilibration sonrasi pencil'in
             mutlak buyuklugune gore ya cok gevsek ya da cok siki kalirdi.
             Goreceli esik, bu ic olceklemeden bagimsiz calisir.
          2) MUTLAK buyukluk siniri (|deger|>1e15 rad/s): fiziksel (gamma
             geri-cevrilmis) sonuc uzerinde, ic olceklemeden BAGIMSIZ son bir
             saglamlik agi - hicbir gercek devre kutbu/sifiri bu mertebeyi
             asmaz.
        """
        if k == 0:
            return []

        N = n * k
        Acomp = np.zeros((N, N), dtype=complex)
        Bcomp = np.zeros((N, N), dtype=complex)

        for i in range(k - 1):
            Acomp[i*n:(i+1)*n, (i+1)*n:(i+2)*n] = np.eye(n)
        for i in range(k):
            Acomp[(k-1)*n:k*n, i*n:(i+1)*n] = -A_coeffs[i]

        for i in range(k - 1):
            Bcomp[i*n:(i+1)*n, i*n:(i+1)*n] = np.eye(n)
        Bcomp[(k-1)*n:k*n, (k-1)*n:k*n] = A_coeffs[k]

        Acomp, Bcomp = self._equilibrate_pencil(Acomp, Bcomp)

        alpha_beta = scipy.eig(Acomp, Bcomp, right=False, homogeneous_eigvals=True)
        alpha = alpha_beta[0, :]
        beta = alpha_beta[1, :]

        beta_tol = np.max(np.abs(beta)) * 1e-10 if beta.size else 0.0
        finite_mask = np.abs(beta) > beta_tol

        raw_eigs = (alpha[finite_mask] / beta[finite_mask]) * gamma

        clean = []
        for e in raw_eigs:
            if not (np.isfinite(e.real) and np.isfinite(e.imag)):
                continue
            if abs(e) > abs_mag_limit:
                continue
            clean.append(complex(e))
        return clean

    def _filter_spurious_roots(self, roots, denom_list, s, rel_tol=1e-6):
        """
        [EN] Remove the common-denominator roots introduced by the rational-entry
             clearing step (if any). Takes a LIST of denominators because A(s)
             and z(s) may each be rational. When every denominator is 1 (both
             were pure polynomials - the normal case) this is a no-op and the
             input list is returned unchanged.

        --- Turkce aciklama / Turkish explanation ---

        Rasyonel eleman temizleme adiminda (varsa) eklenen ortak payda
        koklerini gercek sonuclardan cikarir. A(s) ve z(s) ayri ayri paydali
        olabilecegi icin bir payda LISTESI alir. Tum paydalar 1 oldugunda
        (yani her ikisi de saf polinomdu - beklenen/yaygin durum) bu fonksiyon
        hicbir sey yapmaz ve girdi listesini oldugu gibi dondurur.
        """
        spurious = []
        for denom in denom_list:
            if denom == 1:
                continue
            poly = sp.Poly(denom, s)
            if poly.degree() < 1:
                continue
            spurious.extend(np.roots([complex(sp.N(c)) for c in poly.all_coeffs()]))
        if not spurious:
            return roots
        clean = []
        for r in roots:
            if not any(abs(r - sr) < rel_tol * max(1.0, abs(sr)) for sr in spurious):
                clean.append(r)
        return clean



    def _resolve_output_node(self, mna_data):
        """[TR] Cikis dugumunu belirler. Bu dugumde SECILMEZ - bagli
               TransferFunction dugumunde secilir ve `src_output_node` ile
               buraya gelir. KUTUPLAR cikis dugumunden bagimsizdir ama
               SIFIRLAR dogrudan ona baglidir; bu yuzden referans bir araca
               karsi karsilastirirken AYNI dugumun secili olmasi onemlidir.
               `src_output_node` gecersizse (or. dogrudan MNA baglanmis) son
               bilinmeyene duser ve uyarir.
        [EN] Determine the output node. It is NOT chosen here - it is chosen on
             the connected TransferFunction node and arrives via
             `src_output_node`. POLES are independent of the output node but
             ZEROS depend on it directly, so when comparing against a reference
             tool the SAME node must be selected on both. Falls back to the last
             unknown (with a warning) if `src_output_node` is not usable
             (e.g. a direct MNA link).
        """
        try:
            names = [str(u) for u in mna_data.get_unknowns()]
        except Exception as e:
            print(f"Bilinmeyenler okunamadi: {e}", flush=True)
            return None

        if self.src_output_node and self.src_output_node in names:
            return self.src_output_node

        chosen = names[-1] if names else None
        print(f"Cikis dugumu TransferFunction dugumunden alinamadi; gecici "
              f"olarak '{chosen}' kullaniliyor.", flush=True)
        print(f"Mevcut dugumler: {names}", flush=True)
        print("TransferFunction dugumunde cikis dugumunu secip Calculate'e basin.",
              flush=True)
        return chosen

    def _calculate_robust_poles_zeros(self, mna_data, unknown_variable: str):
        """
        [EN] NUMERIC path. Descriptor (DAE) state-space form: standard MNA is
             exactly affine in s, A(s) = G + s*C_dyn (G, C_dyn from the value
             at s=0 and the analytic derivative - no finite differences, no
             approximation). Poles solve det(G + s*C_dyn) = 0, i.e. the
             generalized eigenproblem eig(G, -C_dyn) (companion-linearized PEP
             for k>1). Zeros use Analog Insydes' exact ZerosByQZ method: replace
             the output column of the pencil with the source vector z and keep
             all finite eigenvalues. gamma scaling + row/column equilibration
             handle the pF-vs-uF magnitude spread. Returns
             {"zeros": [...], "poles": [...]} sorted by magnitude.

        --- Turkce aciklama / Turkish explanation ---

        Descriptor durum-uzayi (DAE) formulasyonu ile TAM kutup/sifir cozumu.

        Standart MNA'da endüktans dallari ayri bir akim degiskeniyle temsil
        edildiginden A(s) = G + s*C_dyn seklinde s'DE TAM OLARAK AFINDIR:
            G x(s) + s*C_dyn x(s) = B u(s)  <=>  (G + s*C_dyn) x(s) = B u(s)
        G ve C_dyn, s=0'daki deger ve s'e gore ANALITIK turev (sonlu fark
        DEGIL) ile TAM olarak ayristirilir - bu adimda hicbir yaklaşiklik
        yoktur. (Olasi bir ust-akis sembolik indirgemesi A(s)'e daha yuksek
        dereceden terim katarsa - s^2, s^3, ... - asagidaki cozucu k>1'i de
        otomatik ve dogru sekilde ele alir; k=1 durumunda regresyon YOKTUR.)

        KUTUPLAR: det(G+s*C_dyn) = 0  <=>  Gv = -s*C_dyn*v, yani
        eig(G, -C_dyn) - genel k icin companion-linearized PEP'e genellenir.

        SIFIRLAR: Rosenbrock sistem matrisi P(s) = [[A(s),-B],[C_out,0]] ile
        eig(P0, -P1) (k=1 icin) - A(s)'in tersinirligine hic bagli olmayan
        tek bir GEVP. Schur tumleyeni ozdesligiyle bu, Cramer/cikis-sutunu
        yontemiyle BIREBIR ayni payi (ayni sifirlari) verir; Rosenbrock
        formulasyonu tercih edilmistir cunku A(s)'i hic ters cevirmeden
        (implicit invertibility varsayimi olmadan) tek bir GEVP'te cozer ve
        descriptor sistemler teorisindeki standart/saglam yontemdir.

        scipy.linalg.eig(a,b) - b verildiginde - LAPACK ggev'i (QZ algoritmasi)
        cagirir; ayrica bkz. _solve_polynomial_eigenproblem docstring'i.

        Sonsuzdaki/sahte ozdegerler goreceli-beta esigi + mutlak |deger|>1e15
        sinirinin BIRLESIMIYLE filtrelenir (sabit 1e-12 beta esigi yerine
        goreceli esik kullanmamizin sayisal gerekcesi _solve_polynomial_
        eigenproblem'da aciklanmistir). Sonuclar buyuklugüne gore SIRALI
        dondurulur.
        """
        s = sp.symbols('s')
        unknown_variable_symbol = sp.symbols(unknown_variable)
        if unknown_variable_symbol not in mna_data.unknowns:
            raise ValueError(f"Bilinmeyen değişken {unknown_variable} sistemde yok.")

        x_syms = list(mna_data.get_unknowns())
        idx_out = x_syms.index(unknown_variable_symbol)

        A_sym = mna_data.A.subs(mna_data.value_dict)
        z_sym = mna_data.z.subs(mna_data.value_dict)
        n = A_sym.shape[0]

        try:
            # 1) Descriptor ayristirma: A(s) = G + s*C_dyn (+ olasi yuksek dereceler)
            A_coeffs, k, denom_lcm = self._extract_poly_coeffs(A_sym, s)
            G = A_coeffs[0]
            C_dyn = A_coeffs[1] if k >= 1 else np.zeros_like(G)
            cond_g = np.linalg.cond(G) if G.size else 0.0
            norm_g = np.max(np.abs(G)) if G.size else 0.0
            dyn_range = (np.max(np.abs(C_dyn)) / norm_g) if norm_g > 0 else 0.0
            print(f"Tespit edilen A(s) polinom derecesi: k={k}"
                  + (" (afin/birinci derece descriptor DAE: A(s)=G+s*C_dyn, kirpma yok)"
                     if k <= 1 else
                     " (yuksek dereceli dinamik tespit edildi - tam PEP cozumu uygulaniyor)")
                  + f" | cond(G)={cond_g:.3e} | ||C_dyn||/||G||={dyn_range:.3e}",
                  flush=True)

            # 2) Kaynak vektorunu de TAM POLINOM olarak cikar. MNA'da z cogu
            #    zaman sabittir, ancak kaynak donusumu (Norton: Vin*s*C) yapan
            #    formulasyonlarda s icerebilir; z.subs(s,0) demek bu durumda
            #    sifirlari tamamen yok etmek olurdu.
            B_coeffs, k_z, denom_lcm_z = self._extract_poly_coeffs(z_sym, s)
            if k_z > 0:
                print(f"NOT: z(s) kaynak vektoru s'e BAGLI (derece {k_z}); "
                      f"tam polinom olarak kullaniliyor.", flush=True)

            # C_out'u G'nin mertebesine olcekle: kokleri DEGISTIRMEZ
            # (det(P) bu carpanla dogrusal olarak olceklenir) ama Rosenbrock
            # pencil'inin son satirinin diger satirlarla ayni buyukluk
            # mertebesinde kalmasini saglar.
            c_scale = norm_g if norm_g > 0 else 1.0
            C_out = np.zeros((1, n), dtype=complex)
            if 0 <= idx_out < n:
                C_out[0, idx_out] = c_scale

            # 3) Kutuplar: A(s) pencil'inin (descriptor sistemin) GEVP'i.
            #    pF (yuksek frekans) / uF (dusuk frekans) mertebe farkini
            #    gidermek icin s=gamma*s_hat olcegi + satir/sutun esitleme.
            gamma_A = self._compute_pencil_scaling(A_coeffs, k)
            A_scaled = [(gamma_A ** i) * A_coeffs[i] for i in range(k + 1)]
            poles_num = self._solve_polynomial_eigenproblem(A_scaled, n, k, gamma_A)
            poles_num = self._filter_spurious_roots(poles_num, [denom_lcm], s)
            # (|z|, Re, Im) ile sirala: sadece |z| kullanmak eslenik ciftler
            # (a+bj, a-bj) icin BELIRSIZ sira uretir - ayni buyukluktedirler.
            poles_num = sorted(poles_num, key=lambda v: (abs(v), v.real, v.imag))

            # 4) Sifirlar.
            if k == 1 and k_z <= 1:
                # Analog Insydes ZerosByQZ ile AYNI yontem: A'nin cikis
                # sutununu kaynak vektoru z ile degistir (Cramer payi
                # det(A_out(s))); (G_z, C_z) descriptor pencil'inin SONLU
                # ozdegerleri = sifirlar. scipy.linalg.eig dogrudan
                # cagrilir - AI'nin QZ.exe'si gibi TUM sonlu ozdegerleri
                # tutar (goreceli beta esigi uygulanmaz), boylece Rosenbrock
                # yolunda kaybolan cok-yuksek-frekans sifirlari da gelir.
                Gz = A_coeffs[0].copy()
                Cz = A_coeffs[1].copy()
                Gz[:, idx_out] = B_coeffs[0][:, 0]
                Cz[:, idx_out] = B_coeffs[1][:, 0] if k_z >= 1 else 0.0
                Gz_eq, Cz_eq = self._equilibrate_pencil(Gz, -Cz)
                ev = scipy.eig(Gz_eq, Cz_eq, right=False)
                zeros_num = [complex(e) for e in ev
                             if np.isfinite(e.real) and np.isfinite(e.imag)]
            else:
                # Yuksek dereceli / s'e bagli kaynak: Rosenbrock sistem
                # matrisi P(s) = [[A(s),-B(s)],[C_out,0]].
                P_coeffs, m, k_P = self._build_rosenbrock_coeffs(
                    A_coeffs, B_coeffs, C_out, n)
                gamma_P = self._compute_pencil_scaling(P_coeffs, k_P)
                P_scaled = [(gamma_P ** i) * P_coeffs[i] for i in range(k_P + 1)]
                zeros_num = self._solve_polynomial_eigenproblem(P_scaled, m, k_P, gamma_P)

            zeros_num = self._filter_spurious_roots(zeros_num, [denom_lcm, denom_lcm_z], s)
            zeros_num = sorted(zeros_num, key=lambda v: (abs(v), v.real, v.imag))

        except Exception as e:
            print(f"Nümerik PEP Çözümleme Hatası: {e}", flush=True)
            zeros_num = []
            poles_num = []

        return {"zeros": zeros_num, "poles": poles_num}

    # ------------------------------------------------------------------
    # [TR] Sembolik cozum: H(s) = det(A_out(s)) / det(A(s)) tam rasyonel olarak.
    # [EN] Symbolic path: H(s) = det(A_out(s)) / det(A(s)) as an exact rational.
    # ------------------------------------------------------------------
    def _to_exact(self, v):
        """[TR] float -> tam rasyonel (yazdirilan ondalik basamak kadar kesin).
               repr(float) round-trip eden en kisa ondaligi verdigi icin
               Rational(repr(x)) amaclanan degeri tam yakalar.
        [EN] float -> exact rational (as precise as the printed decimal).
             repr(float) gives the shortest round-tripping decimal, so
             Rational(repr(x)) captures the intended value exactly.
        """
        f = float(v)
        if f != f or f in (float("inf"), float("-inf")):
            raise ValueError(f"deger sonlu degil: {v!r}")
        try:
            return sp.Rational(repr(f))
        except (ValueError, TypeError):
            return sp.nsimplify(f, rational=True)

    def _roots_of_exact_poly(self, poly, s):
        """[TR] Tam katsayili polinomun kokleri. Once sondaki sifir katsayilar
               sayilarak s=0 kokleri TAM alinir; sonra rasyonel/kat kokler
               (sp.roots), en son sayisal kokler (nroots, 25 basamak).
        [EN] Roots of an exact-coefficient polynomial. First the trailing zero
             coefficients are counted to take the roots at s=0 EXACTLY, then
             rational / repeated roots (sp.roots), then the rest numerically
             (nroots, 25 digits).
        """
        if poly is None or poly.total_degree() < 1:
            return []
        coeffs = poly.all_coeffs()  # en yuksek dereceden dusuge
        mult0 = 0
        for c in reversed(coeffs):
            if c == 0:
                mult0 += 1
            else:
                break
        out = [complex(0.0, 0.0)] * mult0
        rest = coeffs[:len(coeffs) - mult0] if mult0 else coeffs
        if len(rest) >= 2:
            deflated = sp.Poly(rest, s)
            # once tam carpanlar (rasyonel kokler, katlilik), sonra sayisal
            try:
                rd = sp.roots(deflated)
                if rd and sum(rd.values()) == deflated.degree():
                    for r, mult in rd.items():
                        out.extend([complex(r)] * mult)
                    return out
            except Exception:
                pass
            for r in deflated.nroots(n=25, maxsteps=500):
                out.append(complex(r))
        return out

    def _calculate_symbolic_poles_zeros(self, mna_data, unknown_variable: str):
        """
        [EN] SYMBOLIC path (Analog-Insydes style closed form). By Cramer's rule
             V_out(s)/U_in(s) = det(A_out(s)) / det(A(s)), where A_out is A with
             the output column replaced by the source vector z. POLES = roots of
             det(A) = 0; ZEROS = roots of det(A_out) = 0 after common factors
             cancel. Element values are converted to exact rationals; the
             determinants use the division-free Berkowitz method. Zeros/poles at
             s=0 (coupling caps) appear as an exact s^k factor in the numerator -
             no "~1e-8" dust like the numeric QZ path. Also returns a factored
             H(s) string. Falls back to the numeric path on failure.

        --- Turkce aciklama / Turkish explanation ---

        Analog Insydes tarzi kapali-form cozum.

        Cramer kurali ile:  V_out(s) / U_in(s) = det(A_out(s)) / det(A(s))
        - A_out = A'nin cikis sutunu z (kaynak vektoru) ile degistirilmis hali
        - KUTUPLAR = det(A) = 0 kokleri
        - SIFIRLAR = det(A_out) = 0 kokleri (ortak carpanlar sadelestikten sonra)

        Eleman degerleri tam rasyonele cevrilir; determinantlar bolme
        kullanmayan Berkowitz yontemiyle alinir. s=0'daki sifirlar (kuplaj
        kondansatorleri) pay'da tam s^k carpani olarak cikar - sayisal
        QZ'deki "≈1e-8" tozu olmaz.
        """
        s = sp.symbols('s')
        x_syms = [str(u) for u in mna_data.get_unknowns()]
        if unknown_variable not in x_syms:
            raise ValueError(f"'{unknown_variable}' bilinmeyenler arasinda yok.")
        idx_out = x_syms.index(unknown_variable)

        # [TR] Eleman degerlerini tam rasyonele cevir. `.subs` yerine `.xreplace`:
        #      sembol->sayi degisimi icin yapisal, alt-ifade degerlendirmesi
        #      yapmayan ve belirgin sekilde daha hizli bir yol.
        # [EN] Convert element values to exact rationals. Use `.xreplace` instead
        #      of `.subs`: a structural symbol->value swap that does not
        #      re-evaluate subexpressions and is noticeably faster.
        vd = {k: self._to_exact(v) for k, v in mna_data.value_dict.items()}
        A = sp.Matrix(mna_data.A).xreplace(vd)
        z = sp.Matrix(mna_data.z).xreplace(vd)
        n = A.shape[0]
        if n > 24:
            print(f"UYARI: {n}x{n} sembolik determinant - bu biraz surebilir.",
                  flush=True)

        # A yalnizca s'e bagli olmali; cozulememis bir eleman sembolu kalmissa
        # sembolik yol anlamli sonuc veremez -> sayisal QZ'ye don.
        extra = A.free_symbols - {s}
        if extra:
            raise ValueError(f"MNA matrisinde cozulememis sembol(ler): "
                             f"{', '.join(map(str, extra))}")

        A_out = A.copy()
        A_out[:, idx_out] = z

        # [TR] Determinantlari dogrudan Poly'ye ver: Poly kurulumu, ham ifade
        #      uzerinde `sp.expand` cagirmaktan daha verimli olarak polinom
        #      halkasi icinde acilim yapar.
        # [EN] Feed the determinants straight to Poly: Poly construction expands
        #      inside the polynomial ring, which is more efficient than calling
        #      `sp.expand` on the raw expression.
        try:
            p_poly = sp.Poly(A.det(method="berkowitz"), s)
            z_poly = sp.Poly(A_out.det(method="berkowitz"), s)
        except sp.PolynomialError as e:
            raise ValueError(f"determinant s'de polinom degil ({e}) - "
                             f"sayisal yola donuluyor")

        all_c = p_poly.all_coeffs() + z_poly.all_coeffs()
        if p_poly.is_zero or any(getattr(c, "is_finite", True) is False for c in all_c):
            raise ValueError("sembolik determinant tekil / tanimsiz "
                             "(D=0 veya nan) - sayisal yola donuluyor")

        # [TR] Ortak (s-bagimli) carpanlari Poly-halkasi GCD'siyle sadelestir -
        #      `sp.cancel(sp.together(N/D))`'den daha dogrudan.
        # [EN] Cancel common (s-dependent) factors via a polynomial-ring GCD -
        #      more direct than `sp.cancel(sp.together(N/D))`.
        g = sp.gcd(z_poly, p_poly)
        if g.degree() > 0:
            z_poly = sp.Poly(sp.quo(z_poly, g), s)
            p_poly = sp.Poly(sp.quo(p_poly, g), s)

        poles = sorted(self._roots_of_exact_poly(p_poly, s),
                       key=lambda v: (abs(v), v.real, v.imag))
        zeros = sorted(self._roots_of_exact_poly(z_poly, s),
                       key=lambda v: (abs(v), v.real, v.imag))

        tf_string = self._factored_tf_string(zeros, poles, z_poly, p_poly, s)
        print(f"Sembolik: pay derecesi {z_poly.degree()}, "
              f"payda derecesi {p_poly.degree()}.", flush=True)
        print(tf_string, flush=True)
        return {"zeros": zeros, "poles": poles, "tf_string": tf_string}

    def _factored_tf_string(self, zeros, poles, z_poly, p_poly, s) -> str:
        """[TR] H(s)'i carpanlarina ayrilmis, okunabilir bicimde yazar:
                 H(s) = K * s^k (s + a)(s^2 + b s + c) / [ (s + p1)(s + p2) ... ]
               Sembolik yolun s=0 kokleri TAM 0 oldugu icin s^k carpani net
               gorunur; eslenik ciftler (s^2 + b s + c) olarak toplanir; kazanc
               K = z_poly.LC() / p_poly.LC().
        [EN] Render H(s) in a readable factored form:
                 H(s) = K * s^k (s + a)(s^2 + b s + c) / [ (s + p1)(s + p2) ... ]
             The symbolic path's s=0 roots are exactly 0 so the s^k factor is
             clean; conjugate pairs are grouped as (s^2 + b s + c); the gain is
             K = z_poly.LC() / p_poly.LC().
        """
        def group(roots):
            origin = sum(1 for r in roots if r == 0)
            rest = [r for r in roots if r != 0]
            parts = []
            if origin:
                parts.append("s" if origin == 1 else f"s^{origin}")
            used = [False] * len(rest)
            for i, r in enumerate(rest):
                if used[i]:
                    continue
                if abs(r.imag) <= 1e-6 * abs(r.real):
                    # kok r -> carpan (s - r)
                    sign = "-" if r.real >= 0 else "+"
                    parts.append(f"(s {sign} {abs(r.real):.4g})")
                    used[i] = True
                    continue
                for j in range(i + 1, len(rest)):
                    if not used[j] and abs(rest[j] - r.conjugate()) <= 1e-6 * abs(r):
                        used[i] = used[j] = True
                        b, c = -2.0 * r.real, abs(r) ** 2
                        bs = "+" if b >= 0 else "-"
                        parts.append(f"(s^2 {bs} {abs(b):.4g} s + {c:.4g})")
                        break
                else:
                    used[i] = True
                    parts.append(f"(s - ({r.real:.4g}{r.imag:+.4g}j))")
            return " ".join(parts) if parts else "1"

        try:
            K = complex(z_poly.LC()) / complex(p_poly.LC())
            k_str = (f"{K.real:.4g}" if abs(K.imag) <= 1e-9 * abs(K.real)
                     else f"{K:.4g}")
        except Exception:
            k_str = "K"
        return (f"H(s) = {k_str} * {group(zeros)}\n"
                f"       / [ {group(poles)} ]")

    def _extract_mna(self, raw, build_from_circuit: bool = True):
        """[TR] Giris pininden gelen ham veriyi ('(log_space, mna)' tuple'i,
               bir MNA node objesi ya da dogrudan bir Circuit) A/z matrisleri
               olan bir MNA nesnesine cevirir. Bulunamazsa None.
        [EN] Normalize whatever comes off the input pin (a '(log_space, mna)'
             tuple, an MNA node object, or a raw Circuit) into an MNA object
             that has A/z matrices. Returns None if none is found.
        """
        data = raw
        if isinstance(data, tuple):
            picked = None
            for item in data:
                if hasattr(item, "mna"):
                    picked = item.mna
                    break
                if hasattr(item, "A") and hasattr(item, "z"):
                    picked = item
                    break
            data = picked if picked is not None else (data[0] if data else None)
        if hasattr(data, "mna"):
            data = data.mna
        if (build_from_circuit and data is not None and not hasattr(data, "A")
                and hasattr(data, "elements")):
            from Modified_Node_Analysis import ModifiedNodalAnalysis
            mna = ModifiedNodalAnalysis(data)
            mna.buildEquationsSystem()
            data = mna
        if data is not None and hasattr(data, "A") and hasattr(data, "z"):
            return data
        return None

    def _read_link_context(self, raw):
        """[TR] Giris pininden gelen TransferFunction yukunu cozer.

               TransferFunction dugumleri `h_out` pininde su tuple'i yayinliyor:
                   (H_list, sweep, mna, mode, output_node)
               `mode` "numeric" | "symbolic" - hesap yolu bununla secilir.
               `output_node` TransferFunction dugumunde secilen cikis dugumudur.

               Geriye donuk / dogrudan-MNA baglantilarinda (2'li tuple, MNA
               node, Circuit) mode/output_node bos kalir; _extract_mna ve
               _resolve_output_node devreye girer.

        [EN] Decode the TransferFunction payload arriving on the input pin.

             TF nodes publish this tuple on the `h_out` pin:
                 (H_list, sweep, mna, mode, output_node)
             `mode` is "numeric" | "symbolic" and selects the calculation path.
             `output_node` is the output node chosen on the TF node.

             For backward-compatible / direct-MNA links (2-tuple, MNA node,
             Circuit) mode/output_node stay empty and _extract_mna /
             _resolve_output_node take over.
        """
        mode, out_node = "", ""
        if (isinstance(raw, (tuple, list)) and len(raw) >= 5
                and hasattr(raw[2], "A") and hasattr(raw[2], "z")):
            m, on = raw[3], raw[4]
            if isinstance(m, str):
                mode = m
            if isinstance(on, str):
                out_node = on
        return self._extract_mna(raw), mode, out_node

    def _update_source_info(self):
        # [TR] Arayuzdeki "Kaynak: ..." satirini bagli TF dugumune gore gunceller.
        # [EN] Update the "Kaynak: ..." (source) status line from the linked TF node.
        if not (self.source_info_tag and dpg.does_item_exist(self.source_info_tag)):
            return
        if self.src_mode:
            label = {"numeric": "TF Numeric (QZ / sayisal)",
                     "symbolic": "TF Symbolic (det N(s)/D(s))"}.get(
                        self.src_mode, self.src_mode)
            node = self.src_output_node or "(TF dugumunde secilmedi)"
            dpg.set_value(self.source_info_tag,
                          f"Kaynak: {label}\nCikis dugumu: {node}")
        else:
            dpg.set_value(self.source_info_tag,
                          "Kaynak: bir TransferFunction dugumu baglayin "
                          "(veya dogrudan MNA).")

    def onlink_callback(self):
        # [TR] Bir link kurulunca: bagli TransferFunction dugumunun modunu ve
        #      cikis dugumunu oku ki kullanici 'Calculate & Plot' oncesi ne
        #      olacagini gorsun.
        # [EN] On link: read the connected TransferFunction node's mode and
        #      output node so the user sees what will happen before pressing
        #      'Calculate & Plot'.
        try:
            raw = self.get_input_pin_value("mna_pin")
            _, mode, out_node = self._read_link_context(raw)
            self.src_mode = mode
            self.src_output_node = out_node
            self._update_source_info()
        except Exception as e:
            print(f"Kaynak baglami okunamadi: {e}", flush=True)
        super().onlink_callback()

    def calculate_callback(self, sender, app_data, user_data=None):
        """[TR] 'Calculate & Plot' dugmesi. Bagli TF dugumunden MNA + mod +
               cikis dugumunu al; mod sembolikse _calculate_symbolic_poles_zeros
               (basarisizsa sayisala don), degilse _calculate_robust_poles_zeros
               calistir; sonuclari metin, carpanli H(s) ve s-duzlemi grafigine yaz.
        [EN] The 'Calculate & Plot' button. Take MNA + mode + output node from
             the linked TF node; if the mode is symbolic run
             _calculate_symbolic_poles_zeros (falling back to numeric on
             failure), otherwise _calculate_robust_poles_zeros; write the
             results into the text fields, the factored H(s), and the s-plane
             scatter plot.
        """
        raw = self.get_input_pin_value("mna_pin")

        print("\n--- POLE/ZERO HESAPLAMA TETİKLENDİ ---", flush=True)
        print(f"Kablodan Gelen İlk Veri Tipi: {type(raw)}", flush=True)

        try:
            mna_data, mode, out_node = self._read_link_context(raw)
            if mode:
                self.src_mode = mode
            if out_node:
                self.src_output_node = out_node
            self._update_source_info()
        except Exception as e:
            import traceback
            traceback.print_exc()
            dpg.set_value(self.text_zeros_tag, "MNA kurulamadi!")
            dpg.set_value(self.text_poles_tag, str(e))
            return

        # --- FİNAL VERİ DOĞRULAMA ---
        if not mna_data or not hasattr(mna_data, 'A') or not hasattr(mna_data, 'z'):
            hata_msj = type(mna_data).__name__ if mna_data else "None (Veri Yok)"
            print(f"Hata: Beklenen özellikler bulunamadı! Mevcut obje: {hata_msj}", flush=True)
            
            dpg.set_value(self.text_zeros_tag, f"Error: Received {hata_msj}")
            dpg.set_value(self.text_poles_tag, "Valid MNA object not found.")
            return

        try:
            target_node = self._resolve_output_node(mna_data)
            if not target_node:
                dpg.set_value(self.text_zeros_tag, "Output node secilemedi.")
                dpg.set_value(self.text_poles_tag, "MNA bilinmeyenleri okunamadi.")
                return
            symbolic_mode = (self.src_mode == "symbolic")
            print(f"Hedef düğüm ({target_node}) için hesaplama yapılıyor "
                  f"[{'sembolik' if symbolic_mode else 'sayisal QZ'} yol]...",
                  flush=True)

            pz_results = None
            if symbolic_mode:
                print("TF Symbolic'ten geldi; H(s) tam rasyonel olarak "
                      "cozuluyor (buyuk devrelerde yavas olabilir)...", flush=True)
                try:
                    pz_results = self._calculate_symbolic_poles_zeros(
                        mna_data, target_node)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    print(f"Sembolik cozum basarisiz ({e}); sayisal QZ yoluna "
                          f"donuluyor.", flush=True)

            if pz_results is None:
                pz_results = self._calculate_robust_poles_zeros(mna_data, target_node)
            
            self.zeros = pz_results["zeros"]
            self.poles = pz_results["poles"]
            
            z_str = "\n".join([f"{z:.2e}" for z in self.zeros]) if self.zeros else "No Zeros"
            p_str = "\n".join([f"{p:.2e}" for p in self.poles]) if self.poles else "No Poles"
            
            dpg.set_value(self.text_zeros_tag, z_str)
            dpg.set_value(self.text_poles_tag, p_str)

            if self.symbolic_tf_tag and dpg.does_item_exist(self.symbolic_tf_tag):
                dpg.set_value(self.symbolic_tf_tag, pz_results.get("tf_string", ""))

            z_real = [float(z.real) for z in self.zeros]
            z_imag = [float(z.imag) for z in self.zeros]
            p_real = [float(p.real) for p in self.poles]
            p_imag = [float(p.imag) for p in self.poles]
            
            dpg.configure_item(self.scatter_zeros_tag, x=z_real, y=z_imag)
            dpg.configure_item(self.scatter_poles_tag, x=p_real, y=p_imag)
            
            # --- DOĞRU EKSEN FİT ETME YÖNTEMİ ---
            # dpg.get_item_parent yerine, scatter serisinin ebeveyni zaten y_axis'tir.
            # x_axis'i güvenli bir şekilde bulmak için y_axis'in parent'ına veya plot'a bakabiliriz,
            # ya da plot içine kaydettiğimiz tag'leri kullanabiliriz.
            
            # Scatter serisinin doğrudan bağlı olduğu üst öğe y_axis'tir:
            y_axis_id = dpg.get_item_parent(self.scatter_zeros_tag)
            # y_axis'in de bir üst öğesi dpg.plot bileşenidir. Plot'un çocukları (children) arasında eksenler bulunur.
            plot_id = dpg.get_item_parent(y_axis_id)
            
            # Plot altındaki eksenleri güvenli bir şekilde bulup fit edelim:
            children = dpg.get_item_children(plot_id, slot=1) # slot=1 eksenleri tutar
            if children and len(children) >= 2:
                x_axis_id = children[0]
                y_axis_id = children[1]
                dpg.fit_axis_data(x_axis_id)
                dpg.fit_axis_data(y_axis_id)
            
            print("Çizim başarıyla tamamlandı ve eksenler fit edildi!", flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            dpg.set_value(self.text_zeros_tag, "Computation Error!")
            dpg.set_value(self.text_poles_tag, str(e))