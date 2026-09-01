from __future__ import annotations
from typing import Dict, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict
import os
from pathlib import Path

if TYPE_CHECKING:
    from netlist.Circuit import Circuit


class Model(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = ""
    type: str = ""
    filename: str = ""
    params: Dict[str, str] = {} 

    def add_param(self, paramSymbol: str, value):
        self.params[paramSymbol] = value

    def get_generated_subcircuit(
        self,
        element_params: Dict[str, str],
        bipolar_model: str,
        mosfet_model: str,
        element_type: str = "",
    ) -> Circuit | None:
        # Merge model params and element params
        param_list = {k.lower(): v for k, v in (self.params | element_params).items()}

        # [TR] Transistoru kucuk-sinyal esdegeriyle degistirmeden once, sembol
        #      -> deger sozlugunu Analog Insydes'in yaptigi gibi hazirla: gate
        #      kapasitesi = bias + ortusme terimi, cikis elemani = 1/g_ds,
        #      parazitik RC/RE/RD/RS model kartindan, vb. Boylece JSON sablonu
        #      ince kalir ve sayilar AI ile birebir cikar.
        # [EN] Before the transistor is replaced by its small-signal equivalent,
        #      resolve the symbol -> value map the way Analog Insydes does: gate
        #      cap = bias + overlap term, output element = 1/g_ds, parasitic
        #      RC/RE/RD/RS from the model card, etc. This keeps the JSON template
        #      thin and makes the numbers match AI term for term.
        if self.type in ("MOS", "NMOS") or element_type == "M":
            param_list = self._mosfet_ac_param_values(param_list)
        elif self.type in ("NPN", "PNP") or element_type == "Q":
            param_list = self._bjt_ac_param_values(param_list)

        from netlist.Circuit import Circuit

        current_file_dir = Path(__file__).resolve().parent
        project_root = current_file_dir.parent

        # 3. Choose correct small signal model library sub-path.
        # Fall back to the element kind ("Q" = bipolar, "M" = mosfet) when the
        # .model card type is unknown - e.g. the model lives in an external
        # .lib we cannot read, but the .out still carries the small-signal params.
        if self.type in ("NPN", "PNP") or element_type == "Q":
            sub_path = Path("library/small_signal_models/bipolar_models") / f"{bipolar_model}.json"
        elif self.type in ("MOS", "NMOS") or element_type == "M":
            sub_path = Path("library/small_signal_models/mosfet_models") / f"{mosfet_model}.json"
        else:
            print(f"Failed to load model! Type: {self.type} is not known!")
            return None

        # target_model = project_root / sub_path
        target_model = sub_path

        # load small signal model from library
        with open(target_model, "r", encoding="utf-8") as f:
            json_string = f.read()
        circuit = Circuit.model_validate_json(json_string)

        # replace the str in the value slot with the numeric values
        for element in circuit.elements:
            element.remap_values(param_list)

        # [TR] DEJENERASYON TEMIZLEME. Kucuk-sinyal sablonlari cogu zaman .OP
        #      bolumunun hic yazmadigi (rc, gmu, cxs, ...) ya da 0 verdigi
        #      (cbx, cjs) parametrelere atifta bulunur. Degeri sayiya
        #      cozulmemis - ya da 0 cozulmus - her eleman bu calisma
        #      noktasinda ihmal edilebilir:
        #        * kondansator             -> acik devre -> at
        #        * kontrollu kaynak        -> at
        #        * seri direnc  (port <-> ic dugum)  -> kisa devre: dugumleri birlestir
        #        * paralel/sizinti direnc (ic <-> ic) -> acik devre -> at
        #      Butun kararlar *orijinal* sablon topolojisinden alinip topluca
        #      uygulanir; boylece bir birlestirme baska bir elemani yanlis
        #      siniflandirtamaz.
        # [EN] DEGENERACY CLEANUP. Small-signal templates often reference
        #      parameters the PSpice .OP section does not emit (rc, gmu, cxs,
        #      ...) or reports as 0 (cbx, cjs). Any element whose value did not
        #      resolve to a number - or resolved to 0 - is negligible for this
        #      operating point:
        #        * capacitor           -> open  -> drop
        #        * controlled source   -> drop
        #        * series resistor     (port <-> internal node) -> short: merge nodes
        #        * shunt/leak resistor (internal <-> internal)   -> open  -> drop
        #      All decisions are taken from the *original* template topology and
        #      then applied together, so one merge cannot make another element
        #      look like something it is not.
        inner = set(circuit.inner_connecting_nodes)

        def _num(v):
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        merges: Dict[str, str] = {}
        survivors = []
        for element in circuit.elements:
            vkey = "value" if element.type in ("E", "G", "F", "H") else "value_dc"
            val = _num(element.params.get(vkey))
            if val is not None and val != 0.0:
                survivors.append(element)
                continue
            if element.type == "R" and len(element.connections) == 2:
                a, b = element.connections
                a_port, b_port = a in inner, b in inner
                if a_port != b_port:                      # series R -> short
                    drop_n, keep_n = (a, b) if not a_port else (b, a)
                    merges[drop_n] = keep_n
                # else: shunt/leak R (internal<->internal) -> just drop

        def canon(node: str) -> str:
            seen = set()
            while node in merges and node not in seen:
                seen.add(node)
                node = merges[node]
            return node

        for element in survivors:
            element.connections = [canon(n) for n in element.connections]
        circuit.elements = survivors
        return circuit

    @staticmethod
    def _num_or_none(value):
        """[TR] Degeri float'a cevirir; cevrilemezse veya sonlu degilse
               (nan / +-inf) None doner. AI formullerinde "parametre var mi
               ve gecerli bir sayi mi?" kontrolu icin kullanilir.
        [EN] Convert a value to float; return None if it cannot be parsed or
             is not finite (nan / +-inf). Used by the AI-style formulas to ask
             "is this parameter present and a usable number?".
        """
        try:
            f = float(value)
        except (TypeError, ValueError):
            return None
        return f if f == f and f not in (float("inf"), float("-inf")) else None

    @classmethod
    def _bjt_ac_param_values(cls, param_list: Dict[str, str]) -> Dict[str, str]:
        """[TR] BJT kucuk-sinyal sembollerini Analog Insydes'in
               `DoBJTSmallSignal` (AC, Level 1) fonksiyonuyla ayni sekilde cozer.

               ModelSupport.m'e gore:
                 * RPI$ac, RO$ac, RX$ac, CBC$ac, CBE$ac, CBX$ac, CJS$ac, GM$ac
                   dogrudan OPERATING POINT bolumunden gelir (isimler zaten dogru)
                 * taban-kollektor sizinti elemani GMU bir iletkenliktir ->
                   1/GMU$ac olarak saklanir
                 * ohmik RC/RE model kartindan gelir, AREA'ya bolunur:
                   Rc = RC/AREA,  Re = RE/AREA
               Yalniz sonlu ve sifirdan farkli sonuclar yazilir; gerisini
               dejenerasyon temizleme acar/kisaltir, yani RC/RE/RX/GMU
               Basic ve Simplified seviyelerinde `DoBJTSmallSignal`'daki
               simp==1 / simp==2 kurallarindaki gibi kaybolur.

        [EN] Resolve the BJT small-signal symbols the way Analog Insydes'
             `DoBJTSmallSignal` (AC, Level 1) does.

             Per ModelSupport.m:
               * RPI$ac, RO$ac, RX$ac, CBC$ac, CBE$ac, CBX$ac, CJS$ac, GM$ac
                 come straight from the OPERATING POINT block (right names)
               * the base-collector leak GMU is a conductance -> store 1/GMU$ac
               * the ohmic RC/RE come from the model card, divided by AREA:
                 Rc = RC/AREA,  Re = RE/AREA
             Only finite non-zero results are written; the degeneracy cleanup
             opens or shorts everything else, so RC/RE/RX/GMU vanish for the
             Basic and Simplified levels exactly as the simp==1 / simp==2
             rules in `DoBJTSmallSignal` prescribe.
        """
        p = dict(param_list)
        num = cls._num_or_none

        # [TR] AREA yoksa 1 (birim alan). [EN] AREA defaults to 1 (unit area).
        area = num(p.get("area")) or 1.0

        # [TR] GMU bir iletkenlik -> direnc olarak 1/GMU. Cogu PSpice .out'unda
        #      GMU yoktur, o zaman GMU elemani zaten dusurulur.
        # [EN] GMU is a conductance -> store it as the resistance 1/GMU. Most
        #      PSpice .out files have no GMU, in which case the element is dropped.
        gmu = num(p.get("gmu$ac"))
        if gmu is None:
            gmu = num(p.get("gmu"))
        if gmu:
            p["gmu"] = repr(1.0 / gmu)

        # [TR] Ohmik taban/kollektor/emiter parazitikleri model kartindan,
        #      AREA'ya bolunmus. [EN] Ohmic base/collector/emitter parasitics
        #      from the model card, divided by AREA.
        rc = num(p.get("rc"))
        if rc:
            p["rc"] = repr(rc / area)
        re_ = num(p.get("re"))
        if re_:
            p["re"] = repr(re_ / area)

        return p

    @staticmethod
    def _mosfet_ac_param_values(param_list: Dict[str, str]) -> Dict[str, str]:
        """[TR] MOSFET kucuk-sinyal sembollerini Analog Insydes'in
               `DoMOSFETSmallSignal` (AC, Level 1-3) fonksiyonuyla ayni sekilde
               cozer; boylece JSON sablonlari ince kalir ve sayilar birebir cikar.

               ModelSupport.m'e gore:
                 * kapi (gate) kapasiteleri bias terimi ile ortusme (overlap)
                   teriminin TOPLAMIDIR:
                   Cgd = CGD$ac + CGDOV$ac,  Cgs = CGS$ac + CGSOV$ac,
                   Cgb = CGB$ac + CGBOV$ac
                 * drain-source elemani kucuk-sinyal iletkenligi GDS$ac'dir
                   (sablonumuz onu direnc olarak modelledigi icin 1/GDS$ac saklanir)
                 * ohmik RD/RS model kartindan; ikisi de 0 ise tabaka
                   direncinden turetilebilir:  RD = NRD*RSH,  RS = NRS*RSH
               Yalniz sonlu ve sifirdan farkli sonuclar yazilir; gerisi
               dokunulmadan birakilir, dejenerasyon temizleme onu acar/kisaltir.

        [EN] Resolve the MOSFET small-signal symbols the way Analog Insydes'
             `DoMOSFETSmallSignal` (AC, Level 1-3) does, so the JSON templates
             stay thin and the numbers come out identical.

             Per ModelSupport.m:
               * gate caps are the SUM of the bias term and the overlap term:
                 Cgd = CGD$ac + CGDOV$ac,  Cgs = CGS$ac + CGSOV$ac,
                 Cgb = CGB$ac + CGBOV$ac
               * the drain-source element is the small-signal conductance GDS$ac
                 (our template models it as a resistor, so store 1/GDS$ac)
               * ohmic RD/RS come from the model card; if both are 0 they may be
                 derived from the sheet resistance:  RD = NRD*RSH,  RS = NRS*RSH
             Only keys that resolve to a finite non-zero value are written;
             anything else is left untouched so the degeneracy cleanup
             opens / shorts it.
        """
        p = dict(param_list)

        def num(key):
            # [TR] p[key]'i float'a cevir, olmazsa None.
            # [EN] parse p[key] to float, else None.
            try:
                return float(p[key])
            except (KeyError, ValueError, TypeError):
                return None

        def put(key, value):
            # [TR] Sonuc sonlu ve sifirdan farkliysa sozluge yaz; degilse
            #      dokunma - boylece ilgili eleman temizleme adiminda dususur.
            # [EN] Write the result into the map only if it is finite and
            #      non-zero; otherwise leave it, so the element is dropped by
            #      the cleanup step.
            if value is not None and value == value and value not in (
                    float("inf"), float("-inf")) and value != 0.0:
                p[key] = repr(value)

        # [TR] Kapi kapasiteleri: bias + ortusme toplami.
        # [EN] Gate caps: bias + overlap term, summed.
        cgd = (num("cgd") or 0.0) + (num("cgdov") or 0.0)
        cgs = (num("cgs") or 0.0) + (num("cgsov") or 0.0)
        cgb = (num("cgb") or 0.0) + (num("cgbov") or 0.0)
        put("cgd", cgd)
        put("cgs", cgs)
        put("cgb", cgb)

        # [TR] Drain-source iletkenligi -> direnc 1/GDS. [EN] D-S conductance
        #      -> resistance 1/GDS.
        gds = num("gds")
        if gds:
            put("rds", 1.0 / gds)

        # [TR] Bulk-junction sizinti iletkenlikleri -> direnc. [EN] Bulk-junction
        #      leak conductances -> resistance.
        gbd, gbs = num("gbd"), num("gbs")
        if gbd:
            put("rbd", 1.0 / gbd)
        if gbs:
            put("rbs", 1.0 / gbs)

        # [TR] Ohmik RD/RS model kartindan; ikisi de 0 ise tabaka direncinden.
        # [EN] Ohmic RD/RS from the model card; if both 0, from sheet resistance.
        rd = num("rd") or 0.0
        rs = num("rs") or 0.0
        if rd == 0.0 and rs == 0.0:
            nrd, nrs, rsh = num("nrd") or 0.0, num("nrs") or 0.0, num("rsh") or 0.0
            if nrd > 0.0:
                rd = nrd * rsh
            if nrs > 0.0:
                rs = nrs * rsh
        put("rd", rd)
        put("rs", rs)

        return p

    def to_ai_string(self, indent: int):
        param_string = ", ".join(f'"{k}" -> {v}' for k, v in self.params.items())
        print("\t" * indent, self.name, self.type, self.filename, param_string)
