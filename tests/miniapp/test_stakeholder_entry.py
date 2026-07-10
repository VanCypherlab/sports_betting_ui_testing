import pytest
from playwright.sync_api import expect

from pages.miniapp.stakeholder_entry_page import StakeholderEntryPage
from tests.miniapp.conftest import requires_miniapp_base_url

pytestmark = [requires_miniapp_base_url, pytest.mark.miniapp]


@pytest.fixture
def stakeholder_entry_page(miniapp_page):
    entry = StakeholderEntryPage(miniapp_page)
    entry.goto()
    return entry


class TestStakeholderEntryUI:
    def test_form_elements_are_visible(self, stakeholder_entry_page: StakeholderEntryPage):
        expect(stakeholder_entry_page.user_id_input).to_be_visible()
        expect(stakeholder_entry_page.amount_input).to_be_visible()
        expect(stakeholder_entry_page.submit_button).to_be_visible()


class TestStakeholderEntryValidation:
    def test_incomplete_submission_does_not_navigate(
        self, stakeholder_entry_page: StakeholderEntryPage
    ):
        # user_id is left blank. The input's native HTML `required`
        # attribute blocks the submit event before Vue's handleSubmit (and
        # its own validateForm() "Please enter user_id." message) ever run,
        # so the only observable, UI-driven signal is that nothing happens.
        stakeholder_entry_page.amount_input.fill("10")
        stakeholder_entry_page.submit_button.click()
        stakeholder_entry_page.expect_remains_on_entry_form()


class TestStakeholderEntryFlow:
    def test_backend_failure_shows_error_message(
        self, stakeholder_entry_page: StakeholderEntryPage
    ):
        stakeholder_entry_page.page.route(
            "**/api/v1/getGameURL",
            lambda route: route.fulfill(
                status=500,
                content_type="application/json",
                body='{"message": "Simulated getGameURL failure"}',
            ),
        )
        stakeholder_entry_page.open_miniapp("test-user-001", "10")
        stakeholder_entry_page.expect_error_message("Simulated getGameURL failure")

    def test_successful_entry_redirects_into_app(
        self, stakeholder_entry_page: StakeholderEntryPage
    ):
        stakeholder_entry_page.open_miniapp("test-user-001", "10")
        stakeholder_entry_page.expect_redirected_into_app()
