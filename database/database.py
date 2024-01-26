import json

import psycopg2
from psycopg2 import sql


class SQL:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname='default_db',
            user='gen_user',
            password='Alisa220!',
            host='109.172.90.131',
            port=5432
        )
        self.cursor = self.conn.cursor()

    def execute_query(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
        except psycopg2.Error as e:
            print(f"Error executing query: {e}")
            self.conn.rollback()

    def fetch_data(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            print(f"Error fetching data: {e}")
            return None

    def close_connection(self):
        self.cursor.close()
        self.conn.close()

    def get_recordings(self, email):
        query = f'''
        select * 
        from follow_up_service.participations
        where SPLIT_PART(email, '@', 1) = SPLIT_PART('{email}', '@', 1)
        '''
        return self.fetch_data(query)

    def get_user(self, email):
        query = f'''
        SELECT * 
        FROM follow_up_service.users
        WHERE SPLIT_PART(email, '@', 1) = SPLIT_PART('{email}', '@', 1)
        '''
        return self.fetch_data(query)

    def add_hashed_password(self, email, hashed_password):
        query = f'''
        update follow_up_service.users
        set password = '{hashed_password}'
        where SPLIT_PART(email, '@', 1) = SPLIT_PART('{email}', '@', 1);
        '''
        self.execute_query(query)

    def get_transcript(self, record_key):
        query = f'''
        select *
        from follow_up_service.transcriptions tr
        where tr.record_key = '{record_key}'
        '''
        return self.fetch_data(query)

    def get_transcripts(self):
        query = f'''
        select record_key
        from follow_up_service.transcriptions tr
        '''
        return self.fetch_data(query)

    def get_summary_data(self, record_key):
        query = f'''
        select *
        from follow_up_service.zip_transcriptions zt
        where zt.record_key = '{record_key}'
        '''
        return self.fetch_data(query)

    def get_openai_keys(self):
        query = f'''
        select key
        from follow_up_service.api_keys ak
        where ak.is_ready = 'True'
        '''
        return self.fetch_data(query)

    def update_openai_usage(self, key, usage):
        query = f'''
        select 
        usage
        from follow_up_service.api_keys ak
        where ak.key = '{key}'
        '''
        current_usage = int(self.fetch_data(query)[0][0]) + int(usage)
        query = f'''
        update follow_up_service.api_keys ak
        set usage = '{current_usage}'
        where ak.key = '{key}';
        '''
        self.execute_query(query)

    def block_openai_key(self, key):
        query = f'''
        update follow_up_service.api_keys ak
        set is_ready = 'False'
        where ak.key = '{key}';
        '''
        self.execute_query(query)

    def add_zip_follow_up(self, record_key, data):
        query = f'''
        insert into follow_up_service.zip_transcriptions (record_key, data)
        values ('{record_key}', '{data}')
        '''
        self.execute_query(query)

    def get_fvs(self, email, query_):
        query = f'''
        SELECT *
        FROM follow_up_service.follow_ups
        WHERE 
           SPLIT_PART(creator_email, '@', 1) = SPLIT_PART('{email}', '@', 1)
           AND (LOWER(follow_ups.follow_up_name) LIKE '%' || LOWER('{query_}') || '%'
           OR LOWER(follow_ups.record_title) LIKE '%' || LOWER('{query_}') || '%');
        '''
        return self.fetch_data(query)

    def add_fv(self, record_data: dict, data: dict, record_name, creator_key, creator_email):
        query = f'''
        insert into follow_up_service.follow_ups (record_key, record_title, follow_up_name, creator_key, creator_email, data) 
        values ('{record_data["key"]}', '{record_data["title"]}', '{record_name}', '{creator_key}', '{creator_email}', '{json.dumps(data)}')
        '''
        self.execute_query(query)

    def update_fv(self, rec_key: str, data: dict = None, follow_up_name: str = None):
        if follow_up_name:
            query = f'''
            update follow_up_service.follow_ups
            set follow_up_name = '{follow_up_name}'
            where record_key = '{rec_key}'
            '''
            self.execute_query(query)

        if data:
            query = f'''
            update follow_up_service.follow_ups
            set data = '{json.dumps(data)}'
            where record_key = '{rec_key}'
            '''
            self.execute_query(query)

    def get_my_send_msgs(self, user_key):
        query = f'''
        select *
        from follow_up_service.mailing
        where from_user_key = '{user_key}'
        '''
        return self.fetch_data(query)

    def get_users_email_for_record(self, rec_key):
        query = f'''
        select *
        from follow_up_service.participations
        where record_key = '{rec_key}'
        '''
        return self.fetch_data(query)

    def add_keys(self):
        with open('/Users/default/Python_projects/Follow_up/database/keys.txt', 'r') as f:
            keys = f.readlines()
        for key in keys:
            query = f'''
            insert into follow_up_service.api_keys (key, is_ready, usage)
            values ('{key}', 'True', '0')
            '''
            self.execute_query(query)

    def get_records_list(self):
        query = f'''
        select record_key
        from follow_up_service.recordings
        '''
        return self.fetch_data(query)

    def add_record(self, rec_key, title, created_date, participants, size, duration):
        query = fr'''
        insert into follow_up_service.recordings (record_key, title, created_date, participants, size, duration)
        values ('{rec_key}', '{title}', '{created_date}', '%s', '{size}', '{duration}')
        '''
        self.execute_query(query, participants)

    def add_user(self, user_key, email, firstname, surname, post, avatar_url):
        query = f'''
        insert into follow_up_service.users (key, email, firstname, surname, post, avatar_url)
        values ('{user_key}', '{email}', '{firstname}', '{surname}', '{post}', '{avatar_url}')
        '''
        self.execute_query(query)


def test():
    db = SQL()
    # db.block_openai_key('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')
    data = db.get_summary_data('kR2RIusTc0Jf6cqzOeLH')
    print(data)

# test()
