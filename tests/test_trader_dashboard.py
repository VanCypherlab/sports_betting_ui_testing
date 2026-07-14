import re

import pytest
from playwright.sync_api import expect

from pages.trader_dashboard_page import TraderDashboardPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


def _breakdown(card_text: str, section_label: str, breakdown_pattern: str):
    """Parse "<section_label>\\n<total>\\n<breakdown...>" out of a summary card's inner text."""
    match = re.search(rf"{re.escape(section_label)}\n(\d+)\n{breakdown_pattern}", card_text)
    assert match, f"could not find {section_label!r} section in card text: {card_text!r}"
    return tuple(int(g) for g in match.groups())


def _currency_to_float(value: str) -> float:
    match = re.fullmatch(r"\$([\d,]+(?:\.\d{2})?)", value.strip())
    assert match, f"{value!r} is not formatted as currency"
    return float(match.group(1).replace(",", ""))


class TestTraderDashboardPage:
    def test_page_loads(self, authenticated_page):
        TraderDashboardPage(authenticated_page).goto()


class TestSummaryCardCalculations:
    """Every summary card breaks a total down into parts; the parts must reconcile with the total."""

    def test_my_matches_breakdown_sums_to_total(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        text = dashboard.card_text("My Matches")

        total, in_play, pre_match = _breakdown(text, "My Matches", r"In-play (\d+)/Pre-match (\d+)")
        assert in_play + pre_match == total

    def test_total_matches_breakdown_sums_to_total(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        text = dashboard.card_text("My Matches")  # both sections live in the same card

        total, in_play, pre_match = _breakdown(text, "Total Matches", r"In-play (\d+)/Pre-match (\d+)")
        assert in_play + pre_match == total

    def test_my_wagers_wl_does_not_exceed_total(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        text = dashboard.card_text("My Wagers (W/L)24h")

        total, won, lost = _breakdown(text, "My Wagers (W/L)24h", r"W (\d+)/L (\d+)")
        # Won + lost can be less than total: unsettled/void wagers count toward
        # the total without being won or lost yet.
        assert won + lost <= total

    def test_total_wagers_wl_does_not_exceed_total(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        text = dashboard.card_text("My Wagers (W/L)24h")

        total, won, lost = _breakdown(text, "Total Wagers (W/L)24h", r"W (\d+)/L (\d+)")
        assert won + lost <= total

    def test_alerts_waiting_does_not_exceed_total(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        text = dashboard.card_text("My Alerts24h")

        my_match = re.search(r"My Alerts24h\n(\d+)\nWaiting", text)
        total_match = re.search(r"Total Alerts24h\n(\d+)\nWaiting", text)
        assert my_match and total_match, f"could not parse alerts card: {text!r}"

        my_waiting, total_waiting = int(my_match.group(1)), int(total_match.group(1))
        # "Waiting" is shown as the count itself here, so this really checks
        # the my-scope count never exceeds the platform-wide count.
        assert my_waiting <= total_waiting

    @pytest.mark.parametrize(
        "label",
        ["My Turnover24h", "My Unsettled Turnover"],
    )
    def test_turnover_cards_are_valid_non_negative_currency(self, authenticated_page, label):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        text = dashboard.card_text(label)

        amounts = re.findall(r"\$[\d,]+(?:\.\d{2})?", text)
        assert amounts, f"no currency amounts found in card: {text!r}"
        for amount in amounts:
            assert _currency_to_float(amount) >= 0


class TestFilterCalculationConsistency:
    """A filter's option counts should reconcile with each other, not just avoid crashing."""

    def test_phase_filter_partitions_all(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        # Widen the kickoff window first so the match set isn't trivially empty.
        dashboard.filter_by_kickoff_window("All")

        dashboard.filter_by_phase("All")
        all_count = dashboard.row_count()

        dashboard.filter_by_phase("In-play")
        in_play_count = dashboard.row_count()

        dashboard.filter_by_phase("Pre-match")
        pre_match_count = dashboard.row_count()

        assert in_play_count + pre_match_count == all_count

    def test_kickoff_window_never_exceeds_all(self, authenticated_page):
        """"All" has no date restriction, so it must return >= any dated window.

        "Today" vs "7 Days" aren't compared directly against each other:
        whether an already-started match counts as "Today" vs "in the next 7
        days from now" is an app-defined boundary call, not something a
        black-box test should assume. But nothing can legitimately beat
        "All" -- as of 2026-07-13 this fails on prod-test ("7 Days" returned
        6 rows while "All" returned only 5 moments later), which points to
        "All" not actually being unrestricted, or the two requests racing
        against live-changing fixture data.
        """
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()

        dashboard.filter_by_kickoff_window("All")
        all_count = dashboard.row_count()

        dashboard.filter_by_kickoff_window("Today")
        today_count = dashboard.row_count()
        assert today_count <= all_count

        dashboard.filter_by_kickoff_window("7 Days")
        seven_days_count = dashboard.row_count()
        assert seven_days_count <= all_count

    def test_selections_column_available_within_total(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        dashboard.filter_by_kickoff_window("All")

        rows = dashboard.row_texts()
        assert rows, "expected at least one match row with Kickoff window = All"

        checked_any = False
        for row in rows:
            match = re.search(r"\b(\d+)/(\d+)\b", row)
            if not match:
                continue
            available, total = int(match.group(1)), int(match.group(2))
            assert 0 <= available <= total, f"Selections {available}/{total} out of a match row is inconsistent"
            checked_any = True
        assert checked_any, "no row exposed a parseable Selections X/Y value"


class TestSearchAndFilterFunctionality:
    def test_default_kickoff_window_is_today(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()

        today_radio = dashboard.kickoff_filter.get_by_role("radio", name="Today", exact=True)
        expect(today_radio).to_have_attribute("aria-checked", "true")

    def test_search_by_team_name_filters_rows(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        dashboard.filter_by_kickoff_window("All")

        rows = dashboard.row_texts()
        if not rows:
            pytest.skip("no matches available in this environment to search for")

        home_or_away = re.search(r"([A-Za-z][A-Za-z .'-]+) vs ([A-Za-z][A-Za-z .'-]+)", rows[0])
        assert home_or_away, f"could not extract a team name from row: {rows[0]!r}"
        team_name = home_or_away.group(1).strip()

        baseline_count = len(rows)
        dashboard.search(team_name)
        filtered_rows = dashboard.row_texts()

        assert 0 < len(filtered_rows) <= baseline_count
        for row in filtered_rows:
            assert team_name in row

    def test_search_by_match_id_returns_single_match(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        dashboard.filter_by_kickoff_window("All")

        rows = dashboard.row_texts()
        if not rows:
            pytest.skip("no matches available in this environment to search for")

        match_id = re.match(r"([A-Z0-9]{20,})", rows[0])
        assert match_id, f"could not extract a match id from row: {rows[0]!r}"

        dashboard.search(match_id.group(1))
        filtered_rows = dashboard.row_texts()

        assert len(filtered_rows) == 1
        assert match_id.group(1) in filtered_rows[0]

    def test_search_with_no_match_shows_empty_results(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        dashboard.filter_by_kickoff_window("All")

        dashboard.search("zzz-no-such-match-or-team-zzz")
        assert dashboard.row_count() == 0

    def test_clearing_search_restores_full_list(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        dashboard.filter_by_kickoff_window("All")
        baseline_count = dashboard.row_count()

        dashboard.search("zzz-no-such-match-or-team-zzz")
        assert dashboard.row_count() == 0

        dashboard.search("")
        assert dashboard.row_count() == baseline_count

    def test_sport_filter_football_does_not_add_rows(self, authenticated_page):
        """Selecting the only sport in the list should never add rows to what "All" already showed.

        The default table view is implicitly scoped to
        status=PRE_MATCH,IN_PLAY,PAUSED. Selecting a sport re-requests the
        list with a `sport` param, and on prod-test that request drops the
        status scoping entirely -- it comes back with every match ever
        played for that sport (finished ones included), so the row count
        jumps well past the baseline instead of staying the same.
        """
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        dashboard.filter_by_kickoff_window("All")
        baseline_count = dashboard.row_count()
        if baseline_count == 0:
            pytest.skip("no matches available in this environment")

        dashboard.select_sport("Football")
        assert dashboard.row_count() <= baseline_count

    def test_league_filter_only_shows_selected_league(self, authenticated_page):
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        dashboard.filter_by_kickoff_window("All")
        if dashboard.row_count() == 0:
            pytest.skip("no matches available in this environment")

        dashboard.select_league("2026 FIFA World Cup")
        rows = dashboard.row_texts()
        assert rows, "expected at least one 2026 FIFA World Cup match"
        for row in rows:
            assert "2026 FIFA World Cup" in row

    def test_pic_assignment_unassigned_and_assigned_partition_all(self, authenticated_page):
        """Unassigned + Assigned should together account for every match under "All"."""
        dashboard = TraderDashboardPage(authenticated_page)
        dashboard.goto()
        dashboard.filter_by_kickoff_window("All")

        dashboard.filter_by_pic_assignment("All")
        all_count = dashboard.row_count()

        dashboard.filter_by_pic_assignment("Unassigned")
        unassigned_count = dashboard.row_count()

        dashboard.filter_by_pic_assignment("Assigned")
        assigned_count = dashboard.row_count()

        assert unassigned_count + assigned_count == all_count
