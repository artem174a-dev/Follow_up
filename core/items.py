import datetime
import locale
import threading
import time
from queue import Queue

from babel.dates import format_datetime
import tzlocal
import pytz

import flet as ft
from playwright.sync_api import sync_playwright

from core.gpt import GPT
from core.mail import report
from ktolk.api import Client, get_record_users_keys, collect_dialogue
from database.database import SQL
from core.passwords import PasswordEncryptor, run

BTN_SHAPE = {
    ft.MaterialState.HOVERED: ft.RoundedRectangleBorder(radius=10),
    ft.MaterialState.DEFAULT: ft.RoundedRectangleBorder(radius=10),
}

PF = '[*]'


# def format_datetime_custom(source_string):
#     dt_object = datetime.datetime.strptime(source_string, "%Y-%m-%d %H:%M")
#
#     # Автоматическое определение локального часового пояса
#     local_tz = tzlocal.get_localzone()
#     dt_object_local = dt_object.replace(tzinfo=pytz.utc).astimezone(local_tz)
#
#     try:
#         # Попытка установить локаль, например, на русскую
#         locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
#     except locale.Error:
#         # В случае ошибки локализации, можно попробовать установить локаль на английскую
#         locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
#
#     # Форматирование даты в строку
#     result_string = format_datetime(dt_object_local, format="d MMMM, HH:mm")
#
#     return result_string


def format_datetime_custom(source_string):
    # dt_object = datetime.datetime.strptime(source_string, "%Y-%m-%d %H:%M")

    # # Автоматическое определение локального часового пояса
    # local_tz = tzlocal.get_localzone()
    # dt_object_local = dt_object.replace(tzinfo=pytz.utc).astimezone(local_tz)

    # Форматирование даты в строку без явного указания локали
    # result_string = format_datetime(dt_object, format="d MMMM, HH:mm")

    return source_string


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
        self.user_email = None
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
        self.main_view = ft.Column([self.rec_page()], scroll=ft.ScrollMode.ALWAYS)

        self.down_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationDestination(
                    icon=ft.icons.VIDEOCAM_OUTLINED,
                    selected_icon=ft.icons.VIDEOCAM,
                ),
                ft.NavigationDestination(
                    icon=ft.icons.EMAIL_OUTLINED,
                    selected_icon=ft.icons.EMAIL,
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
                    icon=ft.icons.EMAIL_OUTLINED,
                    selected_icon=ft.icons.EMAIL,
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
        print('[*] Record Page')
        self.records_page = ft.Column([
            self.records_header(),
            self.follow_up_view()
        ], alignment=ft.MainAxisAlignment.START)
        return self.records_page

    def save_red_fv(self, e):
        e.control.content = ft.Icon(ft.icons.CHECK, scale=0.7)
        e.control.disabled = True
        e.control.update()

        data = e.control.data
        SQL().update_fv(data['rec_key'], {"text": self.edit_fv_text_field.value}, self.edit_fv_name_field.value)

        e.control.content = None
        e.control.disabled = False
        e.control.update()


    def new_generate(self, e):
        print('[*] Start regenerate')
        data = e.control.data
        self.edit_fv_regenerate_btn.disabled = True
        e.control.content=ft.ProgressRing(scale=0.7)
        self.edit_fv_regenerate_btn.update()
        summary_data = self.db.get_summary_data(data['rec_key'])[0][2]
        summary_text = ''
        for item in summary_data:
            summary_text += f"[{item['user']}]-({item['post']})> {item['text']}"

        def create_follow_up():
            follow_up = GPT().streaming(summary_text)
            self.edit_fv_text_field.value = ''
            for chunk in follow_up:
                try:
                    self.edit_fv_text_field.value += chunk.choices[0].delta.content
                    self.edit_fv_text_field.update()
                except:
                    continue

        thread = threading.Thread(target=create_follow_up)
        thread.start()
        thread.join()

        self.edit_fv_regenerate_btn.disabled = False
        e.control.content = None
        self.edit_fv_regenerate_btn.update()

    def update_edit_fv_name(self, e):
        self.edit_fv_text_field.label = self.edit_fv_name_field.value
        self.edit_fv_text_field.update()

    def edit_fv(self, e):
        data = e.control.data
        self.edit_fv_name_field = ft.TextField(value=data['fv_name'], label='Название', multiline=False,
                                               on_change=self.update_edit_fv_name)
        self.edit_fv_text_field = ft.TextField(value=data['fv_text'], label=self.edit_fv_name_field.value, expand=1,
                                               multiline=True)

        self.edit_fv_regenerate_btn = ft.ElevatedButton('Пересоздать', on_click=self.new_generate, data=data, disabled=False)
        fv = ft.Container(ft.Column([
            self.edit_fv_name_field,
            self.edit_fv_text_field,
            ft.Row([
                self.edit_fv_regenerate_btn,
                ft.ElevatedButton('Сохранить', on_click=self.save_red_fv, data=data)
            ], alignment=ft.MainAxisAlignment.END)
        ]))

        self.dlg_edit_fv = ft.AlertDialog(
            title=ft.Text(f'Редактирование'),
            content=ft.Container(
                content=fv,
                width=self.page.width
            ),
            on_dismiss=lambda e: print("Dialog dismissed!")
        )
        self.page.dialog = self.dlg_edit_fv
        self.page.update()
        self.dlg_edit_fv.open = True
        self.page.update()

    def func_fv_list(self, query):
        result = self.db.get_fvs(self.page.client_storage.get('email'), query)
        if not result:
            return ft.Column([
                ft.Container(
                    ft.Column([
                        ft.Row([
                            ft.Text("Follow up не найдены. Выберите запись и создайте новый Follow Up",
                                    size=14, weight=ft.FontWeight.BOLD)
                        ], alignment=ft.MainAxisAlignment.CENTER)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    border_radius=3,
                    height=70,
                    border=ft.Border(None, None, ft.BorderSide(width=2, color=ft.colors.WHITE)),
                    padding=5
                )
            ])
        out = ft.Column()
        for item in result:
            message_data = {'rec_key': item[1],
                            'rec_title': item[2],
                            'fv_name': item[3],
                            'creator_name': item[4],
                            'creator_email': item[5],
                            'fv_text': item[6]['text'],
                            'fv_create_stamp': item[7]}
            out.controls.append(
                ft.Container(
                    ft.Column([
                        ft.Row([
                            ft.Container(ft.Text(item[2]), padding=3, border_radius=3, bgcolor=ft.colors.TEAL_700),
                            ft.Container(ft.Text(format_datetime_custom(str(item[7])[:16])), padding=3, border_radius=3,
                                         bgcolor=ft.colors.TEAL_700)
                        ]),
                        ft.Container(ft.Text('@' + item[5]), padding=3, border_radius=3,
                                     bgcolor=ft.colors.DEEP_ORANGE_600, opacity=0.7),
                        ft.Container(ft.Row([
                            ft.Text(item[3].capitalize(), size=18, weight=ft.FontWeight.BOLD),
                            ft.Row([
                                ft.IconButton(icon=ft.icons.EDIT, icon_color=ft.colors.BLUE_400, disabled=False,
                                              opacity=0.3, on_click=self.edit_fv, data=message_data),
                                ft.IconButton(icon=ft.icons.SEND, icon_color=ft.colors.TEAL_700,
                                              on_click=self.send_message_page, data=message_data)
                            ], alignment=ft.MainAxisAlignment.END)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            margin=ft.Margin(left=0, right=0, top=10, bottom=10))
                    ]),
                    border_radius=2,
                    border=ft.Border(None, None, ft.BorderSide(width=1, color=ft.colors.WHITE)),
                    padding=5,
                    margin=ft.Margin(left=0, right=0, top=0, bottom=10)
                )
            )
        return out

    def search_follow_up(self, e):
        print(e.control.value)
        self.fvs_list.content = self.func_fv_list(e.control.value)
        self.fvs_list.update()

    def follow_up_view(self, data=None, opacity=1):
        self.fv_search_field = ft.TextField(
            label='Поиск',
            border_color=ft.colors.GREY_700,
            focused_border_color=ft.colors.WHITE,
            on_submit=self.search_follow_up,
            expand=1
        )
        body_nav = ft.Column([
            ft.Container(ft.Row([
                self.fv_search_field
            ],
                expand=1))
        ])
        self.fvs_list = ft.Container(self.func_fv_list(''))
        body = ft.Column(
            [
                ft.Container(body_nav),
                self.fvs_list
            ]
        )
        header = ft.Row([
            ft.Row([ft.Icon(ft.icons.TEXT_SNIPPET),
                    ft.Container(ft.Text('Фоллоу апы', size=22))], alignment=ft.MainAxisAlignment.START),
            ft.Container(ft.ElevatedButton('Назад', icon=ft.icons.ARROW_BACK_IOS_NEW_OUTLINED, visible=False))
        ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            expand=1
        )
        self.fv_body = ft.Container()
        main = ft.Container(
            ft.Column(
                [
                    ft.Container(header),
                    ft.Container(ft.Divider(height=3)),
                    ft.Container(body)
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

    def click_save_fv(self, e):
        if len(self.fv_name_filed.value) < 3:
            return
        record_data = e.control.data
        self.db.add_fv(record_data, {"text": self.fv_field.value}, self.fv_name_filed.value,
                       self.page.client_storage.get('user_key'), self.page.client_storage.get('email'))
        view = ft.Container(ft.Column([
            ft.Icon(ft.icons.CHECK, scale=12)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, height=300,
            width=300))
        self.dlg_create_fv.content = view
        self.page.update()

        self.fv_name_filed.value = ''
        self.fvs_list.content = self.func_fv_list(' ')
        self.fvs_list.update()

    def change_filed_name_fv(self, e):
        if len(self.fv_name_filed.value) < 3:
            self.fv_name_filed.border_color = ft.colors.RED
            self.fv_name_filed.update()
        else:
            self.fv_name_filed.border_color = ft.colors.GREEN_600
            self.fv_name_filed.update()

    def save_fv(self, e):
        record_data = e.control.data
        self.fv_name_filed = ft.TextField(label='Имя генерации', on_submit=self.click_save_fv, data=record_data)
        view = ft.Container(ft.Column([
            self.fv_name_filed,
            ft.ElevatedButton(opacity=0),
            ft.ElevatedButton('Готово', on_click=self.click_save_fv, data=record_data)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, height=300,
            width=300))
        self.dlg_create_fv.content = view
        self.page.update()

    def next_plan_create_fv(self, e):
        record_data = e.control.data
        summary_data = self.db.get_summary_data(record_data['key'])[0][2]
        summary_text = ''
        for item in summary_data:
            summary_text += f"[{item['user']}]-({item['post']})> {item['text']}"
        view = ft.Container(ft.Column([
            ft.Text('Follow Up готовится...'),
            ft.ProgressRing()
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, height=300,
            width=300))
        self.dlg_create_fv.content = view
        self.page.update()

        def create_follow_up():
            self.fv_field = ft.TextField(value=' ', multiline=True, border=ft.InputBorder.NONE)
            progress = ft.ProgressRing(scale=0.5)
            view = ft.Column([self.fv_field], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                             scroll=ft.ScrollMode.AUTO)
            self.dlg_create_fv.title = ft.Row([ft.Text(f'Follow Up: {record_data["title"]}'), progress])
            self.dlg_create_fv.content = ft.Container(
                view,
                width=self.page.width)
            follow_up = GPT().streaming(summary_text)
            self.page.update()
            for chunk in follow_up:
                try:
                    self.fv_field.value += chunk.choices[0].delta.content
                    self.fv_field.update()
                except:
                    break
            progress.visible = False
            record_data['follow_up'] = self.fv_field.value
            view.controls.append(
                ft.Row([ft.ElevatedButton('Пересоздать', on_click=self.next_plan_create_fv, data=record_data),
                        ft.ElevatedButton('Сохранить', on_click=self.save_fv, data=record_data)]))
            self.page.update()

        thread = threading.Thread(target=create_follow_up)
        thread.start()

    def create_follow_up(self, e):
        record_data = e.control.data
        print(record_data)
        summary_data = self.db.get_summary_data(record_data['key'])[0][2]
        summary = ft.Column([], scroll=ft.ScrollMode.AUTO)
        for item in summary_data:
            summary.controls.append(
                ft.Container(ft.Column([
                    ft.Row([
                        ft.Icon(ft.icons.FIBER_MANUAL_RECORD, size=14),
                        ft.Container(ft.Text(item['user']), padding=2, border_radius=3, bgcolor=ft.colors.TEAL_700),
                    ]),
                    ft.Container(
                        ft.TextField(value=item['text'].capitalize(), border=ft.InputBorder.NONE, multiline=True),
                        margin=ft.Margin(left=22, right=0, top=0, bottom=0)),
                    ft.Divider(height=3, color=ft.colors.WHITE)
                ]))
            )
        summary.controls.append(ft.Container(
            ft.Row([ft.ElevatedButton('Дальше', on_click=self.next_plan_create_fv, data=record_data)],
                   alignment=ft.MainAxisAlignment.END)))
        self.dlg_create_fv = ft.AlertDialog(
            title=ft.Text(record_data['title']),
            content=ft.Container(
                content=summary,
                width=self.page.width
            ),
            on_dismiss=lambda e: print("Dialog dismissed!")
        )
        self.page.dialog = self.dlg_create_fv
        self.page.update()
        self.dlg_create_fv.open = True
        self.page.update()

    def build_records(self, query=None, date=None):
        recordings = self.db.get_recordings(self.page.client_storage.get('email'))
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
                        ft.Text(f'Участники ({rec[6]})', size=16)]),
                        border_radius=10,
                        bgcolor=ft.colors.GREY_700,
                        padding=7),
                ]),
                ft.Row([
                    ft.ElevatedButton(
                        'Follow Up',
                        icon=ft.icons.TEXTSMS_OUTLINED,
                        style=ft.ButtonStyle(shape=BTN_SHAPE),
                        on_click=self.create_follow_up,
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
                                                      border_color=ft.colors.GREY_700,
                                                      focused_border_color=ft.colors.WHITE,
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
    def click_send(self, e):
        msg_data = e.control.data
        progress = ft.ProgressRing()
        status = ft.Text('Отправка сообщений...')
        logs = ft.Text(value='')
        main = ft.Container(ft.Column([
            ft.Row([status, progress]),
            ft.Column([logs], scroll=ft.ScrollMode.AUTO)
        ]), height=300, width=300)
        self.dlg_mail_form.content = main
        self.page.update()

        receivers = self.users_get_msgs_filed.value.split(', ')
        for user in receivers:
            user = user.lower()
            user = user.strip()
            if report(body=self.body_message.value, subject=self.subject_message.value, receiver=user,
                      mail_from=msg_data['creator_email']) == True:
                logs.value += f'[*] Сообщение отправленно. \n[*] Получатель: {user}\n\n'
                logs.update()

        progress.visible = False
        status.value = "Сообщения отправлены"
        status.update()
        progress.update()

    def send_message_page(self, e):
        msg_data = e.control.data
        users_records = self.db.get_users_email_for_record(msg_data['rec_key'])
        self.subject_message = ft.TextField(value='Follow Up: ' + msg_data['rec_title'], border_color=ft.colors.WHITE,
                                            focused_border_color=ft.colors.GREEN_600, border_radius=1,
                                            border=ft.InputBorder.UNDERLINE, expand=1)
        self.body_message = ft.TextField(value=msg_data['fv_text'], label='Сообщение', multiline=True,
                                         border_color=ft.colors.WHITE, focused_border_color=ft.colors.GREEN_600,
                                         border_radius=1, border=ft.InputBorder.OUTLINE, expand=1)
        self.users_get_msgs_filed = ft.TextField(label='Получатели',
                                                 value=' '.join(user[1] + ", " for user in users_records),
                                                 multiline=True, border_color=ft.colors.WHITE,
                                                 focused_border_color=ft.colors.GREEN_600, border_radius=1,
                                                 border=ft.InputBorder.OUTLINE, expand=1)
        main = ft.Column([
            ft.Row([
                ft.Text('Тема: ', size=18, weight=ft.FontWeight.BOLD),
                self.subject_message
            ]),
            self.body_message,
            # ft.Row([
            #     ft.Text('Получатели: ', size=18, weight=ft.FontWeight.BOLD),
            #     # ft.IconButton(icon=ft.icons.PERSON_ADD_ALT_SHARP, icon_color=ft.colors.TEAL)
            # ]),
            ft.Row([
                self.users_get_msgs_filed
            ]),
            ft.Row([ft.ElevatedButton("Отправить", on_click=self.click_send, data=msg_data)],
                   alignment=ft.MainAxisAlignment.END)
        ])
        self.dlg_mail_form = ft.AlertDialog(
            title=ft.Text('Отправка сообщения'),
            content=ft.Container(
                content=ft.Container(main, width=self.page.width),
            ),
        )
        self.page.dialog = self.dlg_mail_form
        self.page.update()
        self.dlg_mail_form.open = True
        self.page.update()

    def mail_page(self):
        msgs = ft.Column(scroll=ft.ScrollMode.AUTO)
        msgs.controls.append(self.messages())
        header = ft.Column(
            [
                ft.Container(ft.Row([
                    ft.Row([ft.Icon(ft.icons.MAIL, size=22),
                            ft.Text('Почта', size=22)], alignment=ft.MainAxisAlignment.START),
                    # ft.Row([
                    #     ft.ElevatedButton('Входящие', icon=ft.icons.MOVE_TO_INBOX_OUTLINED),
                    #     ft.ElevatedButton('Исходящие', icon=ft.icons.SEND)
                    # ], alignment=ft.MainAxisAlignment.END)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)),
                ft.Divider(height=3)
            ]
        )
        main = ft.Container(
            content=ft.Column([header,
                               msgs], alignment=ft.MainAxisAlignment.START),
            padding=10,
            border_radius=10,
            bgcolor=ft.colors.GREY_900,
        )

        return main

    def messages(self):
        owner_msgs = self.db.get_my_send_msgs(self.page.client_storage.get('key'))
        if not owner_msgs:
            return ft.Container()
        else:
            out_col = ft.Column([])
            for msg in owner_msgs:
                out_col.controls.append(
                    ft.Container()
                )
            return ft.Container(out_col)
        # time_send = ft.Container(
        #     ft.Text('23, Ноября 14:54'),
        #     border_radius=5,
        #     bgcolor=ft.colors.BLUE_GREY_900,
        #     padding=5
        # )
        # rec_title = ft.Container(
        #     ft.Text('Новая запись'),
        #     border_radius=5,
        #     bgcolor=ft.colors.BLUE_GREY_900,
        #     padding=5
        # )
        # users = ft.Container(
        #     ft.Row([
        #         ft.Container(
        #             ft.Text('Иван Иванов Иванович', size=18),
        #             border_radius=5,
        #             bgcolor=ft.colors.BLUE_GREY_900,
        #             padding=5
        #         ) for _ in range(10)
        #     ],
        #         scroll=ft.ScrollMode.ADAPTIVE
        #     ),
        #     padding=5,
        #     height=50,
        #     border_radius=10,
        #     border=ft.border.all(3, ft.colors.GREY_600)
        # )
        # follow_up_btn = ft.Container(
        #     ft.Row(
        #         [
        #             ft.ElevatedButton(
        #                 'Follow Up',
        #                 icon=ft.icons.TEXTSMS_OUTLINED,
        #                 style=ft.ButtonStyle(shape=BTN_SHAPE)
        #             ),
        #             ft.ElevatedButton(
        #                 'Запись',
        #                 icon=ft.icons.VIDEOCAM,
        #                 style=ft.ButtonStyle(shape=BTN_SHAPE)
        #             )
        #         ]
        #     )
        # )
        # return ft.Container(ft.Column([
        #     ft.Container(ft.Row([
        #         time_send,
        #         rec_title,
        #     ]),
        #     ),
        #     users,
        #     follow_up_btn
        # ]),
        #     padding=10,
        #     border_radius=15,
        #     bgcolor=ft.colors.GREY_800
        # )

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
        self.page.update()

    def check_user_pass(self, e):
        def get_main_vw():
            self.page.clean()
            self.page.client_storage.set("login", "True")
            self.page.client_storage.set("email", login)
            self.page.client_storage.set("user_key", user_key)
            self.user_email = login

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
                        ft.Container(expand=1, content=self.main_view),

                    ],
                    height=self.page.height,
                    vertical_alignment=ft.CrossAxisAlignment.START,
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
                return
            else:
                details = self.db.get_user(login)
                print(details)
                if details:
                    details = details[0]
                    user_key = details[1]
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
        if int(item_index) == 1:
            self.page.scroll = False
            self.main_view.controls.clear()
            self.main_view.alignment = ft.MainAxisAlignment.START
            self.main_view.controls.append(self.mail_page())
            self.page.update()
            return
        # if int(item_index) == 2:
        #     self.page.scroll = True
        #     self.main_view.controls.clear()
        #     self.main_view.controls.append(self.aichat_page())
        #     self.page.update()
        #     return
        if int(item_index) == 3:
            self.click_logout(None)
            return
