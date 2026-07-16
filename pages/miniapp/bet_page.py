import re

from playwright.sync_api import expect

from pages.miniapp.bottom_navigation import BottomNavigation


class BetPage:
    """Page Object for the Bet tab (frontend-miniapp: src/views/BetSlipsView.vue)."""

    TICKET_NUMBER_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

    def __init__(self, page):
        self.page = page
        self.heading = page.get_by_role("heading", name="My Bet Slips", exact=True)
        # Most-recently-placed bet renders first -- verified live.
        self.ticket_numbers = page.get_by_text(self.TICKET_NUMBER_PATTERN)

    def goto(self):
        BottomNavigation(self.page).go_to("Bet")
        expect(self.heading).to_be_visible()

    def select_tab(self, tab_name: str):
        self.page.get_by_role("button", name=tab_name, exact=True).click()

    def most_recent_ticket_number(self) -> str:
        expect(self.ticket_numbers.first).to_be_visible(timeout=10_000)
        return self.ticket_numbers.first.inner_text().strip()
