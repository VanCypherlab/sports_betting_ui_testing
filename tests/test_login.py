import os

import pytest
from playwright.sync_api import Browser, expect

from pages.login_page import LoginPage
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, requires_admin_creds

# Credentials are injected via environment variables (see .env.example) so no
# real accounts are hard-coded in the repo. Tests that need a valid backoffice
# admin / non-admin account are skipped automatically when the vars are unset.
NON_ADMIN_EMAIL = os.environ.get("TEST_NON_ADMIN_EMAIL")
NON_ADMIN_PASSWORD = os.environ.get("TEST_NON_ADMIN_PASSWORD")

requires_non_admin_creds = pytest.mark.skipif(
    not (NON_ADMIN_EMAIL and NON_ADMIN_PASSWORD),
    reason="TEST_NON_ADMIN_EMAIL / TEST_NON_ADMIN_PASSWORD not set",
)


@pytest.fixture
def login_page(page):
    login = LoginPage(page)
    login.goto()
    yield login

    # Single-session enforcement means a successful login here leaves the
    # account "signed in" server-side until its TTL expires, blocking later
    # tests/runs with the same account. Log out so the session doesn't leak
    # across tests.
    if login.URL_PATH not in page.url:
        page.request.post("/api/backoffice/v2/auth/logout")


class TestLoginPageUI:
    def test_form_elements_are_visible(self, login_page: LoginPage):
        expect(login_page.email_input).to_be_visible()
        expect(login_page.password_input).to_be_visible()
        expect(login_page.submit_button).to_be_visible()

    def test_submit_disabled_when_fields_empty(self, login_page: LoginPage):
        login_page.expect_submit_disabled()

    def test_password_is_masked_and_toggle_reveals_it(self, login_page: LoginPage):
        expect(login_page.password_input).to_have_attribute("type", "password")
        login_page.fill_and_blur(login_page.password_input, "some-password")

        login_page.toggle_password_visibility()
        expect(login_page.password_input).to_have_attribute("type", "text")

        login_page.toggle_password_visibility()
        expect(login_page.password_input).to_have_attribute("type", "password")


class TestLoginClientSideValidation:
    def test_invalid_email_format_shows_inline_error(self, login_page: LoginPage):
        login_page.fill_and_blur(login_page.email_input, "not-an-email")
        login_page.expect_email_field_error("valid email")

    def test_empty_email_shows_required_error_on_blur(self, login_page: LoginPage):
        login_page.email_input.click()
        login_page.email_input.press("Tab")
        login_page.expect_email_field_error("required")

    def test_empty_password_shows_required_error_on_blur(self, login_page: LoginPage):
        login_page.password_input.click()
        login_page.password_input.press("Tab")
        login_page.expect_password_field_error("required")

    def test_short_password_shows_min_length_error(self, login_page: LoginPage):
        login_page.fill_and_blur(login_page.password_input, "short")
        login_page.expect_password_field_error("at least 8 characters")


class TestLoginAuthentication:
    @requires_admin_creds
    def test_login_success_redirects_to_dashboard(self, login_page: LoginPage):
        login_page.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        login_page.expect_login_success()

    @requires_admin_creds
    def test_wrong_password_shows_401_error(self, login_page: LoginPage):
        login_page.login(ADMIN_EMAIL, "WrongPassword123")
        login_page.expect_error_message("Incorrect email or password.")

    @requires_non_admin_creds
    def test_non_admin_account_is_rejected_with_403(self, login_page: LoginPage):
        login_page.login(NON_ADMIN_EMAIL, NON_ADMIN_PASSWORD)
        login_page.expect_error_message("not a backoffice admin")

    @requires_admin_creds
    @pytest.mark.slow
    def test_concurrent_login_is_rejected_as_already_signed_in(
        self, browser: Browser, base_url: str, login_page: LoginPage
    ):
        # Single-session enforcement: a second browser context (no bo_sid
        # cookie) logging in with the same account while a session is
        # already active should get 409 AlreadySignedIn.
        #
        # Runs before test_repeated_failures_trigger_rate_limit_429 on
        # purpose: that test intentionally burns the account's login rate
        # limit, which would otherwise block this test's first (legitimate)
        # login attempt with a 429 instead of exercising the 409 path.
        login_page.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        login_page.expect_login_success()

        second_context = browser.new_context(base_url=base_url)
        try:
            second_login = LoginPage(second_context.new_page())
            second_login.goto()
            second_login.login(ADMIN_EMAIL, ADMIN_PASSWORD)
            second_login.expect_error_message("already signed in elsewhere")
        finally:
            second_context.close()

    @requires_admin_creds
    @pytest.mark.slow
    def test_repeated_failures_trigger_rate_limit_429(self, login_page: LoginPage):
        # Backend allows 5 failed attempts per email per minute (handler.go),
        # the 6th should be rejected with 429 before hitting the upstream.
        for _ in range(5):
            login_page.login(ADMIN_EMAIL, "WrongPassword123")
            expect(login_page.error_alert).to_be_visible()
            login_page.goto()

        login_page.login(ADMIN_EMAIL, "WrongPassword123")
        login_page.expect_error_message("Too many login attempts")
