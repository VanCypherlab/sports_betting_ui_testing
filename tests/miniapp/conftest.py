import os

import pytest
from playwright.sync_api import expect

from pages.miniapp.stakeholder_entry_page import StakeholderEntryPage

# frontend-miniapp is deployed on its own origin, separate from the
# backoffice-ui base URL wired through pytest.ini's --base-url addopt, so it
# gets its own env var and its own browser context (see miniapp_page below)
# rather than sharing the global base_url fixture.
MINIAPP_BASE_URL = os.environ.get("MINIAPP_BASE_URL")

requires_miniapp_base_url = pytest.mark.skipif(
    not MINIAPP_BASE_URL,
    reason="MINIAPP_BASE_URL not set",
)


def _set_english_locale(context):
    # The app defaults to zh-CN (src/i18n/index.js reads localStorage
    # "app-locale", not Accept-Language/browser locale) unless this is set,
    # so locators built on the English strings would otherwise never match.
    context.add_init_script("window.localStorage.setItem('app-locale', 'en')")


@pytest.fixture
def miniapp_page(browser):
    context = browser.new_context(base_url=MINIAPP_BASE_URL)
    _set_english_locale(context)
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope="session")
def authenticated_miniapp_page(browser):
    # Session-scoped: entering through /stakeholder-entry triggers a branded
    # intro animation + session bootstrap (WS connect, profile/wallet/bets
    # calls) that takes ~9s before real content renders, plus a one-time
    # "Welcome" popup. Paying that cost once and navigating via the bottom
    # nav for every test (rather than a fresh login per test) keeps the
    # suite fast, mirroring the backoffice-ui regression suite's approach.
    context = browser.new_context(base_url=MINIAPP_BASE_URL)
    _set_english_locale(context)
    page = context.new_page()

    entry = StakeholderEntryPage(page)
    entry.goto()
    entry.open_miniapp("test-user-001", "10")
    entry.expect_redirected_into_app()

    # The first-visit "Welcome" popup renders as a modal overlay that marks
    # the rest of the app aria-hidden while open, so the wallet balance chip
    # is unreachable by role until the popup is dismissed.
    got_it = page.get_by_role("button", name="Got it!")
    try:
        got_it.wait_for(state="visible", timeout=15_000)
        got_it.click()
    except Exception:
        pass

    expect(page.get_by_role("button", name="Wallet balance")).to_be_visible(timeout=15_000)

    yield page
    context.close()
