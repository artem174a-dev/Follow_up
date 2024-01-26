import json

import requests

from database.database import SQL

API_KEY = 'Y7H12KplHperx2i8LaJWU1EXlRp7ChfT'
PF = '[*]'


class Client:
    def __init__(self):
        self.api_key = API_KEY
        self.space = 'gulliver-group'
        self.base_url = f'https://{self.space}.ktalk.ru/api/'

    def get_users(self):
        endpoint = 'users/scan'
        query_params = {
            'top': 1000,
        }

        headers = {
            'X-Auth-Token': self.api_key
        }

        url = f'{self.base_url}{endpoint}'
        response = requests.get(url, params=query_params, headers=headers)

        if response.status_code == 200:
            return response.json().get('users', [])
        else:
            print(f"Error: {response.status_code}")
            return None

    def get_user_info_by_email(self, email):
        endpoint = 'users'
        query_params = {
            'query': email,
            'fillInMeetingStatus': 'true'
        }

        headers = {
            'X-Auth-Token': self.api_key
        }

        url = f'{self.base_url}{endpoint}'
        response = requests.get(url, params=query_params, headers=headers)

        if response.status_code == 200:
            return response.json().get('users', [])
        else:
            print(f"Error: {response.status_code}")
            return None

    def get_user_info_by_key(self, key):
        endpoint = 'users'
        query_params = {
        }

        headers = {
            'X-Auth-Token': self.api_key
        }

        url = f'{self.base_url}{endpoint}'
        response = requests.get(url, params=query_params, headers=headers)

        if response.status_code == 200:
            return response.json().get('users', [])
        else:
            print(f"Error: {response.status_code}")
            return None

    def get_recordings(self, top=30, skip=0, role=None, query=None, order_mode=2,
                       max_participant_count=10, start_to=None, start_from=None, login=None):
        endpoint = 'domain/recordings'
        query_params = {
            'top': top,
            'skip': skip,
            'role': role,
            'query': query,
            'orderMode': order_mode,
            'maxParticipantCount': max_participant_count,
            'startTo': start_to,
            'startFrom': start_from
        }

        headers = {
            'X-Auth-Token': self.api_key
        }

        url = f'{self.base_url}{endpoint}'
        response = requests.get(url, params=query_params, headers=headers)

        if response.status_code == 200:
            if login:
                records = response.json()
                result = []

                for recording in records.get('recordings', []):
                    participants = recording.get('participants', [])
                    participant_found = any(
                        participant.get('userInfo', {}).get('login') == login for participant in
                        participants)

                    if not participant_found and len(participants) > 10:
                        # Если участник не найден и количество участников больше 10, обращаемся к API
                        print('get record')
                        record = Client().get_record_for_key(recording['key'])
                        if any(participant.get('userInfo', {}).get('login') == login for participant in
                               record.get('participants', [])):
                            result.append(record)
                    elif participant_found:
                        result.append(recording)

                return result
            return response.json()['recordings']
        else:
            print(f"Error: {response.status_code}")
            return None

    def get_record_for_key(self, key):
        endpoint = f'domain/recordings/{key}'
        query_params = {
        }

        headers = {
            'X-Auth-Token': self.api_key
        }

        url = f'{self.base_url}{endpoint}'
        response = requests.get(url, params=query_params, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            return None

    def get_users_for_key(self, key):
        endpoint = f'domain/recordings/{key}/participants'
        query_params = {
            'top': 100
        }

        headers = {
            'X-Auth-Token': self.api_key
        }

        url = f'{self.base_url}{endpoint}'
        response = requests.get(url, params=query_params, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            return None

    def get_transcription_for_key(self, key):
        endpoint = f'recordings/{key}/transcript'
        query_params = {
        }

        headers = {
            'X-Auth-Token': self.api_key
        }

        url = f'{self.base_url}{endpoint}'
        response = requests.get(url, params=query_params, headers=headers)

        if response.status_code == 200:
            json_data = response.json()

            # Здесь добавлен код для записи JSON в файл
            with open('output.json', 'w', encoding='utf-8') as json_file:
                json.dump(json_data, json_file, ensure_ascii=False, indent=4)

            return json_data
        else:
            print(f"Error: {response.status_code}")
            return None

    def get_cal_for_email(self, email):
        endpoint = f'emailCalendar/{email}'
        query_params = {
            'email': email,
            'start': '2023-01-01',
            'to': '2023-12-31',
            'take': 10
        }

        headers = {
            'X-Auth-Token': self.api_key
        }

        url = f'{self.base_url}{endpoint}'
        response = requests.get(url, params=query_params, headers=headers)

        if response.status_code == 200:
            json_data = response.json()
            return json_data
        else:
            print(f"Error: {response.status_code}")
            return None


def find_recordings_by_participant(records_json, participant_login):
    records = records_json
    result = []

    for recording in records.get('recordings', []):
        participants = recording.get('participants', [])
        participant_found = any(
            participant.get('userInfo', {}).get('login') == participant_login for participant in participants)

        if not participant_found and len(participants) > 10:
            # Если участник не найден и количество участников больше 10, обращаемся к API
            print('get record')
            record = Client().get_record_for_key(recording['key'])
            if any(participant.get('userInfo', {}).get('login') == participant_login for participant in
                   record.get('participants', [])):
                result.append(record)
        elif participant_found:
            result.append(recording)

    return result


def collect_dialogue(json_data):
    dialogue = []

    # Перебираем треки в tracks
    for track in json_data.get("tracks", []):
        speaker_info = track.get("speaker", {}).get("userInfo", {})
        speaker_name = f"{speaker_info.get('firstname', '')} {speaker_info.get('surname', '')}"
        speaker_key = speaker_info.get('key', '')
        speaker_post = speaker_info.get('post', '')

        # Перебираем чанки внутри трека
        for chunk in track.get("chunks", []):
            start_time = chunk.get("startTimeOffsetInMillis", 0)
            end_time = chunk.get("endTimeOffsetInMillis", 0)
            text = chunk.get("text", "")

            dialogue.append({
                "text": text,
                "start_time": start_time,
                "end_time": end_time,
                "speaker_key": speaker_key,
                "speaker_name": speaker_name,
                "speaker_post": speaker_post,
            })

    # Сортируем диалог по времени
    dialogue.sort(key=lambda x: (x["start_time"], x["end_time"]))

    return dialogue


def get_record_users_keys(record_key):
    ktalk_api = Client()
    keys = []
    emails = []
    users = ktalk_api.get_users_for_key(record_key)
    for user in users:
        keys.append(user['userInfo']['key'])
    users_emails = ktalk_api.get_user_info_by_key(record_key)
    for us in users_emails:
        if us['key'] in keys:
            emails.append(us['email'])
    return emails


# Пример использования
# api = Client()
# records = SQL().get_records_list()
# trs = SQL().get_transcripts()
# new_trs = 0
# for key in records:
#     if any(key in tpl for tpl in trs):
#         continue
#     key = key[0]
#     # dialog_data = collect_dialogue(api.get_transcription_for_key(key))
#     new_trs += 1
#     print(f'new_tr: {key}')
#     # break
#
# print(f'{new_trs=}, {len(records)=}')





# # for index, user in enumerate(ktalk_api.get_users()):
# #     print(f'[*] User: {index + 1}')
# #     SQL().add_user(user.get('key', ''), user.get('email', ''), user.get('firstname', ''), user.get('surname', ''), user.get('post', ''), user.get('avatarUrl', ''))
# # print(Client().get_transcription_for_key('9zDQS73zPW7m1Er1bR9B'))
# # print(Client().get_user_info_by_email('motovilov.aa'))

