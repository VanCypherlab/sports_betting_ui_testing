import re

from playwright.sync_api import Locator, Page, expect


class LoginPage:
    """Page Object for the Backoffice login page (backoffice-ui: src/pages/Login.tsx)."""

    URL_PATH = "/login"
    POST_LOGIN_URL = "/trader-dashboard"

    def __init__(self, page: Page):
        self.page = page
        # No data-testid exists in the source component, so locators rely on
        # accessible name (label / aria-label) as recommended by pytest-playwright.
        self.email_input = page.get_by_label("Email", exact=True)
        self.password_input = page.get_by_label("Password", exact=True)
        # Visible button text is "Login" (i18n auth.login), but aria-label="Sign in"
        # wins as the accessible name, so getByRole must match on that.
        self.submit_button = page.get_by_role("button", name="Sign in")
        self.toggle_password_button = page.get_by_role(
            "button", name=re.compile(r"show password|hide password", re.IGNORECASE)
        )
        self.error_alert = page.get_by_role("alert")
        self.email_field_error = page.locator("#email-error")
        self.password_field_error = page.locator("#password-error")

    def goto(self):
        self.page.goto(self.URL_PATH)
        expect(self.email_input).to_be_visible()

    def login(self, email: str, password: str):
        self.fill_and_blur(self.email_input, email)
        self.fill_and_blur(self.password_input, password)
        self.submit_button.click()

    def fill_and_blur(self, field: Locator, value: str):
        field.fill(value)
        field.press("Tab")

    def toggle_password_visibility(self):
        self.toggle_password_button.click()

    def expect_login_success(self):
        expect(self.page).to_have_url(self.POST_LOGIN_URL)

    def expect_error_message(self, message: str):
        expect(self.error_alert).to_be_visible()
        expect(self.error_alert).to_contain_text(message)

    def expect_email_field_error(self, message: str):
        expect(self.email_field_error).to_be_visible()
        expect(self.email_field_error).to_contain_text(message)

    def expect_password_field_error(self, message: str):
        expect(self.password_field_error).to_be_visible()
        expect(self.password_field_error).to_contain_text(message)

    def expect_submit_disabled(self):
        expect(self.submit_button).to_be_disabled()
