import dearpygui.dearpygui as dpg

BIPOLAR_MODELS = ["beta_with_r_be", "beta_with_r_be_G"]
MOSFET_MODELS = ["BSIM"]


class Node:
    def __init__(self, label, position=(100, 100)):
        self.label = label
        self.position = position
        # Add the editor to access the other nodes
        self.editor = None
        self.node_id = None

        # {pin_id: connected_node}
        self.connections = {}
        # {pin_id: variable}
        self.output_values = {}
        self.output_pins = {}
        self.input_pins = {}

    def setup(self, build_fn, parent):
        with dpg.node(
            label=self.label, pos=self.position, parent=parent
        ) as self.node_id:
            build_fn()

            with self.add_static_attr():
                dpg.add_button(label="Debug Log", callback=self.debug_print)
            print("Output Pins: ", self.output_pins)

        print(f"node_id of node {self.label} with id: {self.node_id}")
        dpg.set_item_pos(self.node_id, self.position)

        return self.node_id

    def delete_output_pins(self):
        for pin_tag, attr_id in list(self.output_pins.items()):
            if dpg.does_item_exist(attr_id):
                dpg.delete_item(attr_id)

            self.output_values.pop(attr_id, None)

        self.output_pins.clear()

    def uuid(self, txt: str):
        return f"{self.node_id}_" + txt

    def add_input_attr(self):
        return dpg.node_attribute(
            parent=self.node_id, attribute_type=dpg.mvNode_Attr_Input
        )

    def add_static_attr(self):
        return dpg.node_attribute(
            parent=self.node_id, attribute_type=dpg.mvNode_Attr_Static
        )

    def add_output_attr(self):
        return dpg.node_attribute(
            parent=self.node_id, attribute_type=dpg.mvNode_Attr_Output
        )

    def add_output_pin_value(self, output_pin_tag, value):
        output_pin = self.output_pins.get(output_pin_tag, None)
        self.output_values[output_pin] = value

        self.editor.propagate(output_pin)
        print("Output Values", self.output_values)

    def add_connection(self, pin_id, connected_node):
        self.connections[pin_id] = connected_node
        print("Connections in Node: ", self.connections)

    def onlink_callback(self):
        pass

    def delink_callback(self):
        pass

    def get_input_pin_value(self, input_pin_tag):
        if input_pin_tag in self.input_pins:
            input_pin = self.input_pins.get(input_pin_tag, None)
            from_pin = self.connections.get(input_pin, None)

            if from_pin is None:
                return None

            # traverse the connection to the connected node
            # and get the object from there
            from_node_id = dpg.get_item_parent(from_pin)
            from_node = self.editor.node_dic[from_node_id]
            return from_node.output_values.get(from_pin, None)

        else:
            return None

    def update(self):
        print("update was called!")

    def debug_print(self):
        print(f"\n\nDebug Output from Node: {self.label}")
        print("Label: ", self.label)
        print("Position: ", self.position)
        print("NodeID: ", self.node_id)
        print("Connections: ", self.connections)
        print("Input Pins", self.input_pins)
        print("output Values: ", self.output_values)
        print("output pins: ", self.output_pins)


###################
#   NODE CLASSES  #
###################


class ImportCircuit(Node):
    def callback(self, sender, app_data):
        def format_feedback(feedback):
            message = ""
            for string in feedback:
                if string is not None:
                    message += "\n" + string
            return message

        from NetlistParser import NetlistParser

        parser = NetlistParser()
        parser.set_cir_file(app_data["file_path_name"])
        feedback = parser.pre_format()

        self.delete_output_pins()

        # when a file is selected create the output pin
        with self.add_output_attr() as output_pin:
            dpg.add_text("Selected file", tag=self.uuid("file_path_out"))
        self.output_pins[self.uuid("file_path_out")] = output_pin
        self.add_output_pin_value(
            self.uuid("file_path_out"), app_data["file_path_name"]
        )

        dpg.set_value(
            self.file_path_widget_id,
            f"Loaded file with following Feedback:\n{format_feedback(feedback)}",
        )

    def setup(self, parent):
        def build():
            with dpg.value_registry():
                dpg.add_string_value(
                    default_value="No file currently selected!",
                    tag=f"{self.node_id}_file_path_string",
                )

            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self.callback,
                tag=f"{self.node_id}_file_dialog_id",
                width=700,
                height=400,
            ):
                dpg.add_file_extension(".cir")

            with self.add_static_attr():
                dpg.add_button(
                    label="Open File Dialog",
                    callback=lambda: dpg.show_item(f"{self.node_id}_file_dialog_id"),
                )
                self.file_path_widget_id = dpg.add_text(
                    source=f"{self.node_id}_file_path_string"
                )

        return super().setup(build, parent)


class NetlistParserNode(Node):
    def __init__(self, label, position=(100, 100)):
        self.row_sources = []
        self.table_rows = {}

        super().__init__(label, position)

    def setup(self, parent):
        def build():
            with dpg.value_registry():
                dpg.add_string_value(
                    default_value="Circuit is not flattend yet!",
                    tag=self.uuid("circuit_parser"),
                )
                dpg.add_string_value(default_value="_", tag=self.uuid("separator"))
                dpg.add_string_value(
                    default_value="beta_with_r_be", tag=self.uuid("bipolar_model")
                )
                dpg.add_string_value(
                    default_value="BSIM", tag=self.uuid("mosfet_model")
                )

            with self.add_input_attr() as input_pin:
                self.file_path_widget_id = dpg.add_text(
                    default_value="Connect ImportNode here! [filepath]",
                    tag=self.uuid("file_path_pin"),
                )
            self.input_pins[self.uuid("file_path_pin")] = input_pin

            with self.add_static_attr():
                with dpg.group(horizontal=True):
                    dpg.add_text("Seperator Symbol")
                    dpg.add_combo(
                        items=("_", ",", ".", ";"),
                        width=50,
                        source=self.uuid("separator"),
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("Default Bioplar model")
                    dpg.add_combo(
                        items=BIPOLAR_MODELS,
                        width=200,
                        source=self.uuid("bipolar_model"),
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("Default Mosfet Model")
                    dpg.add_combo(
                        items=MOSFET_MODELS, width=200, source=self.uuid("mosfet_model")
                    )

                # create table to edit all subcircuits
                dpg.add_text(
                    "Select the default small signal models for the subcircuits"
                )

                # add a filter text-box above the table
                with dpg.group(horizontal=True):
                    dpg.add_text("Filter by subcircuit name:")
                    dpg.add_input_text(
                        width=200,
                        hint="type to filter...",
                        callback=self.filter_table,
                        tag=self.uuid("subckt_filter"),
                    )
                with dpg.table(
                    header_row=True,
                    policy=dpg.mvTable_SizingFixedFit,
                    resizable=True,
                    no_host_extendX=True,
                    borders_innerV=True,
                    borders_outerV=True,
                    borders_outerH=True,
                    tag=self.uuid("subcircuit_table"),
                ):
                    # create the header of the table
                    dpg.add_table_column(label="name")
                    dpg.add_table_column(label="bpiolar_model")
                    dpg.add_table_column(label="mosfet_model")

                dpg.add_text("When nothing is selected the default value will be used!")

                # temperary update button
                dpg.add_button(label="Flatten Subcircuits", callback=self.update)

            """
            with self.add_output_attr() as ouput_pin:
                self.circuit_out_pin = dpg.add_text(source=self.uuid("circuit_parser"))
            self.output_pins.append(ouput_pin)
            """

        return super().setup(build, parent)

    def onlink_callback(self):
        filepath = self.get_input_pin_value(self.uuid("file_path_pin"))
        from NetlistParser import NetlistParser

        parser = NetlistParser()
        parser.set_cir_file(filepath)
        self.circuit = parser.parse_netlist()

        # populate the subcircuit table
        def add_cubcircuit_row(subct_name, bipolar_model, mosfet_model):
            with dpg.value_registry():
                bipolar_source_id = dpg.add_string_value(
                    default_value="", tag=self.uuid(f"{subct_name}_bipolar_model")
                )
                self.row_sources.append(bipolar_source_id)
                mosfet_source_id = dpg.add_string_value(
                    default_value="", tag=self.uuid(f"{subct_name}_mosfet_model")
                )
                self.row_sources.append(mosfet_source_id)

            row = dpg.add_table_row(parent=self.uuid("subcircuit_table"))
            self.table_rows[subct_name] = row

            dpg.add_text(subct_name, parent=row)
            dpg.add_combo(
                items=BIPOLAR_MODELS,
                source=self.uuid(f"{subct_name}_bipolar_model"),
                parent=row,
            )
            dpg.add_combo(
                items=MOSFET_MODELS,
                source=self.uuid(f"{subct_name}_mosfet_model"),
                parent=row,
            )

        subct_list = self.circuit.get_subcircuits()
        self.delete_table()
        for subct_name, subct_obj in subct_list.items():
            add_cubcircuit_row(
                subct_name, subct_obj.bipolar_model, subct_obj.mosfet_model
            )

        super().onlink_callback()

    def filter_table(self, sender, app_data):
        filter_text = app_data.lower()

        for subct_name, row_id in self.table_rows.items():
            visible = filter_text in subct_name.lower()
            dpg.configure_item(row_id, show=visible)

    def delete_table(self):
        dpg.delete_item(self.uuid("subcircuit_table"), children_only=True, slot=1)

        # delete the used sources of each cell
        for source in self.row_sources:
            dpg.delete_item(source)

        self.row_sources.clear()
        self.table_rows.clear()

    def delink_callback(self):
        self.delete_table()

        super().delink_callback()

    def update(self):
        # apply all options to the circuit
        # separator
        separator = dpg.get_value(self.uuid("separator"))
        self.circuit.set_separator(separator)
        # small signal models
        # circuit
        self.circuit.set_bipolar_model(dpg.get_value(self.uuid("bipolar_model")))
        self.circuit.set_mosfet_model(dpg.get_value(self.uuid("mosfet_model")))

        subct_list = self.circuit.get_subcircuits()
        for subct_name, subct_obj in subct_list.items():
            bipolar_model = dpg.get_value(self.uuid(f"{subct_name}_bipolar_model"))
            mosfet_model = dpg.get_value(self.uuid(f"{subct_name}_mosfet_model"))

            subct_obj.set_bipolar_model(bipolar_model)
            subct_obj.set_mosfet_model(mosfet_model)

            # if nothing was selected use the default values
            if bipolar_model == "":
                subct_obj.set_bipolar_model(dpg.get_value(self.uuid("bipolar_model")))

            if mosfet_model == "":
                subct_obj.set_mosfet_model(dpg.get_value(self.uuid("mosfet_model")))

        flattend_circuit = self.circuit.copy()
        flattend_circuit.flatten()

        # delte all output pins that already exist
        self.delete_output_pins()

        # create a output pin for the flattend circuit
        with self.add_output_attr() as output_pin:
            dpg.add_text("Flattend Circuit", tag=self.uuid("flattend_circuit"))
        self.output_pins[self.uuid("flattend_circuit")] = output_pin
        self.add_output_pin_value(self.uuid("flattend_circuit"), flattend_circuit)

        flattend_circuit.to_ai_string()

        # apply it to UI
        dpg.set_value(self.uuid("circuit_parser"), "Circuit with flattend Subcircuits")

        super().update()


class FlattenNode(Node):
    def __init__(self, label, position=(100, 100)):
        self.row_sources = []
        self.table_rows = {}

        super().__init__(label, position)

    def callback(self, sender, app_data):
        print(sender)
        print(app_data)
        self.out_file_path = app_data["file_path_name"]
        dpg.set_value(self.uuid("out_file_path"), f"Selected {self.out_file_path}")

    def setup(self, parent):
        def build():
            with dpg.value_registry():
                dpg.add_string_value(
                    default_value="Circuit is not flattend yet!",
                    tag=self.uuid("flattend_circuit_out"),
                )
                dpg.add_string_value(
                    default_value="No .out file currently selected!",
                    tag=self.uuid("out_file_path"),
                )

            with self.add_input_attr() as input_pin:
                dpg.add_text(
                    default_value="Connect Circuit here! [circuit]",
                    tag=self.uuid("file_path_pin"),
                )
            self.input_pins[self.uuid("file_path_pin")] = input_pin

            with self.add_static_attr():
                with dpg.file_dialog(
                    directory_selector=False,
                    show=False,
                    callback=self.callback,
                    tag=self.uuid("file_dialog_id"),
                    width=700,
                    height=400,
                ):
                    dpg.add_file_extension(".out")

                dpg.add_button(
                    label="Select .out File",
                    callback=lambda: dpg.show_item(self.uuid("file_dialog_id")),
                )
                dpg.add_text(source=self.uuid("out_file_path"))

                with dpg.group(horizontal=True):
                    dpg.add_text("Filter by element name:")
                    dpg.add_input_text(
                        width=200,
                        hint="type to filter...",
                        callback=self.filter_table,
                        tag=self.uuid("subckt_filter"),
                    )
                # create table to edit all subcircuits
                dpg.add_text("Select small signal models for every element")
                with dpg.table(
                    header_row=True,
                    policy=dpg.mvTable_SizingFixedFit,
                    resizable=True,
                    no_host_extendX=True,
                    borders_innerV=True,
                    borders_outerV=True,
                    borders_outerH=True,
                    tag=self.uuid("element_table"),
                ):
                    # create the header of the table
                    dpg.add_table_column(label="name")
                    dpg.add_table_column(label="bpiolar_model")
                    dpg.add_table_column(label="mosfet_model")

                dpg.add_text("When nothing is selected the default value will be used!")

                # temperary update button
                dpg.add_button(label="Flatten Elements", callback=self.update)

        return super().setup(build, parent)

    def onlink_callback(self):
        self.circuit = self.get_input_pin_value(self.uuid("file_path_pin"))

        self.circuit.to_ai_string()

        # populate the subcircuit table
        def add_element_row(name, bipolar_model, mosfet_model):
            with dpg.value_registry():
                bipolar_source_id = dpg.add_string_value(
                    default_value=bipolar_model, tag=self.uuid(f"{name}_bipolar_model")
                )
                self.row_sources.append(bipolar_source_id)
                mosfet_source_id = dpg.add_string_value(
                    default_value=mosfet_model, tag=self.uuid(f"{name}_mosfet_model")
                )

                self.row_sources.append(mosfet_source_id)

            row = dpg.add_table_row(parent=self.uuid("element_table"))
            self.table_rows[name] = row

            dpg.add_text(name, parent=row)
            dpg.add_combo(
                items=BIPOLAR_MODELS,
                source=self.uuid(f"{name}_bipolar_model"),
                parent=row,
                width=-1,
            )
            dpg.add_combo(
                items=MOSFET_MODELS,
                source=self.uuid(f"{name}_mosfet_model"),
                parent=row,
                width=-1,
            )

        # populate the table with all elements
        self.element_list = self.circuit.get_elements()
        print(self.element_list)
        self.delete_table()
        for item in self.element_list:
            if item.type == "Q":
                (
                    add_element_row(
                        item.name,
                        item.params["bipolar_model"],
                        item.params["mosfet_model"],
                    ),
                )

        super().onlink_callback()

    def filter_table(self, sender, app_data):
        filter_text = app_data.lower()

        for subct_name, row_id in self.table_rows.items():
            visible = filter_text in subct_name.lower()
            dpg.configure_item(row_id, show=visible)

    def delete_table(self):
        dpg.delete_item(self.uuid("subcircuit_table"), children_only=True, slot=1)

        # delete the used sources of each cell
        for source in self.row_sources:
            dpg.delete_item(source)

        self.row_sources.clear()
        self.table_rows.clear()

    def delink_callback(self):
        self.delete_table()
        super().delink_callback()

    def update(self):
        # apply the changed small signal models to all elements
        for element in self.element_list:
            bipolar_model = dpg.get_value(self.uuid(f"{element.name}_bipolar_model"))
            mosfet_model = dpg.get_value(self.uuid(f"{element.name}_mosfet_model"))
            element.params["bipolar_model"] = bipolar_model
            element.params["mosfet_model"] = mosfet_model

        flattend_circuit = self.circuit.copy()
        flattend_circuit.flatten(True, self.out_file_path)

        self.delete_output_pins()

        # output pin
        with self.add_output_attr() as output_pin:
            dpg.add_text(source=self.uuid("flattend_circuit_out"))
        self.output_pins[self.uuid("flattend_circuit_out")] = output_pin

        self.add_output_pin_value(self.uuid("flattend_circuit_out"), flattend_circuit)

        flattend_circuit.to_ai_string()

        # apply it to UI
        dpg.set_value(self.uuid("flattend_circuit_out"), "Circuit with flattend Models")

        super().update()


class ModifiedNodalAnalysis(Node):
    def __init__(self, label, position=(100, 100)):
        self.nma = None

        super().__init__(label, position)

    def setup(self, parent):
        def build():
            with self.add_input_attr() as magn_pin:
                dpg.add_text(
                    default_value="Connect Circuit here",
                    tag=self.uuid("circuit_input_pin"),
                )
            self.input_pins[self.uuid("circuit_input_pin")] = magn_pin

            with self.add_static_attr():
                # add selection for the transfer-function
                with dpg.group(horizontal=True):
                    dpg.add_text("From Node:")
                    dpg.add_combo(tag=self.uuid("from_node"))

                with dpg.group(horizontal=True):
                    dpg.add_text("To Node:")
                    dpg.add_combo(tag=self.uuid("to_node"))

                dpg.add_button(label="Calculate Numeric Values", callback=self.update)

        return super().setup(build, parent)

    def onlink_callback(self):
        self.circuit = self.get_input_pin_value(self.uuid("circuit_input_pin"))

        from Modified_Node_Analysis import ModifiedNodalAnalysis

        self.mna = ModifiedNodalAnalysis(self.circuit)
        # populate the from and to_node combo boxes
        # with the possible nodes
        nodes = list(self.mna.node_map.keys())
        dpg.configure_item(self.uuid("from_node"), items=nodes)
        dpg.configure_item(self.uuid("to_node"), items=nodes)

        dpg.set_value(self.uuid("circuit_input_pin"), "Circuit connected!")
        super().onlink_callback()

    def update(self):
        import sympy as sp

        self.mna.buildEquationsSystem()
        num_results = self.mna.solveNumerical(self.mna.value_dict)

        # use the selected nodes
        from_node = dpg.get_value(self.uuid("from_node"))
        to_node = dpg.get_value(self.uuid("to_node"))

        H = (
            num_results[sp.symbols(f"V_{to_node}")]
            / num_results[sp.symbols(f"V_{from_node}")]
        )

        self.delete_output_pins()

        # create output pins for those arrays

        with self.add_output_attr() as output_pin:
            dpg.add_text("H", tag=self.uuid("h_out"))
        self.output_pins[self.uuid("h_out")] = output_pin
        self.add_output_pin_value(self.uuid("h_out"), H)

        super().update()


class BodePlot(Node):
    def setup(self, parent):
        def build():
            # create pins for all nessary inputs
            with self.add_input_attr() as input_pin:
                dpg.add_text(
                    default_value="Connect freq_log here!",
                    tag=self.uuid("freq_log_pin"),
                )
            self.input_pins[self.uuid("freq_log_pin")] = input_pin

            with self.add_input_attr() as magn_pin:
                dpg.add_text(
                    default_value="Connect magnitude here!",
                    tag=self.uuid("magnitude_pin"),
                )
            self.input_pins[self.uuid("magnitude_pin")] = magn_pin

            with self.add_input_attr() as phase_pin:
                dpg.add_text(
                    default_value="Connect phase here!", tag=self.uuid("phase_pin")
                )
            self.input_pins[self.uuid("phase_pin")] = phase_pin

            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                with dpg.subplots(
                    2, 1, label="", link_all_x=True, height=600
                ) as subplot_id:
                    # -------- Magnitude Plot --------
                    with dpg.plot(label="Betrag (dB)"):
                        dpg.add_plot_legend()
                        dpg.plot_axis(dpg.mvXAxis, label="log10(ω) [rad/s]")
                        with dpg.plot_axis(dpg.mvYAxis, label="Betrag [dB]"):
                            dpg.add_line_series(
                                [], [], label="|H(jω)|", tag=self.uuid("mag_series")
                            )

                    # -------- Phase Plot --------
                    with dpg.plot(label="Phase (°)"):
                        dpg.add_plot_legend()
                        dpg.plot_axis(dpg.mvXAxis, label="log10(ω) [rad/s]")
                        with dpg.plot_axis(dpg.mvYAxis, label="Phase [°]"):
                            dpg.add_line_series(
                                [], [], label="∠H(jω)", tag=self.uuid("phase_series")
                            )

        return super().setup(build, parent)

    def onlink_callback(self):
        freq_log = self.get_input_pin_value(self.uuid("freq_log_pin"))
        magnitude = self.get_input_pin_value(self.uuid("magnitude_pin"))
        phase = self.get_input_pin_value(self.uuid("phase_pin"))
        print(freq_log)
        print(magnitude)
        print(phase)

        # update the plots with the new values
        if freq_log is not None and magnitude is not None:
            dpg.set_value(
                self.uuid("mag_series"), [freq_log.tolist(), magnitude.tolist()]
            )

        if freq_log is not None and phase is not None:
            dpg.set_value(
                self.uuid("phase_series"), [freq_log.tolist(), phase.tolist()]
            )

        super().onlink_callback()

    def update(self):
        super().update()


class NumericSolver(Node):
    def setup(self, parent):
        def build():
            with dpg.value_registry():
                dpg.add_int_value(default_value=2, tag=self.uuid("start_log_int"))
                dpg.add_int_value(default_value=8, tag=self.uuid("end_log_int"))
                dpg.add_int_value(default_value=10000, tag=self.uuid("points_in_log"))

            with self.add_input_attr() as input_pin:
                dpg.add_text(
                    default_value="Connect H here",
                    tag=self.uuid("h_input_pin"),
                )
            self.input_pins[self.uuid("h_input_pin")] = input_pin

            with self.add_static_attr():
                dpg.add_text("Configure the log-Space")

                with dpg.group(horizontal=True):
                    dpg.add_text("Start Frequenzy in 10^x")
                    dpg.add_input_int(
                        label="input int", source=self.uuid("start_log_int")
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("End Frequenzy in 10^x")
                    dpg.add_input_int(
                        label="input int", source=self.uuid("end_log_int")
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("Number of Points between start and end")
                    dpg.add_input_int(
                        label="input int", source=self.uuid("points_in_log")
                    )

                dpg.add_button(label="Calculate Numeric Values", callback=self.update)

        return super().setup(build, parent)

    def onlink_callback(self):
        self.h = self.get_input_pin_value(self.uuid("h_input_pin"))

        super().onlink_callback()

    def update(self):
        import numpy as np
        import sympy as sp

        s = sp.symbols("s")
        # --- 2. SymPy → numerische Funktion umwandeln ---
        H_lambdified = sp.lambdify(s, self.h, "numpy")
        # --- 3. Frequenzachse definieren ---
        w = np.logspace(-2, 8, 10000)  # Kreisfrequenz
        jw = 1j * w
        H_eval = H_lambdified(jw)

        # create solved arrays for later plotting
        freq_log = np.log10(w)
        magnitude_db = 20 * np.log10(np.abs(H_eval))
        phase_deg = np.angle(H_eval, deg=True)

        print(freq_log)
        print(magnitude_db)
        print(phase_deg)

        # freq_log
        with self.add_output_attr() as output_pin:
            dpg.add_text("fraq_log (x-Achse)", tag=self.uuid("freq_log_out"))
        self.output_pins[self.uuid("freq_log_out")] = output_pin
        self.add_output_pin_value(self.uuid("freq_log_out"), freq_log)

        # freq_log
        with self.add_output_attr() as output_pin:
            dpg.add_text("magnitude_db (y-Achse)", tag=self.uuid("magnitude_out"))
        self.output_pins[self.uuid("magnitude_out")] = output_pin
        self.add_output_pin_value(self.uuid("magnitude_out"), magnitude_db)

        # freq_log
        with self.add_output_attr() as output_pin:
            dpg.add_text("phase_deg (y-Achse)", tag=self.uuid("phase_out"))
        self.output_pins[self.uuid("phase_out")] = output_pin
        self.add_output_pin_value(self.uuid("phase_out"), phase_deg)
        super().update()


class Copy(Node):
    def setup(self, parent):
        def build():
            pass

        return super().setup(build, parent)

    def onlink_callback(self):
        super().onlink_callback()

    def update(self):
        super().update()
