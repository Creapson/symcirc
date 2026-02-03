import dearpygui.dearpygui as dpg

from gui.nodes.Node import Node
from gui.windows.ApproximatorWindow import ApproximatorWindow


class ApproximatorNode(Node):
    def __init__(self, label, position=(100, 100)):
        self.h = None

        super().__init__(label, position)

    def setup(self, node_editor_tag):
        def build():
            with self.add_input_attr() as input_pin:
                dpg.add_text("Connect h here", source=self.uuid("h_input"))
            self.input_pins[self.uuid("h_input")] = input_pin

            with self.add_static_attr():
                dpg.add_button(
                    label="Configure/Settings", callback=self.open_settings_window
                )

        return super().setup(build, node_editor_tag)

    def open_settings_window(self):
        if self.h is not None:
            self.settings_window = ApproximatorWindow(self.h, self.mna, self.node_id)
            self.settings_window.setup()

    def onlink_callback(self):
        self.h, self.mna = self.get_input_pin_value(self.uuid("h_input"))

        super().onlink_callback()

    def update(self):
        super().update()
