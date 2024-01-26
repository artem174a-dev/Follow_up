from datetime import datetime

from database.database import SQL
from ktolk.api import Client


class Updates:
    def __init__(self):
        self.api = Client()

    def __add_records(self):
        result = self.api.get_recordings(100)
        records = SQL().get_records_list()
        success_publish_rec = 0
        error_publish_rec = 0
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] | Start update records')
        for rec in result:
            key = rec.get('key', '')
            if not any(key in tpl for tpl in records):
                continue
            title = rec.get('title', '')
            create_date = rec.get('createdDate', '')
            participants = rec.get('participantsCount')
            size = rec.get('size', ('',)),
            duration = rec.get('duration', '')
            users_key = []

            if participants <= 10:
                participants_list = rec.get('participants')
            else:
                participants_list = self.api.get_users_for_key(key)

            for user in participants_list:
                user_info = user.get('userInfo', {'key': 'None'})
                users_key.append(user_info['key'])
            try:
                SQL().add_record(key, title, create_date, users_key, size[0], duration)
            except Exception as e:
                error_publish_rec += 1
                print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] | Add records | ERROR: {e}')
            else:
                success_publish_rec += 1
        print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] | Add records | Success: {success_publish_rec} / Error: {error_publish_rec}')


    def __add_transcriptions(self):
        pass