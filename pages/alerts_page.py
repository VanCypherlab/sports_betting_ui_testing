from pages.base_page import BackofficePage


class AlertsPage(BackofficePage):
    """Page Object for the risk alert feed (backoffice-ui: src/resources/alerts)."""

    URL_PATH = "/alerts"
    HEADING_TEXT = "Alerts"
