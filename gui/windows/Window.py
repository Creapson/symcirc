import dearpygui.dearpygui as dpg


class Window:
    def __init__(self, title=None):
        self.title = title
        self.id = None

    def setup(self, build_func, show_menu_bar):
        with dpg.window(
            tag=self.title, on_close=self.on_close, menubar=show_menu_bar
        ) as self.id:
            build_func()
        pass

    def uuid(self, tag):
        return f"{self.id}_{tag}"

    def on_close(self, sender, app_data, user_data):
        pass


"""
class CopyClass(Window):
    def __init__(self):
        self.title = "Approximator Settings Window"

        super().__init__()
        pass

    def setup(self):
        def build():
            pass

        super().setup(build)

    def on_close(self, sender, app_data, user_data):
        super().on_close()
"""
