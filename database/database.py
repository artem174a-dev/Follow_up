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
        from follow_up_service.user_participation
        where email = '{email}'
        '''
        return self.fetch_data(query)

    def get_user(self, email):
        query = f'''
        select * 
        from follow_up_service.users
        where email = '{email}'
        '''
        return self.fetch_data(query)

    def add_hashed_password(self, email, hashed_password):
        query = f'''
        update follow_up_service.users
        set password = '{hashed_password}'
        where email = '{email}';
        '''
        self.execute_query(query)


# print(SQL().get_recordings('motovilov.aa@gulliver-group.com'))

