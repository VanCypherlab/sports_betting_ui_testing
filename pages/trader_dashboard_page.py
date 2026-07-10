from pages.base_page import BackofficePage


class TraderDashboardPage(BackofficePage):
    """Page Object for the post-login landing dashboard (backoffice-ui: src/resources/trader-dashboard)."""

    URL_PATH = "/trader-dashboard"
    HEADING_TEXT = "Trader Dashboard"
