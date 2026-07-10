import os

import pytest

from pages.login_page import LoginPage

ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD")

requires_admin_creds = pytest.mark.skipif(
    not (ADMIN_EMAIL and ADMIN_PASSWORD),
    reason="TEST_ADMIN_EMAIL / TEST_ADMIN_PASSWORD not set",
)


@pytest.fixture(scope="session")
def authenticated_page(browser, base_url):
    # Session-scoped: logging in once per test function (one browser login
    # per resource-page test) hit the backend's login rate limit once the
    # regression suite grew past ~20 modules, so every module smoke test
    # shares a single authenticated session/page instead. Each test still
    # starts with its own goto() to a fresh URL, so cross-test state leakage
    # isn't a practical concern for these read-mostly smoke checks.
    context = browser.new_context(base_url=base_url)
    page = context.new_page()
    login = LoginPage(page)
    login.goto()
    login.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    try:
        login.expect_login_success()
    except AssertionError:
        # test_login.py's own rate-limit test (see pytest_collection_modifyitems
        # below) runs immediately before this fixture's first use and
        # intentionally burns the account's ~1-minute login rate limit, which
        # can still be in effect here. Wait it out and retry once.
        page.wait_for_timeout(65_000)
        login.goto()
        login.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        login.expect_login_success()
    yield page

    if login.URL_PATH not in page.url:
        page.request.post("/api/backoffice/v2/auth/logout")
    context.close()


def pytest_collection_modifyitems(items):
    # test_login.py exercises the login/logout flow itself with the same
    # TEST_ADMIN_EMAIL account the session-scoped authenticated_page fixture
    # above logs into once and holds for the rest of the run. Single-session
    # enforcement means those two can't hold a session at the same time, so
    # test_login.py must fully run (and log itself out) before anything
    # triggers authenticated_page's one-time login.
    items.sort(key=lambda item: 0 if item.nodeid.split("::", 1)[0].endswith("test_login.py") else 1)
