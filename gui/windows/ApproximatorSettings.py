from gui.windows.Window import Window


class ApproximatorWindow(Window):
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
