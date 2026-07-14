import os
import re

import pytest
from playwright.sync_api import expect

from pages.audit_log_page import AuditLogPage
from pages.markets_page import MarketsPage
from pages.matches_page import MatchesPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds

ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD")


class TestMatchesPage:
    def test_page_loads(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        expect(matches.table).to_be_visible()

    def test_lifecycle_filter_does_not_crash(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_lifecycle("Pre-match")
        matches.search()
        expect(matches.table).to_be_visible()

    def test_default_date_window_is_today(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()

        today_radio = matches.date_window_filter.get_by_role("radio", name="Today", exact=True)
        expect(today_radio).to_have_attribute("aria-checked", "true")


class TestFilterCalculationConsistency:
    """A filter's option counts should reconcile with each other, not just avoid crashing."""

    def test_lifecycle_partitions_all(self, authenticated_page):
        """Pre-match + In-play + Finished should add up to "All lifecycles".

        As of 2026-07-13 this fails on prod-test: e.g. Pre-match=5,
        In-play=0, Finished=42 (sum 47) vs All lifecycles=45 -- the parts
        don't reconcile with the total.
        """
        matches = MatchesPage(authenticated_page)
        matches.goto()
        # Widen the date window first so the match set isn't trivially empty.
        matches.filter_by_date_window("All")

        matches.filter_by_lifecycle("Pre-match")
        matches.search()
        pre_match_count = matches.total_count()

        matches.filter_by_lifecycle("In-play")
        matches.search()
        in_play_count = matches.total_count()

        matches.filter_by_lifecycle("Finished")
        matches.search()
        finished_count = matches.total_count()

        matches.filter_by_lifecycle("All lifecycles")
        matches.search()
        all_count = matches.total_count()

        assert pre_match_count + in_play_count + finished_count == all_count

    def test_reconciliation_partitions_all(self, authenticated_page):
        """Unsettled + Settled should add up to "All" under Reconciliation.

        As of 2026-07-13 this fails on prod-test: e.g. Unsettled=14,
        Settled=28 (sum 42) vs All=45 -- either a third reconciliation
        state exists that isn't exposed as a filter option, or the "All"
        count is inflated relative to the two named buckets.
        """
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")

        matches.filter_by_reconciliation("Unsettled")
        matches.search()
        unsettled_count = matches.total_count()

        matches.filter_by_reconciliation("Settled")
        matches.search()
        settled_count = matches.total_count()

        matches.filter_by_reconciliation("All")
        matches.search()
        all_count = matches.total_count()

        assert unsettled_count + settled_count == all_count

    def test_league_partitions_all(self, authenticated_page):
        """Every individual league's count should add up to "All leagues".

        As of 2026-07-13 this fails on prod-test, and badly: summing all 5
        leagues (2026 FIFA World Cup=44, Premier League=9, UEFA Champions
        League=1, UEFA Nations League=41, UEFA Super Cup=1 -- sum 96) gives
        more than double "All leagues" (45). Selecting almost any single
        league returns a big chunk of the platform's historical match data
        rather than just that league's matches -- the same "filter drops
        the implicit status/date scope" pattern seen on the Sport filter
        (see test_sport_filter_reset_restores_previous_count) and on the
        Trader Dashboard's Sport filter.
        """
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")

        matches.filter_by_league("All leagues")
        matches.search()
        all_count = matches.total_count()

        leagues = [
            "2026 FIFA World Cup",
            "Premier League",
            "UEFA Champions League",
            "UEFA Nations League",
            "UEFA Super Cup",
        ]
        per_league_total = 0
        for league in leagues:
            matches.filter_by_league(league)
            matches.search()
            per_league_total += matches.total_count()

        assert per_league_total == all_count

    def test_sport_filter_reset_restores_previous_count(self, authenticated_page):
        """Selecting "All sports" again after "Football" must return to the pre-filter count.

        As of 2026-07-13, on prod-test the request fired after re-selecting
        "All sports" still carries the previously-selected `sport` query
        param (confirmed via request interception), so the result count
        stays stuck at whatever "Football" showed instead of resetting.
        """
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()
        baseline_count = matches.total_count()

        matches.filter_by_sport("Football")
        matches.search()

        matches.filter_by_sport("All sports")
        matches.search()
        reset_count = matches.total_count()

        assert reset_count == baseline_count

    def test_selections_column_available_within_total(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()

        rows = matches.row_texts()
        assert rows, "expected at least one match row with date window = All"

        checked_any = False
        for row in rows:
            match = re.search(r"\b(\d+)\s*/\s*(\d+)\b", row)
            if not match:
                continue
            available, total = int(match.group(1)), int(match.group(2))
            assert 0 <= available <= total, f"Selections {available}/{total} in a match row is inconsistent"
            checked_any = True
        assert checked_any, "no row exposed a parseable Selections X/Y value"

    def test_turnover_values_are_valid_non_negative_currency(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.filter_by_lifecycle("Finished")
        matches.search()

        rows = matches.row_texts()
        assert rows, "expected at least one finished match with date window = All"

        checked_any = False
        for row in rows:
            for amount in re.findall(r"\$[\d,]+(?:\.\d{2})?", row):
                value = float(amount[1:].replace(",", ""))
                assert value >= 0
                checked_any = True
        assert checked_any, "no row exposed a parseable Turnover value"


class TestSearchAndFilterFunctionality:
    def test_search_by_team_name_narrows_results(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()
        baseline_count = matches.row_count()
        if baseline_count == 0:
            pytest.skip("no matches available in this environment to search for")

        # "Home" is column index 5: Risk, Match ID, Sport, Region, League, Home, Away, ...
        team_name = matches.table.locator("tbody tr").first.locator("td").nth(5).inner_text().strip()
        assert team_name, "could not read a Home team name from the first row"

        matches.search(team_name)
        filtered_rows = matches.row_texts()

        assert 0 < len(filtered_rows) <= baseline_count
        for row in filtered_rows:
            assert team_name in row

    def test_search_with_no_match_shows_empty_results(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")

        matches.search("zzz-no-such-match-or-team-zzz")
        assert matches.row_count() == 0

    def test_clearing_search_restores_full_list(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()
        baseline_count = matches.total_count()

        matches.search("zzz-no-such-match-or-team-zzz")
        assert matches.row_count() == 0

        matches.search("")
        assert matches.total_count() == baseline_count

    def test_league_filter_only_shows_selected_league(self, authenticated_page):
        """Every visible row should belong to the selected league.

        As of 2026-07-13 this fails on prod-test: filtering to "2026 FIFA
        World Cup" still returns at least one row with a blank League cell.
        """
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.filter_by_league("2026 FIFA World Cup")
        matches.search()

        row_count = matches.row_count()
        assert row_count, "expected at least one 2026 FIFA World Cup match"

        # "League" is column index 4: Risk, Match ID, Sport, Region, League, Home, Away, ...
        rows = matches.table.locator("tbody tr")
        for i in range(row_count):
            league_cell = rows.nth(i).locator("td").nth(4).inner_text().strip()
            assert "2026 FIFA" in league_cell, f"row {i} belongs to league {league_cell!r}, not 2026 FIFA World Cup"

    def test_pic_filter_unassigned_does_not_exceed_all(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()
        all_count = matches.total_count()

        matches.filter_by_pic("Unassigned")
        matches.search()
        unassigned_count = matches.total_count()

        assert unassigned_count <= all_count


class TestRowLevelControls:
    """Status switch, Show switch, PIC assignment popover, and the three
    action icons (Market Activity, Manage markets, Audit log) in a match row.
    """

    @staticmethod
    def _match_id(matches: MatchesPage, row_index: int = 0) -> str:
        """A row's full Match ID, read from the Manage-markets link's href.

        The Match ID *cell* only ever shows a truncated "01KX6X…" -- pulling
        the full ID from the link href is what makes it possible to
        re-locate this exact row later via search(), since a team name can
        match multiple rows (verified live: e.g. "France" matches several
        matches within date window "All").
        """
        href = matches.manage_markets_link(row_index).get_attribute("href")
        assert href, "could not read the Manage markets link href"
        match_id = href.split("matchId=", 1)[1]
        assert match_id
        return match_id

    @staticmethod
    def _row_with_assigned_role(matches: MatchesPage, role_name: str, max_rows: int = 20):
        """Index of the first row (up to max_rows) whose role_name already has an assignee, or None.

        Assignment drifts on the shared prod-test environment (other
        QA/admin activity), so row 0 isn't reliably assigned -- scanning is
        what makes these tests reproducible.
        """
        for i in range(min(matches.row_count(), max_rows)):
            if matches.pic_role_button(i, role_name).inner_text().strip() != role_name:
                return i
        return None

    def test_status_switch_toggles_and_reverts(self, authenticated_page):
        """Closing/reopening a match's Status always raises the reauth dialog.

        Closing also drops the match out of the default Lifecycle filter's
        results -- verified live -- so every re-locate below pins Lifecycle
        to "All lifecycles" to keep finding the same row.
        """
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.filter_by_lifecycle("All lifecycles")
        matches.search()
        if matches.row_count() == 0:
            pytest.skip("no matches available to test the Status switch")

        match_id = self._match_id(matches)

        def locate():
            matches.goto()
            matches.filter_by_date_window("All")
            matches.filter_by_lifecycle("All lifecycles")
            matches.search(match_id)

        locate()
        initial = matches.status_switch(0).get_attribute("aria-checked")

        matches.toggle_status_switch(0, ADMIN_PASSWORD)
        locate()
        toggled = matches.status_switch(0).get_attribute("aria-checked")
        assert toggled != initial, "Status switch did not change state after toggling"

        matches.toggle_status_switch(0, ADMIN_PASSWORD)
        locate()
        final = matches.status_switch(0).get_attribute("aria-checked")
        assert final == initial, "Status switch did not revert to its original state"

    def test_show_switch_toggles_and_reverts(self, authenticated_page):
        """Revealing a hidden match raises the reauth dialog; hiding a shown one does not."""
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()
        if matches.row_count() == 0:
            pytest.skip("no matches available to test the Show switch")

        match_id = self._match_id(matches)

        def locate():
            matches.goto()
            matches.filter_by_date_window("All")
            matches.search(match_id)

        locate()
        initial = matches.show_switch(0).get_attribute("aria-checked")

        matches.toggle_show_switch(0, ADMIN_PASSWORD)
        locate()
        toggled = matches.show_switch(0).get_attribute("aria-checked")
        assert toggled != initial, "Show switch did not change state after toggling"

        matches.toggle_show_switch(0, ADMIN_PASSWORD)
        locate()
        final = matches.show_switch(0).get_attribute("aria-checked")
        assert final == initial, "Show switch did not revert to its original state"

    def test_pic_popover_opens_with_role_toggle(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()
        if matches.row_count() == 0:
            pytest.skip("no matches available to test the PIC popover")

        expect(matches.pic_role_button(0, "Supervisor")).to_be_visible()
        expect(matches.pic_role_button(0, "Trader")).to_be_visible()

        matches.pic_role_button(0, "Supervisor").click()
        popover = authenticated_page.get_by_role("dialog")
        expect(popover).to_be_visible()
        expect(popover.get_by_role("radio", name="Supervisor", exact=True)).to_have_attribute("aria-checked", "true")
        expect(popover.get_by_role("radio", name="Trader", exact=True)).to_have_attribute("aria-checked", "false")

        authenticated_page.keyboard.press("Escape")
        expect(popover).not_to_be_visible()

    def test_pic_assignment_updates_and_reverts(self, authenticated_page):
        """Selecting a person commits immediately (no Confirm click, no reauth), then revert.

        Handles both starting states verified live: if the role already has
        someone assigned, reassign to a different person and revert by
        re-selecting the original; if unassigned, assign anyone and revert
        via the popover's "Reset PIC" button.
        """
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()
        if matches.row_count() == 0:
            pytest.skip("no matches available to test PIC assignment")

        match_id = self._match_id(matches)

        def locate():
            matches.goto()
            matches.filter_by_date_window("All")
            matches.search(match_id)

        locate()
        original_text = matches.pic_role_button(0, "Supervisor").inner_text().strip()
        was_unassigned = original_text == "Supervisor"

        popover = matches.open_pic_popover(0, "Supervisor")
        items = matches.pic_assignable_items(popover)
        expect(items.first).to_be_visible()

        current_item = popover.locator('[data-slot="pic-assign-dropdown-item"][data-current="true"]')
        has_current = current_item.count() > 0
        original_uuid = current_item.get_attribute("data-value") if has_current else None

        if has_current:
            other_item = popover.locator(
                f'[data-slot="pic-assign-dropdown-item"]:not([data-value="{original_uuid}"])'
            ).first
        else:
            other_item = items.first
        matches.assign_pic(popover, other_item)

        locate()
        reassigned_text = matches.pic_role_button(0, "Supervisor").inner_text().strip()
        assert reassigned_text != original_text, "Supervisor assignment did not change"

        if was_unassigned:
            popover = matches.open_pic_popover(0, "Supervisor")
            matches.reset_pic(popover)
        else:
            popover = matches.open_pic_popover(0, "Supervisor")
            original_item = popover.locator(f'[data-slot="pic-assign-dropdown-item"][data-value="{original_uuid}"]')
            matches.assign_pic(popover, original_item)

        locate()
        final_text = matches.pic_role_button(0, "Supervisor").inner_text().strip()
        assert final_text == original_text, "Supervisor assignment did not revert to the original state"

    def test_clicking_current_supervisor_assignee_again_is_a_noop(self, authenticated_page):
        """Re-selecting the already-assigned Supervisor does not unassign them.

        Confirmed with the team (2026-07-14) that this is intentional, not a
        bug: Supervisor and Trader are not meant to behave the same way
        here -- Trader supports toggle-to-unassign (see
        test_clicking_current_trader_assignee_again_unassigns), Supervisor
        does not. Verified live: no PATCH fires, the popover just closes,
        and the assignee is unchanged.
        """
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()
        row_index = self._row_with_assigned_role(matches, "Supervisor")
        if row_index is None:
            pytest.skip("no row with an already-assigned Supervisor found")

        match_id = self._match_id(matches, row_index)

        def locate():
            matches.goto()
            matches.filter_by_date_window("All")
            matches.search(match_id)

        locate()
        original_text = matches.pic_role_button(0, "Supervisor").inner_text().strip()

        popover = matches.open_pic_popover(0, "Supervisor")
        current_item = popover.locator('[data-slot="pic-assign-dropdown-item"][data-current="true"]')
        expect(current_item).to_be_visible()
        original_uuid = current_item.get_attribute("data-value")

        current_item.click()
        expect(popover).not_to_be_visible(timeout=5_000)
        authenticated_page.wait_for_timeout(1000)

        locate()
        final_text = matches.pic_role_button(0, "Supervisor").inner_text().strip()

        # Revert defensively in case this behavior ever changes: if the
        # click above did unassign the Supervisor, restore the original.
        if final_text == "Supervisor":
            popover = matches.open_pic_popover(0, "Supervisor")
            original_item = popover.locator(f'[data-slot="pic-assign-dropdown-item"][data-value="{original_uuid}"]')
            matches.assign_pic(popover, original_item)

        assert final_text == original_text, "clicking the already-assigned Supervisor again changed the assignment"

    def test_clicking_current_trader_assignee_again_unassigns(self, authenticated_page):
        """Re-selecting the already-assigned Trader unassigns them (toggle-to-clear).

        Verified live: a PATCH fires and the row reverts to unassigned.
        Supervisor shares the same popover component but does not support
        this -- confirmed intentional, not a bug (see
        test_clicking_current_supervisor_assignee_again_is_a_noop).
        """
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()
        row_index = self._row_with_assigned_role(matches, "Trader")
        if row_index is None:
            pytest.skip("no row with an already-assigned Trader found")

        match_id = self._match_id(matches, row_index)

        def locate():
            matches.goto()
            matches.filter_by_date_window("All")
            matches.search(match_id)

        locate()
        original_text = matches.pic_role_button(0, "Trader").inner_text().strip()

        popover = matches.open_pic_popover(0, "Trader")
        current_item = popover.locator('[data-slot="pic-assign-dropdown-item"][data-current="true"]')
        expect(current_item).to_be_visible()
        original_uuid = current_item.get_attribute("data-value")

        matches.assign_pic(popover, current_item)

        locate()
        unassigned_text = matches.pic_role_button(0, "Trader").inner_text().strip()
        assert unassigned_text == "Trader", "clicking the already-assigned Trader again did not unassign them"

        popover = matches.open_pic_popover(0, "Trader")
        original_item = popover.locator(f'[data-slot="pic-assign-dropdown-item"][data-value="{original_uuid}"]')
        matches.assign_pic(popover, original_item)

        locate()
        final_text = matches.pic_role_button(0, "Trader").inner_text().strip()
        assert final_text == original_text, "Trader assignment did not revert to the original person"

    def test_market_activity_icon_navigates(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()
        if matches.row_count() == 0:
            pytest.skip("no matches available to test the action icons")

        matches.market_activity_link(0).click()
        expect(authenticated_page).to_have_url(re.compile(r"/matches/[^/?]+/activity"))
        expect(authenticated_page.get_by_text("Something went wrong", exact=False)).not_to_be_visible()

    def test_manage_markets_icon_navigates(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()
        if matches.row_count() == 0:
            pytest.skip("no matches available to test the action icons")

        matches.manage_markets_link(0).click()
        expect(authenticated_page).to_have_url(re.compile(r"/markets\?matchId="))
        expect(MarketsPage(authenticated_page).heading).to_be_visible()

    def test_audit_log_icon_navigates(self, authenticated_page):
        matches = MatchesPage(authenticated_page)
        matches.goto()
        matches.filter_by_date_window("All")
        matches.search()
        if matches.row_count() == 0:
            pytest.skip("no matches available to test the action icons")

        matches.audit_log_link(0).click()
        expect(authenticated_page).to_have_url(re.compile(r"/audit\?matchId="))
        expect(AuditLogPage(authenticated_page).heading).to_be_visible()
