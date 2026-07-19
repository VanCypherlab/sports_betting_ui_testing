import random

import pytest
from playwright.sync_api import expect

from pages.market_activity_page import MarketActivityPage
from pages.markets_page import MarketsPage
from pages.matches_page import MatchesPage
from tests.conftest import ADMIN_PASSWORD, requires_admin_creds

pytestmark = requires_admin_creds


def _to_int(value: str):
    try:
        return int(value)
    except ValueError:
        return None


def _clean_truncated(text: str) -> str:
    """Strip a trailing ellipsis from Matches-table cells that visually
    truncate long names (verified live: inner_text() reflects the
    rendered "…", not the full underlying value -- e.g. "Switzerlan…"),
    so callers can safely substring-match against the untruncated text
    shown elsewhere (e.g. the Markets page header).
    """
    return text.rstrip("…").strip()


def _pick_zero_wager_prematch_fixture(page):
    """Find a Pre-match, not-yet-started fixture with zero wagers.

    Used for Status/Edit action tests instead of a hardcoded match ID, so
    they keep working once any specific fixture match finishes or is
    archived -- rather than breaking outright if that match stops existing.
    On finished matches the STATUS/AUTOPILOT switches and Edit button are
    disabled, so mutating them there isn't
    possible, but a still-open Pre-match fixture's markets are; picking one
    with zero wagers keeps that mutation low-risk (not touching any real
    trading activity).

    Returns (match_id, home_team, away_team), or None if no such fixture
    is currently available (callers should pytest.skip in that case).
    """
    matches = MatchesPage(page)
    matches.goto()
    matches.filter_by_date_window("All")
    matches.filter_by_lifecycle("Pre-match")
    matches.search()

    for i in range(matches.row_count()):
        row = matches.row(i)
        wagers_cell = row.locator("td").nth(11).inner_text().strip()
        if wagers_cell == "—":
            href = matches.manage_markets_link(i).get_attribute("href")
            match_id = href.split("matchId=", 1)[1]
            home = _clean_truncated(row.locator("td").nth(5).inner_text())
            away = _clean_truncated(row.locator("td").nth(6).inner_text())
            return match_id, home, away
    return None


def _pick_finished_zero_wager_fixture(page):
    """Find a Finished match with markets loaded and zero wagers on every market.

    Used for filter/numeric-calculation tests instead of a hardcoded match
    ID, so they keep working once any specific fixture match is archived.
    Dynamically discovered and validated rather than assumed -- verified
    live that some matches labeled "Finished" in the Matches list
    inconsistently show as Pre-match with blank team names on the Markets
    page (a real uat data inconsistency, e.g. 01KWZCNW8YXBAXV0PKYBEGE3C4
    "Argentina vs Switzerland"), so candidates are validated by actually
    checking the Markets page resolves the expected team names and has at
    least one row with genuinely parseable ("0", not "—" N/A) wager/turnover
    figures, not just accepted on Lifecycle label + a nonzero row count.

    Returns (match_id, home_team, away_team, league), or None if no such
    fixture is currently available (callers should pytest.skip in that case).
    """
    matches = MatchesPage(page)
    matches.goto()
    matches.filter_by_date_window("All")
    matches.filter_by_lifecycle("Finished")
    matches.search()

    markets = MarketsPage(page)
    for i in range(matches.row_count()):
        href = matches.manage_markets_link(i).get_attribute("href")
        match_id = href.split("matchId=", 1)[1]
        home = _clean_truncated(matches.row(i).locator("td").nth(5).inner_text())
        away = _clean_truncated(matches.row(i).locator("td").nth(6).inner_text())
        league = _clean_truncated(matches.row(i).locator("td").nth(4).inner_text())

        markets.goto()
        markets.search_by_match_id(match_id)
        row_count = markets.row_count()

        if row_count and _is_valid_finished_fixture(markets, row_count, home, away):
            return match_id, home, away, league

        matches.goto()
        matches.filter_by_date_window("All")
        matches.filter_by_lifecycle("Finished")
        matches.search()
    return None


def _is_valid_finished_fixture(markets: MarketsPage, row_count: int, home: str, away: str) -> bool:
    body_text = markets.page.locator("body").inner_text()
    if home not in body_text or away not in body_text:
        return False  # team names didn't resolve -- not the fixture it claimed to be

    has_real_wager_activity = False
    has_parseable_row = False
    for r in range(row_count):
        if markets.row_cell_count(r) != 27:
            continue  # section header rows ("IN-PLAY", "PRE-MATCH", ...) have a single cell

        home_wagers = markets.row_cell(r, MarketsPage.COL_HOME_WAGERS)
        if home_wagers not in ("0", "—", ""):
            has_real_wager_activity = True

        wagers_parseable = None not in (
            _to_int(home_wagers),
            _to_int(markets.row_cell(r, MarketsPage.COL_AWAY_WAGERS)),
            _to_int(markets.row_cell(r, MarketsPage.COL_DRAW_WAGERS)),
            _to_int(markets.row_cell(r, MarketsPage.COL_SUMMARY_WAGERS)),
        )
        turnover_parseable = None not in (
            _to_int(markets.row_cell(r, MarketsPage.COL_HOME_TURNOVER)),
            _to_int(markets.row_cell(r, MarketsPage.COL_AWAY_TURNOVER)),
            _to_int(markets.row_cell(r, MarketsPage.COL_DRAW_TURNOVER)),
            _to_int(markets.row_cell(r, MarketsPage.COL_SUMMARY_TOTAL_TURNOVER)),
        )
        if wagers_parseable and turnover_parseable:
            has_parseable_row = True

    return not has_real_wager_activity and has_parseable_row


def _pick_prematch_match_ids_sample(page, max_sample: int = 10):
    """A broad, unfiltered sample of Pre-match fixture IDs (any wager count,
    any league) -- deliberately NOT narrowed to a single "known-good"
    fixture like `_pick_finished_zero_wager_fixture`, since the point here
    is to catch whichever matches currently have a broken Markets header
    (see QA-477), not to avoid them.

    Scoped to Pre-match rather than the page's default "Today" window/all
    lifecycles so this doesn't also trip over the already-tracked QA-474
    tmp:lsports placeholder matches (blank at the source, a different bug).
    """
    matches = MatchesPage(page)
    matches.goto()
    matches.filter_by_date_window("All")
    matches.filter_by_lifecycle("Pre-match")
    matches.search()

    row_count = matches.row_count()
    if row_count == 0:
        return []

    match_ids = [matches.manage_markets_link(i).get_attribute("href").split("matchId=", 1)[1] for i in range(row_count)]
    return random.sample(match_ids, min(max_sample, len(match_ids)))


class TestMarketsPage:
    def test_page_loads(self, authenticated_page):
        MarketsPage(authenticated_page).goto()

    def test_match_id_search_does_not_crash(self, authenticated_page):
        markets = MarketsPage(authenticated_page)
        markets.goto()
        markets.search_by_match_id("nonexistent-match-id")
        markets.page.wait_for_timeout(500)
        assert markets.heading.is_visible()

    def test_search_valid_match_id_shows_match_summary(self, authenticated_page):
        fixture = _pick_finished_zero_wager_fixture(authenticated_page)
        if fixture is None:
            pytest.skip("no zero-wager Finished fixture currently available")
        match_id, home, away, league = fixture

        markets = MarketsPage(authenticated_page)
        markets.goto()
        markets.search_by_match_id(match_id)

        body_text = markets.page.locator("body").inner_text()
        assert home in body_text
        assert away in body_text
        assert league in body_text

    def test_manage_markets_header_shows_real_team_names_and_kickoff(self, authenticated_page):
        """BUG (QA-477): when a match's `/markets` projection 404s ("market
        projection not found"), the Markets page header collapses to a
        blank "vs" title and an empty "Kick off:" line instead of falling
        back to the match's own data, which is fully populated -- verified
        live, e.g. every 2026 FIFA World Cup fixture currently reproduces
        this on uat (Canada vs Bosnia-Herz, USA vs Paraguay, Qatar vs
        Switzerland, ...), while ordinary league fixtures (Premier League,
        etc.) render correctly.

        Samples a broad, random set of Pre-match fixtures (see
        `_pick_prematch_match_ids_sample`) rather than a single hardcoded
        match ID, so this keeps working regardless of which specific
        fixtures happen to be affected on a given day/environment. Skips
        only if there are currently no Pre-match fixtures to sample at all.
        """
        match_ids = _pick_prematch_match_ids_sample(authenticated_page)
        if not match_ids:
            pytest.skip("no Pre-match fixtures currently available to sample")

        markets = MarketsPage(authenticated_page)
        broken = []
        for match_id in match_ids:
            markets.goto()
            markets.search_by_match_id(match_id)
            title = markets.match_title.inner_text().strip()
            kickoff = markets.kickoff_line.inner_text().strip()
            if title == "vs" or kickoff == "Kick off:":
                broken.append((match_id, title, kickoff))

        assert not broken, (
            f"{len(broken)}/{len(match_ids)} sampled Pre-match fixtures show a blank team "
            f"name and/or kickoff time in their Markets page header despite the match's own "
            f"record having real data (see QA-477): {broken}"
        )


class TestFilterFunctionality:
    def test_market_type_filter_narrows_to_selected_type(self, authenticated_page):
        """Every market type actually present on the picked fixture should filter cleanly.

        Which types exist varies by match (verified live: some Finished
        fixtures only have 1X2/AH/NG/OE/OU, others also have CS), so the
        types to check are discovered from the fixture's unfiltered grid
        rather than assuming a fixed list.
        """
        fixture = _pick_finished_zero_wager_fixture(authenticated_page)
        if fixture is None:
            pytest.skip("no zero-wager Finished fixture currently available")
        match_id, _, _, _ = fixture

        markets = MarketsPage(authenticated_page)
        markets.goto()
        markets.search_by_match_id(match_id)

        market_types = set()
        for i in range(markets.row_count()):
            if markets.row_cell_count(i) != 27:
                continue  # section header rows ("IN-PLAY", "PRE-MATCH", ...) have a single cell
            t = markets.row_cell(i, 0)
            if t:
                market_types.add(t)
        assert market_types, "expected at least one market type on the picked fixture"

        for market_type in sorted(market_types):
            markets.select_market(market_type)
            row_count = markets.row_count()
            assert row_count, f"expected at least one {market_type} market row"

            checked_any = False
            for i in range(row_count):
                if markets.row_cell_count(i) != 27:
                    continue
                cell_type = markets.row_cell(i, 0)
                assert cell_type in (market_type, ""), (
                    f"row {i} has unexpected market type {cell_type!r} while filtering by {market_type!r}"
                )
                checked_any = True
            assert checked_any, f"no market row was left to check after filtering by {market_type}"

    def test_alert_filter_with_alerts_only_never_exceeds_all(self, authenticated_page):
        fixture = _pick_finished_zero_wager_fixture(authenticated_page)
        if fixture is None:
            pytest.skip("no zero-wager Finished fixture currently available")
        match_id, _, _, _ = fixture

        markets = MarketsPage(authenticated_page)
        markets.goto()
        markets.search_by_match_id(match_id)
        baseline_count = markets.row_count()

        markets.select_alert("With alerts only")
        alerts_only_count = markets.row_count()

        assert alerts_only_count <= baseline_count

    def test_hide_markets_with_no_wagers_narrows_the_grid(self, authenticated_page):
        """Every market on the picked fixture shows "No bets" / 0 wagers (see
        `_pick_finished_zero_wager_fixture`).

        Toggling "Hide markets with no wagers" should therefore drop every
        individual market line, leaving only structural rows (section
        headers, Subtotal roll-ups) that aren't themselves a wagered line.
        """
        fixture = _pick_finished_zero_wager_fixture(authenticated_page)
        if fixture is None:
            pytest.skip("no zero-wager Finished fixture currently available")
        match_id, _, _, _ = fixture

        markets = MarketsPage(authenticated_page)
        markets.goto()
        markets.search_by_match_id(match_id)
        baseline_count = markets.row_count()
        assert baseline_count, "expected the picked fixture to have markets loaded"

        markets.toggle_hide_no_wagers()
        assert markets.row_count() < baseline_count


class TestNumericCalculations:
    """The SUMMARY block's WAGERS / TOTAL TURNOVER should equal the sum of
    the HOME, AWAY, and DRAW sides -- true for every row type (single-line
    markets, handicap/total sub-lines, and Subtotal roll-up rows alike),
    since it's just a wagers/turnover count regardless of what the side's
    VALUE column happens to display for that market type.
    """

    def test_summary_wagers_equals_sum_of_sides(self, authenticated_page):
        fixture = _pick_finished_zero_wager_fixture(authenticated_page)
        if fixture is None:
            pytest.skip("no zero-wager Finished fixture currently available")
        match_id, _, _, _ = fixture

        markets = MarketsPage(authenticated_page)
        markets.goto()
        markets.search_by_match_id(match_id)

        row_count = markets.row_count()
        assert row_count, "expected the picked fixture to have markets loaded"

        checked_any = False
        for i in range(row_count):
            if markets.row_cell_count(i) != 27:
                continue  # section header rows ("IN-PLAY", "PRE-MATCH", ...) have a single cell
            home = _to_int(markets.row_cell(i, MarketsPage.COL_HOME_WAGERS))
            away = _to_int(markets.row_cell(i, MarketsPage.COL_AWAY_WAGERS))
            draw = _to_int(markets.row_cell(i, MarketsPage.COL_DRAW_WAGERS))
            summary = _to_int(markets.row_cell(i, MarketsPage.COL_SUMMARY_WAGERS))
            if None in (home, away, draw, summary):
                continue  # side not applicable for this market type ("—")
            assert home + away + draw == summary, f"row {i}: {home}+{away}+{draw} != {summary}"
            checked_any = True
        assert checked_any, "no row exposed parseable WAGERS values to check"

    def test_summary_total_turnover_equals_sum_of_sides(self, authenticated_page):
        fixture = _pick_finished_zero_wager_fixture(authenticated_page)
        if fixture is None:
            pytest.skip("no zero-wager Finished fixture currently available")
        match_id, _, _, _ = fixture

        markets = MarketsPage(authenticated_page)
        markets.goto()
        markets.search_by_match_id(match_id)

        row_count = markets.row_count()
        assert row_count, "expected the picked fixture to have markets loaded"

        checked_any = False
        for i in range(row_count):
            if markets.row_cell_count(i) != 27:
                continue
            home = _to_int(markets.row_cell(i, MarketsPage.COL_HOME_TURNOVER))
            away = _to_int(markets.row_cell(i, MarketsPage.COL_AWAY_TURNOVER))
            draw = _to_int(markets.row_cell(i, MarketsPage.COL_DRAW_TURNOVER))
            summary = _to_int(markets.row_cell(i, MarketsPage.COL_SUMMARY_TOTAL_TURNOVER))
            if None in (home, away, draw, summary):
                continue
            assert home + away + draw == summary, f"row {i}: {home}+{away}+{draw} != {summary}"
            checked_any = True
        assert checked_any, "no row exposed parseable TURNOVER values to check"


class TestMarketActions:
    """Actions column: STATUS (open/close switch) and Edit (opens Market Activity in a new tab).

    AUTOPILOT is skipped -- it was disabled on every row observed live, so
    there's nothing to safely exercise yet.
    """

    def test_status_switch_close_and_reopen_full_cycle(self, authenticated_page):
        """Close a market, then reopen it, ending back at the original state.

        Uses a dynamically-discovered zero-wager Pre-match fixture (see
        `_pick_zero_wager_prematch_fixture`) so this doesn't touch a market
        anyone is actually trading on.

        Closing needs no confirmation and applies immediately. Reopening a
        closed market prompts a password-confirmation `alertdialog` --
        verified live via `role="dialog"` returning 0 matches while
        `role="alertdialog"` returns 1, with fields "Reopen this market?" /
        "Re-enter your password..." and Cancel/Reopen buttons.

        State is verified via a fresh navigation after each step
        (`read_status_via_fresh_load`), not the in-page switch label --
        reading it in the same session right after a click was unreliable
        while its confirmation dialog was still open (a stale read there
        hung for 30s+ until the dialog was actually handled).
        """
        fixture = _pick_zero_wager_prematch_fixture(authenticated_page)
        if fixture is None:
            pytest.skip("no zero-wager Pre-match fixture currently available to test Status toggle")
        match_id, _, _ = fixture

        markets = MarketsPage(authenticated_page)

        original = markets.read_status_via_fresh_load(match_id, 2)
        assert original in ("Open", "Closed")

        try:
            markets.toggle_status_for_row(2, ADMIN_PASSWORD)
            toggled = markets.read_status_via_fresh_load(match_id, 2)
            assert toggled != original, "status did not change after the first toggle"

            markets.toggle_status_for_row(2, ADMIN_PASSWORD)
            restored = markets.read_status_via_fresh_load(match_id, 2)
            assert restored == original, "status did not return to its original value after the second toggle"
        finally:
            current = markets.read_status_via_fresh_load(match_id, 2)
            if current != original:
                markets.toggle_status_for_row(2, ADMIN_PASSWORD)
            assert markets.read_status_via_fresh_load(match_id, 2) == original

    def test_edit_button_opens_market_activity_page(self, authenticated_page):
        """Clicking Edit should open the correct match/market's Activity page in a new tab.

        Only navigation is verified here -- the Activity page itself has
        Update/Reset controls that adjust live odds/spread/limits, which is
        a separate, more invasive feature this test deliberately leaves
        untouched.
        """
        fixture = _pick_zero_wager_prematch_fixture(authenticated_page)
        if fixture is None:
            pytest.skip("no zero-wager Pre-match fixture currently available to test the Edit button")
        match_id, home, away = fixture

        markets = MarketsPage(authenticated_page)
        markets.goto()
        markets.search_by_match_id(match_id)

        edit_button = markets.edit_button_for_row(2)  # the "1X2 FT" market row
        with markets.page.context.expect_page() as new_page_info:
            edit_button.click()
        activity_page = new_page_info.value
        activity_page.wait_for_load_state()
        activity_page.wait_for_timeout(1000)

        try:
            assert match_id in activity_page.url
            assert "/activity" in activity_page.url
            assert "marketType=1X2" in activity_page.url
            body_text = activity_page.locator("body").inner_text()
            assert home in body_text
            assert away in body_text
        finally:
            activity_page.close()


class TestInGameData:
    """The "In-game data" card on the Market Activity page: provider/status
    header, Score/Clock/Period/Teams tiles, and the Timeline/Statistics/
    Lineup sub-panels.

    Uses a dynamically-discovered zero-wager Pre-match fixture (see
    `_pick_zero_wager_prematch_fixture`) rather than a hardcoded match ID,
    so every test here observes the not-started/no-live-feed-data state.
    There is currently no In-play match on uat to verify what this
    card looks like with live score/clock/timeline/stats/lineup data --
    that gap should be covered separately once one is available.
    """

    def _open_activity_page(self, markets: MarketsPage):
        edit_button = markets.edit_button_for_row(2)  # the "1X2 FT" market row
        with markets.page.context.expect_page() as new_page_info:
            edit_button.click()
        activity_page = new_page_info.value
        activity_page.wait_for_load_state()
        activity_page.wait_for_timeout(1000)
        return activity_page

    def test_ingame_data_header_shows_provider_status_and_seq(self, authenticated_page):
        fixture = _pick_zero_wager_prematch_fixture(authenticated_page)
        if fixture is None:
            pytest.skip("no zero-wager Pre-match fixture currently available to test In-game data")
        match_id, _, _ = fixture

        markets = MarketsPage(authenticated_page)
        markets.goto()
        markets.search_by_match_id(match_id)

        activity_page = self._open_activity_page(markets)
        try:
            activity = MarketActivityPage(activity_page)
            expect(activity.ingame_card).to_be_visible()
            expect(activity.ingame_provider).to_be_visible()
            expect(activity.ingame_status_badge).to_have_text("Scheduled")
            expect(activity.ingame_seq).to_be_visible()
        finally:
            activity_page.close()

    def test_ingame_data_fields_match_the_selected_fixture(self, authenticated_page):
        """Score/Clock/Period/Teams tiles should reflect a not-yet-started match."""
        fixture = _pick_zero_wager_prematch_fixture(authenticated_page)
        if fixture is None:
            pytest.skip("no zero-wager Pre-match fixture currently available to test In-game data")
        match_id, home, away = fixture

        markets = MarketsPage(authenticated_page)
        markets.goto()
        markets.search_by_match_id(match_id)

        activity_page = self._open_activity_page(markets)
        try:
            activity = MarketActivityPage(activity_page)
            expect(activity.ingame_field("Teams")).to_have_text(f"{home} / {away}")
            expect(activity.ingame_field("Period")).to_have_text("Not started")
            expect(activity.ingame_field("Clock")).to_have_text("0:00")
            # No score has been recorded yet -- just the "home : away" separator.
            expect(activity.ingame_field("Score")).to_have_text(":")
        finally:
            activity_page.close()

    def test_ingame_data_shows_empty_states_with_no_live_feed(self, authenticated_page):
        fixture = _pick_zero_wager_prematch_fixture(authenticated_page)
        if fixture is None:
            pytest.skip("no zero-wager Pre-match fixture currently available to test In-game data")
        match_id, _, _ = fixture

        markets = MarketsPage(authenticated_page)
        markets.goto()
        markets.search_by_match_id(match_id)

        activity_page = self._open_activity_page(markets)
        try:
            activity = MarketActivityPage(activity_page)
            expect(activity.ingame_timeline_section).to_contain_text("No in-game events yet.")
            expect(activity.ingame_card.get_by_text("No statistics yet.")).to_be_visible()
            expect(activity.ingame_card.get_by_text("No lineup data.")).to_be_visible()
        finally:
            activity_page.close()
