import re

from playwright.sync_api import Page, expect


class WagerDetailPage:
    """Page Object for the Wager detail page (backoffice-ui: src/resources/bet/detail).

    URL is /bets/{wagerUuid} -- the full UUID, not the truncated ID shown
    in the Wagers list table (use BetsPage.row_wager_uuid to read it from
    a row's title attribute).
    """

    URL_PATH_TEMPLATE = "/bets/{wager_id}"

    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name=re.compile(r"^Wager "), level=1)

        self.stake_value = self._stat_value("Stake")
        self.win_loss_value = self._stat_value("Win/Loss")
        self.exposure_value = self._stat_value("Exposure")
        self.odds_value = self._stat_value("Odds")

        self.match_teams = page.get_by_text("Match", exact=True).locator("xpath=following-sibling::div[1]//p[1]")
        self.match_time_value = page.get_by_text("Match Time", exact=True).locator("xpath=following-sibling::p[1]")
        self.match_time_badge = page.get_by_text("Match Time", exact=True).locator("xpath=following-sibling::span[1]")
        self.market_value = page.get_by_text("Market", exact=True).locator("xpath=following-sibling::p[1]")
        self.selection_value = page.get_by_text("Selection", exact=True).locator("xpath=following-sibling::p[1]")
        self.merchant_value = page.get_by_text("Merchant", exact=True).locator("xpath=following-sibling::div[1]//p[1]")
        self.player_value = page.get_by_text("Player", exact=True).locator("xpath=following-sibling::div[1]//p[1]")

    def _stat_value(self, label: str):
        """One of the Stake/Win-Loss/Exposure/Odds stat cards (label and value are sibling spans)."""
        return self.page.get_by_text(label, exact=True).locator("xpath=following-sibling::span[1]")

    def goto(self, wager_id: str):
        self.page.goto(self.URL_PATH_TEMPLATE.format(wager_id=wager_id))
        expect(self.heading).to_be_visible()
