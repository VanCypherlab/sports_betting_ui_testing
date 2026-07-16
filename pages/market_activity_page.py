import re

from playwright.sync_api import Page


class MarketActivityPage:
    """Page Object for the Market Activity page (backoffice-ui: src/resources/markets/activity).

    Reached via MarketsPage's Edit button, which opens this in a new
    browser tab -- callers get the Page instance via
    `page.context.expect_page()` around that click (see
    MarketsPage.edit_button_for_row), not via a goto(). Not a
    BackofficePage subclass for that reason.
    """

    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading")

        # The "In-game data" card -- verified live against
        # admin.uat.cypherlab.tech: a single bordered container
        # holding the header (title/provider/status badge/seq), the
        # Score/Clock/Period/Teams tiles, and the Timeline/Statistics/Lineup
        # sections. Scoped by text rather than the exact class list since
        # other cards on the page (activity log, vendor odds) share similar
        # "rounded-md border" styling.
        self.ingame_card = page.locator("div.rounded-md.border").filter(has_text="In-game data")
        self.ingame_provider = self.ingame_card.get_by_text(re.compile(r"^Provider\s"))
        self.ingame_status_badge = self.ingame_card.locator('[data-slot="badge"]')
        self.ingame_seq = self.ingame_card.get_by_text(re.compile(r"^Seq\s"))
        self.ingame_timeline_section = self.ingame_card.locator("section").filter(has_text="Timeline")

    def ingame_field(self, label: str):
        """The value tile for one of Score/Clock/Period/Teams (label and value are sibling divs)."""
        label_div = self.ingame_card.get_by_text(label, exact=True)
        return label_div.locator("xpath=following-sibling::div[1]")
