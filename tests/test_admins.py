from playwright.sync_api import expect

from pages.admins_page import AdminsPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestAdminsPage:
    def test_page_loads(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        expect(admins.table).to_be_visible()

    def test_search_does_not_crash(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        admins.search("van")
        admins.page.wait_for_timeout(500)
        expect(admins.heading).to_be_visible()
