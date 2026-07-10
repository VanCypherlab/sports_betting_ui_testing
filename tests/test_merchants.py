from playwright.sync_api import expect

from pages.merchants_page import MerchantsPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestMerchantsPage:
    def test_page_loads(self, authenticated_page):
        merchants = MerchantsPage(authenticated_page)
        merchants.goto()
        expect(merchants.table).to_be_visible()
