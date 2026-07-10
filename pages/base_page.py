from playwright.sync_api import Page, expect


class BackofficePage:
    """Shared shape for authenticated backoffice-ui resource pages.

    Subclasses set URL_PATH/HEADING_TEXT and add locators only for controls
    verified live against admin.prod-test.cypherlab.tech.
    """

    URL_PATH: str = ""
    HEADING_TEXT: str = ""

    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name=self.HEADING_TEXT, exact=True)

    def goto(self):
        self.page.goto(self.URL_PATH)
        expect(self.heading).to_be_visible()
        expect(self.page.get_by_text("Something went wrong", exact=False)).not_to_be_visible()
