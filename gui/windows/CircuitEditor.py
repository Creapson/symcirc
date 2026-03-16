import dearpygui.dearpygui as dpg
from gui.windows.Window import Window
from netlist.Circuit import Circuit
from netlist.Element import Element 
from netlist.Model import Model


class CircuitEditor(Window):
    def __init__(self, circuit : Circuit, parent_tag:str):
        self.circuit = circuit

        super().__init__(title=str(parent_tag + ":CircuitEditor"), autosize=False)
        pass

    def setup(self):
        def build():
            self.show_circuit(circuit=self.circuit)

            with dpg.group(horizontal=True):
                dpg.add_button(label="Save")
                dpg.add_button(label="Close")

        super().setup(build)

    def on_close(self, sender, app_data, user_data):
        super().on_close(sender, app_data, user_data)

    def add_text_input(self, label : str, default_value:str):
        with dpg.group(horizontal=True):
            dpg.add_text(label)
            dpg.add_input_text(default_value=default_value)

    def add_array_edit(self, label:str, default_values:list[str]):
        with dpg.group(horizontal=True):
            dpg.add_text(label)
            for item in default_values:
                dpg.add_input_text(default_value=item, width=50)

    def show_info(self):
        self.add_text_input("Name", self.circuit.name)
        self.add_text_input("Netlist file path", self.circuit.netlist_file_path)
        self.add_text_input("bipolar_model", self.circuit.bipolar_model)
        self.add_text_input("mosfet_model", self.circuit.mosfet_model)

        self.add_array_edit("Inner connecting nodes", self.circuit.inner_connecting_nodes)


    def show_elements(self, elements: list[Element]):
        if len(elements) == 0:
            return
        dpg.add_text("Elements:")
        with dpg.child_window(height=300):
            for element in elements:
                self.show_element(element)

    def show_models(self, models: dict[str, Model]):
        if len(models) == 0:
            return
        dpg.add_text("Models:")
        with dpg.child_window(height=300):
            for name, model in models.items():
                self.show_model(model)

    def show_subcts(self, sub_cts: dict[str, Circuit]):
        if len(sub_cts) == 0:
            return
        dpg.add_text("Subcirctuis:")
        with dpg.child_window(autosize_x=True):
            for _, circuit in sub_cts.items():
                self.show_circuit(circuit)

    def show_circuit(self, circuit: Circuit):
        self.show_info()
        self.show_elements(circuit.elements)
        self.show_models(circuit.models)
        self.show_subcts(circuit.subcircuits)

    def show_element(self, element: Element):
        with dpg.group(horizontal=True):
            dpg.add_input_text(default_value=element.name, width=50)
            dpg.add_input_text(default_value=element.get_symbol(), width=50)
            dpg.add_input_text(default_value=element.type, width=50)
            self.add_array_edit("connections", element.connections)

    def show_model(self, model: Model):
        with dpg.group(horizontal=True):
            dpg.add_input_text(default_value=model.name, width=50)
            dpg.add_text("params here!")

