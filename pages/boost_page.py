from pages.base_page import BackofficePage


class BoostPage(BackofficePage):
    """Page Object for the odds/promo boost configuration page (backoffice-ui: src/resources/boost)."""

    URL_PATH = "/boost"
    HEADING_TEXT = "BOOST"
