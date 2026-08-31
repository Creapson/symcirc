"""
mna_inspect.py -- symcirc MNA matrisi denetleyicisi

NEDEN: Kutup/sifir farkinin cozucude olmadigi kanitlandiktan sonra geriye tek
olasilik kalir: A(s) matrisi farkli. Bu arac, matrisi baska bir araca (or.
Analog Insydes) karsi SATIR SATIR karsilastirilabilir hale getirir.

Surekli farkli BJT'lerle calisiyorsaniz asil kontrol noktasi burasidir:
model kutuphaneniz yanlissa her devre yanlis cikar, cozucu ne kadar iyi olursa
olsun.

KULLANIM
    from tools.mna_inspect import inspect_mna
    inspect_mna(mna_data)                    # tam rapor
    inspect_mna(mna_data, symbolic=True)     # deger yerlestirmeden, sembolik
"""

import numpy as np
import sympy as sp


def inspect_mna(mna_data, symbolic=False, max_print=14):
    s = sp.symbols('s')
    names = [str(u) for u in mna_data.get_unknowns()]
    n = len(names)

    A = mna_data.A if symbolic else mna_data.A.subs(mna_data.value_dict)
    z = mna_data.z if symbolic else mna_data.z.subs(mna_data.value_dict)

    print("=" * 76)
    print(f"MNA SISTEMI  n = {n}")
    print("=" * 76)
    print("Bilinmeyenler:", ", ".join(f"[{i}] {v}" for i, v in enumerate(names)))

    if symbolic:
        print("\nA(s) (sembolik):")
        sp.pprint(A)
        print("\nz(s) (sembolik):")
        sp.pprint(z.T)
        return

    free = A.free_symbols - {s}
    if free:
        print(f"\n!! COZULMEMIS SEMBOLLER: {sorted(free, key=str)}")
        print("   value_dict eksik - asagidaki sayisal rapor guvenilir degil.")
        return

    G = np.array(A.subs(s, 0), dtype=complex)
    C = np.array(sp.diff(A, s).subs(s, 0), dtype=complex)

    print("\n" + "-" * 76)
    print("C_dyn (REAKTIF eleman matrisi) -- sifirdan farkli girdiler")
    print("-" * 76)
    print("Bunlar devrenizdeki kapasiteleri (ve endüktans katkilarini) gosterir.")
    print("Referans aracin netlist genislemesiyle BIRE BIR ayni olmalidir.\n")
    ent = [(i, j, C[i, j]) for i in range(n) for j in range(n) if C[i, j] != 0]
    if not ent:
        print("   (bos - hic reaktif eleman yok?)")
    for i, j, v in ent[:max_print * 2]:
        kind = "kosegen" if i == j else "capraz "
        print(f"   C[{names[i]:>6},{names[j]:>6}] {kind} = {v.real:+.6e}")
    if len(ent) > max_print * 2:
        print(f"   ... ({len(ent) - max_print*2} girdi daha)")

    print("\n" + "-" * 76)
    print("DUGUM BASINA TOPLAM KAPASITE (toprak dahil)")
    print("-" * 76)
    print("Bir dugumun satir toplami sifirsa, o dugumdeki kondansatorlerin")
    print("TOPRAKLA baglantisi yoktur (yuzen kondansator agi).\n")
    for i in range(n):
        rs = C[i, :].sum().real
        tag = "  <- toprakla bagi yok" if abs(rs) < 1e-18 * max(1.0, abs(C[i, i])) else ""
        print(f"   {names[i]:>8}: kosegen {C[i,i].real:+.4e}   satir toplami {rs:+.4e}{tag}")

    print("\n" + "-" * 76)
    print("YAPISAL OZET")
    print("-" * 76)
    rk = np.linalg.matrix_rank(C)
    print(f"   rank(C_dyn) = {rk} / {n}   -> {rk} sonlu kutup beklenir")
    print(f"   cond(G)     = {np.linalg.cond(G):.4e}")
    nzC = C[C != 0]
    if nzC.size:
        print(f"   |C| araligi = {np.min(np.abs(nzC)):.3e} .. {np.max(np.abs(nzC)):.3e}"
              f"  ({np.max(np.abs(nzC))/np.min(np.abs(nzC)):.2e}x)")
    print(f"   z vektoru s'e bagli mi: {'EVET' if z.has(s) else 'hayir'}")
    nzz = [(i, z[i, 0]) for i in range(n) if z[i, 0] != 0]
    print(f"   kaynak girdileri: " +
          (", ".join(f"{names[i]}={complex(v).real:+.3e}" for i, v in nzz) or "(yok)"))

    print("\n" + "-" * 76)
    print("ASIMETRIK G GIRDILERI (kontrollu kaynaklar: gm, mu, ...)")
    print("-" * 76)
    print("BJT kucuk-sinyal modelinizin gm damgasi burada gorunur.\n")
    asym = [(i, j, G[i, j], G[j, i]) for i in range(n) for j in range(i + 1, n)
            if abs(G[i, j] - G[j, i]) > 1e-15 * max(1.0, abs(G[i, j]))]
    if not asym:
        print("   (yok - kontrollu kaynak damgasi bulunamadi)")
    for i, j, a, b in asym[:max_print]:
        print(f"   G[{names[i]:>6},{names[j]:>6}] = {a.real:+.6e}   "
              f"G[{names[j]:>6},{names[i]:>6}] = {b.real:+.6e}   "
              f"fark = {(a-b).real:+.6e}")

    print("\n" + "=" * 76)
    print("KARSILASTIRMA KONTROL LISTESI")
    print("=" * 76)
    print("  1. Referans aracta hangi BJT model SEVIYESI secili? (Analog Insydes")
    print("     BJT icin uc ayri sadelestirme seviyesi sunuyor.)")
    print("  2. C_jc, C_je degerleri iki tarafta ayni mi? Yuksek frekans")
    print("     kutuplarini TAM OLARAK bunlar belirler.")
    print("  3. Referans model r_b (baz yayilma direnci), r_o (Early), C_cs")
    print("     (kollektor-substrat) iceriyor mu? Sizinki iceriyor mu?")
    print("  4. Kaynak direnci ve kuplaj kondansatorleri ayni mi?")
    print("  5. Cikis dugumu iki tarafta AYNI mi? (sifirlar buna baglidir)")
    print("=" * 76)


def check_index_mapping(mna_data):
    """get_unknowns() SIRASI ile A matrisinin SUTUN SIRASI ayni mi?

    Neden onemli: idx_out = get_unknowns().index(dugum) ile bulunuyor ve bu
    indeks Cramer/Rosenbrock'ta HANGI SUTUNUN degistirilecegini belirliyor.
    Sira uyusmazsa KUTUPLAR DOGRU KALIR (det permutasyona duyarsizdir) ama
    SIFIRLAR yanlis cikar. Yani "kutuplar tutuyor, sifirlar tutmuyor"
    tablosunun sebeplerinden biri tam olarak budur.

    Test: MNA'da bir dal akimi bilinmeyeni I_X'in SATIRI, gerilim kaynagi
    kisitidir; girdileri +/-1 (ve 0) olmalidir - iletkenlik degeri ICERMEZ.
    Dugum gerilimi satirlari ise tam tersi. Bu ayrim mekanik olarak
    kontrol edilebilir.
    """
    s = sp.symbols('s')
    names = [str(u) for u in mna_data.get_unknowns()]
    A = mna_data.A.subs(mna_data.value_dict)
    G = np.array(A.subs(s, 0), dtype=complex)
    n = len(names)

    print("=" * 76)
    print("INDEKS ESLEME TUTARLILIK TESTI")
    print("=" * 76)
    if G.shape[0] != n:
        print(f"!! BOYUT UYUSMAZLIGI: A {G.shape[0]}x{G.shape[1]}, "
              f"get_unknowns() {n} eleman. Bu tek basina bir hatadir.")
        return False

    ok = True
    for i, nm in enumerate(names):
        row = G[i, :]
        nz = row[row != 0]
        if nz.size == 0:
            continue
        looks_pm1 = bool(np.all(np.isclose(np.abs(nz), 1.0, rtol=1e-9)))
        is_current = nm.startswith("I_")
        if is_current and not looks_pm1:
            print(f"  !! {nm:<26} dal akimi ama satiri +/-1 DEGIL "
                  f"(maks |girdi| = {np.max(np.abs(nz)):.3e})")
            ok = False
        elif (not is_current) and looks_pm1 and nz.size <= 2:
            print(f"  ?  {nm:<26} dugum gerilimi ama satiri +/-1 gibi "
                  f"gorunuyor - siralama kaymis olabilir")
            ok = False

    if ok:
        print("  Tum satirlar beklenen tipte. Siralama TUTARLI gorunuyor.")
        print("  (Yine de kesin kanit degil; asagidaki kaynak testi de bakin.)")
    print()
    z = mna_data.z.subs(mna_data.value_dict)
    zn = np.array(z.subs(s, 0), dtype=complex).ravel()
    nzi = [i for i in range(n) if zn[i] != 0]
    print("  z vektorunde sifirdan farkli satirlar:")
    for i in nzi:
        kind = "dal akimi (BEKLENEN: gerilim kaynagi)" if names[i].startswith("I_") \
               else "dugum gerilimi (BEKLENEN: akim kaynagi)"
        print(f"     [{i}] {names[i]:<26} = {zn[i].real:+.4e}   {kind}")
    if not nzi:
        print("     (yok - kaynak vektoru bos?)")
    print("=" * 76)
    return ok


def junction_caps(mna_data, device_hint="Q"):
    """Transistor ic dugumlerine dokunan kapasiteleri ayikla ve listele.

    Yuksek frekans kutuplarini TAM OLARAK bu degerler belirler. Referans
    aracin ayni transistor icin kullandigi degerlerle bire bir
    karsilastirilmalidir.

    DIKKAT (siklikla atlanan iki nokta):
      * C_pi = C_je(deplesyon) + C_diff,  C_diff = TF * gm
        2N2222 icin TF ~ 0.4 ns, gm ~ 0.04 S  ->  C_diff ~ 16 pF,
        yani deplesyon terimiyle AYNI MERTEBEDE. Difuzyon terimi
        atlanirsa yuksek frekans kutuplari ciddi kayar.
      * Jonksiyon kapasiteleri BIAS'A BAGLIDIR:
        C_jc(V) = CJC / (1 + V_CB/VJC)^MJC
        Sifir-bias CJC degerini dogrudan kullanmak, V_CB=5V'ta yaklasik
        2 kat hata verir.
    Iki arac bu iki noktadan birinde ayrilirsa, DUSUK frekans sonuclari
    birebir tutar ama YUKSEK frekans kutup/sifirlari ayrisir.
    """
    s = sp.symbols('s')
    names = [str(u) for u in mna_data.get_unknowns()]
    C = np.array(sp.diff(mna_data.A.subs(mna_data.value_dict), s).subs(s, 0),
                 dtype=complex)
    n = len(names)
    dev = [i for i, nm in enumerate(names) if device_hint in nm]

    print("=" * 76)
    print("CIHAZ IC DUGUMLERINE DOKUNAN KAPASITELER")
    print("=" * 76)
    if not dev:
        print(f"  '{device_hint}' iceren bilinmeyen bulunamadi.")
    else:
        print("  Cihaz ic dugumleri:", [names[i] for i in dev])
    print()
    seen = set()
    for i in range(n):
        for j in range(i + 1, n):
            if C[i, j] == 0:
                continue
            if i in dev or j in dev:
                key = (i, j)
                if key in seen:
                    continue
                seen.add(key)
                print(f"   {names[i]:>28} -- {names[j]:<28} C = {abs(C[i,j].real):.6e} F"
                      f"  ({abs(C[i,j].real)*1e12:.3f} pF)")
    print()
    print("  TUM capraz kapasiteler (buyukten kucuge):")
    allc = sorted([(abs(C[i, j].real), i, j) for i in range(n) for j in range(i + 1, n)
                   if C[i, j] != 0], reverse=True)
    for v, i, j in allc[:12]:
        print(f"   {v:.6e} F  ({v*1e12:>12.3f} pF)   {names[i]} -- {names[j]}")
    print("=" * 76)