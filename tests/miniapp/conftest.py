import pytest
from playwright.sync_api import expect

from pages.miniapp.stakeholder_entry_page import StakeholderEntryPage


def _set_english_locale(context):
    # The app defaults to zh-CN (src/i18n/index.js reads localStorage
    # "app-locale", not Accept-Language/browser locale) unless this is set,
    # so locators built on the English strings would otherwise never match.
    context.add_init_script("window.localStorage.setItem('app-locale', 'en')")


@pytest.fixture(scope="session")
def requires_miniapp_base_url(pytestconfig):
    """Skip the test if pytest.ini's `miniapp_base_url` isn't set.

    A fixture, not a module-level skipif marker -- fixtures resolve at test
    setup time, well after pytest_configure/ini parsing complete, so this
    can safely read the value via pytest's own `config.getini()` (the ini
    key itself is registered in tests/conftest.py's pytest_addoption). A
    module-level marker couldn't do this: nested conftest.py modules like
    this one are imported during pytest's early addoption-discovery pass,
    before pytest_configure ever runs -- verified live.

    Session-scoped so authenticated_miniapp_page (also session-scoped) can
    depend on it -- a session fixture can't depend on a function-scoped one.
    miniapp_page and authenticated_miniapp_page below both depend on this,
    so any test using either already gets the skip for free.
    """
    if not pytestconfig.getini("miniapp_base_url"):
        pytest.skip("miniapp_base_url not set in pytest.ini")


@pytest.fixture
def miniapp_page(browser, pytestconfig, requires_miniapp_base_url):
    context = browser.new_context(base_url=pytestconfig.getini("miniapp_base_url"))
    _set_english_locale(context)
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope="session")
def authenticated_miniapp_page(browser, pytestconfig, requires_miniapp_base_url):
    # Session-scoped: entering through /stakeholder-entry triggers a branded
    # intro animation + session bootstrap (WS connect, profile/wallet/bets
    # calls) that takes ~9s before real content renders, plus a one-time
    # "Welcome" popup. Paying that cost once and navigating via the bottom
    # nav for every test (rather than a fresh login per test) keeps the
    # suite fast, mirroring the backoffice-ui regression suite's approach.
    context = browser.new_context(base_url=pytestconfig.getini("miniapp_base_url"))
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
