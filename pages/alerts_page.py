from playwright.sync_api import Page

from pages.base_page import BackofficePage


class AlertsPage(BackofficePage):
    """Page Object for the risk alert feed (backoffice-ui: src/resources/alerts).

    Not a table -- a 3-column kanban (Critical / Warning / Info), one
    `<section>` per severity with an h2 heading (exact text "Critical" /
    "Warning" / "Info", verified live -- the CRITICAL/WARNING/INFO look is
    just a CSS text-transform) plus a card count, and each alert card is a
    `role="button"` Card that opens an AlertDetailDialog on click.

    Search and the All/Unread toggle are both client-side only (they
    filter the already-fetched list, no network refetch) -- verified live,
    so only a brief settle is needed, no long wait.

    Read/Takeover state is local-only (browser localStorage) and separate
    from the *real* backend "acknowledge" call that the dialog's "Take
    Over" button triggers (`POST /alerts/{id}/acknowledge`) -- tests here
    must NOT click Take Over. Unlike Players' Safe Mode/Ban (which have a
    reverse action), there is no "un-acknowledge" endpoint to undo it, and
    doing so would mutate real alert data on the shared qat/uat environment.
    """

    URL_PATH = "/alerts"
    HEADING_TEXT = "Alerts"

    SEVERITIES = ["Critical", "Warning", "Info"]

    def __init__(self, page: Page):
        super().__init__(page)
        self.search_input = page.get_by_placeholder("Search alerts by type or object...")
        self.all_toggle = page.get_by_role("radio", name="All", exact=True)
        self.unread_toggle = page.get_by_role("radio", name="Unread", exact=True)

    def goto(self):
        super().goto()
        # While the alerts query is loading, the page shows only a spinner
        # -- no severity columns, no "All Clear" state, no filter controls
        # -- verified live. Wait for whichever the load resolves to.
        critical_heading = self.page.get_by_role("heading", name="Critical", exact=True)
        all_clear = self.page.get_by_text("All Clear", exact=True)
        critical_heading.or_(all_clear).first.wait_for(state="visible", timeout=10_000)

    def search(self, text: str):
        self.search_input.fill(text)
        self.page.wait_for_timeout(500)

    def show_unread_only(self):
        self.unread_toggle.click()
        self.page.wait_for_timeout(500)

    def show_all(self):
        self.all_toggle.click()
        self.page.wait_for_timeout(500)

    def reset_local_state(self):
        """Clear the browser's local read/takeover state and reload.

        Keeps Unread-filter tests independent of whatever earlier tests
        (in the session-scoped shared browser) may already have marked
        read by opening a card -- purely local, no backend call involved.
        """
        self.page.evaluate(
            "localStorage.removeItem('alerts.readIds'); localStorage.removeItem('alerts.takeovers')"
        )
        self.page.reload()
        expect_heading = self.heading
        expect_heading.wait_for(state="visible")
        self.page.wait_for_timeout(1000)

    def _column(self, severity: str):
        return self.page.get_by_role("heading", name=severity, exact=True).locator("xpath=ancestor::section[1]")

    def column_count(self, severity: str) -> int:
        """The card count shown next to a column's heading (e.g. the "1" in "CRITICAL 1")."""
        span = self._column(severity).locator("h2").locator("xpath=following-sibling::span[1]")
        return int(span.inner_text().strip())

    def cards(self, severity: str | None = None):
        if severity:
            return self._column(severity).locator('[role="button"]')
        return self.page.locator('[role="button"]').filter(has_text="CURRENT VALUE")

    def card_count(self, severity: str | None = None) -> int:
        return self.cards(severity).count()

    def card_text(self, severity: str, index: int = 0) -> str:
        return self.cards(severity).nth(index).inner_text().strip()

    def open_card(self, severity: str, index: int = 0):
        self.cards(severity).nth(index).click()
        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible")
        return dialog

    def close_dialog(self, dialog):
        dialog.get_by_role("button", name="Close", exact=True).click()
        dialog.wait_for(state="hidden")

    def take_over_button(self, dialog):
        return dialog.get_by_role("button", name="Take Over", exact=True)
