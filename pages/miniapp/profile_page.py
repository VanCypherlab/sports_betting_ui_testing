from playwright.sync_api import expect

from pages.miniapp.bottom_navigation import BottomNavigation


class ProfilePage:
    """Page Object for the Profile tab (frontend-miniapp: src/views/ProfileView.vue).

    Unlike the other tabs, this view has no role=heading element, so its
    presence is verified via the "Wallet Balance" row label instead.
    """

    def __init__(self, page):
        self.page = page
        self.wallet_balance_label = page.get_by_text("Wallet Balance", exact=True)

    def goto(self):
        BottomNavigation(self.page).go_to("Profile")
        expect(self.wallet_balance_label).to_be_visible()
