import re

from playwright.sync_api import Page, expect


class StakeholderEntryPage:
    """Page Object for the miniapp's stakeholder game entry form
    (frontend-miniapp: src/views/StakeholderGameEntryView.vue).

    frontend-miniapp has no in-app email/password login page — auth is
    host-token-only. This dev-only form (user_id/amount -> real getGameURL
    backend call -> redirect with a token-bearing URL) is the closest
    functional analog to a login page and the only deterministic, UI-driven
    way to reach an authenticated route in automation.
    """

    URL_PATH = "/stakeholder-entry"
    # The router strips the token/refresh_token query params but preserves
    # others (e.g. ?currency=CYP), so the path is anchored, not the full URL.
    POST_ENTRY_URL_PATTERN = re.compile(r"/main(\?|$)")
    ENTRY_FORM_URL_PATTERN = re.compile(r"/stakeholder-entry$")

    def __init__(self, page: Page):
        self.page = page
        self.user_id_input = page.get_by_label("User ID")
        self.amount_input = page.get_by_label("Amount")
        self.submit_button = page.get_by_role("button", name="Open miniapp")
        self.status_alert = page.get_by_role("alert")

    def goto(self):
        self.page.goto(self.URL_PATH)
        expect(self.user_id_input).to_be_visible()

    def open_miniapp(self, user_id: str, amount: str):
        self.user_id_input.fill(user_id)
        self.amount_input.fill(amount)
        self.submit_button.click()

    def expect_redirected_into_app(self):
        expect(self.page).to_have_url(self.POST_ENTRY_URL_PATTERN)

    def expect_remains_on_entry_form(self):
        expect(self.page).to_have_url(self.ENTRY_FORM_URL_PATTERN)

    def expect_error_message(self, message: str):
        expect(self.status_alert).to_be_visible()
        expect(self.status_alert).to_contain_text(message)
