from datetime import datetime

import pytest
from playwright.sync_api import expect

from pages.audit_log_page import AuditLogPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


def _parse_timestamp(value: str):
    try:
        return datetime.strptime(value, "%b %d, %Y, %I:%M:%S %p")
    except ValueError:
        return None


class TestAuditLogPage:
    def test_page_loads(self, authenticated_page):
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        expect(audit.table).to_be_visible()

    def test_search_does_not_crash(self, authenticated_page):
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        audit.search("login")
        expect(audit.heading).to_be_visible()


class TestFilterFunctionality:
    def test_action_type_filter_only_shows_selected_action(self, authenticated_page):
        """Every Action Type option that currently has entries should filter to only that action."""
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        baseline_count = audit.row_count()
        assert baseline_count, "expected at least one audit log entry"

        actions = audit.action_type_options()
        assert actions, "expected at least one Action Type filter option"

        checked_any = False
        for action in actions:
            audit.filter_by_action_type(action)
            row_count = audit.row_count()
            if row_count == 0:
                continue
            for i in range(row_count):
                assert audit.row_cell(i, AuditLogPage.COL_ACTION) == action, (
                    f"row {i} has Action {audit.row_cell(i, AuditLogPage.COL_ACTION)!r}, expected {action!r}"
                )
            checked_any = True
        assert checked_any, "no Action Type option currently has any entries to check"

    def test_object_type_filter_only_shows_selected_object_type(self, authenticated_page):
        """Every Object Type option that currently has entries should filter to only that type."""
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        baseline_count = audit.row_count()
        assert baseline_count, "expected at least one audit log entry"

        object_types = audit.object_type_options()
        assert object_types, "expected at least one Object Type filter option"

        checked_any = False
        for object_type in object_types:
            audit.filter_by_object_type(object_type)
            row_count = audit.row_count()
            if row_count == 0:
                continue
            for i in range(row_count):
                object_cell = audit.row_cell(i, AuditLogPage.COL_OBJECT)
                cell_type = object_cell.split("\n")[0].strip()
                assert cell_type == object_type, (
                    f"row {i} has Object type {cell_type!r}, expected {object_type!r}"
                )
            checked_any = True
        assert checked_any, "no Object Type option currently has any entries to check"

    def test_actor_filter_only_shows_selected_actor(self, authenticated_page):
        """Every Actor option that currently has entries should filter to only that actor."""
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        baseline_count = audit.row_count()
        assert baseline_count, "expected at least one audit log entry"

        actors = audit.actor_options()
        if not actors:
            pytest.skip("no Actor filter options currently available")

        checked_any = False
        for actor in actors:
            audit.filter_by_actor(actor)
            row_count = audit.row_count()
            if row_count == 0:
                continue
            for i in range(row_count):
                assert audit.row_cell(i, AuditLogPage.COL_ACTOR) == actor, (
                    f"row {i} has Actor {audit.row_cell(i, AuditLogPage.COL_ACTOR)!r}, expected {actor!r}"
                )
            assert row_count <= baseline_count
            checked_any = True
        assert checked_any, "no Actor option currently has any entries to check"

    def test_date_range_today_narrows_to_recent_entries(self, authenticated_page):
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        baseline_count = audit.row_count()
        assert baseline_count, "expected at least one audit log entry"

        audit.filter_by_date_range("Today")
        row_count = audit.row_count()
        if row_count == 0:
            pytest.skip("no audit log entries from today currently available")
        assert row_count <= baseline_count

        for i in range(row_count):
            timestamp = _parse_timestamp(audit.row_cell(i, AuditLogPage.COL_TIME))
            assert timestamp is not None, f"row {i} Time is not parseable"
            assert timestamp.date() == datetime.now().date(), (
                f"row {i} Time {timestamp} is not from today, but Date Range is set to \"Today\""
            )

    def test_search_by_action_narrows_results(self, authenticated_page):
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        baseline_count = audit.row_count()
        assert baseline_count, "expected at least one audit log entry"

        action = audit.row_cell(0, AuditLogPage.COL_ACTION)
        audit.search(action)
        row_count = audit.row_count()
        assert row_count, f"expected at least one entry matching action {action!r}"
        for i in range(row_count):
            assert audit.row_cell(i, AuditLogPage.COL_ACTION) == action

    def test_clear_all_resets_filters(self, authenticated_page):
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        baseline_count = audit.row_count()
        assert baseline_count, "expected at least one audit log entry"

        actions = audit.action_type_options()
        assert actions, "expected at least one Action Type filter option"
        audit.filter_by_action_type(actions[0])
        audit.clear_all_filters()

        assert audit.row_count() == baseline_count
        expect(audit.clear_all_button).not_to_be_visible()


class TestPagination:
    def test_load_more_does_not_duplicate_entries_once_every_page_is_loaded(self, authenticated_page):
        """BUG (QA-441): once every entry is already loaded (no real next
        page left), "Load More" is still shown, and clicking it re-fetches
        and re-appends the same first page again instead of staying put --
        verified live on qat, where total entries currently fit on one
        page. Root cause: the list API returns `nextCursor: ""` instead of
        null/absent when there's no next page, and the frontend's
        `nextCursor ?? undefined` check doesn't treat an empty string as
        "no more pages".
        """
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        baseline_count = audit.row_count()
        assert baseline_count, "expected at least one audit log entry"
        total = audit.total_count()
        if baseline_count < total:
            pytest.skip("more than one page of entries currently available -- can't reach the buggy last-page state")

        if audit.load_more_button.count() == 0:
            pytest.skip('"Load More" is not shown once every entry is loaded -- bug appears fixed')

        audit.load_more_button.click()
        audit.page.wait_for_timeout(1500)

        assert audit.row_count() == baseline_count, (
            f"Load More duplicated rows: had {baseline_count}, now {audit.row_count()} (see QA-441)"
        )
        assert audit.displayed_count() <= audit.total_count(), (
            f"\"Showing X of Y\" displayed count {audit.displayed_count()} exceeds total "
            f"{audit.total_count()} after Load More (see QA-441)"
        )


class TestDataContent:
    def test_rows_have_populated_time_action_object_outcome(self, authenticated_page):
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        row_count = audit.row_count()
        assert row_count, "expected at least one audit log entry"

        for i in range(row_count):
            time_text = audit.row_cell(i, AuditLogPage.COL_TIME)
            assert time_text, f"row {i} Time is blank"
            assert _parse_timestamp(time_text) is not None, f"row {i} Time {time_text!r} is not a parseable timestamp"

            action = audit.row_cell(i, AuditLogPage.COL_ACTION)
            assert action, f"row {i} Action is blank"

            object_cell = audit.row_cell(i, AuditLogPage.COL_OBJECT)
            assert object_cell.split("\n")[0].strip(), f"row {i} Object type is blank"

            outcome = audit.row_cell(i, AuditLogPage.COL_OUTCOME)
            assert outcome, f"row {i} Outcome is blank"

    def test_showing_count_matches_rendered_rows(self, authenticated_page):
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        row_count = audit.row_count()
        assert row_count, "expected at least one audit log entry"

        assert audit.displayed_count() == row_count, (
            f"\"Showing X of Y\" displayed count {audit.displayed_count()} != actual rendered rows {row_count}"
        )
        assert audit.total_count() >= audit.displayed_count()

    def test_rows_are_ordered_newest_first(self, authenticated_page):
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        row_count = audit.row_count()
        assert row_count, "expected at least one audit log entry"

        timestamps = [_parse_timestamp(audit.row_cell(i, AuditLogPage.COL_TIME)) for i in range(row_count)]
        assert all(timestamps), "not every row's Time was parseable"
        assert timestamps == sorted(timestamps, reverse=True), "rows are not ordered newest Time first"


class TestViewDialog:
    def test_view_dialog_shows_action_reason_title_and_matches_row(self, authenticated_page):
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        row_count = audit.row_count()
        assert row_count, "expected at least one audit log entry"

        action = audit.row_cell(0, AuditLogPage.COL_ACTION)
        actor = audit.row_cell(0, AuditLogPage.COL_ACTOR)

        dialog = audit.open_view_dialog(0)
        expect(dialog.get_by_role("heading", name="Action Reason", exact=True)).to_be_visible()
        expect(dialog).to_contain_text(action)
        if actor:
            expect(dialog).to_contain_text(actor)

        audit.close_dialog(dialog)
        expect(dialog).not_to_be_visible()

    def test_view_dialog_change_section_reflects_row_change_column(self, authenticated_page):
        """Every field name shown in the list's Change column for a row should
        also appear in that row's View dialog -- the dialog just renders the
        same before/after data field-by-field instead of the list's
        truncated one-line summary.
        """
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        row_count = audit.row_count()
        assert row_count, "expected at least one audit log entry"

        checked_any = False
        for i in range(min(row_count, 10)):
            change_cell = audit.row_cell(i, AuditLogPage.COL_CHANGE)
            if ":" not in change_cell:
                continue  # blank ("-") or an override-style headline with no field-level diff to compare
            keys = [part.split(":", 1)[0].strip() for part in change_cell.split(",")]
            keys = [k for k in keys if k]
            if not keys:
                continue

            dialog = audit.open_view_dialog(i)
            dialog_text = dialog.inner_text()
            for key in keys:
                assert key in dialog_text, (
                    f"row {i}: Change field {key!r} from the list is missing from the View dialog"
                )
            audit.close_dialog(dialog)
            checked_any = True

        assert checked_any, "no row exposed a field-level Change diff to cross-check against its View dialog"

    def test_view_dialog_renders_reason_or_change_body_content(self, authenticated_page):
        """The Reason column only ever shows a "View" button (never the
        reason text itself), so the dialog is the only place the actual
        reason/comment (and the full Change detail) is readable -- assert
        it renders real body content underneath the title/description, not
        a blank/empty state.
        """
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        row_count = audit.row_count()
        assert row_count, "expected at least one audit log entry"

        dialog = audit.open_view_dialog(0)
        lines = [line for line in dialog.inner_text().splitlines() if line.strip()]
        # Expect more than just title + description + Close button.
        assert len(lines) > 3, f"View dialog appears to render no reason/Change body content: {lines!r}"
        audit.close_dialog(dialog)
