import os

import pytest
from playwright.sync_api import expect

from pages.bets_page import BetsPage
from pages.miniapp.bet_page import BetPage
from pages.miniapp.main_page import MainPage
from pages.miniapp.match_page import MatchPage
from pages.miniapp.stakeholder_entry_page import StakeholderEntryPage
from pages.wager_detail_page import WagerDetailPage
from tests.conftest import requires_admin_creds
# requires_miniapp_base_url isn't used directly below -- it's miniapp_page's
# own fixture dependency, which must still be importable here for pytest to
# resolve it outside tests/miniapp/'s own conftest-fixture scope.
from tests.miniapp.conftest import miniapp_page, requires_miniapp_base_url  # noqa: F401 -- fixture imports

pytestmark = requires_admin_creds

BULK_VOID_PASSWORD = os.environ.get("BULK_VOID_PASSWORD")

# A different stakeholder than the shared session-scoped "test-user-001" used
# by every other miniapp test, so this test doesn't compete with them for the
# same account's session. Note: bet placement is rate-limited at a level
# broader than per-account -- verified live, switching accounts did not avoid
# a 429 hit shortly after another account's -- so this alone doesn't
# guarantee avoiding rate limits under repeated/rapid test runs.
BULK_VOID_TEST_USER = "test-user-002"


def _parse_currency(value: str):
    cleaned = value.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_match_time(list_value: str) -> str:
    """The list cell renders date/time as two stacked lines; the detail page
    shows them comma-joined on one line -- e.g. "Jul 12\\n\\n05:00:00 AM
    (UTC+4)" (list) vs "Jul 12, 05:00:00 AM (UTC+4)" (detail).
    """
    parts = [p for p in list_value.splitlines() if p.strip()]
    return ", ".join(parts)


def _find_row(bets: BetsPage, row_count: int, predicate):
    for i in range(row_count):
        if predicate(i):
            return i
    return None


class TestBetsPage:
    def test_page_loads(self, authenticated_page):
        bets = BetsPage(authenticated_page)
        bets.goto()
        expect(bets.table).to_be_visible()

    def test_status_filter_does_not_crash(self, authenticated_page):
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.filter_by_status("Unsettled")
        expect(bets.table).to_be_visible()


class TestFilterFunctionality:
    def test_stake_range_filter_narrows_by_turnover(self, authenticated_page):
        """Raising the Stake Range minimum should only leave wagers whose Turnover meets it."""
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.search()
        baseline_count = bets.row_count()
        assert baseline_count, "expected at least one wager in the default view"

        bets.increase_stake_range_min(presses=10)
        min_value, _ = bets.stake_range_values()
        assert min_value > 0, "stake range minimum did not change after raising it"

        bets.search()
        filtered_count = bets.row_count()
        assert filtered_count <= baseline_count

        checked_any = False
        for i in range(filtered_count):
            turnover = _parse_currency(bets.row_cell(i, BetsPage.COL_TURNOVER))
            if turnover is None:
                continue
            assert turnover >= min_value, f"row {i} turnover {turnover} is below the stake range minimum {min_value}"
            checked_any = True
        assert checked_any, "no row exposed a parseable Turnover value to check against the stake range"

    def test_stake_range_filter_excludes_amounts_above_lowered_max(self, authenticated_page):
        """Lowering the Stake Range maximum should only leave wagers whose Turnover is within it."""
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.search()
        baseline_count = bets.row_count()
        assert baseline_count, "expected at least one wager in the default view"

        bets.decrease_stake_range_max(presses=50)  # 50 * 50 = -2500, from 10000 -> 7500
        _, max_value = bets.stake_range_values()
        assert max_value < 10000, "stake range maximum did not change after lowering it"

        bets.search()
        filtered_count = bets.row_count()
        assert filtered_count <= baseline_count

        checked_any = False
        for i in range(filtered_count):
            turnover = _parse_currency(bets.row_cell(i, BetsPage.COL_TURNOVER))
            if turnover is None:
                continue
            assert turnover <= max_value, f"row {i} turnover {turnover} is above the stake range maximum {max_value}"
            checked_any = True
        assert checked_any, "no row exposed a parseable Turnover value to check against the stake range"


class TestDataContent:
    def test_settled_wagers_have_a_win_loss_value(self, authenticated_page):
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.filter_by_status("Settled")
        bets.search()

        row_count = bets.row_count()
        assert row_count, "expected at least one Settled wager"

        checked_any = False
        for i in range(row_count):
            status = bets.row_cell(i, BetsPage.COL_STATUS)
            if status != "Settled":
                continue
            win_loss = bets.row_cell(i, BetsPage.COL_WIN_LOSS)
            assert win_loss not in ("", "--", "-"), f"row {i} is Settled but has no Win/Loss value: {win_loss!r}"
            # Usually a signed amount ("+$X" / "-$X"); a push/break-even
            # settlement can legitimately show unsigned "$0.00" -- verified live.
            assert win_loss == "$0.00" or (win_loss[0] in ("+", "-") and "$" in win_loss), (
                f"row {i} Win/Loss value {win_loss!r} doesn't look like a currency amount"
            )
            checked_any = True
        assert checked_any, "no Settled row was found to check a Win/Loss value on"


class TestBulkVoid:
    """Selecting wagers and Bulk Void: settled wagers must not be voidable;
    unsettled wagers must be. The full void-and-confirm flow (password +
    reason submission) is only exercised against a wager this suite placed
    itself via the miniapp -- see TestPlaceBetThenBulkVoid below -- never
    against real historical wagers.
    """

    def test_settled_wagers_cannot_be_bulk_voided(self, authenticated_page):
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.filter_by_status("Settled")
        bets.search()

        row_count = bets.row_count()
        assert row_count, "expected at least one Settled wager to test"

        bets.row_checkbox(0).click()
        expect(bets.bulk_void_button).to_be_visible()
        expect(bets.bulk_void_button).to_be_disabled()

    def test_unsettled_wagers_can_be_bulk_voided(self, authenticated_page):
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.filter_by_status("Unsettled")
        bets.search()

        row_count = bets.row_count()
        if row_count == 0:
            pytest.skip("no Unsettled wagers currently available")

        bets.row_checkbox(0).click()
        expect(bets.bulk_void_button).to_be_visible()
        expect(bets.bulk_void_button).to_be_enabled()


@pytest.mark.miniapp
class TestPlaceBetThenBulkVoid:
    """End-to-end: place a real bet via the miniapp, then bulk void that
    exact wager in the backoffice -- never against a real historical wager.

    No explicit miniapp-base-url skip needed here -- the miniapp_page
    fixture used below already depends on it (see tests/miniapp/conftest.py).
    """

    def test_place_bet_via_miniapp_then_bulk_void_it(self, miniapp_page, authenticated_page):
        assert BULK_VOID_PASSWORD, "BULK_VOID_PASSWORD not set in .env"

        entry = StakeholderEntryPage(miniapp_page)
        entry.goto()
        entry.open_miniapp(BULK_VOID_TEST_USER, "10")
        entry.expect_redirected_into_app()

        got_it = miniapp_page.get_by_role("button", name="Got it!")
        try:
            got_it.wait_for(state="visible", timeout=15_000)
            got_it.click()
        except Exception:
            pass
        expect(miniapp_page.get_by_role("button", name="Wallet balance")).to_be_visible(timeout=15_000)

        main = MainPage(miniapp_page)
        main.goto()
        miniapp_page.wait_for_timeout(1500)
        main.filter_by("All")
        miniapp_page.wait_for_timeout(2000)
        main.open_first_match()
        miniapp_page.wait_for_timeout(1500)

        match = MatchPage(miniapp_page)
        match.select_win_loss_home_odds()
        miniapp_page.wait_for_timeout(800)

        with miniapp_page.expect_response(lambda r: "/bets/place" in r.url, timeout=15_000) as response_info:
            match.place_bet("10")
        response = response_info.value
        if response.status == 429:
            pytest.skip(f"miniapp bet placement is currently rate-limited: {response.text()[:200]}")
        assert response.status == 200, (
            f"bet placement failed with status {response.status}: {response.text()[:300]}"
        )
        miniapp_page.wait_for_timeout(1500)

        # Placing a bet navigates straight to a ticket confirmation view (no
        # bottom nav on this view) that already shows the new ticket number
        # -- verified live -- so read it here rather than via the Bet tab.
        ticket_el = miniapp_page.get_by_text(BetPage.TICKET_NUMBER_PATTERN).first
        expect(ticket_el).to_be_visible(timeout=10_000)
        ticket_number = ticket_el.inner_text().strip()

        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.wager_id_search.fill(ticket_number)
        bets.search()
        assert bets.row_count() == 1, f"expected exactly one wager for ticket {ticket_number}"
        assert bets.row_cell(0, BetsPage.COL_STATUS) == "Unsettled"

        bets.row_checkbox(0).click()
        expect(bets.bulk_void_button).to_be_enabled()
        dialog = bets.open_bulk_void_dialog()
        bets.submit_bulk_void(dialog, reason="Automated QA test wager (placed by this test)", password=BULK_VOID_PASSWORD)
        authenticated_page.wait_for_timeout(2000)

        bets.goto()
        bets.wager_id_search.fill(ticket_number)
        bets.search()
        assert bets.row_count() == 1
        assert bets.row_cell(0, BetsPage.COL_STATUS) == "Voided", "wager was not voided"


class TestWagerDetailPage:
    """The wager detail page (/bets/{wagerUuid}) should show the same values
    as the corresponding row in the Wagers list.
    """

    def test_detail_page_stat_values_match_the_list_row(self, authenticated_page):
        """Uses a Settled wager specifically -- the detail page's fourth stat
        card is conditional on wager state: Settled wagers show "Win/Loss",
        while Unsettled/Voided wagers show "Potential Return" instead
        (verified live). Filtering to Settled here keeps this test's row 0
        stable regardless of what real or test-placed wagers occupy the
        unfiltered list's row 0.
        """
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.filter_by_status("Settled")
        bets.search()
        row_count = bets.row_count()
        assert row_count, "expected at least one Settled wager"

        turnover = bets.row_cell(0, BetsPage.COL_TURNOVER)
        win_loss = bets.row_cell(0, BetsPage.COL_WIN_LOSS)
        exposure = bets.row_cell(0, BetsPage.COL_EXPOSURE)
        odds = bets.row_cell(0, BetsPage.COL_ODDS)
        wager_id = bets.row_wager_uuid(0)

        detail = WagerDetailPage(authenticated_page)
        detail.goto(wager_id)

        expect(detail.stake_value).to_have_text(turnover)
        expect(detail.win_loss_value).to_have_text(win_loss)
        # Exposure is unsigned/uncommaed on the detail page ("1000" vs list's "$1,000").
        expect(detail.exposure_value).to_have_text(str(int(_parse_currency(exposure))))
        expect(detail.odds_value).to_have_text(odds)

    def test_detail_page_match_and_selection_details_match_the_list_row(self, authenticated_page):
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.search()
        row_count = bets.row_count()
        assert row_count, "expected at least one wager"

        home = bets.row_home_team(0)
        away = bets.row_cell(0, BetsPage.COL_AWAY_TEAM)
        market = bets.row_cell(0, BetsPage.COL_MARKET)
        selection = bets.row_cell(0, BetsPage.COL_SELECTION)
        merchant = bets.row_merchant_name(0)
        user_id = bets.row_user_id(0)
        wager_id = bets.row_wager_uuid(0)

        detail = WagerDetailPage(authenticated_page)
        detail.goto(wager_id)

        expect(detail.match_teams).to_have_text(f"{home} vs {away}")
        expect(detail.market_value).to_have_text(market)
        expect(detail.selection_value).to_have_text(selection)
        expect(detail.merchant_value).to_have_text(merchant)
        expect(detail.player_value).to_have_text(user_id)

    def test_detail_page_match_time_matches_list_when_populated(self, authenticated_page):
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.search()
        row_count = bets.row_count()
        assert row_count, "expected at least one wager"

        row_index = _find_row(bets, row_count, lambda i: bets.row_cell(i, BetsPage.COL_MATCH_TIME) != "--")
        if row_index is None:
            pytest.skip("no wager with a populated Match Time currently available")

        list_match_time = bets.row_cell(row_index, BetsPage.COL_MATCH_TIME)
        wager_id = bets.row_wager_uuid(row_index)

        detail = WagerDetailPage(authenticated_page)
        detail.goto(wager_id)
        expect(detail.match_time_value).to_have_text(_normalize_match_time(list_match_time))

    def test_detail_page_phase_badge_matches_list_phase(self, authenticated_page):
        """BUG: the badge next to Match Time on the detail page should reflect
        the same Phase as the list's Phase column for the same wager.

        Verified live across multiple wagers on different matches: the
        badge always reads "Live" regardless of the list's actual Phase
        (e.g. "Final"). This asserts the expected/correct behavior
        directly, so it is expected to fail until fixed -- that's fine.
        """
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.search()
        row_count = bets.row_count()
        assert row_count, "expected at least one wager"

        list_phase = bets.row_cell(0, BetsPage.COL_PHASE)
        wager_id = bets.row_wager_uuid(0)

        detail = WagerDetailPage(authenticated_page)
        detail.goto(wager_id)
        expect(detail.match_time_badge).to_have_text(list_phase)

    def test_detail_page_shows_placeholder_not_bogus_date_for_missing_match_time(self, authenticated_page):
        """BUG: when the list shows Match Time as "--" (no data available),
        the detail page should show an equivalent placeholder, not a
        specific fallback date/time.

        Verified live: the detail page shows a bogus "Jan 1, HH:MM:SS AM
        (UTC+4)" instead. This asserts the expected/correct behavior
        directly, so it is expected to fail until fixed -- that's fine.
        """
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.search()
        row_count = bets.row_count()
        assert row_count, "expected at least one wager"

        row_index = _find_row(bets, row_count, lambda i: bets.row_cell(i, BetsPage.COL_MATCH_TIME) == "--")
        if row_index is None:
            pytest.skip("no wager with a missing Match Time currently available")

        wager_id = bets.row_wager_uuid(row_index)

        detail = WagerDetailPage(authenticated_page)
        detail.goto(wager_id)
        text = detail.match_time_value.inner_text().strip()
        assert text in ("--", "N/A", "Unknown", ""), f"expected a placeholder for missing match time, got {text!r}"
