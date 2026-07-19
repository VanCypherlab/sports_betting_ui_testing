import re

from playwright.sync_api import Page


class PlayerDetailPage:
    """Page Object for the Player detail page (backoffice-ui: src/resources/players/detail).

    URL is /players/{playerId} -- reached from the Players list by clicking
    a row's Username cell.
    """

    URL_PATH_TEMPLATE = "/players/{player_id}"

    # 0-indexed column positions in the Wager History table: Wager ID, Home
    # Team, Away Team, Match Date, Placed At, Market, Selection, Turnover,
    # Odds, Result, Payout.
    COL_HOME_TEAM = 1
    COL_AWAY_TEAM = 2
    COL_MATCH_DATE = 3
    COL_TURNOVER = 7
    COL_ODDS = 8
    COL_RESULT = 9
    COL_PAYOUT = 10

    # 0-indexed column positions in the Open Wagers table: Home Team, Away
    # Team, Match Time, Placed At, Phase, Market, Selection, Turnover,
    # Odds, Potential Win.
    OPEN_COL_HOME_TEAM = 0
    OPEN_COL_AWAY_TEAM = 1
    OPEN_COL_MATCH_TIME = 2
    OPEN_COL_TURNOVER = 7
    OPEN_COL_ODDS = 8
    OPEN_COL_POTENTIAL_WIN = 9

    def __init__(self, page: Page):
        self.page = page
        self.open_wagers_tab_button = page.get_by_role("tab", name="Open Wagers", exact=True)
        self.wager_history_tab_button = page.get_by_role("tab", name="Wager History", exact=True)
        self.notes_tab_button = page.get_by_role("tab", name="Notes", exact=True)
        self.table = page.get_by_role("table")
        self.notes_textarea = page.locator("textarea")
        self.save_notes_button = page.get_by_role("button", name="Save Notes")

        # The Status badge next to the username heading -- e.g. "Active" or
        # "Safe Mode" -- located relative to the (unique) <h1> rather than by
        # a fixed class name, since several other badges on the page share
        # the same "rounded-md border" styling.
        self.status_badge = page.locator("h1").locator(
            "xpath=following::span[contains(@class,'rounded-md') and contains(@class,'border')][1]"
        )
        # Reads "Safe Mode" when Off, "Safe Mode (S1)"/"Safe Mode (S2)" when
        # a level is active -- verified live.
        self.safe_mode_button = page.get_by_role("button", name=re.compile(r"^Safe Mode"))
        # Reads "Ban Player" when Active, "Unban Player" once Suspended --
        # verified live -- so the same locator/flow works for both directions.
        self.ban_unban_button = page.get_by_role("button", name=re.compile(r"^(Ban|Unban) Player$"))

    def goto(self, player_id: str):
        self.page.goto(self.URL_PATH_TEMPLATE.format(player_id=player_id))
        self.page.wait_for_timeout(1000)

    def open_open_wagers_tab(self):
        self.open_wagers_tab_button.click()
        self.page.wait_for_timeout(800)

    def open_wager_history_tab(self):
        self.wager_history_tab_button.click()
        self.page.wait_for_timeout(800)

    def open_notes_tab(self):
        self.notes_tab_button.click()
        self.page.wait_for_timeout(800)

    def wager_count(self) -> int:
        """Total row count in the currently-active tab's table, from the
        "X-Y of Z" pagination label ("0 results" when empty).

        This is the TRUE total across all pages, not how many rows are
        actually rendered right now -- e.g. a player with 43 wagers still
        only renders the first 20 in the DOM until "Load more"/next page
        is clicked (verified live). Use `rendered_row_count()` instead
        when iterating over rows currently in the DOM.
        """
        body_text = self.page.locator("body").inner_text()
        match = re.search(r"\d+-\d+ of (\d+)", body_text)
        if match:
            return int(match.group(1))
        return 0

    def rendered_row_count(self) -> int:
        """How many rows are actually present in the DOM right now for the
        current tab -- may be less than `wager_count()`'s true total if
        the table is paginated (only the current page's rows render).
        """
        return self.table.locator("tbody tr").count()

    def row_cell(self, row_index: int, col_index: int) -> str:
        return self.table.locator("tbody tr").nth(row_index).locator("td").nth(col_index).inner_text().strip()

    def wager_history_wager_id_button(self, row_index: int):
        return self.table.locator("tbody tr").nth(row_index).locator("td").first.get_by_role("button")

    def save_notes(self, text: str):
        self.notes_textarea.fill(text)
        self.save_notes_button.click()
        self.page.wait_for_timeout(1500)

    def open_safe_mode_dialog(self):
        self.safe_mode_button.click()
        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible")
        return dialog

    def set_safe_mode_level(self, dialog, level: str, reason: str):
        """Select a Safe Mode level card ("Off", "S1", or "S2" -- matched
        against the card's leading text), fill the required reason, and
        submit. The footer submit button's label depends on the target
        level -- "Apply Safe Mode" for S1/S2, "Disable Safe Mode" for Off --
        so it's matched dynamically rather than by a fixed name.
        """
        dialog.get_by_role("button", name=re.compile(rf"^{re.escape(level)}")).click()
        dialog.locator("#safe-mode-reason").fill(reason)
        dialog.get_by_role("button", name=re.compile(r"^(Apply|Disable) Safe Mode$")).click()
        self.page.wait_for_timeout(1500)

    def open_ban_dialog(self):
        self.ban_unban_button.click()
        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible")
        return dialog

    def confirm_ban_or_unban(self, dialog, reason: str):
        """Fill the required reason and submit, whichever direction the
        dialog opened as ("Confirm Ban" or "Confirm Unban" -- matched
        dynamically since the same button locator/flow handles both).
        """
        dialog.locator("#reason").fill(reason)
        dialog.get_by_role("button", name=re.compile(r"^Confirm (Ban|Unban)$")).click()
        self.page.wait_for_timeout(1500)
