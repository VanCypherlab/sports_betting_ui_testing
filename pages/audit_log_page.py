import re

from playwright.sync_api import Page

from pages.base_page import BackofficePage


class AuditLogPage(BackofficePage):
    """Page Object for the audit log (backoffice-ui: src/resources/audit-log).

    The four dropdown filters (Action Type, Object Type, Actor, Date Range)
    live inside a "Filters" popover that must be opened before its
    comboboxes exist in the accessibility tree -- verified live against
    admin.qat.cypherlab.tech: `get_by_role("combobox")` only returns the
    top-of-page "Filter by match" control until the popover is open, at
    which point it returns 5 (match filter + the 4 popover ones, in DOM
    order). The popover button also toggles closed on a second click, so
    filter helpers only open it if it isn't already showing.

    Search/filters DO refetch live (debounced ~300ms server-side query,
    verified live), unlike Matches/Players/Markets -- there is no separate
    "Search" button to press afterwards.
    """

    URL_PATH = "/audit"
    HEADING_TEXT = "Audit Log"

    # 0-indexed column positions, stable across all rows: Time, Actor,
    # Action, Outcome, Object, Change, Reason.
    COL_TIME = 0
    COL_ACTOR = 1
    COL_ACTION = 2
    COL_OUTCOME = 3
    COL_OBJECT = 4
    COL_CHANGE = 5
    COL_REASON = 6

    DATE_RANGE_VALUES = {"Today", "Last 24 Hours", "Last 7 Days", "Last 30 Days"}

    def __init__(self, page: Page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.search_input = page.get_by_placeholder("Search by actor, action, object...")

        self.filters_button = page.get_by_role("button", name="Filters", exact=True)
        self.clear_all_button = page.get_by_role("button", name="Clear all", exact=True)
        # A stable marker for "the Filters popover is currently open" --
        # its own label, not a combobox (those only exist once open).
        self._action_type_label = page.get_by_text("Action Type", exact=True)

        combos = page.get_by_role("combobox")
        self.match_filter = combos.nth(0)
        self.action_type_filter = combos.nth(1)
        self.object_type_filter = combos.nth(2)
        self.actor_filter = combos.nth(3)
        self.date_range_filter = combos.nth(4)

        self.load_more_button = page.get_by_role("button", name="Load More", exact=True)
        # "Showing X of Y entries" -- X is rows currently rendered
        # (accumulates across Load More pages), Y is the true result total.
        self.showing_label = page.get_by_text(re.compile(r"^Showing \d+ of \d+ entries?$"))

    def goto(self):
        super().goto()
        # The initial load briefly renders 10 skeleton rows (blank cells)
        # before real data arrives -- verified live -- so wait for either
        # the "Showing X of Y" label (results) or the empty-state message,
        # whichever loading actually resolves to.
        no_results = self.page.get_by_text("No audit logs found", exact=True)
        self.showing_label.or_(no_results).first.wait_for(state="visible", timeout=10_000)

    def _ensure_filters_open(self):
        if not self._action_type_label.is_visible():
            self.filters_button.click()
            self.page.wait_for_timeout(300)

    def search(self, text: str):
        self.search_input.fill(text)
        self.page.wait_for_timeout(1200)

    def filter_by_action_type(self, option_text: str):
        self._ensure_filters_open()
        self.action_type_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()
        self.page.wait_for_timeout(1200)

    def filter_by_object_type(self, option_text: str):
        self._ensure_filters_open()
        self.object_type_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()
        self.page.wait_for_timeout(1200)

    def filter_by_actor(self, option_text: str):
        self._ensure_filters_open()
        self.actor_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()
        self.page.wait_for_timeout(1200)

    def filter_by_date_range(self, option_text: str):
        self._ensure_filters_open()
        self.date_range_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()
        self.page.wait_for_timeout(1200)

    def action_type_options(self) -> list[str]:
        """Every Action Type option except "All Actions", read live -- the
        set of actions drifts as new admin/system activity happens.
        """
        self._ensure_filters_open()
        self.action_type_filter.click()
        options = self.page.get_by_role("option")
        texts = [options.nth(i).inner_text().strip() for i in range(options.count())]
        self.page.keyboard.press("Escape")
        return [t for t in texts if t != "All Actions"]

    def object_type_options(self) -> list[str]:
        self._ensure_filters_open()
        self.object_type_filter.click()
        options = self.page.get_by_role("option")
        texts = [options.nth(i).inner_text().strip() for i in range(options.count())]
        self.page.keyboard.press("Escape")
        return [t for t in texts if t != "All Types"]

    def actor_options(self) -> list[str]:
        self._ensure_filters_open()
        self.actor_filter.click()
        options = self.page.get_by_role("option")
        texts = [options.nth(i).inner_text().strip() for i in range(options.count())]
        self.page.keyboard.press("Escape")
        return [t for t in texts if t != "All Actors"]

    def clear_all_filters(self):
        self._ensure_filters_open()
        self.clear_all_button.click()
        self.page.wait_for_timeout(1200)

    def row_count(self) -> int:
        if self.table.count() == 0:
            return 0
        return self.table.locator("tbody tr").count()

    def row_cell(self, row_index: int, col_index: int) -> str:
        return self.table.locator("tbody tr").nth(row_index).locator("td").nth(col_index).inner_text().strip()

    def row(self, row_index: int = 0):
        return self.table.locator("tbody tr").nth(row_index)

    def total_count(self) -> int:
        match = re.search(r"Showing \d+ of (\d+) entries?", self.showing_label.inner_text())
        assert match, 'could not find the "Showing X of Y entries" total label'
        return int(match.group(1))

    def displayed_count(self) -> int:
        match = re.search(r"Showing (\d+) of \d+ entries?", self.showing_label.inner_text())
        assert match, 'could not find the "Showing X of Y entries" total label'
        return int(match.group(1))

    def view_button(self, row_index: int):
        return self.row(row_index).get_by_role("button", name="View", exact=True)

    def open_view_dialog(self, row_index: int):
        self.view_button(row_index).click()
        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible")
        return dialog

    def close_dialog(self, dialog):
        dialog.get_by_role("button", name="Close", exact=True).click()
        dialog.wait_for(state="hidden")
