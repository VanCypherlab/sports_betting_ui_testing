from playwright.sync_api import expect

from pages.matches_page import MatchesPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestMatchesPage:
    def test_page_loads(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        expect(matches.table).to_be_visible()

    def test_lifecycle_filter_does_not_crash(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_lifecycle("Pre-match")
        expect(matches.table).to_be_visible()
