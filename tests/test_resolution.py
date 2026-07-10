from playwright.sync_api import expect

from pages.resolution_page import ResolutionPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestResolutionPage:
    def test_page_loads(self, authenticated_page):
        resolution = ResolutionPage(authenticated_page)
        resolution.goto()
        expect(resolution.table).to_be_visible()
