from playwright.sync_api import Page, expect


class ChangePasswordPage:
    """Page Object for the self-service change-password page
    (backoffice-ui: src/pages/ChangePassword.tsx), reached from the
    Profile page's "Change password" button.

    KNOWN LIMITATION (per source comment, BAC-984): the backend's
    SetPassword RPC may not be implemented yet upstream, in which case a
    real submission surfaces an "upstream unavailable" notice instead of
    actually changing the password. Tests here intentionally only cover
    client-side validation (mismatch, must-differ-from-current, native
    required/minLength blocking empty/short submissions) -- never a real
    submission with the actual current password, since a successful
    change would rotate the shared TEST_ADMIN_PASSWORD credential the
    whole suite depends on.
    """

    URL_PATH = "/change-password"

    def __init__(self, page: Page):
        self.page = page
        # CardTitle renders as a plain <div>, not a heading element --
        # verified live -- and "Change password" text also appears on the
        # submit button, so this page's own description text (unique to
        # it) is the reliable "did this page load" signal instead.
        self.heading = page.get_by_text(
            "Set a new password for your backoffice account.", exact=False
        )
        self.current_password_input = page.get_by_label("Current password", exact=True)
        self.new_password_input = page.get_by_label("New password", exact=True)
        self.confirm_password_input = page.get_by_label("Confirm new password", exact=True)
        self.submit_button = page.get_by_role("button", name="Change password", exact=True)
        self.error_alert = page.get_by_role("alert")

    def goto(self):
        self.page.goto(self.URL_PATH)
        expect(self.heading).to_be_visible()

    def fill_form(self, current_password: str, new_password: str, confirm_password: str):
        self.current_password_input.fill(current_password)
        self.new_password_input.fill(new_password)
        self.confirm_password_input.fill(confirm_password)

    def submit(self):
        self.submit_button.click()
        self.page.wait_for_timeout(500)

    def toggle_show_current_password(self):
        self.page.get_by_role("button", name="Show password", exact=True).first.click()

    def toggle_show_new_password(self):
        # Whichever of the two toggle buttons is still "Show password" after
        # the current-password one may have already been toggled -- select
        # by position (second field) instead of assuming label state.
        self.page.locator('button[aria-label="Show password"], button[aria-label="Hide password"]').nth(1).click()
