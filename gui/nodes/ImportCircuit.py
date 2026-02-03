import dearpygui.dearpygui as dpg

from gui.nodes.Node import Node


class ImportCircuit(Node):
    def callback(self, sender, app_data):
        def format_feedback(feedback):
            message = ""
            for string in feedback:
                if string is not None:
                    message += "\n" + string
            return message

        from parser.NetlistParser import NetlistParser

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

    def setup(self, node_editor_tag):
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

        return super().setup(build, node_editor_tag)
