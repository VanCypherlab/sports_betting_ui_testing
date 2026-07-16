import re

import pytest
from playwright.sync_api import expect

from pages.alerts_page import AlertsPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


def _first_populated_severity(alerts: AlertsPage):
    for severity in AlertsPage.SEVERITIES:
        if alerts.card_count(severity):
            return severity
    return None


class TestAlertsPage:
    def test_page_loads(self, authenticated_page):
        AlertsPage(authenticated_page).goto()

    def test_search_does_not_crash(self, authenticated_page):
        alerts = AlertsPage(authenticated_page)
        alerts.goto()
        alerts.search("test")
        expect(alerts.heading).to_be_visible()


class TestFilterFunctionality:
    def test_search_narrows_to_matching_alert_and_clears_on_no_match(self, authenticated_page):
        alerts = AlertsPage(authenticated_page)
        alerts.goto()
        baseline = alerts.card_count()
        assert baseline, "expected at least one alert"

        severity = _first_populated_severity(alerts)
        assert severity is not None, "expected at least one alert in some severity column"
        dialog = alerts.open_card(severity)
        alert_type = dialog.get_by_role("heading").inner_text().strip()
        alerts.close_dialog(dialog)
        assert alert_type, "could not read the alert's type from its dialog title"

        alerts.search(alert_type)
        assert alerts.card_count() >= 1, f"expected at least one alert matching {alert_type!r} after search"

        alerts.search("zzz-no-such-alert-should-match-nothing")
        assert alerts.card_count() == 0
        expect(alerts.page.get_by_text("All Clear", exact=True)).to_be_visible()

    def test_unread_toggle_hides_a_card_once_opened_and_marked_read(self, authenticated_page):
        alerts = AlertsPage(authenticated_page)
        alerts.goto()
        alerts.reset_local_state()

        severity = _first_populated_severity(alerts)
        assert severity is not None, "expected at least one alert to test the Unread filter against"

        alerts.show_unread_only()
        baseline_unread = alerts.card_count(severity)
        assert baseline_unread, "expected the alert to start Unread right after resetting local state"
        alerts.show_all()

        # Opening a card marks it read as a side effect (verified live) --
        # purely local state, no backend call involved.
        dialog = alerts.open_card(severity)
        alerts.close_dialog(dialog)

        alerts.show_unread_only()
        assert alerts.card_count(severity) == baseline_unread - 1, (
            "opening a card should remove it from the Unread filter"
        )


class TestDataContent:
    def test_column_counts_match_rendered_cards(self, authenticated_page):
        alerts = AlertsPage(authenticated_page)
        alerts.goto()

        checked_any = False
        for severity in AlertsPage.SEVERITIES:
            count = alerts.card_count(severity)
            if count == 0:
                continue
            assert alerts.column_count(severity) == count, (
                f"{severity} column heading count {alerts.column_count(severity)} != rendered cards {count}"
            )
            checked_any = True
        assert checked_any, "no severity column currently has any alerts to check"

    def test_header_badges_match_critical_and_warning_column_counts(self, authenticated_page):
        alerts = AlertsPage(authenticated_page)
        alerts.goto()

        critical_count = alerts.card_count("Critical")
        warning_count = alerts.card_count("Warning")
        if not critical_count and not warning_count:
            pytest.skip("no Critical or Warning alerts currently available to check header badges against")

        if critical_count:
            expect(alerts.page.get_by_text(re.compile(rf"^{critical_count} Critical$"))).to_be_visible()
        if warning_count:
            expect(alerts.page.get_by_text(re.compile(rf"^{warning_count} Warnings?$"))).to_be_visible()

    def test_each_alert_has_populated_type_object_and_valid_trigger_time(self, authenticated_page):
        alerts = AlertsPage(authenticated_page)
        alerts.goto()

        checked_any = False
        for severity in AlertsPage.SEVERITIES:
            count = min(alerts.card_count(severity), 5)
            for i in range(count):
                dialog = alerts.open_card(severity, i)
                title = dialog.get_by_role("heading").inner_text().strip()
                assert title, f"{severity} alert {i}: type is blank"

                body = dialog.inner_text()
                assert "Invalid Date" not in body, f"{severity} alert {i}: Trigger Time shows Invalid Date"
                assert re.search(r"[A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2} [AP]M", body), (
                    f"{severity} alert {i}: could not find a parseable Trigger Time in the dialog"
                )
                alerts.close_dialog(dialog)
                checked_any = True
        assert checked_any, "expected at least one alert to check"


class TestViewDialog:
    def test_dialog_shows_matching_severity_and_take_over_visibility(self, authenticated_page):
        """The dialog's severity badge should match the card's column, and
        "Take Over" should only be offered for non-Info severities --
        verified live against source (AlertDetailDialog hides it when
        `alert.severity === 'info'`). Never actually clicked -- it POSTs a
        real acknowledge with no way to undo it.
        """
        alerts = AlertsPage(authenticated_page)
        alerts.goto()

        checked_any = False
        for severity in AlertsPage.SEVERITIES:
            if alerts.card_count(severity) == 0:
                continue
            dialog = alerts.open_card(severity)
            expect(dialog).to_contain_text(severity)

            take_over = alerts.take_over_button(dialog)
            if severity == "Info":
                expect(take_over).to_have_count(0)
            else:
                expect(take_over).to_be_visible()

            alerts.close_dialog(dialog)
            expect(dialog).not_to_be_visible()
            checked_any = True

        assert checked_any, "expected at least one alert to check"

    def test_dialog_current_value_matches_card(self, authenticated_page):
        alerts = AlertsPage(authenticated_page)
        alerts.goto()

        severity = _first_populated_severity(alerts)
        assert severity is not None, "expected at least one alert"

        card_text = alerts.card_text(severity)
        dialog = alerts.open_card(severity)
        dialog_text = dialog.inner_text()
        alerts.close_dialog(dialog)

        # The Current Value shown in the dialog should be the same string
        # rendered on the card -- extract whatever (possibly blank) text
        # follows the "CURRENT VALUE" / "Current Value" label on each side.
        card_value = card_text.split("CURRENT VALUE")[-1].strip()
        dialog_value = dialog_text.split("CURRENT VALUE")[-1].split("TRIGGER TIME")[0].strip()
        assert card_value == dialog_value, (
            f"card Current Value {card_value!r} != dialog Current Value {dialog_value!r}"
        )
