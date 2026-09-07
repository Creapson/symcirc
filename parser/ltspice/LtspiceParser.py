from __future__ import annotations

from typing import Dict, List
from pathlib import Path
import os
import re

from netlist.Circuit import Circuit
from netlist.Element import Element
from netlist.Model import Model
import Pspice_util as pu


# Structurally mirrors parser/spice/SpiceParser.py (Line merge -> tokenize -> dispatch),
# adapted for LTspice's plain-text ".net" export. Differences from PSpice, confirmed
# against real LTspice-exported .net/.cir/.log files:
#   - comments start with "*" OR ";" (SpiceParser only strips "*")
#   - no "* Schematics Netlist *" header, no split .cir/.net + separate .lib/.INC driver
#     file - LTspice's own .net export is (mostly) self-contained
#   - element ref-des is used as-is (e.g. "R1", "C1"), not the MicroSim "TYPE_REFDES"
#     duplication (e.g. "R_R1") that Element.remove_type_prefix() strips
#   - BJT (Q) lines carry an explicit 4th (substrate/bulk) node that PSpice's 3-terminal
#     dialect doesn't - see the note in _parse_element
#   - .net/.log files are commonly Latin-1, but .cir files hand-saved from Notepad have
#     shown up as UTF-16 - see _read_text_lines
#   - typically ends with ".backanno" / ".end" and may include ".tran"/".step"/".meas",
#     which are simply ignored (unhandled dot-directives), same as SpiceParser does today.
class LtspiceParser:
    def __init__(self, path: str = "") -> None:
        self._path = str(Path(path).resolve()) if path else ""
        self._raw_lines: List[str] = []
        self._libs: List[str] = []
        self.feedback: List[str] = []

        if self._path:
            try:
                self._raw_lines = self._read_text_lines(self._path)
            except (OSError, UnicodeDecodeError):
                self.feedback.append(f"Could not load file: {self._path}")
                print(f"Could not load file: {self._path}")

        self._add_includes()

        formatted_lines: List[str] = self._format_lines(self._raw_lines)
        self.lines: List[Line] = self._merge_lines(formatted_lines)

    @staticmethod
    def _read_text_lines(path: str) -> List[str]:
        """Reads a netlist/library file, tolerating the encodings seen in the wild:
        LTspice's own .net/.log output is typically Latin-1/ASCII, but a .cir/.lib
        file that's been hand-saved (e.g. from Notepad) can come back as UTF-16 -
        sometimes with a BOM, sometimes without one. Without a BOM, every other
        byte is a literal NUL for plain-ASCII content, which real SPICE netlists
        never contain - used as a heuristic below. Falls back to Latin-1, which
        never raises on arbitrary bytes.
        """
        with open(path, "rb") as f:
            raw = f.read()

        if raw.startswith(b"\xff\xfe"):
            return raw.decode("utf-16-le").splitlines(keepends=True)
        if raw.startswith(b"\xfe\xff"):
            return raw.decode("utf-16-be").splitlines(keepends=True)

        sample = raw[:400]
        if len(sample) >= 4:
            if sample[1::2].count(0) > len(sample[1::2]) * 0.6:
                return raw.decode("utf-16-le", errors="replace").splitlines(keepends=True)
            if sample[0::2].count(0) > len(sample[0::2]) * 0.6:
                return raw.decode("utf-16-be", errors="replace").splitlines(keepends=True)

        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        return text.splitlines(keepends=True)

    def _resolve_path(self, ref_path: str) -> str:
        if os.path.isabs(ref_path):
            return ref_path
        base_dir = os.path.dirname(self._path) if self._path else ""
        return os.path.join(base_dir, ref_path)

    def _add_includes(self):
        # Splices .inc/.include target files directly into the raw lines (so their
        # elements/models end up in whatever scope is active when _parse() reaches
        # that point); records .lib paths in self._libs to be mined for models/
        # subcircuits after the main parse (see the tail of _parse()), same split
        # SpiceParser._add_includes uses.
        idx = 0
        while idx < len(self._raw_lines):
            line = self._raw_lines[idx].strip()
            lower = line.lower()

            if lower.startswith(".inc") and line.split():
                directive_len = len(line.split()[0])
                inc_path = line[directive_len:].strip().strip('"')
                resolved = self._resolve_path(inc_path)
                try:
                    inc_lines = self._read_text_lines(resolved)
                    self._raw_lines = (
                        self._raw_lines[:idx] + inc_lines + self._raw_lines[idx + 1:]
                    )
                    continue  # re-scan from the same index: spliced-in lines may
                              # themselves contain includes.
                except (OSError, UnicodeDecodeError):
                    self.feedback.append(f"Could not load include: {resolved}")

            elif lower.startswith(".lib") and line.split():
                directive_len = len(line.split()[0])
                lib_path = line[directive_len:].strip().strip('"')
                self._libs.append(self._resolve_path(lib_path))

            idx += 1

    def _format_lines(self, raw_lines: List[str]) -> List[str]:
        lines: List[str] = []
        for idx, line in enumerate(raw_lines):
            if idx == 0:                      
                continue
            line = line.split(";", 1)[0]      
            stripped = line.strip()
            if not stripped or stripped.startswith("*"):
                continue
            first = stripped.lower().split(None, 1)[0]
            if first == ".end":          # ".ends" değil, tam ".end"
                break                          # .end sonrası her şey yok sayılır
            lines.append(stripped)
        return lines
        

    def _merge_lines(self, raw_lines: List[str]) -> List[Line]:
        lines = []
        current_line: Line = Line()
        for line_string in raw_lines:
            if line_string.startswith('+'):
                current_line.append(line_string[1:].strip('\r\n'))
            else:
                if line_string:
                    line = Line(line_string)
                    lines.append(line)
                    current_line = line
        return lines

    def _parse(self) -> Circuit:
        base_circuit: Circuit = Circuit()
        tmp_subct: Circuit = Circuit()
        _scope = base_circuit

        used_models: List[str] = []
        used_subckts: List[str] = []

        for line in self.lines:
            line_str = line._text.lower()
            if line_str.startswith("."):
                if line_str.startswith(".ends"):
                    base_circuit.add_subcircuit(tmp_subct)
                    _scope = base_circuit

                elif line_str.startswith(".subckt"):
                    tmp_subct = self._parse_subct(line)
                    _scope = tmp_subct

                elif line_str.startswith(".model"):
                    model = self._parse_model(line)
                    _scope.add_model(model)

                elif line_str.startswith(".ac"):
                    sweep = self._parse_sweep(line)
                    _scope.add_param("sweep", sweep)

                # other directives (.tran, .op, .step, .meas, .backanno, .end,
                # .lib, .inc/.include, .param, ...) are intentionally left
                # unhandled here, matching SpiceParser's behaviour for
                # directives it doesn't model. .lib/.inc are already consumed
                # in _add_includes() before this loop runs.

            else:
                element = self._parse_element(line)
                _scope.add_element(element)
                if _scope == base_circuit:
                    if element.type in ("Q", "M"):
                        used_models.append(element.params.get("ref_model", ""))
                    if element.type == "X":
                        used_subckts.append(element.params.get("ref_cir", ""))

        # Resolve models/subcircuits referenced by name from .lib files (e.g.
        # LTspice's own standard.bjt/standard.mos) that weren't defined inline.
        for lib in self._libs:
            try:
                lib_ct = LtspiceParser(lib)._parse()
                models = lib_ct.get_models()
                subcts = lib_ct.get_subcircuits()
            except Exception:
                self.feedback.append(f"Could not parse lib: {lib}")
                continue

            for model_name in used_models:
                if model_name in models:
                    base_circuit.add_model(models[model_name])

            for subckt_name in used_subckts:
                if subckt_name in subcts:
                    base_circuit.add_subcircuit(subcts[subckt_name])

        return base_circuit

    def _parse_element(self, line: Line) -> Element:
        """Parses the element from the given Line.

        Args:
            line: Line representing the Element

        Returns:
            The parsed Element
        """
        element: Element = Element()

        name = line.tokens[0]
        ele_type = name[0].upper()
        element.set_type(ele_type)

        element.name = name
        element.historical_name = name
        # No-op for plain LTspice ref-des like "R1"/"C1" - only strips the
        # MicroSim "TYPE_REFDES" duplication (e.g. "R_R1") if present.
        element.remove_type_prefix()

        match element.type:
            # Admittance
            case "R" | "C" | "L" | "D":
                element.set_connections(line.tokens[1:-1])
                element.add_param("value_dc", line.tokens[-1])

            # Sources
            case "V" | "I":
                if line.token_cnd == 4:
                    element.set_connections(line.tokens[1:-1])
                    element.add_param("value_dc", line.tokens[-1])
                elif line.token_cnd > 4:
                    element.set_connections(line.tokens[1:3])

                    # parse all values from this token, mirrors SpiceParser's
                    # DC/AC/SIN/PULSE/EXP/SFFM token walk so element.params ends
                    # up with the "value_dc"/"value_ac" keys Modified_Node_Analysis
                    # expects, regardless of which parser produced the Circuit.
                    # LTspice additionally spells the sine source "SINE(...)" and
                    # supports "PWL(...)" - both included below so they're
                    # recognised as waveform keywords (their own parameter lists
                    # aren't captured into a param, same limitation SpiceParser
                    # already has for SIN/PULSE/EXP/SFFM).
                    def parse_token(index, token_str):
                        """Collects the values following a DC/AC keyword.

                        LTspice writes an AC source as "AC <magnitude> [phase]"
                        (e.g. "Vin 1 0 SINE(...) AC 1 0"). SpiceParser simply
                        concatenates every token up to the next keyword, which
                        here would turn "AC 1 0" into the magnitude "10" - a
                        factor-of-ten error in every AC analysis - so magnitude
                        and phase are kept apart instead.
                        """
                        token_list = [
                            "DC", "AC", "SIN(", "SIN", "SINE(", "SINE",
                            "PULSE", "EXP", "SFFM", "PWL",
                        ]
                        token_list.remove(token_str)
                        param_token_str = "value_" + token_str.lower()
                        values = []
                        index += 1
                        while (
                            index < line.token_cnd
                            and not line.tokens[index].upper().startswith(tuple(token_list))
                        ):
                            values.append(line.tokens[index])
                            index += 1

                        element.add_param(param_token_str, values[0] if values else "")
                        if token_str == "AC" and len(values) > 1:
                            element.add_param("value_ac_phase", values[1])
                        return index

                    i = 3
                    while i < len(line.tokens):
                        token = line.tokens[i].upper()

                        if token == "DC":
                            i = parse_token(i, "DC")
                            continue
                        elif token == "AC":
                            i = parse_token(i, "AC")
                            continue
                        elif token.startswith("SIN") or token.startswith("PWL"):
                            i += 1
                            continue
                        elif token == "PULSE":
                            i += 1
                            continue
                        elif token == "EXP":
                            i += 1
                            continue
                        elif token == "SFFM":
                            i += 1
                            continue
                        else:
                            i += 1

            # Controlled sources
            case "E" | "G" | "F" | "H":
                if line.token_cnd == 6:
                    element.set_connections(line.tokens[1:-1])
                    element.add_param("value", line.tokens[-1])

            # Transistors
            case "Q" | "M":
                if line.token_cnd <= 6:
                    connections = line.tokens[1:-1]
                    ref_model = line.tokens[-1]
                    area = None
                    extra_params: Dict[str, str] = {}
                else:
                    connections = line.tokens[1:5]
                    ref_model = line.tokens[5]
                    area = line.tokens[6]
                    extra_params = Line.get_kwargs(" ".join(line.tokens[7:]))

                if element.type == "Q" and len(connections) == 4:
                    # LTspice always writes an explicit substrate/bulk node for
                    # BJTs (Q<name> C B E S model ...); PSpice's 3-terminal
                    # dialect doesn't. library/small_signal_models/bipolar_models
                    # only models 3 terminals (C, B, E), so the substrate node
                    # is dropped rather than being fed into flatten_subcircuit()
                    # as a bogus 4th terminal.
                    connections = connections[:3]

                element.set_connections(connections)
                element.add_param("ref_model", ref_model)
                if area is not None:
                    element.add_param("area", area)
                element.params.update(extra_params)

            # Subcircuits
            case "X":
                element.set_connections(line.tokens[1:-1])
                element.add_param("ref_cir", line.tokens[-1])
                # Fixme Subcircuits can have Params "PARAMS:"

            case _:
                print(f"Unrecognised element: {line._text}")
                return Element()

        return element

    def _parse_model(self, line: Line) -> Model:
        model: Model = Model()

        text = line.right_of('.model').strip()
        mtch = re.match(r"\s*([^ \t]+)\s*([^ \t(]+)(.*)", text)
        if mtch:
            model.name = mtch[1]
            model.type = mtch[2].upper()
            params = mtch[3].strip('() ')
            model.params = Line.get_kwargs(params)

        return model

    def _parse_subct(self, line: Line) -> Circuit:
        circuit = Circuit()
        circuit.name = line.tokens[1]
        circuit.inner_connecting_nodes = line.tokens[2:]
        return circuit

    def _parse_sweep(self, line: Line) -> str:
        line_splits = line.tokens
        if len(line_splits) < 3:
            return ""

        sweep_type = line_splits[1].upper()
        num_of_points = str(int(pu.pspice_to_float(line_splits[2])))

        if sweep_type in ("LIN", "DEC", "OCT"):
            start = str(pu.pspice_to_float(line_splits[3]))
            stop = str(pu.pspice_to_float(line_splits[4]))
            return f"{sweep_type} {num_of_points} {start} {stop}"

        if sweep_type == "POI":
            points_of_interest = [str(pu.pspice_to_float(point)) for point in line_splits[3:]]
            return sweep_type + " " + " ".join(points_of_interest)

        return ""

    def parse_element_params(self, log_filepath: str, elements: List[Element]):
        """Reads an LTspice ".log" small-signal operating-point dump and writes
        the parsed parameters onto the matching Elements (the ".log" equivalent
        of SpiceParser.parse_element_params, which reads PSpice's ".out").

        Format (real example, see Basisschaltung.log / Draft5.log):
            Semiconductor Device Operating Points:
                                --- Bipolar Transistors ---
            Name:       q1
            Model:    bc547b
            Ib:       3.12e-06
            ...

        Each transistor is a vertical block starting at "Name:" and ending at
        a blank line or the next "Name:". Section-header lines like
        "--- Bipolar Transistors ---" and preamble lines before the first
        "Name:" (Circuit:/Warning:/Start Time:) don't match "Key: value" and
        are simply skipped - no need to look for specific header text, so the
        same code handles both BJT and MOSFET blocks.
        """
        try:
            raw_lines = self._read_text_lines(log_filepath)
        except (OSError, UnicodeDecodeError):
            self.feedback.append(f"Could not load file: {log_filepath}")
            print(f"Could not load file: {log_filepath}")
            return

        # LTspice always lowercases the ref-des in .log ("q1"), but the netlist
        # keeps it as written ("Q1") - lowercase before normalising so lookup
        # is case-insensitive.
        lookup = {
            Element.get_normalised_name(el.historical_name.lower()): el
            for el in elements
        }

        current_element: Element | None = None
        current_params: Dict[str, str] = {}
        seen_any_name = False
        matched_keys: set[str] = set()

        def finalize_block():
            if current_element is None:
                return
            # MOSFET blocks give Gds (conductance), never Rds directly - derive
            # Rds = 1/Gds when Rds isn't already present (confirmed against a
            # real MOSFET .log block: Id/Vgs/Vds/.../Gm/Gds/Gmb/Cbd/Cbs/...).
            has_rds = any(k.lower() == "rds" for k in current_params)
            gds_entry = next(
                ((k, v) for k, v in current_params.items() if k.lower() == "gds"),
                None,
            )
            if not has_rds and gds_entry is not None:
                try:
                    gds_val = float(gds_entry[1])
                    if gds_val != 0:
                        current_element.add_param("Rds", str(1.0 / gds_val))
                except (TypeError, ValueError):
                    pass

        name_re = re.compile(r"^Name:\s*(.+)$", re.IGNORECASE)
        param_re = re.compile(r"^([A-Za-z][A-Za-z0-9_]*):\s*(.+)$")

        for raw_line in raw_lines:
            line = raw_line.strip()

            name_match = name_re.match(line)
            if name_match:
                finalize_block()
                seen_any_name = True
                raw_name = name_match.group(1).strip()
                key = Element.get_normalised_name(raw_name.lower())
                current_element = lookup.get(key)
                current_params = {}
                if current_element is None:
                    self.feedback.append(f"Element {raw_name} not found in lookup.")
                    print(f"Warning: element {raw_name} not found in lookup.")
                else:
                    matched_keys.add(key)
                continue

            if not seen_any_name:
                continue  # preamble: Circuit:/Warning:/Start Time:/...

            if line == "":
                finalize_block()
                current_element = None
                current_params = {}
                continue

            param_match = param_re.match(line)
            if param_match and current_element is not None:
                pkey, pval_raw = param_match.group(1), param_match.group(2).strip()
                try:
                    pval = str(float(pval_raw))
                except ValueError:
                    pval = pval_raw
                current_params[pkey] = pval
                current_element.add_param(pkey, pval)

        finalize_block()

        # Without these two warnings the failure is silent: the small-signal
        # placeholders ("rpi"/"ro"/"gm"/...) stay unresolved and only blow up
        # much later in Modified_Node_Analysis as
        # "could not convert string to float: 'rpi'".
        if not seen_any_name:
            message = (
                f"No 'Semiconductor Device Operating Points' data in {log_filepath}. "
                "LTspice only writes that table when a '.op' analysis is active - "
                "re-run the circuit in LTspice with '.op' and use that .log."
            )
            self.feedback.append(message)
            print(f"Warning: {message}")
            return

        missing = [
            el.name
            for el in elements
            if el.type in ("Q", "M")
            and Element.get_normalised_name(el.historical_name.lower()) not in matched_keys
        ]
        if missing:
            message = (
                f"No operating point data for: {', '.join(missing)} - "
                f"these transistors are not listed in {log_filepath}."
            )
            self.feedback.append(message)
            print(f"Warning: {message}")


class Line:
    """Local copy of parser.spice.SpiceParser.Line with one fix: append() keeps
    .tokens/.token_cnd in sync with "+"-continuation text. In SpiceParser.Line,
    append() only updates ._text, so a continuation line never shows up in
    .tokens - harmless there today since SpiceParser's V/I parsing doesn't lean
    on continuation, but here the DC/AC/SIN/PULSE token walk above does, so a
    split-across-"+"-lines source directive needs the merged tokens to be correct.
    Not shared with SpiceParser.py to avoid touching the working PSpice path.
    """

    def __init__(self, line: str = "") -> None:
        self._text = line.strip()
        self.tokens = self._text.split()
        self.token_cnd = len(self.tokens)

    def append(self, line: str):
        self._text += " " + line
        self.tokens = self._text.split()
        self.token_cnd = len(self.tokens)

    def right_of(self, text):
        return self._text[len(text):].strip()

    @staticmethod
    def get_kwargs(text: str) -> Dict[str, str]:
        text = text.strip(" ;()")
        dict_parameters = {}

        parts = []
        for part in text.split():
            if '=' in part and part != '=':
                left, right = [x for x in part.split('=')]
                parts.append(left)
                parts.append('=')
                if right:
                    parts.append(right)
            else:
                parts.append(part)

        i = 0
        i_stop = len(parts)
        while i < i_stop:
            if i + 1 < i_stop and parts[i + 1] == '=':
                key, value = parts[i], parts[i + 2]
                dict_parameters[key] = value
                i += 3
            else:
                i += 3

        return dict_parameters
