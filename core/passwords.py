import hashlib
from playwright.sync_api import Playwright, sync_playwright, expect


class PasswordEncryptor:
    @staticmethod
    def encrypt(password):
        # Хешируем пароль с использованием SHA-256
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        return hashed_password

    @staticmethod
    def check_password(hashed_password, password_to_check):
        # Проверяем, совпадает ли хеш сохраненного пароля с хешем введенного пароля
        return hashed_password == hashlib.sha256(password_to_check.encode()).hexdigest()


def run(playwright: Playwright, email, password):
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://gulliver-group.ktalk.ru/")
    page.goto(
        "https://keycloak.gulliver.ru:8443/realms/KonturTalk/protocol/openid-connect/auth?response_type=id_token%20token&client_id=kontur-talk&state=blgzMmRvcy1uRm9sYlozeDhEWUsydEtMcnVneHRjRFpYczlhLTNTOEtURX5Q&redirect_uri=https%3A%2F%2Fgulliver-group.ktalk.ru%2Fsystem%2Fauthorize&scope=openid%20profile%20email&nonce=blgzMmRvcy1uRm9sYlozeDhEWUsydEtMcnVneHRjRFpYczlhLTNTOEtURX5Q")
    page.get_by_label("Имя пользователя или E-mail").click()
    page.get_by_label("Имя пользователя или E-mail").fill(email)
    page.get_by_label("Пароль").click()
    page.get_by_label("Пароль").fill(password)
    page.get_by_role("button", name="Вход").click()
    url = page.url

    if 'https://gulliver-group.ktalk.ru' in url:
        is_valid = True
    else:
        is_valid = False

    # ---------------------
    context.close()
    browser.close()

    return is_valid
