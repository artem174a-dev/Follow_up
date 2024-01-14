import datetime
import locale
import threading
import time
from queue import Queue

from babel.dates import format_datetime
import tzlocal
import pytz

import flet as ft
from flet_core.alignment import center_left
from playwright.sync_api import sync_playwright

from ktolk.api import Client, get_record_users_keys, collect_dialogue
from database import SQL
from passwords import PasswordEncryptor, run

BTN_SHAPE = {
    ft.MaterialState.HOVERED: ft.RoundedRectangleBorder(radius=10),
    ft.MaterialState.DEFAULT: ft.RoundedRectangleBorder(radius=10),
}

PF = '[*]'


def format_datetime_custom(source_string):
    dt_object = datetime.datetime.strptime(source_string, "%Y-%m-%d %H:%M")

    # Автоматическое определение локального часового пояса
    local_tz = tzlocal.get_localzone()

    dt_object_local = dt_object.replace(tzinfo=pytz.utc).astimezone(local_tz)

    current_locale, encoding = locale.getdefaultlocale()
    result_string = format_datetime(dt_object_local, format="d MMMM, HH:mm", locale=current_locale)

    return result_string


def minutes_to_time(minutes):
    hours = minutes // 60
    remaining_minutes = minutes % 60
    return f"{hours:02d}:{remaining_minutes:02d}"


def millis_to_time(milliseconds):
    seconds = milliseconds // 1000
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"


class Items:
    def __init__(self, page: ft.Page):
        self._click_nav = None
        self.page = page  # Страница
        self.api = Client()
        self.db = SQL()
        self.rec_data = None
        self.user_email = 'motovilov.aa@gulliver-group.com'
        self.in_gen_dict = {}
        #
        # Настройки
        #
        self.page.title = "Flet controls gallery"
        self.page.fonts = {
            "Roboto Mono": "RobotoMono-VariableFont_wght.ttf",
        }
        self.page.theme_mode = ft.ThemeMode.DARK
        self.width_item = self.page.width
        #
        # Фундаментальные элементы
        #
        self.main_view = ft.Column([self.rec_page()], height=1700, scroll=ft.ScrollMode.ALWAYS)

        self.down_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationDestination(
                    icon=ft.icons.VIDEOCAM_OUTLINED,
                    selected_icon=ft.icons.VIDEOCAM,
                ),
                ft.NavigationDestination(
                    icon_content=ft.Badge(
                        content=ft.Icon(ft.icons.EMAIL_OUTLINED),
                        small_size=10),
                    selected_icon=ft.icons.EMAIL
                ),
                ft.NavigationDestination(
                    icon=ft.icons.DATA_OBJECT_OUTLINED,
                    selected_icon=ft.icons.DATA_OBJECT,
                ),
                ft.NavigationDestination(
                    icon=ft.icons.LOGOUT_OUTLINED,
                    selected_icon=ft.icons.LOGOUT,
                ),
            ],
            on_change=self.change_selector,
        )

        self.left_bar = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=70,
            min_extended_width=200,
            group_alignment=-0.95,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.VIDEOCAM_OUTLINED,
                    selected_icon=ft.icons.VIDEOCAM,
                ),
                ft.NavigationRailDestination(
                    icon_content=ft.Badge(
                        content=ft.Icon(ft.icons.EMAIL_OUTLINED),
                        small_size=10),
                    selected_icon=ft.icons.EMAIL
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.DATA_OBJECT_OUTLINED,
                    selected_icon=ft.icons.DATA_OBJECT,
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.LOGOUT_OUTLINED,
                    selected_icon=ft.icons.LOGOUT,
                ),
            ],
            on_change=self.change_selector,
        )

    def generate(self, key):
        title = self.rec_data['title']
        self.page.dialog = None
        self.page.update()
        self.generate_alert_modal = ft.AlertDialog(
            # modal=True,
            title=ft.Text(
                title + '\n\nДуступ к GPT-3 временно закрыт, ожидается обновление 1.3.0\n\nДоступ к GPT возобновится 23.12.2023'),
            on_dismiss=lambda e: print("Modal dialog dismissed!"),
        )
        self.page.dialog = self.generate_alert_modal
        self.generate_alert_modal.open = True
        self.page.update()

    # RECORD_PAGE #

    def rec_page(self):
        self.records_page = ft.Column([
            self.records_header(),
            self.follow_up_view()
        ], alignment=ft.MainAxisAlignment.START)
        return self.records_page

    def click_follow_up(self, e):
        data = e.control.data
        print(data)
        self.follow_up_container.opacity = 0
        self.page.update()
        time.sleep(1)
        self.records_page.controls[1] = self.follow_up_view(data, opacity=0)
        self.follow_up_container.opacity = 1
        self.page.update()

    def _close_generate_follow_up(self, e):
        self.generate_modal.open = False
        self.page.update()

    def click_generate_follow_up(self, e):
        self.main_generate = ft.Column(
            [ft.Text("Можете закрыть окно", text_align=center_left), ft.ProgressRing(width=40, height=40)],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, height=100)
        self.close_modal_btn = ft.TextButton("Close", on_click=self._close_generate_follow_up)
        self.generate_modal = ft.AlertDialog(
            modal=True,
            content=self.main_generate,
            actions=[
                self.close_modal_btn
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: print("Modal dialog dismissed!"),
        )
        self.page.dialog = self.generate_modal
        self.generate_modal.open = True
        self.page.update()

        # self.in_gen_dict.append({self.rec_data['key']: True})

        th = threading.Thread(target=self.generate(self.rec_data['key']), args=(), daemon=True)
        th.start()
        th.join()

    def fv_main(self):
        try:
            emails = get_record_users_keys(self.rec_data['key'])
            email_str = ''
            for email in emails:
                email_str += email + ', '
            body = f'''
{self.rec_data['result']}

Запись: https://gulliver-group.ktalk.ru/recordings/{self.rec_data['key']}
'''
            mailto_url = f'mailto:{email_str}?body={body}&subject=Follow Up встречи {self.rec_data["title"]}'
        except:
            mailto_url = 'https://example.com'
        self.generate_btn = ft.ElevatedButton('Сгенерировать', icon=ft.icons.ADD,
                                              disabled=self.rec_data['is_can_generate'],
                                              on_click=self.click_generate_follow_up)
        self.send_btn = ft.ElevatedButton('Отправить', icon=ft.icons.SEND, disabled=self.rec_data['is_can_send'],
                                          url=mailto_url)
        self.fv_body.content = ft.Column(
            [
                ft.Container(content=ft.Column([ft.Text(self.rec_data['title'], size=24)], scroll=ft.ScrollMode.AUTO),
                             width=355,
                             height=70,
                             border_radius=5,
                             # bgcolor=ft.colors.GREY_700,
                             padding=0),
                ft.Row([
                    self.generate_btn,
                    self.send_btn
                ])
            ]
        )
        return self.fv_body

    def fv_questions(self):
        print(self.rec_data, 'data')
        self.fv_body.content = ft.Column(
            [
                ft.Container(content=ft.Column([
                    ft.TextField(
                        label='Вопросы на встрече',
                        value=self.rec_data['questions'],
                        multiline=True,
                        min_lines=10
                    )
                ], scroll=ft.ScrollMode.AUTO if self.page.width < 600 else None, expand=1),
                    height=300 if self.page.width < 600 else None
                ),
                ft.Container(content=ft.Column([
                    ft.TextField(
                        label='Ответы на поставленные вопросы',
                        value=self.rec_data['answers'],
                        multiline=True,
                        min_lines=10
                    )
                ], scroll=ft.ScrollMode.AUTO if self.page.width < 600 else None, expand=1),
                    height=300 if self.page.width < 600 else None
                ),
                ft.ElevatedButton('Главная страницa', data='main', on_click=self.click_change_fv_menu)
            ]
        )
        return self.fv_body

    def fv_tasks(self):
        self.fv_body.content = ft.Column(
            [
                ft.Container(content=ft.Column([
                    ft.TextField(
                        label='Поставленные задачи',
                        value=self.rec_data['tasks'],
                        multiline=True,
                        min_lines=10
                    )
                ], scroll=ft.ScrollMode.AUTO if self.page.width < 600 else None, expand=1),
                    height=300 if self.page.width < 600 else None
                ),
                ft.ElevatedButton('Главная страницa', data='main', on_click=self.click_change_fv_menu)
            ]
        )
        return self.fv_body

    def fv_total(self):
        self.fv_body.content = ft.Column(
            [
                ft.Container(content=ft.Column([
                    ft.TextField(
                        label='Итоги встречи',
                        value=self.rec_data['total'],
                        multiline=True,
                        min_lines=10
                    )
                ], scroll=ft.ScrollMode.AUTO if self.page.width < 600 else None, expand=1),
                    height=300 if self.page.width < 600 else None
                ),
                ft.ElevatedButton('Главная страницa', data='main', on_click=self.click_change_fv_menu)
            ]
        )
        return self.fv_body

    def fv_result(self):
        self.fv_body.content = ft.Column(
            [
                ft.Container(content=ft.Column([
                    ft.TextField(
                        label='Follow up',
                        value=self.rec_data['result'],
                        multiline=True,
                        min_lines=10
                    )
                ], scroll=ft.ScrollMode.AUTO if self.page.width < 600 else None, expand=1),
                    height=300 if self.page.width < 600 else None
                ),
                ft.ElevatedButton('Главная страницa', data='main', on_click=self.click_change_fv_menu)
            ]
        )
        self.page.update()
        return self.fv_body

    def click_change_fv_menu(self, e):
        if e.control.data == 'questions':
            self.fv_questions()
        if e.control.data == 'tasks':
            self.fv_tasks()
        if e.control.data == 'total':
            self.fv_total()
        if e.control.data == 'result':
            self.fv_result()
        if e.control.data == 'main':
            self.fv_main()
        self.page.update()

    def follow_up_view(self, data=None, opacity=1):
        data = {'title': ' '}
        data['questions'] = ' '
        data['answers'] = ' '
        data['tasks'] = ' '
        data['total'] = ' '
        data['result'] = ' '
        data['is_can_generate'] = True
        data['is_can_send'] = True
        data['generated_items'] = []

        self.rec_data = data

        self.follow_up_list = ft.Dropdown(
            width=180,
            height=70,
            label='Follow Up',
            options=[
            ],
            value='Создать',
        )
        if len(data['generated_items']) == 0:
            self.follow_up_list.options.append(ft.dropdown.Option('Создать'))
            # for i in data['generated_item']:
            #     self.follow_up_list.options.append(ft.dropdown.Option(i))
        else:
            for i in data['generated_items']:
                self.follow_up_list.options.append(ft.dropdown.Option(i))

        header = ft.Container(ft.Row([
            ft.Container(self.follow_up_list),
            ft.Container(ft.Row(
                [
                    ft.ElevatedButton(
                        'Вопросы',
                        icon=ft.icons.TEXTSMS_OUTLINED,
                        style=ft.ButtonStyle(shape=BTN_SHAPE),
                        on_click=self.click_change_fv_menu,
                        data='questions',
                    ),
                    ft.ElevatedButton(
                        'Задачи',
                        icon=ft.icons.TEXTSMS_OUTLINED,
                        style=ft.ButtonStyle(shape=BTN_SHAPE),
                        on_click=self.click_change_fv_menu,
                        data='tasks'
                    ),
                    ft.ElevatedButton(
                        'Итоги',
                        icon=ft.icons.TEXTSMS_OUTLINED,
                        style=ft.ButtonStyle(shape=BTN_SHAPE),
                        on_click=self.click_change_fv_menu,
                        data='total'
                    ),
                    ft.ElevatedButton(
                        'Результат',
                        icon=ft.icons.TEXTSMS_OUTLINED,
                        style=ft.ButtonStyle(shape=BTN_SHAPE),
                        on_click=self.click_change_fv_menu,
                        data='result'
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=10,
                scroll=ft.ScrollMode.ALWAYS
            ), margin=15)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, expand=1,
            scroll=ft.ScrollMode.AUTO if self.page.width < 600 else None))
        self.fv_body = ft.Container()
        main = ft.Container(
            ft.Column(
                [
                    header,
                    ft.Divider(height=3),
                    self.fv_main()
                ]
            )
        )
        self.follow_up_container = ft.Container(
            main,
            padding=10,
            border_radius=10,
            bgcolor=ft.colors.GREY_900,
            expand=None,
            opacity=opacity,
            animate_opacity=300,
            animate_size=300
        )
        return self.follow_up_container

    def build_records(self, query=None, date=None):
        recordings = self.db.get_recordings(self.user_email)
        records_row = ft.Row([], scroll=ft.ScrollMode.AUTO)
        for rec in recordings:
            data = {'key': rec[2], 'title': rec[3]}

            record = ft.Container(content=ft.Column([
                ft.Row([
                    ft.Container(content=ft.Row([
                        ft.Text(format_datetime_custom(rec[4]), size=16)]),
                        border_radius=10,
                        bgcolor=ft.colors.GREY_700,
                        padding=7),
                    ft.Container(content=ft.Row([
                        ft.Text(minutes_to_time(int(rec[5])), size=16)]),
                        border_radius=10,
                        bgcolor=ft.colors.GREY_700,
                        padding=7),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(content=ft.Column([ft.Text(rec[3], size=24)], scroll=ft.ScrollMode.AUTO),
                             width=355,
                             height=70,
                             border_radius=5,
                             # bgcolor=ft.colors.GREY_700,
                             padding=0),
                ft.Row([
                    ft.Container(content=ft.Row([
                        ft.Icon(ft.icons.GROUP, size=16),
                        ft.Text(f'Участники (3)', size=16)]),
                        border_radius=10,
                        bgcolor=ft.colors.GREY_700,
                        padding=7),
                ]),
                ft.Row([
                    ft.ElevatedButton(
                        'Follow Up',
                        icon=ft.icons.TEXTSMS_OUTLINED,
                        style=ft.ButtonStyle(shape=BTN_SHAPE),
                        on_click=self.click_follow_up,
                        data=data,
                        expand=1
                    ),
                    ft.IconButton(
                        icon=ft.icons.MESSAGE_OUTLINED,
                        style=ft.ButtonStyle(shape=BTN_SHAPE),
                        on_click=self.transcript,
                        data=data
                    ),
                    ft.IconButton(
                        icon=ft.icons.LINK,
                        style=ft.ButtonStyle(shape=BTN_SHAPE),
                        url=f'https://gulliver-group.ktalk.ru/recordings/{data["key"]}',
                        data=data
                    )])
            ]),
                padding=20,
                width=370,
                height=260,
                border_radius=15,
                bgcolor=ft.colors.GREY_800)
            records_row.controls.append(record)
        return records_row

    def records_header(self):
        #  SEARCH BOX ELEMENTS
        self.records_search_text_filed = ft.TextField(label='Поиск', multiline=False, on_submit=self.search_submit,
                                                      expand=1)
        self.records_search_date_picker = ft.DatePicker(
            first_date=datetime.datetime(2023, 10, 1),
            last_date=datetime.datetime(2024, 10, 1),
            # locale='ru-RU',
            cancel_text='Отмена',
            confirm_text='Готово',
            error_format_text='Недопустимый формат',
            error_invalid_text='Вне диапазона',
            field_label_text='Введите дату',
            help_text='Выбрать дату',
            on_change=self.choose_date,
        )
        self.records_search_date_picker_btn = ft.IconButton(icon=ft.icons.CALENDAR_TODAY,
                                                            on_click=self.open_date_picker)
        #  SEARCH BOX CONTAINERS
        self.records_search_box = ft.Row(
            [
                self.records_search_text_filed,
                self.records_search_date_picker_btn,
            ],
            alignment=ft.MainAxisAlignment.START
        )

        #  RECORDS BOX ELEMENTS
        self.record_list_title = ft.Container(content=ft.Row([
            ft.Icon(ft.icons.FIBER_MANUAL_RECORD),
            ft.Text('Записи', size=22)]),
            padding=5)
        #  RECORDS BOX CONTAINERS
        self.records_list = ft.Container(content=self.build_records(), border_radius=5, animate_opacity=300)
        self.records_container = ft.Container(
            content=ft.Column([
                self.records_search_box,
                self.record_list_title,
                self.records_list
            ]),
            padding=10,
            border_radius=10,
            bgcolor=ft.colors.GREY_900,
            expand=None,
            animate_size=300
        )
        return self.records_container

    def transcript(self, e):
        data = e.control.data
        transcript_data = collect_dialogue(self.api.get_transcription_for_key(data['key']))
        chat = ft.Column(
            [

            ],
            height=self.page.height - 170 if self.page.width < 810 else self.page.height - 70,
            scroll=ft.ScrollMode.AUTO
        )
        for message in transcript_data:
            msg = ft.Container(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Container(
                                    ft.Text(message['speaker']),
                                    border_radius=5,
                                    bgcolor=ft.colors.TEAL_700,
                                    padding=5
                                ),
                                ft.Container(
                                    ft.Text(millis_to_time(message['start_time'])),
                                    border_radius=5,
                                    bgcolor=ft.colors.TEAL_700,
                                    padding=5
                                ),
                            ], scroll=ft.ScrollMode.AUTO
                        ),
                        ft.Container(
                            ft.Text(message['text'])
                        )
                    ]
                )
            )
            chat.controls.append(msg)
            chat.controls.append(ft.Divider(height=3))

        self.dlg_transcript = ft.AlertDialog(
            title=ft.Text(data['title']),
            content=ft.Container(
                content=chat,
            ),
            on_dismiss=lambda e: print("Dialog dismissed!")
        )
        self.page.dialog = self.dlg_transcript
        self.page.update()
        self.dlg_transcript.open = True
        self.page.update()

    def search_submit(self, e):
        print(e.control.value)
        self.records_list.opacity = 0
        self.page.update()
        time.sleep(1)
        self.records_list.content = self.build_records(
            query=self.records_search_text_filed.value,
            date=self.records_search_date_picker.value
        )
        self.records_list.opacity = 1
        self.page.update()

    def open_date_picker(self, e):
        self.page.overlay.append(self.records_search_date_picker)
        self.page.update()
        self.records_search_date_picker.pick_date()

    def choose_date(self, e):
        print(e.control.value)
        self.records_list.opacity = 0
        self.page.update()
        time.sleep(1)
        self.records_list.content = self.build_records(
            query=self.records_search_text_filed.value,
            date=self.records_search_date_picker.value
        )
        self.records_list.opacity = 1
        self.page.update()

    # MAIL PAGE #
    def send_page(self):
        main = ft.Container()

    def mail_page(self):
        msgs = ft.Column(scroll=ft.ScrollMode.AUTO)
        [msgs.controls.append(self.messages()) for _ in range(10)]
        if self.page.width < 810:
            msgs.height = self.page.height - 170
        else:
            msgs.height = self.page.height - 90
        header = ft.Column(
            [
                ft.Container(ft.Row([
                    ft.Icon(ft.icons.MAIL, size=22),
                    ft.Text('Рассылки', size=22)
                ])),
                ft.Divider(height=3),
                msgs
            ]
        )
        main = ft.Container(
            content=header,
            padding=10,
            border_radius=10,
            bgcolor=ft.colors.GREY_900,
        )

        return main

    def messages(self):
        time_send = ft.Container(
            ft.Text('23, Ноября 14:54'),
            border_radius=5,
            bgcolor=ft.colors.BLUE_GREY_900,
            padding=5
        )
        rec_title = ft.Container(
            ft.Text('Новая запись'),
            border_radius=5,
            bgcolor=ft.colors.BLUE_GREY_900,
            padding=5
        )
        users = ft.Container(
            ft.Row([
                ft.Container(
                    ft.Text('Иван Иванов Иванович', size=18),
                    border_radius=5,
                    bgcolor=ft.colors.BLUE_GREY_900,
                    padding=5
                ) for _ in range(10)
            ],
                scroll=ft.ScrollMode.ADAPTIVE
            ),
            padding=5,
            height=50,
            border_radius=10,
            border=ft.border.all(3, ft.colors.GREY_600)
        )
        follow_up_btn = ft.Container(
            ft.Row(
                [
                    ft.ElevatedButton(
                        'Follow Up',
                        icon=ft.icons.TEXTSMS_OUTLINED,
                        style=ft.ButtonStyle(shape=BTN_SHAPE)
                    ),
                    ft.ElevatedButton(
                        'Запись',
                        icon=ft.icons.VIDEOCAM,
                        style=ft.ButtonStyle(shape=BTN_SHAPE)
                    )
                ]
            )
        )
        return ft.Container(ft.Column([
            ft.Container(ft.Row([
                time_send,
                rec_title,
            ]),
            ),
            users,
            follow_up_btn
        ]),
            padding=10,
            border_radius=15,
            bgcolor=ft.colors.GREY_800
        )

    # AI CHAT PAGE #
    def aichat_page(self):
        msg_list = ft.Column()
        [msg_list.controls.append(self.own_message()) for _ in range(2)]
        [msg_list.controls.append(self.ai_message()) for _ in range(2)]
        main = ft.Container(
            ft.Column(
                [
                    ft.Container(expand=1, content=msg_list, border=ft.border.all(3, color=ft.colors.GREY_700),
                                 border_radius=10, margin=5, padding=10),
                    ft.Container(expand=0, content=ft.Row([ft.TextField(expand=1, multiline=True, label='Сообщение',
                                                                        border_width=3, border_color=ft.colors.GREY_700,
                                                                        border_radius=10),
                                                           ft.IconButton(icon=ft.icons.SEND)]), height=70, margin=5)
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=10
            ),
            padding=10,
            border_radius=15,
            bgcolor=ft.colors.GREY_800
        )
        if self.page.width < 810:
            main.height = self.page.height - 100
        else:
            main.height = self.page.height - 20
        return main

    def own_message(self):

        msg = ft.Container(
            ft.Row([
                ft.Text('Иван Иванов'),
                ft.CircleAvatar(
                    foreground_image_url="https://avatars.githubusercontent.com/u/_5041459?s=88&v=4",
                    content=ft.Text("ИИ"),
                ),
            ],

                alignment=ft.MainAxisAlignment.END),
            padding=10,
            border_radius=10,
        )
        main = ft.Container(msg)
        return main

    def ai_message(self):

        msg = ft.Container(
            ft.Row([ft.Text('Привет')], alignment=ft.MainAxisAlignment.START),
            padding=10,
            border_radius=10,
            bgcolor=ft.colors.GREY_900,
        )
        main = ft.Container(msg)
        return main

    # АВТОРИЗАЦИЯ #
    def click_logout(self, e):
        self.page.clean()
        self.page.client_storage.set("login", "False")
        self.page.add(self.auth_page())

    def check_user_pass(self, e):
        def get_main_vw():
            self.page.clean()
            self.page.client_storage.set("login", "True")
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
        def check_details():
            dlg = ft.AlertDialog(
                title=ft.Text("Неверный логин или пароль\nПроверьте поля авторизации"),
                on_dismiss=lambda e: print("Dialog dismissed!")
            )
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()

        login = self.email_field.value
        pswd = self.password_field.value
        # 'motovilov.aa@gulliver-group.com', 'uEQU6kmw'
        if login and pswd:
            if login.replace(' ', '') == '' and pswd.replace(' ', '') == '':
                return print('data is empty')
            else:
                print(login, pswd)
                details = self.db.get_user(login)
                if details:
                    details = details[0]
                    print(details)
                    if details[7]:
                        if PasswordEncryptor.check_password(details[7], pswd):
                            # Пропускаем
                            get_main_vw()
                        else:
                            check_details()
                            return
                    else:
                        queue = Queue()

                        def web_sess(queue, login, pswd):
                            with sync_playwright() as playwright:
                                if run(playwright, login, pswd) is True:
                                    queue.put(True)
                                else:
                                    queue.put(False)

                        thread = threading.Thread(target=web_sess, args=(queue, login, pswd))
                        self.bar_auth.visible = True
                        self.page.update()
                        thread.start()
                        thread.join()
                        result = queue.get()
                        self.bar_auth.visible = False
                        self.page.update()
                        print(result)
                        if str(result) == "False":
                            check_details()
                            return
                        else:
                            hashed_password = PasswordEncryptor.encrypt(pswd)
                            self.db.add_hashed_password(login, hashed_password)
                            # Пропускаем
                            get_main_vw()
                else:
                    check_details()
                    return

    def auth_page(self):
        print(PF + ' Authorization page')
        self.bar_auth = ft.ProgressBar(width=400, color=ft.colors.GREEN_600, bgcolor="#eeeeee", visible=False)
        self.page.clean()
        self.page.update()
        self.email_field = ft.TextField(label="SSO Email", width=350)
        self.password_field = ft.TextField(label="Password", width=350, password=True)
        main = ft.Container(
            content=ft.Column(
                [
                    ft.Container(ft.Text("Авторизация", size=24), margin=40),
                    self.email_field,
                    self.password_field,
                    ft.Container(ft.ElevatedButton('Войти', on_click=self.check_user_pass), margin=20),
                    ft.Container(self.bar_auth, width=250)
                ], alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            border_radius=10,
            width=400,
            height=400,
            bgcolor=ft.colors.GREY_900
        )
        return ft.Row([main], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def change_selector(self, e):
        item_index = e.control.selected_index
        if int(item_index) == 0:
            self.page.scroll = False
            self.main_view.controls.clear()
            self.main_view.controls.append(self.rec_page())
            self.page.update()
            return
        # if int(item_index) == 1:
        #     self.page.scroll = False
        #     self.main_view.controls.clear()
        #     self.main_view.controls.append(self.mail_page())
        #     self.page.update()
        #     return
        # if int(item_index) == 2:
        #     self.page.scroll = True
        #     self.main_view.controls.clear()
        #     self.main_view.controls.append(self.aichat_page())
        #     self.page.update()
        #     return
        if int(item_index) == 3:
            self.click_logout(None)
            return
