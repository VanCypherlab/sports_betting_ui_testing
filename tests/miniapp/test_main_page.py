import pytest
from playwright.sync_api import expect

from pages.miniapp.main_page import MainPage
from tests.miniapp.conftest import requires_miniapp_base_url

pytestmark = [requires_miniapp_base_url, pytest.mark.miniapp]


class TestMainPage:
    def test_page_loads(self, authenticated_miniapp_page):
        main = MainPage(authenticated_miniapp_page)
        main.goto()
        expect(main.wallet_balance).to_be_visible()

    def test_filter_tab_does_not_crash(self, authenticated_miniapp_page):
        main = MainPage(authenticated_miniapp_page)
        main.goto()
        main.filter_by("Today")
        expect(main.heading).to_be_visible()
