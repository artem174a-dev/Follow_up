import flet as ft

from core.items import Items


class App(Items):
    def __init__(self, page: ft.Page):
        super().__init__(page)
        self.page.scroll = False
        self.page.title = "Follow Up"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.theme = ft.Theme(color_scheme=ft.ColorScheme(
            primary=ft.colors.GREEN
        ))

        self.is_auth = None

        self.main()

    def main(self):
        self.is_auth = bool(self.page.client_storage.get('login'))
        print(self.is_auth)
        if self.is_auth is True:
            if self.page.width < 600:
                page_view = ft.Column(
                    [
                        self.main_view
                    ],
                    height=None,
                    width=None,
                    expand=True,
                    scroll=ft.ScrollMode.ADAPTIVE
                )
                self.page.navigation_bar = self.down_bar
            else:
                page_view = ft.Row(
                    [
                        ft.Container(expand=0, content=self.left_bar),
                        ft.Container(expand=0, content=ft.VerticalDivider(width=1)),
                        ft.Container(expand=1, content=self.main_view, height=1500),

                    ],
                    height=self.page.height,
                    width=None,
                )
            self.page.add(page_view)
            self.page.update()
        else:
            self.page.add(self.auth_page())
            self.page.update()


ft.app(target=App, host='*', port=7000, view=None)
