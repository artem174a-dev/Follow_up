import json
import re

import openai
from openai import OpenAI
import tiktoken

from database.database import SQL
from core.prompts import *

RECORDS = [
'5v5C4gjnrWwJu0WouowM',
'kR2RIusTc0Jf6cqzOeLH',
'474C6Zk3qKUwnkx0jgg9',
'6t05NXsWv2xO6GR5ke28',
'a1dGunCMFNJTzDoCpV7U',
'C8iQ6N7AFrryAIqQoV0Z',
'chEapVtdFrxm5GzeXUr0',
'd36lAU15ku5th8cnLyr6',
'D4ew5BHUMO0Do0f1IhMO',
'D9tjDMES2mj2q6OMGeG6',
'fJq58nRUUZX3uxqlGTHk',
'JaWaYhSzl3972Qo8SarK',
'jlmwrExNoudaGmDXjP7X',
'Mm7mcvPyDKeYX4W442Gy',
'mQ2hsW334Kl3YHjwMIt4',
'qlmouObuGAjE1pDNnaPw',

'TnNEhsYyvMU9eSkm0xQL',
'TQq701rARZWYofXljneU',
'uUIytJWJLM2CnY3YEjJI',
'yBdnlwRZ4iMirNpdI4WQ',
'Z2JEJ8lvm1Nm4J4FEdRz',
'zsL40qaWzJ3RJy1GmhZX',
]


def convert_to_json(text):
    entries = re.findall(r'\[(.*?)\]-(.*?)>(.*?)', text)
    json_data = []

    for entry in entries:
        user, post, text = entry
        post = post.strip('()')  # Убираем скобки из должности
        json_entry = {"user": user.strip(), "post": post.strip(), "text": text.strip()}
        json_data.append(json_entry)

    return json.dumps(json_data, ensure_ascii=False, indent=2)


class GPT:
    def __init__(self):
        self.db = SQL()
        self.api_key = self.db.get_openai_keys()[0][0]
        self.client = OpenAI(api_key=self.api_key)

    @staticmethod
    def num_tokens_from_string(string: str) -> int:
        """Returns the number of tokens in a text string."""
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        num_tokens = len(encoding.encode(string))
        return num_tokens

    def make_chunks(self, record_key):
        dialog_data = self.db.get_transcript(record_key)
        full_dialog = ''
        chunk = ''
        summary = ''
        total_tokens = 0
        for index, item in enumerate(dialog_data[0][2]):
            chunk += f"{item['speaker_name'] if item['speaker_name'] != ' ' else 'unknown'} - ({item['speaker_post'] if item['speaker_post'] != '' else 'unknown'}):{item['text']}\n"
            full_dialog += f"{item['speaker_name'] if item['speaker_name'] != ' ' else 'unknown'} - ({item['speaker_post'] if item['speaker_post'] != '' else 'unknown'}):{item['text']}\n"
            if self.num_tokens_from_string(chunk) > 10000:
                try:
                    constrict_data = self.constrict_dialog(chunk)
                except openai.RateLimitError as e:
                    print(e)
                    self.db.block_openai_key(self.api_key)
                    self.api_key = self.db.get_openai_keys()[0][0]
                    constrict_data = self.constrict_dialog(chunk)
                summary += constrict_data['content']
                total_tokens += int(constrict_data['total-usage'])
                self.db.update_openai_usage(self.api_key, int(constrict_data['total-usage']))
                chunk = ''
                print(
                    f'[*] Chunk: {index}, chunk-tokens: {constrict_data["total-usage"]}, total tokens: {total_tokens}')
        if chunk != '':
            try:
                constrict_data = self.constrict_dialog(chunk)
            except openai.RateLimitError as e:
                print(e)
                self.db.block_openai_key(self.api_key)
                self.api_key = self.db.get_openai_keys()[0][0]
                constrict_data = self.constrict_dialog(chunk)
            try:
                self.db.update_openai_usage(self.api_key, int(constrict_data['total-usage']))
            except Exception as e:
                print(e)
            summary += constrict_data['content']
            total_tokens += int(constrict_data['total-usage'])
        print(f'[*] Total tokens: {total_tokens}')
        print(f'[*] Full dialog: {self.num_tokens_from_string(full_dialog)}')
        return convert_to_json(summary)

    def constrict_dialog(self, chunk):
        try:
            result = self.client.chat.completions.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        'role': 'system',
                        'content': CONSTRICT_DIALOG_SYSTEM
                    },
                    {
                        "role": "user",
                        "content": CONSTRICT_DIALOG_USER
                    },
                    {
                        'role': 'assistant',
                        'content': CONSTRICT_DIALOG_ASSISTANT
                    },
                    {
                        "role": "user",
                        "content": f'''Сожми данный диалог и ОБЯЗАТЕЛЬНО укажи от какого участника была информация:\n{chunk}'''
                    }
                ],
                temperature=1,
                max_tokens=1200,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
        except Exception as e:
            raise e
        else:
            return {'content': result.choices[0].message.content, 'total-usage': result.usage.total_tokens}

    def streaming(self, summary):
        try:
            result = self.client.chat.completions.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        'role': 'system',
                        'content': STREAMING_SYSTEM
                    },
                    {
                        "role": "user",
                        "content": STREAMING_USER
                    },
                    {
                        'role': 'assistant',
                        'content': STREAMING_ASSISTANT
                    },
                    {
                        "role": "user",
                        "content": f'Собери Follow up по данной встрече:\n{summary}'
                    }
                ],
                temperature=1,
                max_tokens=9000,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stream=True
            )
        except Exception as e:
            raise e
        else:
            return result
            # return {'content': result.choices[0].message.content, 'total-usage': result.usage.total_tokens}



# for key in RECORDS:
#     data = GPT().make_chunks(key)
#     SQL().add_zip_follow_up(key, data)

# result = GPT().streaming()
# print(result['content'])
# print(result['total-usage'])
# client = OpenAI(api_key='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')
#
# response = client.chat.completions.create(
#   model="gpt-3.5-turbo",
#   messages=[
#     {
#       "role": "user",
#       "content": "Привет!"
#     }
#   ],
#   temperature=1,
#   max_tokens=256,
#   top_p=1,
#   frequency_penalty=0,
#   presence_penalty=0
# )
#
# print(response.choices[0].message.content)
