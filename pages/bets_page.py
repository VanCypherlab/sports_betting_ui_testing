from pages.base_page import BackofficePage


class BetsPage(BackofficePage):
    """Page Object for the wagers/bets list (backoffice-ui: src/resources/bet)."""

    URL_PATH = "/bets"
    HEADING_TEXT = "Wagers"

    # 0-indexed column positions, stable across all rows: '', Wager ID,
    # Wager Time, Match ID, Home Team, Away Team, Match Time, Phase,
    # Market, Selection, Odds, Turnover, Exposure, Merchant, User ID,
    # Status, Win/Loss.
    COL_WAGER_ID = 1
    COL_MATCH_ID = 3
    COL_HOME_TEAM = 4
    COL_AWAY_TEAM = 5
    COL_MATCH_TIME = 6
    COL_PHASE = 7
    COL_MARKET = 8
    COL_SELECTION = 9
    COL_ODDS = 10
    COL_TURNOVER = 11
    COL_EXPOSURE = 12
    COL_MERCHANT = 13
    COL_USER_ID = 14
    COL_STATUS = 15
    COL_WIN_LOSS = 16

    def __init__(self, page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.team_name_search = page.get_by_placeholder("Team name")
        self.wager_id_search = page.get_by_placeholder("Wager ID")
        self.match_id_search = page.get_by_placeholder("Match ID")

        # Filter dropdowns -- located by the id their <label for=...> points
        # at rather than by current display text, since their visible text
        # changes to the selected option (e.g. "All Status" -> "Settled"),
        # which would break a has_text-based locator on every re-selection.
        self.status_filter = page.locator("#filter-status")
        self.phase_filter = page.locator("#filter-phase")
        self.merchant_filter = page.locator("#filter-merchant")
        self.market_filter = page.locator("#filter-market-id")
        self.selection_filter = page.locator("#filter-selection-id")

        self.search_button = page.get_by_role("button", name="Search", exact=True)

        # Stake Range is a Radix dual-handle slider (not a combobox) --
        # verified live: role="slider" thumbs labelled "Minimum"/"Maximum",
        # range 0-10000, step 50. Keyboard-driven (Home/ArrowRight/
        # ArrowLeft) rather than mouse-dragged for reliability.
        self.stake_range_min_slider = page.get_by_role("slider", name="Minimum")
        self.stake_range_max_slider = page.get_by_role("slider", name="Maximum")

        self.clear_selection_button = page.get_by_role("button", name="Clear selection")
        self.bulk_void_button = page.get_by_role("button", name="Bulk Void", exact=True)

    def filter_by_status(self, option_text: str):
        self.status_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()

    def filter_by_phase(self, option_text: str):
        self.phase_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()

    def filter_by_merchant(self, option_text: str):
        self.merchant_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()

    def search(self):
        """Apply every currently-selected filter -- filters here don't refetch on change."""
        self.search_button.click()
        self.page.wait_for_timeout(1000)

    def stake_range_values(self) -> tuple[int, int]:
        return (
            int(self.stake_range_min_slider.get_attribute("aria-valuenow")),
            int(self.stake_range_max_slider.get_attribute("aria-valuenow")),
        )

    def increase_stake_range_min(self, presses: int = 1):
        self.stake_range_min_slider.click()
        for _ in range(presses):
            self.page.keyboard.press("ArrowRight")

    def decrease_stake_range_max(self, presses: int = 1):
        self.stake_range_max_slider.click()
        for _ in range(presses):
            self.page.keyboard.press("ArrowLeft")

    def row_count(self) -> int:
        rows = self.table.locator("tbody tr")
        if rows.count() == 1 and "No " in rows.first.inner_text():
            return 0
        return rows.count()

    def row_cell(self, row_index: int, col_index: int) -> str:
        return self.table.locator("tbody tr").nth(row_index).locator("td").nth(col_index).inner_text().strip()

    def row_home_team(self, row_index: int) -> str:
        """Just the Home Team name, without the league name stacked underneath it in the same cell."""
        cell = self.table.locator("tbody tr").nth(row_index).locator("td").nth(self.COL_HOME_TEAM)
        return cell.locator("p").first.inner_text().strip()

    def row_merchant_name(self, row_index: int) -> str:
        """Just the Merchant name, without the secondary "--" placeholder stacked underneath it."""
        cell = self.table.locator("tbody tr").nth(row_index).locator("td").nth(self.COL_MERCHANT)
        return cell.locator("p").first.inner_text().strip()

    def row_user_id(self, row_index: int) -> str:
        """The full User ID for a row, read from the visually-truncated cell's title attribute."""
        cell = self.table.locator("tbody tr").nth(row_index).locator("td").nth(self.COL_USER_ID)
        user_id = cell.locator("span").get_attribute("title")
        assert user_id, f"could not read the full user ID for row {row_index}"
        return user_id

    def row_checkbox(self, row_index: int):
        return self.table.locator("tbody tr").nth(row_index).get_by_role("checkbox")

    def row_wager_uuid(self, row_index: int) -> str:
        """The full wager UUID for a row, read from the truncated Wager ID cell's title attribute."""
        cell = self.table.locator("tbody tr").nth(row_index).locator("td").nth(self.COL_WAGER_ID)
        uuid = cell.locator("span").get_attribute("title")
        assert uuid, f"could not read the full wager UUID for row {row_index}"
        return uuid

    def open_bulk_void_dialog(self):
        self.bulk_void_button.click()
        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible")
        return dialog

    def submit_bulk_void(self, dialog, reason: str, password: str):
        dialog.locator("#bulk-void-reason").fill(reason)
        dialog.locator("#void-authorization-password").fill(password)
        dialog.get_by_role("button", name="Void", exact=False).click()
