import re

from playwright.sync_api import Page

from pages.base_page import BackofficePage


class AdminsPage(BackofficePage):
    """Page Object for the admin accounts list (backoffice-ui: src/resources/admins).

    Search, the Status filter, and column sorting are ALL client-side --
    verified live (`useAdminsFilter` filters/sorts the already-fetched full
    `admins` array in a `useMemo`, no network refetch) -- so no wait beyond
    a brief redraw is needed after any of them.

    The Status filter lives inside a "Filters" popover that must be opened
    before its combobox exists in the DOM -- same pattern as Audit Log --
    and the popover button toggles closed on a second click, so
    `filter_by_status`/`clear_all_filters` only open it if not already showing.

    KNOWN BUG (QA-446): Edit Role, Suspend, and Delete all return 202 and
    show a success toast, but never actually change the admin's data --
    verified live. Only Create currently works. Do NOT write tests here
    that create throwaway admins to exercise Edit/Suspend/Delete, since
    Delete being broken means any admin created that way is now
    un-removable via the UI and would pile up permanently in qat.
    """

    URL_PATH = "/admins"
    HEADING_TEXT = "Admins"

    # 0-indexed column positions: Admin (name+email), Role, Status, Last Login, Actions.
    COL_ADMIN = 0
    COL_ROLE = 1
    COL_STATUS = 2
    COL_LAST_LOGIN = 3
    COL_ACTIONS = 4

    STATUS_VALUES = {"Active", "Suspended", "Pending", "Revoked", "Unknown"}
    STATUS_FILTER_OPTIONS = ["Active", "Suspended", "Pending"]

    def __init__(self, page: Page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.search_input = page.get_by_placeholder("Search admins...")

        self.filters_button = page.get_by_role("button", name="Filters", exact=True)
        self.status_filter = page.get_by_role("combobox")
        # A stable marker for "the Filters popover is currently open" -- the
        # combobox itself only exists in the DOM once the popover is open.
        self._clear_all_button = page.get_by_role("button", name="Clear all", exact=True)

    def goto(self):
        super().goto()
        # The initial load briefly renders a single "Loading admins..." row
        # -- verified live -- so wait for whichever the load resolves to: a
        # real row (has an "@" email) or the "no admins" empty state.
        first_real_row = self.page.locator("table tbody tr").filter(has_text="@")
        no_results = self.page.get_by_text("No admins match the current filters", exact=True)
        first_real_row.or_(no_results).first.wait_for(state="visible", timeout=10_000)

    def _ensure_filters_open(self):
        if self.status_filter.count() == 0:
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

    def clear_all_filters(self):
        self._ensure_filters_open()
        self._clear_all_button.click()
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
        if rows.count() == 1 and "No admins match the current filters" in rows.first.inner_text():
            return 0
        return rows.count()

    def row(self, row_index: int = 0):
        return self.table.locator("tbody tr").nth(row_index)

    def row_cell(self, row_index: int, col_index: int) -> str:
        return self.row(row_index).locator("td").nth(col_index).inner_text().strip()

    def row_names(self) -> list[str]:
        """Each row's Admin-column display name, in current on-screen order."""
        count = self.row_count()
        return [self.row_cell(i, self.COL_ADMIN).split("\n")[0].strip() for i in range(count)]

    def row_for_email(self, email: str):
        return self.table.locator("tbody tr").filter(has_text=email)
