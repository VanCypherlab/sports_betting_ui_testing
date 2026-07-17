import re

from playwright.sync_api import expect

from pages.change_password_page import ChangePasswordPage
from pages.profile_page import ProfilePage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds

CHANGE_PASSWORD_URL_PATTERN = re.compile(r"/change-password$")


class TestProfilePage:
    def test_page_loads(self, authenticated_page):
        ProfilePage(authenticated_page).goto()

    def test_profile_card_shows_email_and_permissions(self, authenticated_page):
        profile = ProfilePage(authenticated_page)
        profile.goto()

        expect(profile.email_value).to_be_visible()
        email = profile.email_value.inner_text().strip()
        assert "@" in email, f"Email value {email!r} doesn't look like an email"

        badges = profile.permission_badges()
        assert badges, "expected at least one 'domain: level' permission badge"

    def test_last_login_shows_a_valid_date(self, authenticated_page):
        """The signed-in admin has definitely logged in (they're viewing
        this page right now), so Last Login should never render as
        "Invalid Date" -- reproduces live on qat.
        """
        profile = ProfilePage(authenticated_page)
        profile.goto()

        last_login = profile.last_login_value.inner_text().strip()
        assert last_login, "Last Login is blank"
        assert "Invalid Date" not in last_login, f"Last Login shows {last_login!r}"

    def test_activity_stats_are_non_negative_numbers(self, authenticated_page):
        profile = ProfilePage(authenticated_page)
        profile.goto()

        total_actions = profile.total_actions_value.inner_text().strip().replace(",", "")
        sessions_today = profile.sessions_today_value.inner_text().strip().replace(",", "")
        assert total_actions.isdigit(), f"Total Actions {total_actions!r} is not a plain non-negative number"
        assert sessions_today.isdigit(), f"Sessions Today {sessions_today!r} is not a plain non-negative number"

    def test_change_password_button_navigates_to_change_password_page(self, authenticated_page):
        profile = ProfilePage(authenticated_page)
        profile.goto()
        profile.open_change_password()

        expect(authenticated_page).to_have_url(CHANGE_PASSWORD_URL_PATTERN)
        expect(
            authenticated_page.get_by_text("Set a new password for your backoffice account.", exact=False)
        ).to_be_visible()


class TestChangePasswordPage:
    """Client-side validation only -- see ChangePasswordPage's docstring
    for why a real submission (with the actual current password) is
    intentionally never exercised here.
    """

    def test_page_loads(self, authenticated_page):
        change_password = ChangePasswordPage(authenticated_page)
        change_password.goto()
        expect(change_password.current_password_input).to_be_visible()
        expect(change_password.new_password_input).to_be_visible()
        expect(change_password.confirm_password_input).to_be_visible()

    def test_mismatched_new_passwords_shows_error(self, authenticated_page):
        change_password = ChangePasswordPage(authenticated_page)
        change_password.goto()
        change_password.fill_form("dummy-current-password", "newpassword123", "different123")
        change_password.submit()
        expect(change_password.error_alert).to_contain_text("New passwords do not match")

    def test_new_password_same_as_current_shows_error(self, authenticated_page):
        change_password = ChangePasswordPage(authenticated_page)
        change_password.goto()
        change_password.fill_form("dummy-current-password", "dummy-current-password", "dummy-current-password")
        change_password.submit()
        expect(change_password.error_alert).to_contain_text("New password must be different from the current one")

    def test_empty_form_does_not_submit(self, authenticated_page):
        """The required inputs block native form submission before any
        JS validation/network call runs -- verified live.
        """
        change_password = ChangePasswordPage(authenticated_page)
        change_password.goto()
        change_password.submit()
        expect(change_password.heading).to_be_visible()
        expect(authenticated_page).to_have_url(CHANGE_PASSWORD_URL_PATTERN)

    def test_short_new_password_does_not_submit(self, authenticated_page):
        """The new/confirm inputs' native minLength=8 blocks submission
        before the JS-level "at least 8 characters" check ever runs --
        verified live.
        """
        change_password = ChangePasswordPage(authenticated_page)
        change_password.goto()
        change_password.fill_form("dummy-current-password", "short", "short")
        change_password.submit()
        expect(change_password.heading).to_be_visible()
        expect(authenticated_page).to_have_url(CHANGE_PASSWORD_URL_PATTERN)

    def test_show_hide_password_toggle_reveals_text(self, authenticated_page):
        change_password = ChangePasswordPage(authenticated_page)
        change_password.goto()
        change_password.current_password_input.fill("some-value")

        assert change_password.current_password_input.get_attribute("type") == "password"
        change_password.toggle_show_current_password()
        assert change_password.current_password_input.get_attribute("type") == "text"
