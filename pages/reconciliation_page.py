from pages.base_page import BackofficePage


class ReconciliationPage(BackofficePage):
    """Page Object for the match reconciliation worklist (backoffice-ui: src/resources/reconciliation)."""

    URL_PATH = "/reconciliation"
    HEADING_TEXT = "Match Reconciliation"

    def __init__(self, page):
        super().__init__(page)
        # Two tables render side by side (Canonical / Vendor sections).
        self.table = page.get_by_role("table").first
        self.refresh_button = page.get_by_role("button", name="Refresh")
