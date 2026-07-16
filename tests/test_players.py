import re

import pytest
from playwright.sync_api import expect

from pages.bets_page import BetsPage
from pages.miniapp.stakeholder_entry_page import StakeholderEntryPage
from pages.player_detail_page import PlayerDetailPage
from pages.players_page import PlayersPage
from tests.conftest import requires_admin_creds
# requires_miniapp_base_url isn't used directly below -- it's miniapp_page's
# own fixture dependency, which must still be importable here for pytest to
# resolve it outside tests/miniapp/'s own conftest-fixture scope.
from tests.miniapp.conftest import miniapp_page, requires_miniapp_base_url  # noqa: F401 -- fixture imports

pytestmark = requires_admin_creds


def _parse_currency(value: str):
    cleaned = value.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_percent(value: str):
    cleaned = value.replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _pick_player_with_open_wager(page):
    """Find a player with at least one Unsettled wager, via Bets -> View Player.

    Returns a player_id, or None if no Unsettled wagers are currently available.
    """
    bets = BetsPage(page)
    bets.goto()
    bets.filter_by_status("Unsettled")
    bets.search()
    if bets.row_count() == 0:
        return None

    wager_id = bets.row_wager_uuid(0)
    page.goto(f"/bets/{wager_id}")
    page.wait_for_timeout(1200)
    view_player_button = page.get_by_role("button", name="View Player")
    if view_player_button.count() == 0:
        return None
    view_player_button.click()
    page.wait_for_timeout(1000)
    return page.url.rsplit("/", 1)[-1]


class TestPlayersPage:
    def test_page_loads(self, authenticated_page):
        players = PlayersPage(authenticated_page)
        players.goto()
        expect(players.table).to_be_visible()

    def test_username_search_does_not_crash(self, authenticated_page):
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search_by_username("test")
        players.page.wait_for_timeout(500)
        expect(players.heading).to_be_visible()


class TestFilterFunctionality:
    def test_status_filter_only_shows_selected_status(self, authenticated_page):
        """Every Status option that currently has players should filter to only that status.

        Not every option necessarily has data right now (verified live: on
        this environment every player is "Active", every other Status
        option returns zero results), so options with nothing to check are
        skipped rather than failing the whole test.
        """
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        baseline_count = players.total_count()
        assert baseline_count, "expected at least one player"

        checked_any_status = False
        for status in sorted(PlayersPage.STATUS_VALUES):
            players.filter_by_status(status)
            players.search()
            row_count = players.row_count()
            if row_count == 0:
                continue
            for i in range(row_count):
                assert players.row_cell(i, PlayersPage.COL_STATUS) == status, (
                    f"row {i} has Status {players.row_cell(i, PlayersPage.COL_STATUS)!r}, expected {status!r}"
                )
            assert players.total_count() <= baseline_count
            checked_any_status = True
        assert checked_any_status, "no Status option currently has any players to check"

    def test_risk_filter_only_shows_selected_risk(self, authenticated_page):
        """Every Risk option that currently has players should filter to only that risk level."""
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        baseline_count = players.total_count()
        assert baseline_count, "expected at least one player"

        checked_any_risk = False
        for risk in sorted(PlayersPage.RISK_VALUES):
            players.filter_by_risk(risk)
            players.search()
            row_count = players.row_count()
            if row_count == 0:
                continue
            for i in range(row_count):
                assert players.row_cell(i, PlayersPage.COL_RISK) == risk, (
                    f"row {i} has Risk {players.row_cell(i, PlayersPage.COL_RISK)!r}, expected {risk!r}"
                )
            assert players.total_count() <= baseline_count
            checked_any_risk = True
        assert checked_any_risk, "no Risk option currently has any players to check"

    def test_high_risk_only_toggle_shows_only_high_risk_players(self, authenticated_page):
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        baseline_count = players.total_count()
        assert baseline_count, "expected at least one player"

        players.high_risk_only_toggle.click()
        players.search()
        row_count = players.row_count()
        if row_count == 0:
            pytest.skip("no High risk players currently available")

        for i in range(row_count):
            assert players.row_cell(i, PlayersPage.COL_RISK) == "High"
        assert players.total_count() <= baseline_count

    def test_username_search_narrows_results(self, authenticated_page):
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        baseline_count = players.row_count()
        assert baseline_count, "expected at least one player row"

        username = players.row_cell(0, PlayersPage.COL_USERNAME)
        players.search_by_username(username)
        players.search()

        filtered_count = players.row_count()
        assert filtered_count, f"expected at least one player matching username {username!r}"
        for i in range(filtered_count):
            assert username in players.row_cell(i, PlayersPage.COL_USERNAME)

    def test_player_id_search_narrows_to_exact_player(self, authenticated_page):
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        baseline_count = players.row_count()
        assert baseline_count, "expected at least one player row"

        player_id = players.row_cell(0, PlayersPage.COL_PLAYER_ID)
        players.player_id_search.fill(player_id)
        players.search()

        row_count = players.row_count()
        assert row_count, f"expected at least one player matching Player ID {player_id!r}"
        for i in range(row_count):
            assert players.row_cell(i, PlayersPage.COL_PLAYER_ID) == player_id

    def test_match_id_search_narrows_results(self, authenticated_page):
        """Match ID requires the full UUID, not a prefix -- verified live: a truncated
        ID (e.g. "01KWTP") returns zero results even though matching full wagers exist.
        """
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.search()
        assert bets.row_count(), "expected at least one wager to source a real Match ID from"
        match_id_cell = bets.table.locator("tbody tr").first.locator("td").nth(BetsPage.COL_MATCH_ID).locator("span")
        match_id = match_id_cell.get_attribute("title")
        assert match_id, "could not read a full Match ID from the Wagers list"

        players = PlayersPage(authenticated_page)
        players.goto()
        players.match_id_search.fill(match_id)
        players.search()

        row_count = players.row_count()
        assert row_count, f"expected at least one player for match {match_id!r}"

    def test_newly_registered_toggle_narrows_results(self, authenticated_page):
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        baseline_count = players.total_count()
        assert baseline_count, "expected at least one player"

        players.newly_registered_toggle.click()
        players.search()
        row_count = players.row_count()
        if row_count == 0:
            pytest.skip("no newly-registered (7d) players currently available")
        assert players.total_count() <= baseline_count

    def test_active_in_7_days_toggle_narrows_results(self, authenticated_page):
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        baseline_count = players.total_count()
        assert baseline_count, "expected at least one player"

        players.active_in_7_days_toggle.click()
        players.search()
        row_count = players.row_count()
        if row_count == 0:
            pytest.skip("no players active in the last 7 days currently available")
        assert players.total_count() <= baseline_count


class TestDataContent:
    def test_status_and_risk_values_are_from_known_sets(self, authenticated_page):
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        row_count = players.row_count()
        assert row_count, "expected at least one player"

        for i in range(row_count):
            status = players.row_cell(i, PlayersPage.COL_STATUS)
            risk = players.row_cell(i, PlayersPage.COL_RISK)
            assert status in PlayersPage.STATUS_VALUES, f"row {i} has unexpected Status {status!r}"
            assert risk in PlayersPage.RISK_VALUES, f"row {i} has unexpected Risk {risk!r}"

    def test_monetary_fields_are_parseable_currency(self, authenticated_page):
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        row_count = players.row_count()
        assert row_count, "expected at least one player"

        checked_any = False
        for i in range(row_count):
            for col in (PlayersPage.COL_OPEN_EXPOSURE, PlayersPage.COL_NET_EXPOSURE, PlayersPage.COL_TURNOVER):
                value = _parse_currency(players.row_cell(i, col))
                assert value is not None, f"row {i} col {col} is not a parseable currency value"
                checked_any = True
        assert checked_any, "no row exposed parseable monetary values to check"

    def test_open_exposure_and_turnover_are_non_negative(self, authenticated_page):
        """Open Exposure (outstanding liability) and Turnover (money wagered) can't be negative."""
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        row_count = players.row_count()
        assert row_count, "expected at least one player"

        checked_any = False
        for i in range(row_count):
            open_exposure = _parse_currency(players.row_cell(i, PlayersPage.COL_OPEN_EXPOSURE))
            turnover = _parse_currency(players.row_cell(i, PlayersPage.COL_TURNOVER))
            if open_exposure is not None:
                assert open_exposure >= 0, f"row {i} Open Exposure {open_exposure} is negative"
                checked_any = True
            if turnover is not None:
                assert turnover >= 0, f"row {i} Turnover {turnover} is negative"
                checked_any = True
        assert checked_any, "no row exposed a parseable Open Exposure/Turnover value to check"

    def test_win_rate_is_a_valid_percentage(self, authenticated_page):
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        row_count = players.row_count()
        assert row_count, "expected at least one player"

        checked_any = False
        for i in range(row_count):
            win_rate = _parse_percent(players.row_cell(i, PlayersPage.COL_WIN_RATE))
            if win_rate is None:
                continue
            assert 0 <= win_rate <= 100, f"row {i} Win Rate {win_rate}% is out of the valid 0-100% range"
            checked_any = True
        assert checked_any, "no row exposed a parseable Win Rate value to check"

    def test_turnover_hold_and_win_rate_match_wager_history(self, authenticated_page):
        """Cross-check the list's aggregate stats against the player's own Wager History rows.

        Verified live against 2 real players before writing this test:
        Turnover = sum of each wager's Turnover; Win Rate = Won-count /
        total-wager-count; Hold% = (total Turnover - total Payout) / total
        Turnover. Only players with a nonzero, single-page (<=20) Wager
        History are checked, to keep this independent of pagination.
        """
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        row_count = players.row_count()
        assert row_count, "expected at least one player"

        candidates = []
        for i in range(min(row_count, 10)):
            turnover = _parse_currency(players.row_cell(i, PlayersPage.COL_TURNOVER))
            if not turnover:
                continue
            candidates.append((
                players.row_cell(i, PlayersPage.COL_PLAYER_ID),
                turnover,
                _parse_percent(players.row_cell(i, PlayersPage.COL_HOLD_PCT)),
                _parse_percent(players.row_cell(i, PlayersPage.COL_WIN_RATE)),
            ))
        assert candidates, "expected at least one player with nonzero turnover to cross-check"

        detail = PlayerDetailPage(authenticated_page)
        checked_any = False
        for player_id, turnover, hold, win_rate in candidates:
            detail.goto(player_id)
            detail.open_wager_history_tab()
            wager_count = detail.wager_count()
            if wager_count == 0 or wager_count > 20:
                continue

            total_turnover = sum(_parse_currency(detail.row_cell(r, PlayerDetailPage.COL_TURNOVER)) for r in range(wager_count))
            total_payout = sum(_parse_currency(detail.row_cell(r, PlayerDetailPage.COL_PAYOUT)) for r in range(wager_count))
            won_count = sum(
                1 for r in range(wager_count) if detail.row_cell(r, PlayerDetailPage.COL_RESULT) == "Won"
            )

            assert abs(total_turnover - turnover) < 0.01, (
                f"player {player_id}: Wager History turnover sum {total_turnover} != list's {turnover}"
            )
            expected_win_rate = won_count / wager_count * 100
            assert abs(expected_win_rate - win_rate) < 0.1, (
                f"player {player_id}: computed win rate {expected_win_rate} != list's {win_rate}"
            )
            if total_turnover:
                expected_hold = (total_turnover - total_payout) / total_turnover * 100
                assert abs(expected_hold - hold) < 0.1, (
                    f"player {player_id}: computed hold% {expected_hold} != list's {hold}"
                )
            checked_any = True

        assert checked_any, "no player with a single-page, nonzero-turnover Wager History was available to cross-check"

    def test_wager_history_payout_matches_result_formula(self, authenticated_page):
        """Each individual wager's Payout should follow from its Turnover, Odds, and Result.

        Verified live against 7 real wagers across 2 players before writing
        this test: Won -> Payout = Turnover x Odds; Push -> Payout =
        Turnover (stake returned); Lost -> Payout = $0.
        """
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search()
        row_count = players.row_count()
        assert row_count, "expected at least one player"

        candidates = []
        for i in range(min(row_count, 10)):
            turnover = _parse_currency(players.row_cell(i, PlayersPage.COL_TURNOVER))
            if turnover:
                candidates.append(players.row_cell(i, PlayersPage.COL_PLAYER_ID))
        assert candidates, "expected at least one player with nonzero turnover to cross-check"

        detail = PlayerDetailPage(authenticated_page)
        checked_any = False
        for player_id in candidates:
            detail.goto(player_id)
            detail.open_wager_history_tab()
            wager_count = detail.wager_count()
            if wager_count == 0 or wager_count > 20:
                continue

            for r in range(wager_count):
                turnover = _parse_currency(detail.row_cell(r, PlayerDetailPage.COL_TURNOVER))
                odds = _parse_currency(detail.row_cell(r, PlayerDetailPage.COL_ODDS))
                result = detail.row_cell(r, PlayerDetailPage.COL_RESULT)
                payout = _parse_currency(detail.row_cell(r, PlayerDetailPage.COL_PAYOUT))

                if result == "Won":
                    expected = turnover * odds
                elif result == "Push":
                    expected = turnover
                elif result == "Lost":
                    expected = 0.0
                else:
                    continue  # unrecognized Result value -- nothing to check the payout formula against

                assert abs(expected - payout) < 0.02, (
                    f"player {player_id} row {r}: {result} wager turnover={turnover} odds={odds} "
                    f"expected payout {expected} but got {payout}"
                )
                checked_any = True

        assert checked_any, "no player with a single-page, nonzero-turnover Wager History was available to cross-check"


class TestPlayerDetailPage:
    """The three data tabs on a player's detail page (/players/{playerId}):
    Open Wagers, Wager History, and Notes.
    """

    def test_open_wagers_potential_win_matches_turnover_times_odds(self, authenticated_page):
        player_id = _pick_player_with_open_wager(authenticated_page)
        if player_id is None:
            pytest.skip("no Unsettled wagers currently available to source an Open Wagers player from")

        detail = PlayerDetailPage(authenticated_page)
        detail.goto(player_id)
        detail.open_open_wagers_tab()
        row_count = detail.wager_count()
        if row_count == 0 or row_count > 20:
            pytest.skip("player's Open Wagers is empty or spans multiple pages")

        checked_any = False
        for r in range(row_count):
            turnover = _parse_currency(detail.row_cell(r, PlayerDetailPage.OPEN_COL_TURNOVER))
            odds = _parse_currency(detail.row_cell(r, PlayerDetailPage.OPEN_COL_ODDS))
            potential_win = _parse_currency(detail.row_cell(r, PlayerDetailPage.OPEN_COL_POTENTIAL_WIN))
            if None in (turnover, odds, potential_win):
                continue
            expected = turnover * odds
            assert abs(expected - potential_win) < 0.02, (
                f"row {r}: turnover={turnover} odds={odds} expected potential win {expected} but got {potential_win}"
            )
            checked_any = True
        assert checked_any, "no row exposed parseable Turnover/Odds/Potential Win values to check"

    def test_open_wagers_shows_match_info_for_known_affected_player(self, authenticated_page):
        """BUG (QA-424): Open Wagers should always show the match's Home/Away team and Match Time.

        Pinned to a player known live to be affected so this reliably
        fails until fixed, rather than passing/failing depending on which
        player happens to be picked dynamically (most players' Open
        Wagers actually render fine).
        """
        detail = PlayerDetailPage(authenticated_page)
        detail.goto("51f66ffe-0b3d-4cf1-b2b3-d4e9a228e0f4")
        detail.open_open_wagers_tab()
        row_count = detail.wager_count()
        assert row_count, "expected this known-fixture player to have open wagers"

        home = detail.row_cell(0, PlayerDetailPage.OPEN_COL_HOME_TEAM)
        away = detail.row_cell(0, PlayerDetailPage.OPEN_COL_AWAY_TEAM)
        match_time = detail.row_cell(0, PlayerDetailPage.OPEN_COL_MATCH_TIME)
        assert home, "Home Team is blank (see QA-424)"
        assert away, "Away Team is blank (see QA-424)"
        assert "Invalid Date" not in match_time, f"Match Time shows {match_time!r} (see QA-424)"

    def test_wager_history_shows_match_info_for_a_working_player(self, authenticated_page):
        detail = PlayerDetailPage(authenticated_page)
        detail.goto("16c94ef1-e162-4bd3-b81d-4d295ee3c584")
        detail.open_wager_history_tab()
        row_count = detail.wager_count()
        assert row_count, "expected this known-fixture player to have wager history"

        for r in range(row_count):
            home = detail.row_cell(r, PlayerDetailPage.COL_HOME_TEAM)
            away = detail.row_cell(r, PlayerDetailPage.COL_AWAY_TEAM)
            match_date = detail.row_cell(r, PlayerDetailPage.COL_MATCH_DATE)
            assert home, f"row {r} Home Team is blank"
            assert away, f"row {r} Away Team is blank"
            assert "Invalid Date" not in match_date, f"row {r} Match Date shows {match_date!r}"

    def test_wager_history_shows_match_info_for_known_affected_wagers(self, authenticated_page):
        """BUG (QA-424): pinned to a player/wagers known live to be affected."""
        detail = PlayerDetailPage(authenticated_page)
        detail.goto("ea0dba8e-192c-49f9-ac23-e9019e39e582")
        detail.open_wager_history_tab()
        row_count = detail.wager_count()
        assert row_count, "expected this known-fixture player to have wager history"

        for r in range(row_count):
            home = detail.row_cell(r, PlayerDetailPage.COL_HOME_TEAM)
            away = detail.row_cell(r, PlayerDetailPage.COL_AWAY_TEAM)
            match_date = detail.row_cell(r, PlayerDetailPage.COL_MATCH_DATE)
            assert home, f"row {r} Home Team is blank (see QA-424)"
            assert away, f"row {r} Away Team is blank (see QA-424)"
            assert "Invalid Date" not in match_date, f"row {r} Match Date shows {match_date!r} (see QA-424)"

    def test_wager_history_wager_id_navigates_to_wager_detail_page(self, authenticated_page):
        detail = PlayerDetailPage(authenticated_page)
        detail.goto("16c94ef1-e162-4bd3-b81d-4d295ee3c584")
        detail.open_wager_history_tab()
        row_count = detail.wager_count()
        assert row_count, "expected at least one wager"

        wager_id_button = detail.wager_history_wager_id_button(0)
        wager_id = wager_id_button.get_attribute("title")
        wager_id_button.click()
        authenticated_page.wait_for_timeout(1200)

        expect(authenticated_page).to_have_url(re.compile(rf"/bets/{re.escape(wager_id)}"))
        expect(authenticated_page.get_by_role("heading", name=f"Wager {wager_id}", exact=True)).to_be_visible()

    def test_safe_mode_can_be_enabled_and_disabled(self, authenticated_page):
        """Applying a Safe Mode level should update both the detail page's
        Status badge/button and the Players list Status column; disabling
        it (reverting to Off) should restore "Active". Uses try/finally so
        a failed assertion still reverts the player back to Off.
        """
        player_id = "16c94ef1-e162-4bd3-b81d-4d295ee3c584"
        page = authenticated_page
        detail = PlayerDetailPage(page)
        players = PlayersPage(page)

        detail.goto(player_id)
        original_badge = detail.status_badge.inner_text()
        assert original_badge == "Active", f"expected fixture player to start Active, got {original_badge!r}"

        try:
            dialog = detail.open_safe_mode_dialog()
            detail.set_safe_mode_level(dialog, "S1", "QA automated test - enabling Safe Mode")

            # Re-navigate fresh rather than reading in-place DOM state --
            # verified live the badge doesn't reliably update until a real
            # reload/navigation happens.
            detail.goto(player_id)
            expect(detail.status_badge).to_have_text("Safe Mode")
            expect(detail.safe_mode_button).to_have_text("Safe Mode (S1)")

            players.goto()
            players.player_id_search.fill(player_id)
            players.search()
            assert "Safe Mode" in players.row_cell(0, PlayersPage.COL_STATUS)
        finally:
            detail.goto(player_id)
            dialog = detail.open_safe_mode_dialog()
            detail.set_safe_mode_level(dialog, "Off", "QA automated test - reverting Safe Mode")

        detail.goto(player_id)
        expect(detail.status_badge).to_have_text("Active")
        expect(detail.safe_mode_button).to_have_text("Safe Mode")

    def test_ban_and_unban_player(self, authenticated_page):
        """Banning should update both the detail page's Status badge/button
        and the Players list Status column to "Suspended"; unbanning should
        restore "Active". Uses try/finally so a failed assertion still
        unbans the player.
        """
        player_id = "16c94ef1-e162-4bd3-b81d-4d295ee3c584"
        page = authenticated_page
        detail = PlayerDetailPage(page)
        players = PlayersPage(page)

        detail.goto(player_id)
        original_badge = detail.status_badge.inner_text()
        assert original_badge == "Active", f"expected fixture player to start Active, got {original_badge!r}"
        expect(detail.ban_unban_button).to_have_text("Ban Player")

        try:
            dialog = detail.open_ban_dialog()
            detail.confirm_ban_or_unban(dialog, "QA automated test - banning player")

            # Re-navigate fresh rather than reading in-place DOM state --
            # verified live (same pattern as Safe Mode) the badge doesn't
            # reliably update until a real reload/navigation happens.
            detail.goto(player_id)
            expect(detail.status_badge).to_have_text("Suspended")
            expect(detail.ban_unban_button).to_have_text("Unban Player")

            players.goto()
            players.player_id_search.fill(player_id)
            players.search()
            assert players.row_cell(0, PlayersPage.COL_STATUS) == "Suspended"
        finally:
            detail.goto(player_id)
            if detail.ban_unban_button.inner_text() == "Unban Player":
                dialog = detail.open_ban_dialog()
                detail.confirm_ban_or_unban(dialog, "QA automated test - reverting ban")

        detail.goto(player_id)
        expect(detail.status_badge).to_have_text("Active")
        expect(detail.ban_unban_button).to_have_text("Ban Player")

    @pytest.mark.miniapp
    def test_banned_player_cannot_log_into_miniapp(self, authenticated_page, miniapp_page):
        """BUG (QA-437): banning a player in the backoffice should block
        them from logging into the miniapp; it currently doesn't.

        Pinned to the miniapp test account "test-user-002" (backoffice
        player_id 9eb2075d-4f55-476a-967b-fba7747eb837) -- the mapping was
        confirmed live via the miniapp's own `GET /api/auth/profile`
        response, which echoes back `external_uid: "test-user-002"` for
        this player_id.

        Verified live: after banning, the backoffice Status badge/list both
        correctly show "Suspended", and the miniapp's own
        `/api/auth/profile` response correctly reflects
        `"status": "suspended"` -- the ban is recorded correctly. But
        `stakeholder-entry` -> `getGameURL` still succeeds (200) and lands
        on a fully-functional Home page (Wallet balance button, 4-item
        bottom nav, match listings) instead of being blocked. Uses
        try/finally so a failed assertion still unbans the player after.
        """
        player_id = "9eb2075d-4f55-476a-967b-fba7747eb837"
        detail = PlayerDetailPage(authenticated_page)

        detail.goto(player_id)
        original_badge = detail.status_badge.inner_text()
        assert original_badge == "Active", f"expected fixture player to start Active, got {original_badge!r}"

        try:
            dialog = detail.open_ban_dialog()
            detail.confirm_ban_or_unban(dialog, "QA automated test - verifying ban blocks miniapp login (QA-437)")

            detail.goto(player_id)
            expect(detail.status_badge).to_have_text("Suspended")

            entry = StakeholderEntryPage(miniapp_page)
            entry.goto()
            entry.open_miniapp("test-user-002", "10")
            # The post-entry view plays a ~9s branded intro animation +
            # session bootstrap before real content renders -- verified
            # live -- plus a one-time "Welcome" popup on first visit.
            miniapp_page.wait_for_timeout(11_000)
            got_it = miniapp_page.get_by_role("button", name="Got it!")
            try:
                got_it.wait_for(state="visible", timeout=5_000)
                got_it.click()
            except Exception:
                pass

            wallet_button = miniapp_page.get_by_role("button", name="Wallet balance")
            assert wallet_button.count() == 0, (
                "banned player was able to log into the miniapp and reach a "
                "fully-functional Home page (see QA-437)"
            )
        finally:
            detail.goto(player_id)
            if detail.ban_unban_button.inner_text() == "Unban Player":
                dialog = detail.open_ban_dialog()
                detail.confirm_ban_or_unban(dialog, "QA automated test - reverting ban")

    def test_notes_can_be_saved_and_persist(self, authenticated_page):
        """BUG (QA-427): saving Notes currently 503s and doesn't persist."""
        player_id = "16c94ef1-e162-4bd3-b81d-4d295ee3c584"
        detail = PlayerDetailPage(authenticated_page)
        detail.goto(player_id)
        detail.open_notes_tab()

        original_note = detail.notes_textarea.input_value()
        test_note = "QA automated test note"

        try:
            detail.save_notes(test_note)
            authenticated_page.reload()
            authenticated_page.wait_for_timeout(1200)
            detail.open_notes_tab()
            assert detail.notes_textarea.input_value() == test_note, "note did not persist after reload (see QA-427)"
        finally:
            detail.goto(player_id)
            detail.open_notes_tab()
            detail.save_notes(original_note)
