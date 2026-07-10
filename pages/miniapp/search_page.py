from playwright.sync_api import expect

from pages.miniapp.bottom_navigation import BottomNavigation


class SearchPage:
    """Page Object for the Search tab (frontend-miniapp: src/views/SearchPage.vue)."""

    def __init__(self, page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Search", exact=True)
        self.search_input = page.get_by_placeholder("Enter event, team")

    def goto(self):
        BottomNavigation(self.page).go_to("Search")
        expect(self.heading).to_be_visible()

    def search(self, text: str):
        self.search_input.fill(text)
