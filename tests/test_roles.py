from playwright.sync_api import expect

from pages.roles_page import RolesPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestRolesPage:
    def test_page_loads(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        expect(roles.table).to_be_visible()

    def test_search_does_not_crash(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        roles.search("admin")
        roles.page.wait_for_timeout(500)
        expect(roles.heading).to_be_visible()
