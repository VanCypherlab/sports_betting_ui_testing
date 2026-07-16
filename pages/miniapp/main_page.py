from playwright.sync_api import expect

from pages.miniapp.bottom_navigation import BottomNavigation


class MainPage:
    """Page Object for the Home tab (frontend-miniapp: src/views/MainPage.vue)."""

    def __init__(self, page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Football", exact=True)
        self.wallet_balance = page.get_by_role("button", name="Wallet balance")

    def goto(self):
        BottomNavigation(self.page).go_to("Home")
        expect(self.heading).to_be_visible()

    def filter_by(self, tab_name: str):
        self.page.get_by_role("button", name=tab_name, exact=True).click()

    def open_first_match(self):
        """Click the first upcoming match card.

        Match cards are buttons with no dedicated ARIA role/name of their
        own -- identified instead by the "UPCOMING" status badge every card
        renders, which the filter-tab buttons don't have -- verified live.
        """
        self.page.get_by_role("button").filter(has_text="UPCOMING").first.click()
