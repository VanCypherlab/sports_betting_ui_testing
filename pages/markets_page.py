from playwright.sync_api import Page, expect

from pages.base_page import BackofficePage


class MarketsPage(BackofficePage):
    """Page Object for the markets list (backoffice-ui: src/resources/markets/market).

    This page is search-driven: it shows nothing (and exposes no filter
    controls) until a valid Match ID is searched -- verified live against
    admin.prod-test.cypherlab.tech. Once a match loads, its odds grid is a
    wide table (27 columns per row): TYPE, ITEM, then a HOME / AWAY / DRAW
    block each with VALUE/WAO/TURNOVER/WAGERS/PLAYERS/ALERT (6 cols), then
    a SUMMARY block with LE%/WAGERS/PLAYERS/TOTAL TURNOVER, then
    STATUS/AUTOPILOT/EDIT. Column *indices* are consistent across every row
    type (single-line markets, handicap/total sub-lines, and Subtotal
    rows); only what's rendered in the VALUE cells varies by market type.
    """

    URL_PATH = "/markets"
    HEADING_TEXT = "Markets"

    # 0-indexed column positions, stable across all row types.
    COL_HOME_TURNOVER = 4
    COL_HOME_WAGERS = 5
    COL_AWAY_TURNOVER = 10
    COL_AWAY_WAGERS = 11
    COL_DRAW_TURNOVER = 16
    COL_DRAW_WAGERS = 17
    COL_SUMMARY_WAGERS = 21
    COL_SUMMARY_TOTAL_TURNOVER = 23
    COL_STATUS = 24
    COL_AUTOPILOT = 25
    COL_EDIT = 26

    def __init__(self, page: Page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.match_id_search = page.get_by_placeholder("Search by Match ID...")
        self.search_button = page.get_by_role("button", name="Search", exact=True)
        combos = page.get_by_role("combobox")
        self.market_filter = combos.nth(0)
        self.period_filter = combos.nth(1)
        self.alert_filter = combos.nth(2)
        self.hide_no_wagers_checkbox = page.get_by_role("checkbox")

    def search_by_match_id(self, match_id: str):
        self.match_id_search.fill(match_id)
        self.search_button.click()
        self.page.wait_for_timeout(1500)

    def select_market(self, option_text: str):
        self.market_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()
        self.page.wait_for_timeout(500)

    def select_period(self, option_text: str):
        self.period_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()
        self.page.wait_for_timeout(500)

    def select_alert(self, option_text: str):
        self.alert_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()
        self.page.wait_for_timeout(500)

    def toggle_hide_no_wagers(self):
        self.hide_no_wagers_checkbox.click()
        self.page.wait_for_timeout(500)

    def row_count(self) -> int:
        rows = self.table.locator("tbody tr")
        count = rows.count()
        if count == 1 and "No markets match the current filters" in rows.first.inner_text():
            return 0
        return count

    def row_cell(self, row_index: int, col_index: int) -> str:
        return self.table.locator("tbody tr").nth(row_index).locator("td").nth(col_index).inner_text().strip()

    def row_cell_count(self, row_index: int) -> int:
        return self.table.locator("tbody tr").nth(row_index).locator("td").count()

    def status_switch_for_row(self, row_index: int):
        """The OPEN/CLOSE switch in a row's STATUS cell (Actions column)."""
        return self.table.locator("tbody tr").nth(row_index).locator("td").nth(self.COL_STATUS).get_by_role("switch")

    def toggle_status_for_row(self, row_index: int, password: str):
        """Toggle a market's OPEN/CLOSE status.

        BOTH directions prompt a `role="alertdialog"` confirmation --
        verified live. Closing shows "Close this market? Are you sure...
        It will stop accepting wagers immediately." with no extra input,
        just Cancel/Close. Reopening shows "Reopen this market? Re-enter
        your password to reopen trading on this market." with a password
        field and Cancel/Reopen. This handles either case so the toggle
        always actually completes.
        """
        self.status_switch_for_row(row_index).click()
        dialog = self.page.get_by_role("alertdialog")
        expect(dialog).to_be_visible(timeout=5_000)
        password_input = dialog.locator("input[type='password']")
        if password_input.count():
            password_input.fill(password)
            dialog.get_by_role("button", name="Reopen", exact=True).click()
        else:
            dialog.get_by_role("button", name="Close", exact=True).click()
        self.page.wait_for_timeout(1500)

    def read_status_via_fresh_load(self, match_id: str, row_index: int) -> str:
        """Navigate fresh and read a row's STATUS label.

        Reading the switch in the *same* page session immediately after a
        toggle is unreliable while its confirmation dialog is still open
        (or just closed) -- verified live (a stale read there can hang for
        30s+). A fresh navigation avoids that entirely.
        """
        self.goto()
        self.search_by_match_id(match_id)
        return self.status_switch_for_row(row_index).get_attribute("aria-label")

    def edit_button_for_row(self, row_index: int):
        """The pencil "Edit market" button in a row's EDIT cell.

        Clicking it opens the Market Activity page (odds/spread/limit
        adjustment) in a new tab -- verified live. Callers should use
        `page.context.expect_page()` around the click to capture it.
        """
        return self.table.locator("tbody tr").nth(row_index).locator("td").nth(self.COL_EDIT).get_by_role("button")
