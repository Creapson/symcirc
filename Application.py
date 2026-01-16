import dearpygui.dearpygui as dpg

from gui.windows.NodeEditor import NodeEditor


class Application:
    def __init__(self):
        pass

    def start(self):
        self.start_dpg()
        pass

    def start_dpg(self):
        dpg.create_context()

        # Viewport
        dpg.create_viewport(title="OOP Node Editor Example", width=1200, height=800)
        editor = NodeEditor()
        # Add nodes
        editor.setup()
        dpg.setup_dearpygui()

        dpg.show_viewport()
        dpg.set_primary_window("Node Editor", True)

        # Render Loop
        dpg.start_dearpygui()
        dpg.destroy_context()
