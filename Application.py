import dearpygui.dearpygui as dpg

from gui.windows.NodeEditorWindow import NodeEditorWindow
from pathlib import Path


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
        base_dir = Path(__file__).resolve().parent
        
        bipolar_path = base_dir / "library" / "small_signal_models" / "bipolar_models"
        mosfet_path = base_dir / "library" / "small_signal_models" / "mosfet_models"

        self.bipolar_models = []
        if bipolar_path.exists():
            self.bipolar_models = [f.stem for f in bipolar_path.iterdir() if f.is_file() and f.suffix == ".json"]

        self.mosfet_models = []
        if mosfet_path.exists():
            self.mosfet_models = [f.stem for f in mosfet_path.iterdir() if f.is_file() and f.suffix == ".json"]

        print(self.bipolar_models)
        print(self.mosfet_models)

    def load_settings(self):
        pass
