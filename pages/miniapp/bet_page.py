from playwright.sync_api import expect

from pages.miniapp.bottom_navigation import BottomNavigation


class BetPage:
    """Page Object for the Bet tab (frontend-miniapp: src/views/BetSlipsView.vue)."""

    def __init__(self, page):
        self.page = page
        self.heading = page.get_by_role("heading", name="My Bet Slips", exact=True)

    def goto(self):
        BottomNavigation(self.page).go_to("Bet")
        expect(self.heading).to_be_visible()

    def select_tab(self, tab_name: str):
        self.page.get_by_role("button", name=tab_name, exact=True).click()
