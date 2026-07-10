import pytest

from pages.miniapp.search_page import SearchPage
from tests.miniapp.conftest import requires_miniapp_base_url

pytestmark = [requires_miniapp_base_url, pytest.mark.miniapp]


class TestSearchPage:
    def test_page_loads(self, authenticated_miniapp_page):
        SearchPage(authenticated_miniapp_page).goto()

    def test_search_input_does_not_crash(self, authenticated_miniapp_page):
        search = SearchPage(authenticated_miniapp_page)
        search.goto()
        search.search("Argentina")
        search.page.wait_for_timeout(500)
        assert search.heading.is_visible()
