import re

from playwright.sync_api import Page

from pages.base_page import BackofficePage


class RolesPage(BackofficePage):
    """Page Object for the roles list (backoffice-ui: src/resources/roles).

    Search, the Status/Scope filters, and column sorting are ALL
    client-side -- verified live (`useRolesFilter` filters/sorts the
    already-fetched full `roles` array in a `useMemo`, no network refetch)
    -- so no wait beyond a brief redraw is needed after any of them.

    The Status/Scope filters live inside a "Filters" popover that must be
    opened before their comboboxes exist in the DOM -- same pattern as
    Admins/Audit Log -- and the popover button toggles closed on a second
    click, so filter helpers only open it if it isn't already showing.
    """

    URL_PATH = "/roles"
    HEADING_TEXT = "Roles"

    # 0-indexed column positions: Role (name+description), Permission
    # Summary, Scope, Admins, Status, Last Updated, Actions.
    COL_ROLE = 0
    COL_PERMISSION_SUMMARY = 1
    COL_SCOPE = 2
    COL_ADMINS = 3
    COL_STATUS = 4
    COL_LAST_UPDATED = 5
    COL_ACTIONS = 6

    STATUS_VALUES = {"Active", "Inactive"}
    STATUS_FILTER_OPTIONS = ["Active", "Inactive"]
    SCOPE_VALUES = {"Global", "Merchant", "Site", "Limited"}
    SCOPE_FILTER_OPTIONS = ["Global", "Limited"]

    def __init__(self, page: Page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.search_input = page.get_by_placeholder("Search roles...")

        self.filters_button = page.get_by_role("button", name="Filters", exact=True)
        self._combos = page.get_by_role("combobox")
        self.status_filter = self._combos.nth(0)
        self.scope_filter = self._combos.nth(1)
        self.clear_all_button = page.get_by_role("button", name="Clear all", exact=True)

    def goto(self):
        super().goto()
        # The initial load briefly renders a single "Loading roles..." row
        # -- verified live -- so wait for whichever the load resolves to: a
        # real row (has an Edit button) or the "no roles" empty state.
        first_real_row = self.page.locator("table tbody tr").filter(has_text="Edit")
        no_results = self.page.get_by_text("No roles match the current filters", exact=True)
        first_real_row.or_(no_results).first.wait_for(state="visible", timeout=10_000)

    def _ensure_filters_open(self):
        if self._combos.count() == 0:
            self.filters_button.click()
            self.page.wait_for_timeout(300)

    def search(self, text: str):
        self.search_input.fill(text)
        self.page.wait_for_timeout(400)

    def filter_by_status(self, option_text: str):
        self._ensure_filters_open()
        self.status_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()
        self.page.wait_for_timeout(400)

    def filter_by_scope(self, option_text: str):
        self._ensure_filters_open()
        self.scope_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()
        self.page.wait_for_timeout(400)

    def clear_all_filters(self):
        self._ensure_filters_open()
        self.clear_all_button.click()
        self.page.wait_for_timeout(400)

    def column_header(self, label: str):
        return self.table.locator("thead th").filter(has_text=re.compile(rf"^{re.escape(label)}"))

    def sort_by(self, column_label: str):
        self.column_header(column_label).click()
        self.page.wait_for_timeout(300)

    def row_count(self) -> int:
        if self.table.count() == 0:
            return 0
        rows = self.table.locator("tbody tr")
        if rows.count() == 1 and "No roles match the current filters" in rows.first.inner_text():
            return 0
        return rows.count()

    def row(self, row_index: int = 0):
        return self.table.locator("tbody tr").nth(row_index)

    def row_cell(self, row_index: int, col_index: int) -> str:
        return self.row(row_index).locator("td").nth(col_index).inner_text().strip()

    def row_names(self) -> list[str]:
        """Each row's Role-column name, in current on-screen order."""
        count = self.row_count()
        return [self.row_cell(i, self.COL_ROLE).split("\n")[0].strip() for i in range(count)]
