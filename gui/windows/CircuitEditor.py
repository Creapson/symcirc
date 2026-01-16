from gui.windows.Window import Window


class CircuitEditor(Window):
    def __init__(self):
        self.title = "Circuit Editor"

        super().__init__()
        pass

    def setup(self):
        def build():
            pass

        super().setup(build)

    def on_close(self, sender, app_data, user_data):
        super().on_close()
