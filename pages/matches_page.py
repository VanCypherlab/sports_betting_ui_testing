import re

from playwright.sync_api import Page, expect

from pages.base_page import BackofficePage


class MatchesPage(BackofficePage):
    """Page Object for the matches list (backoffice-ui: src/resources/matches).

    Unlike the Trader Dashboard, filter controls here do NOT refetch on
    change -- verified live against admin.prod-test.cypherlab.tech by
    watching network requests: selecting a Lifecycle/Sport/League/PIC/
    Reconciliation option, or toggling the date window, fires nothing by
    itself. The list only re-queries once the "Search" button (or Enter in
    the search box) is pressed, which then sends every currently-selected
    filter in one request. Callers must call `search()` after setting
    filters to actually apply them.
    """

    URL_PATH = "/matches"
    HEADING_TEXT = "Matches"

    # aria-label reflects the switch's *current* state rather than a fixed
    # name -- verified live against admin.prod-test.cypherlab.tech.
    STATUS_SWITCH_NAME = re.compile(r"^(Open|Closed)$")
    SHOW_SWITCH_NAME = re.compile(r"^(Show|Hide)$")

    def __init__(self, page: Page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.search_input = page.get_by_role("searchbox")
        self.search_button = page.get_by_role("button", name="Search", exact=True)
        self.lifecycle_filter = page.get_by_role("combobox", name="Lifecycle filter")
        self.sport_filter = page.get_by_role("combobox", name="Sport filter")
        self.league_filter = page.get_by_role("combobox", name="League filter")
        self.pic_filter = page.get_by_role("combobox", name="PIC filter")
        groups = page.get_by_role("group")
        self.reconciliation_filter = groups.nth(0)
        self.date_window_filter = groups.nth(1)
        # "N matches" label -- the true result total. The table body only
        # ever renders one page (pageSize=20), so row_count() undercounts
        # once a filter's real total exceeds 20; use total_count() instead
        # whenever comparing counts across filters that can exceed a page.
        self.match_count_label = page.get_by_text(re.compile(r"^\d+\s+match(?:es)?$"))

    def filter_by_lifecycle(self, option_text: str):
        self.lifecycle_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()

    def filter_by_sport(self, option_text: str):
        self.sport_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()

    def filter_by_league(self, option_text: str):
        self.league_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()

    def filter_by_pic(self, option_text: str):
        self.pic_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()

    def filter_by_reconciliation(self, option_text: str):
        self.reconciliation_filter.get_by_role("radio", name=option_text, exact=True).click()

    def filter_by_date_window(self, option_text: str):
        self.date_window_filter.get_by_role("radio", name=option_text, exact=True).click()

    def search(self, term: str = ""):
        """Apply every currently-selected filter (and optionally a search term)."""
        self.search_input.fill(term)
        self.search_button.click()
        self.page.wait_for_timeout(1000)

    def row_count(self) -> int:
        rows = self.table.locator("tbody tr")
        if rows.count() == 1 and "No data available" in rows.first.inner_text():
            return 0
        return rows.count()

    def row_texts(self) -> list[str]:
        if self.row_count() == 0:
            return []
        return self.table.locator("tbody tr").all_inner_texts()

    def total_count(self) -> int:
        """The true result total from the "N matches" label, unaffected by the 20-row page cap."""
        match = re.match(r"(\d+)\s+match(?:es)?", self.match_count_label.inner_text())
        assert match, "could not find the \"N matches\" total label"
        return int(match.group(1))

    def row(self, row_index: int = 0):
        return self.table.locator("tbody tr").nth(row_index)

    def status_switch(self, row_index: int = 0):
        """The Open/Closed switch in a row's Status cell."""
        return self.row(row_index).get_by_role("switch", name=self.STATUS_SWITCH_NAME)

    def show_switch(self, row_index: int = 0):
        """The Show/Hide switch in a row's Show cell."""
        return self.row(row_index).get_by_role("switch", name=self.SHOW_SWITCH_NAME)

    def pic_cell(self, row_index: int = 0):
        return self.row(row_index).locator('[data-slot="pic-cell"]')

    # Positional, not by accessible name: once a role has an assignee, the
    # button's name becomes "<code> <name>" instead of the literal role
    # word -- verified live (e.g. "Sf5a9 Jody Supervisor" once assigned,
    # vs. plain "Supervisor" when unassigned). Slot order is stable.
    PIC_ROLE_SLOT = {"Supervisor": 0, "Trader": 1}

    def pic_role_button(self, row_index: int, role_name: str):
        """The Supervisor/Trader popover-trigger button in a row's PIC cell."""
        return self.pic_cell(row_index).get_by_role("button").nth(self.PIC_ROLE_SLOT[role_name])

    def open_pic_popover(self, row_index: int, role_name: str):
        self.pic_role_button(row_index, role_name).click()
        popover = self.page.get_by_role("dialog")
        expect(popover).to_be_visible()
        return popover

    def pic_assignable_items(self, popover):
        """Every selectable person row in an open PIC popover."""
        return popover.locator('[data-slot="pic-assign-dropdown-item"]')

    def assign_pic(self, popover, item):
        """Select a person in an open PIC popover.

        Clicking a person commits the assignment immediately (a PATCH to
        .../matches/{id}/assignment) -- verified live, the PATCH fires on
        this click alone, no separate Confirm click or password reauth
        needed, unlike Status/Show. The popover usually closes itself
        afterward, but not reliably (e.g. assigning from a previously
        unassigned state can leave it open) -- verified live -- so this
        closes it explicitly rather than asserting on the auto-close.
        """
        item.click()
        self.page.wait_for_timeout(500)
        if popover.is_visible():
            self.page.keyboard.press("Escape")
            expect(popover).not_to_be_visible(timeout=3_000)
        # Same eventual-consistency gap as the Status/Show reauth dialog --
        # verified live: reloading immediately after can still read the
        # pre-assignment PIC.
        self.page.wait_for_timeout(1500)

    def reset_pic(self, popover):
        """Clear a role's assignment back to unassigned via the popover's "Reset PIC" button."""
        popover.locator('[data-slot="pic-assign-dropdown-reset"]').click()
        expect(popover).not_to_be_visible(timeout=5_000)
        self.page.wait_for_timeout(1500)

    def market_activity_link(self, row_index: int = 0):
        return self.row(row_index).get_by_role("link", name="Market Activity / Compare odds")

    def manage_markets_link(self, row_index: int = 0):
        return self.row(row_index).get_by_role("link", name="Manage markets")

    def audit_log_link(self, row_index: int = 0):
        return self.row(row_index).get_by_role("link", name="View audit log")

    def confirm_reauth_dialog(self, password: str):
        """Handle the "Confirm your password" dialog that follows a Status
        or Show toggle -- verified live. Closing/reopening Status always
        raises it; for Show, only revealing a hidden match raises it
        (hiding applies immediately with no confirmation). Email is
        pre-filled, so only the password needs entering.
        """
        dialog = self.page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=5_000)
        dialog.locator("input[type='password']").fill(password)
        confirm_button = dialog.get_by_role("button", name="Confirm")
        expect(confirm_button).to_be_enabled(timeout=5_000)
        confirm_button.click()
        expect(dialog).not_to_be_visible(timeout=5_000)
        # The dialog closes optimistically before the underlying PATCH
        # commits -- verified live: reloading immediately after can still
        # read the pre-toggle state. Give the backend a moment to settle.
        self.page.wait_for_timeout(1500)

    def toggle_status_switch(self, row_index: int, password: str):
        """Toggle a match's Status (Open<->Closed) and complete the reauth dialog it always raises."""
        self.status_switch(row_index).click()
        self.confirm_reauth_dialog(password)

    def toggle_show_switch(self, row_index: int, password: str):
        """Toggle a match's Show/Hide visibility.

        Only completes the reauth dialog if one actually appears (revealing
        a hidden match raises it; hiding a shown one does not -- verified
        live), so this works for either direction.
        """
        self.show_switch(row_index).click()
        self.page.wait_for_timeout(500)
        if self.page.get_by_role("dialog").count():
            self.confirm_reauth_dialog(password)
        else:
            self.page.wait_for_timeout(1000)
