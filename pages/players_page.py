import re

from pages.base_page import BackofficePage


class PlayersPage(BackofficePage):
    """Page Object for the players list (backoffice-ui: src/resources/players).

    Unlike Matches/Markets/Bets, when a filter yields zero results the
    `<table>` element is removed entirely (a "No Players Found" panel
    replaces it) rather than the table persisting with an empty/placeholder
    row -- verified live, e.g. filtering Status="Suspended" currently.
    row_count()/table accessors below account for that.
    """

    URL_PATH = "/players"
    HEADING_TEXT = "Players"

    # 0-indexed column positions, stable across all rows: Player ID,
    # Username, Status, Risk, Merchant, Open Exposure, Net Exposure,
    # Turnover, Hold %, Win Rate, Wagers/Hour.
    COL_PLAYER_ID = 0
    COL_USERNAME = 1
    COL_STATUS = 2
    COL_RISK = 3
    COL_MERCHANT = 4
    COL_OPEN_EXPOSURE = 5
    COL_NET_EXPOSURE = 6
    COL_TURNOVER = 7
    COL_HOLD_PCT = 8
    COL_WIN_RATE = 9
    COL_WAGERS_PER_HOUR = 10

    STATUS_VALUES = {"Active", "Inactive", "Inactive 30d", "Inactive 3m", "Safe Mode", "Block Live", "Suspended"}
    RISK_VALUES = {"Low", "Medium", "High"}

    def __init__(self, page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.player_id_search = page.get_by_placeholder("Player ID")
        self.username_search = page.get_by_placeholder("Username")
        self.match_id_search = page.get_by_placeholder("Match ID")

        # Located by the id their <label for=...> points at, not by current
        # display text -- the visible text changes to the selected option
        # (e.g. "All" -> "Active"), which would break a has_text locator.
        self.market_filter = page.locator("#filter-market-id")
        self.selection_filter = page.locator("#filter-selection-id")
        self.status_filter = page.locator("#filter-status")
        self.risk_filter = page.locator("#filter-risk")
        self.merchant_filter = page.locator("#filter-merchant")

        self.high_risk_only_toggle = page.get_by_text("High Risk Only", exact=True).locator(
            "xpath=.."
        ).get_by_role("switch")
        self.newly_registered_toggle = page.get_by_text("Newly Registered (7d)", exact=True).locator(
            "xpath=.."
        ).get_by_role("switch")
        self.active_in_7_days_toggle = page.get_by_text("Active in 7 Days", exact=True).locator(
            "xpath=.."
        ).get_by_role("switch")

        self.search_button = page.get_by_role("button", name="Search", exact=True)
        # "Showing N players" -- the true result total, unaffected by any page-size cap.
        self.showing_count_label = page.get_by_text(re.compile(r"^Showing \d+ players?$"))

    def search_by_username(self, username: str):
        self.username_search.fill(username)

    def filter_by_status(self, option_text: str):
        self.status_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()

    def filter_by_risk(self, option_text: str):
        self.risk_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()

    def search(self):
        """Apply every currently-selected filter -- filters here don't refetch on change."""
        self.search_button.click()
        self.page.wait_for_timeout(1000)

    def row_count(self) -> int:
        if self.table.count() == 0:
            return 0
        return self.table.locator("tbody tr").count()

    def row_cell(self, row_index: int, col_index: int) -> str:
        return self.table.locator("tbody tr").nth(row_index).locator("td").nth(col_index).inner_text().strip()

    def total_count(self) -> int:
        match = re.match(r"Showing (\d+) players?", self.showing_count_label.inner_text())
        assert match, "could not find the \"Showing N players\" total label"
        return int(match.group(1))
