from pages.base_page import BackofficePage


class AuditLogPage(BackofficePage):
    """Page Object for the audit log (backoffice-ui: src/resources/audit-log)."""

    URL_PATH = "/audit"
    HEADING_TEXT = "Audit Log"

    def __init__(self, page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.search_input = page.get_by_placeholder("Search by actor, action, object...")

    def search(self, text: str):
        self.search_input.fill(text)
