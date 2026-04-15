import dearpygui.dearpygui as dpg

from gui.windows.NodeEditorWindow import NodeEditorWindow


class Application:
    def __init__(self):
        pass

    def start(self):
        self.load_settings()
        self.load_library()
        self.start_dpg()
        pass

    def start_dpg(self):
        dpg.create_context()

        # Viewport
        dpg.create_viewport(title="OOP Node Editor Example", width=1200, height=800)
        editor = NodeEditorWindow(application=self)
        # Add nodes
        editor.setup()
        dpg.setup_dearpygui()

        dpg.show_viewport()
        dpg.set_primary_window("Node Editor", True)

        # Render Loop
        dpg.start_dearpygui()
        dpg.destroy_context()

    def load_library(self):
        # load all small signal model 
        from os import listdir
        from os.path import isfile, join
        bipolar_path = "library/small_signal_models/bipolar_models"
        mosfet_path = "library/small_signal_models/mosfet_models"

        self.bipolar_models = [f.removesuffix(".json") for f in listdir(bipolar_path) if isfile(join(bipolar_path, f))]
        self.mosfet_models = [f.removesuffix(".json") for f in listdir(mosfet_path) if isfile(join(mosfet_path, f))]

        print(self.bipolar_models)
        print(self.mosfet_models)

    def load_settings(self):
        pass
