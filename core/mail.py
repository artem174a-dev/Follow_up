import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMPT_USER = 'bi.reporting@gulliver.ru'
SMPT_PASSWORD = 'i@OH~AGi8Q'
SMTP_SERVER = 'dep.gulliver.ru'
SMPT_PORT = 2525


def report(mail_from: str, receiver: str, subject: str, body: str):
        message = MIMEMultipart()
        message['From'] = mail_from
        message['To'] = receiver
        message['Subject'] = subject

        # Добавление текстового сообщения
        text = MIMEText(body)
        message.attach(text)

        # Отправка сообщения
        try:
            server = smtplib.SMTP(SMTP_SERVER, SMPT_PORT)
            print("Connecting to SMTP server...")
            server.login(SMPT_USER, SMPT_PASSWORD)
            server.sendmail(SMPT_USER, receiver, message.as_string())
            server.close()
        except Exception as error:
            print(error)
        else:
            return True
