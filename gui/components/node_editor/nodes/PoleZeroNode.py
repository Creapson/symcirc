import dearpygui.dearpygui as dpg
import numpy as np
import sympy as sp
from pydantic import Field
from typing import Literal, List
import scipy.linalg as scipy
import mpmath
from gui.components.node_editor.nodes.Node import Node, NodeType

class PoleZeroNode(Node):
    node_type: Literal[NodeType.POLE_ZERO_PLOT] = NodeType.POLE_ZERO_PLOT

    zeros: List[complex] = Field(default_factory=list, exclude=True)
    poles: List[complex] = Field(default_factory=list, exclude=True)

    text_zeros_tag: str = Field(default="", exclude=True)
    text_poles_tag: str = Field(default="", exclude=True)
    scatter_zeros_tag: str = Field(default="", exclude=True)
    scatter_poles_tag: str = Field(default="", exclude=True)
    exact_mode_tag: str = Field(default="", exclude=True)
    symbolic_mode_tag: str = Field(default="", exclude=True)
    symbolic_tf_tag: str = Field(default="", exclude=True)
    output_node_tag: str = Field(default="", exclude=True)

    def build(self):
        self.add_input_pin("mna_pin", "Connect MNA/Solver here!")

        with self.add_static_attr():
            dpg.add_button(label="Calculate & Plot", callback=self.calculate_callback)

            self.output_node_tag = self.uuid("output_node")
            dpg.add_text("Output node (transfer function):")
            dpg.add_combo([], tag=self.output_node_tag, width=200,
                          default_value="")
            dpg.add_text("MNA baglandiktan sonra doldurulur.",
                         color=[150, 150, 150])
            dpg.add_separator()

            self.exact_mode_tag = self.uuid("exact_mode")
            dpg.add_checkbox(label="Exact Precision Calculation (mpmath, 50 dps)",
                             tag=self.exact_mode_tag, default_value=False)
            dpg.add_text("Yavas ama tam; float64 QZ ile karsilastirmak icin.",
                         color=[150, 150, 150])

            self.symbolic_mode_tag = self.uuid("symbolic_mode")
            dpg.add_checkbox(label="Symbolic Solve (exact N(s)/D(s), like Analog Insydes)",
                             tag=self.symbolic_mode_tag, default_value=False)
            dpg.add_text("H(s)=det(A_out)/det(A) tam rasyonel; s=0 sifirlari tam.",
                         color=[150, 150, 150])
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
        return ["solver_numeric", "solver_symbolic", "mna"]

    # ------------------------------------------------------------------
    # Yardimci fonksiyonlar: Descriptor (DAE) durum-uzayi / Rosenbrock
    # sistem matrisi tabanli Polinom Ozdeger Problemi (PEP) cozucusu
    # ------------------------------------------------------------------

    def _extract_poly_coeffs(self, A_mat, s):
        """
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


    # ------------------------------------------------------------------
    # Keyfi hassasiyetli (bignum) cozucu: mpmath, DAE indeks indirgeme
    # ------------------------------------------------------------------

    def _hp_rationalize(self, M):
        """float64 girdileri AMACLANAN ondalik degere geri cevirir.

        Bu adim sanildigindan cok daha kritiktir. Ornek: kondansatorleri
        toprakla baglantisi olmayan bir alt agda (yuzen kondansatorler),
        C_dyn'in TAM rank'i n-1'dir cunku "tum dugumler birlikte kayar"
        vektoru cekirdektedir. Ancak degerler float64'e cevrildiginde satir
        toplamlari tam sifir olmaz ve rank YAPAY OLARAK 1 artar. 50 basamakta
        calismak bu gurultuyu sinyal gibi cozumleyip SAHTE bir kutup uretir.
        Yani yuksek hassasiyet, girdide zaten kaybolmus bilgiyi geri
        getirmez - onu once burada kurtarmak gerekir.

        repr(float) round-trip eden en kisa ondaligi verdigi icin
        Rational(repr(x)) amaclanan degeri tam yakalar (2e-11 -> 1/50000000000)
        ve nsimplify'dan ~1000 kat hizlidir.
        """
        def f(e):
            if e.is_number and not e.is_Integer and not e.is_Rational:
                try:
                    return sp.Rational(repr(float(e)))
                except Exception:
                    return e
            return e
        return M.applyfunc(f)

    def _hp_num(self, e):
        """Sympy sayisi -> mpmath, TAM calisma hassasiyetinde.

        complex() uzerinden gecmek float64'e yuvarlar ve bir onceki adimda
        yapilan rasyonellestirmeyi cope atardi - yani bu yolun var olma
        sebebini ortadan kaldirirdi.
        """
        re_, im_ = sp.re(e), sp.im(e)
        if re_.is_rational and im_.is_rational:
            r, i = sp.Rational(re_), sp.Rational(im_)
            return mpmath.mpc(mpmath.mpf(r.p) / mpmath.mpf(r.q),
                              mpmath.mpf(i.p) / mpmath.mpf(i.q))
        return mpmath.mpmathify(complex(e))

    def _hp_mat(self, M):
        R = mpmath.matrix(M.rows, M.cols)
        for i in range(M.rows):
            for j in range(M.cols):
                R[i, j] = self._hp_num(M[i, j])
        return R

    def _hp_ctrans(self, M):
        R = mpmath.matrix(M.cols, M.rows)
        for i in range(M.rows):
            for j in range(M.cols):
                R[j, i] = mpmath.conj(M[i, j])
        return R

    def _hp_cols(self, M, a, b):
        R = mpmath.matrix(M.rows, b - a)
        for i in range(M.rows):
            for j in range(a, b):
                R[i, j - a] = M[i, j]
        return R

    def _hp_dae_reduce(self, G, C, B, Cout, rank_tol, max_steps=8):
        """DAE indeks indirgeme: tekil demeti (G, C) duzenli hale getirir.

        C'nin SVD'siyle dinamik alt uzay (sifirdan farkli tekil degerler) ile
        cebirsel kisitlar ayrilir, ardindan Schur tumleyeni uygulanir:

            G~ = G11 - G12 * G22^-1 * G21
            C~ = Sigma_r
            B~ = B1  - G12 * G22^-1 * B2
            C~out = Cv1 - Cv2 * G22^-1 * G21
            D~ = Cv2 * G22^-1 * B2        (ileri besleme terimi)

        NOT: Sadece "kondansatorsuz dugumler" seklinde YAPISAL bir ayirma
        YETMEZ - toprakla baglantisi olmayan bir kondansator alt agi, hicbir
        satiri yapisal olarak sifir olmadigi halde C[dyn,dyn]'i rank eksik
        birakir. SVD gercek rank'i verdigi icin bu durum da dogru islenir.
        Rank eksikligi tek adimda gitmezse (yuksek DAE indeksi) dongu tekrar
        eder; cozulmezse None doner ve cagiran taraf QZ'ye geri duser.

        rank_tol MAKINE EPSILON'A GORE DEGIL, FIZIKSEL olarak secilmelidir
        (varsayilan 1e-12): float64 girdi gurultusunun (~1e-16 bagil) uzerinde,
        gercek yapinin altinda.
        """
        D = mpmath.matrix(1, 1)
        for _ in range(max_steps):
            n = C.rows
            U, S, Vh = mpmath.svd_c(C.copy())
            smax = max((abs(S[i]) for i in range(len(S))), default=mpmath.mpf(0))
            if smax == 0:
                return None
            r = sum(1 for i in range(len(S)) if abs(S[i]) > smax * rank_tol)
            if r == n:
                return G, C, B, Cout, D
            if r == 0:
                return None
            V = self._hp_ctrans(Vh)
            U1, U2 = self._hp_cols(U, 0, r), self._hp_cols(U, r, n)
            V1, V2 = self._hp_cols(V, 0, r), self._hp_cols(V, r, n)
            U1H, U2H = self._hp_ctrans(U1), self._hp_ctrans(U2)
            G11, G12 = U1H * G * V1, U1H * G * V2
            G21, G22 = U2H * G * V1, U2H * G * V2
            Sr = mpmath.matrix(r, r)
            for i in range(r):
                Sr[i, i] = S[i]
            B1, B2 = U1H * B, U2H * B
            Cv1, Cv2 = Cout * V1, Cout * V2
            try:
                G22inv = G22 ** -1
            except Exception:
                return None
            X, Y = G22inv * G21, G22inv * B2
            G, C, B, Cout, D = (G11 - G12 * X, Sr, B1 - G12 * Y,
                                Cv1 - Cv2 * X, D + Cv2 * Y)
        return None

    def _hp_poly_on_circle(self, evalfn, deg, gamma):
        """Derece `deg` polinomunu, yaricapi gamma olan bir CEMBER uzerinde
        ornekleyerek cikarir.

        Spec Vandermonde onerdi; ancak Vandermonde matrisi klasik olarak kotu
        kosullanmistir (Wilkinson) - kotu kosullanmayi duzeltmek icin kotu
        kosullanmis bir yontem kullanmak olurdu. Birim cemberin koklerinde
        ornekleme yapildiginda Vandermonde matrisi bir DFT matrisine donusur
        ve kosul sayisi TAM OLARAK 1 olur; boylece bu sorun tamamen ortadan
        kalkar. Katsayilar ters DFT ile elde edilir.
        """
        N = deg + 1
        vals = [evalfn(gamma * mpmath.exp(2j * mpmath.pi * j / N)) for j in range(N)]
        out = []
        for m in range(N):
            acc = mpmath.mpc(0)
            for j in range(N):
                acc += vals[j] * mpmath.exp(-2j * mpmath.pi * j * m / N)
            out.append(acc / N / (gamma ** m))
        return out

    def _hp_solve_once(self, A_sym, z_sym, idx_out, dps, rank_tol):
        s = sp.symbols('s')
        A_r = self._hp_rationalize(A_sym)
        z_r = self._hp_rationalize(z_sym)
        n = A_r.shape[0]

        G = self._hp_mat(A_r.subs(s, 0))
        C = self._hp_mat(sp.diff(A_r, s).subs(s, 0))
        B = self._hp_mat(z_r.subs(s, 0))
        co = sp.zeros(1, n)
        co[0, idx_out] = 1
        Cout = self._hp_mat(co)

        red = self._hp_dae_reduce(G, C, B, Cout, mpmath.mpf(rank_tol))
        if red is None:
            return None
        Gt, Ct, Bt, Cto, Dt = red
        nt = Gt.rows

        # Indirgemeden sonra C~ TERSINIRDIR, yani problem STANDART ozdeger
        # problemine doner: s = eig(-C~^-1 G~). mpmath'ta genellestirilmis
        # (QZ) cozucu yok ama standart cozucu (mp.eig) var; bu yuzden
        # polinom katsayisi cikarmaya hic gerek kalmaz.
        E, _ = mpmath.mp.eig(-(Ct ** -1) * Gt)
        poles = list(E)

        # Sifirlar: indirgenmis koordinatlarda Rosenbrock determinanti.
        gam = mpmath.mpf(max([abs(p) for p in poles] + [mpmath.mpf(1)]))

        def rosen_det(sv):
            P = mpmath.matrix(nt + 1, nt + 1)
            for i in range(nt):
                for j in range(nt):
                    P[i, j] = Gt[i, j] + sv * Ct[i, j]
                P[i, nt] = -Bt[i, 0]
                P[nt, i] = Cto[0, i]
            P[nt, nt] = Dt[0, 0]
            return mpmath.det(P)

        coeffs = self._hp_poly_on_circle(rosen_det, nt, gam)
        mx = max((abs(c) for c in coeffs), default=mpmath.mpf(0))
        while len(coeffs) > 1 and abs(coeffs[-1]) < mx * mpmath.mpf('1e-25'):
            coeffs.pop()
        if len(coeffs) > 1:
            zeros = list(mpmath.polyroots(list(reversed(coeffs)),
                                          maxsteps=500, extraprec=40 * dps))
        else:
            zeros = []
        return poles, zeros

    def _calculate_high_precision_roots(self, A_sym, z_sym, idx_out,
                                        dps=50, rank_tol='1e-12', verify=True):
        """Keyfi hassasiyetli (bignum) kutup/sifir cozucusu.

        scipy.linalg HIC kullanilmaz. Basarisizlikta None doner; cagiran taraf
        float64 QZ yoluna geri duser.

        `verify=True` iken hesap dps ve 2*dps'te iki kez yapilir ve sonuclar
        karsilastirilir. Bunun sebebi olculmustur: sifir yolu (determinant
        tabanli) bu devrelerde ~28 HANE kaybediyor - dps=30'da sifirlarin
        bagil hatasi 1.5e-2 iken dps=50'de 1.8e-12, dps=80'de 1.6e-27 oluyor.
        Yani tek bir sabit dps degeri her devre icin guvenli DEGILDIR; iki
        kosum uyusmazsa hassasiyet yetersizdir ve uyari verilir.
        (Kutup yolu ozdeger tabanli oldugu icin bu kayiptan etkilenmiyor.)
        """
        old_dps = mpmath.mp.dps
        try:
            mpmath.mp.dps = dps
            first = self._hp_solve_once(A_sym, z_sym, idx_out, dps, rank_tol)
            if first is None:
                print("[Bignum] DAE indirgeme basarisiz (yuksek indeks olabilir); "
                      "float64 QZ yoluna donuluyor.", flush=True)
                return None

            if verify:
                mpmath.mp.dps = 2 * dps
                second = self._hp_solve_once(A_sym, z_sym, idx_out, 2 * dps, rank_tol)
                if second is not None:
                    worst = 0.0
                    for a_list, b_list in zip(first, second):
                        if len(a_list) != len(b_list):
                            worst = float('inf')
                            break
                        rem = list(range(len(a_list)))
                        for b in b_list:
                            j = min(rem, key=lambda i: abs(a_list[i] - b))
                            rem.remove(j)
                            denom = max(mpmath.mpf(1), abs(b))
                            worst = max(worst, float(abs(a_list[j] - b) / denom))
                    if worst > 1e-20:
                        print(f"[Bignum] dps={dps} bu devre icin YETERSIZDI "
                              f"(dps={2*dps} ile {worst:.2e} bagil fark). "
                              f"dps={2*dps} sonucu kullaniliyor; daha da emin olmak "
                              f"icin dps degerini artirip tekrar calistirin.",
                              flush=True)
                    else:
                        print(f"[Bignum] dps={dps} ve dps={2*dps} uyusuyor "
                              f"(bagil fark {worst:.2e}) - sonuc yakinsamis.",
                              flush=True)
                    first = second

            poles, zeros = first
            # float64'e indirgeme SADECE burada, GUI uyumlulugu icin.
            key = lambda v: (abs(v), v.real, v.imag)
            return {"zeros": sorted([complex(z) for z in zeros], key=key),
                    "poles": sorted([complex(p) for p in poles], key=key)}
        except Exception as e:
            print(f"[Bignum] Hata: {e} -- float64 QZ yoluna donuluyor.", flush=True)
            return None
        finally:
            mpmath.mp.dps = old_dps


    def _resolve_output_node(self, mna_data):
        """Cikis dugumunu belirler ve combo'yu mevcut bilinmeyenlerle doldurur.

        Bu eskiden `target_node = "V_2"` seklinde SABIT KODLUYDU. Genel amacli
        bir arac icin bu bir hatadir: KUTUPLAR cikis dugumunden bagimsizdir ama
        SIFIRLAR dogrudan ona baglidir. Yanlis dugum secilirse sifirlar baska
        bir transfer fonksiyonuna ait cikar ve baska bir aracla karsilastirma
        anlamsizlasir.

        Teshis ipucu: dogru cikis dugumunde, kuplaj kondansatoru iceren bir
        yukseltecte ORIJINDE sifir(lar) beklenir (DC'de kuplaj kondansatoru
        sinyali bloklar). Sifirlarin bir kismi KUTUPLARLA cakisiyorsa ve
        orijinde hic sifir yoksa, secili dugum buyuk olasilikla sinyal
        yolunun disinda (or. kaynak dugumu) kalmistir.
        """
        try:
            names = [str(u) for u in mna_data.get_unknowns()]
        except Exception as e:
            print(f"Bilinmeyenler okunamadi: {e}", flush=True)
            return None

        if self.output_node_tag and dpg.does_item_exist(self.output_node_tag):
            dpg.configure_item(self.output_node_tag, items=names)
            current = dpg.get_value(self.output_node_tag)
        else:
            current = ""

        if current in names:
            return current

        chosen = names[-1] if names else None
        if self.output_node_tag and dpg.does_item_exist(self.output_node_tag) and chosen:
            dpg.set_value(self.output_node_tag, chosen)
        print(f"Cikis dugumu secilmemisti; gecici olarak '{chosen}' kullaniliyor.",
              flush=True)
        print(f"Mevcut dugumler: {names}", flush=True)
        print("Karsilastirma yapiyorsaniz, referans araciyla AYNI dugumu secin.",
              flush=True)
        return chosen

    def _calculate_robust_poles_zeros(self, mna_data, unknown_variable: str):
        """
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
    # Sembolik cozum: H(s) = det(A_out(s)) / det(A(s)) tam rasyonel olarak
    # ------------------------------------------------------------------
    def _to_exact(self, v):
        """float -> tam rasyonel (yazdirilan basamak kadar kesin)."""
        f = float(v)
        if f != f or f in (float("inf"), float("-inf")):
            raise ValueError(f"deger sonlu degil: {v!r}")
        try:
            return sp.Rational(repr(f))
        except (ValueError, TypeError):
            return sp.nsimplify(f, rational=True)

    def _roots_of_exact_poly(self, poly, s):
        """Tam katsayili polinomun kokleri. s=0 kokleri TAM; gerisi 25 basamak."""
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

        vd = {k: self._to_exact(v) for k, v in mna_data.value_dict.items()}
        A = sp.Matrix(mna_data.A.subs(vd))
        z = sp.Matrix(mna_data.z.subs(vd))
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

        D = sp.expand(A.det(method="berkowitz"))
        N = sp.expand(A_out.det(method="berkowitz"))

        if D == 0 or D.has(sp.nan, sp.zoo, sp.oo) or N.has(sp.nan, sp.zoo, sp.oo):
            raise ValueError("sembolik determinant tekil / tanimsiz "
                             "(D=0 veya nan) - sayisal yola donuluyor")

        # ortak (s-bagimli) carpanlari sadelestir
        H = sp.cancel(sp.together(N / D))
        N2, D2 = sp.fraction(H)

        p_poly = sp.Poly(sp.expand(D2), s)
        z_poly = sp.Poly(sp.expand(N2), s)

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
        """H(s)'i carpanlarina ayrilmis, okunabilir biçimde yazar:
           H(s) = K * s^2 (s + a)(s^2 + b s + c) / [ (s + p1)(s + p2) ... ]
        Sembolik yolun s=0 kokleri TAM 0 oldugu icin s^k carpani net gorunur."""
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
        """Girdi pininden gelen ham veriyi ('(log_space, mna)' tuple'i, MNA
        node objesi, ya da dogrudan bir Circuit) A/z matrisleri olan bir MNA
        nesnesine cevirir. Bulunamazsa None."""
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

    def _populate_output_nodes(self, mna_data):
        """Cikis dugumu combo'sunu MNA'nin bilinmeyenleriyle doldurur."""
        if not (self.output_node_tag and dpg.does_item_exist(self.output_node_tag)):
            return
        try:
            names = [str(u) for u in mna_data.get_unknowns()]
        except Exception:
            return
        current = dpg.get_value(self.output_node_tag)
        dpg.configure_item(self.output_node_tag, items=names)
        if current not in names and names:
            pref = [n for n in names if n.lower().lstrip("v_").startswith(
                ("out", "vout", "ua", "aus"))]
            dpg.set_value(self.output_node_tag, pref[0] if pref else names[-1])

    def onlink_callback(self):
        # MNA (veya Circuit) baglaninca / hesaplaninca cikis dugumu listesini
        # simdiden doldur ki kullanici 'Calculate' oncesi secebilsin.
        try:
            mna_data = self._extract_mna(self.get_input_pin_value("mna_pin"))
            if mna_data is not None:
                self._populate_output_nodes(mna_data)
        except Exception as e:
            print(f"Cikis dugumu listesi doldurulamadi: {e}", flush=True)
        super().onlink_callback()

    def calculate_callback(self, sender, app_data, user_data=None):
        raw = self.get_input_pin_value("mna_pin")

        print("\n--- POLE/ZERO HESAPLAMA TETİKLENDİ ---", flush=True)
        print(f"Kablodan Gelen İlk Veri Tipi: {type(raw)}", flush=True)

        try:
            mna_data = self._extract_mna(raw)
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
            print(f"Hedef düğüm ({target_node}) için hesaplama yapılıyor...", flush=True)
            
            exact_mode = (dpg.get_value(self.exact_mode_tag)
                          if self.exact_mode_tag and dpg.does_item_exist(self.exact_mode_tag)
                          else False)
            symbolic_mode = (dpg.get_value(self.symbolic_mode_tag)
                             if self.symbolic_mode_tag and dpg.does_item_exist(self.symbolic_mode_tag)
                             else False)

            pz_results = None
            if symbolic_mode:
                print("Symbolic Solve secili; H(s) tam rasyonel olarak "
                      "cozuluyor (buyuk devrelerde yavas olabilir)...", flush=True)
                try:
                    pz_results = self._calculate_symbolic_poles_zeros(
                        mna_data, target_node)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    print(f"Sembolik cozum basarisiz ({e}); sayisal QZ yoluna "
                          f"donuluyor.", flush=True)

            if pz_results is None and exact_mode:
                print("Exact Precision Calculation (mpmath) secili; bignum yolu "
                      "deneniyor...", flush=True)
                s_sym = sp.symbols('s')
                A_sym = mna_data.A.subs(mna_data.value_dict)
                z_sym = mna_data.z.subs(mna_data.value_dict)
                x_syms = [str(u) for u in mna_data.get_unknowns()]
                if target_node in x_syms:
                    pz_results = self._calculate_high_precision_roots(
                        A_sym, z_sym, x_syms.index(target_node))
                else:
                    print(f"Hata: '{target_node}' bilinmeyenler arasinda yok.", flush=True)

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