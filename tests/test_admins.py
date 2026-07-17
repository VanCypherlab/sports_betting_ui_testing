import pytest
from playwright.sync_api import expect

from pages.admins_page import AdminsPage
from tests.conftest import ADMIN_EMAIL, requires_admin_creds

pytestmark = requires_admin_creds


class TestAdminsPage:
    def test_page_loads(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        expect(admins.table).to_be_visible()

    def test_search_does_not_crash(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        admins.search("van")
        admins.page.wait_for_timeout(500)
        expect(admins.heading).to_be_visible()


class TestFilterFunctionality:
    def test_status_filter_only_shows_selected_status(self, authenticated_page):
        """Every Status option that currently has admins should filter to only that status."""
        admins = AdminsPage(authenticated_page)
        admins.goto()
        baseline_count = admins.row_count()
        assert baseline_count, "expected at least one admin"

        checked_any = False
        for status in AdminsPage.STATUS_FILTER_OPTIONS:
            admins.filter_by_status(status)
            row_count = admins.row_count()
            if row_count == 0:
                continue
            for i in range(row_count):
                assert admins.row_cell(i, AdminsPage.COL_STATUS) == status, (
                    f"row {i} has Status {admins.row_cell(i, AdminsPage.COL_STATUS)!r}, expected {status!r}"
                )
            assert row_count <= baseline_count
            checked_any = True
            admins.clear_all_filters()
        assert checked_any, "no Status option currently has any admins to check"

    def test_status_filter_with_no_matches_shows_empty_state(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        baseline_count = admins.row_count()
        assert baseline_count, "expected at least one admin"

        checked_any = False
        for status in AdminsPage.STATUS_FILTER_OPTIONS:
            admins.filter_by_status(status)
            if admins.row_count() == 0:
                expect(admins.page.get_by_text("No admins match the current filters")).to_be_visible()
                checked_any = True
            admins.clear_all_filters()
        if not checked_any:
            pytest.skip("every Status option currently has at least one admin -- no empty state to check")

    def test_search_narrows_by_name_email_or_role(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        baseline_count = admins.row_count()
        assert baseline_count, "expected at least one admin"

        role = admins.row_cell(0, AdminsPage.COL_ROLE).split("\n")[0].strip()
        assert role, "expected the first admin to have a Role"

        admins.search(role)
        row_count = admins.row_count()
        assert row_count, f"expected at least one admin matching role {role!r}"
        for i in range(row_count):
            assert role in admins.row_cell(i, AdminsPage.COL_ROLE)

        admins.search("zzz-no-such-admin-should-match-nothing")
        assert admins.row_count() == 0
        expect(admins.page.get_by_text("No admins match the current filters")).to_be_visible()

    def test_clear_all_resets_filters(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        baseline_count = admins.row_count()
        assert baseline_count, "expected at least one admin"

        admins.filter_by_status("Suspended")
        admins.clear_all_filters()

        assert admins.row_count() == baseline_count
        expect(admins._clear_all_button).not_to_be_visible()


class TestSorting:
    def test_name_column_sorts_ascending_then_descending_then_resets(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        original_order = admins.row_names()
        assert len(original_order) > 1, "expected more than one admin to meaningfully test sorting"

        # Compared against each other rather than a Python-side re-sort --
        # the app sorts via JS `localeCompare` (verified live it treats
        # punctuation like "-" differently from a plain lowercase byte
        # comparison, e.g. "VanYou" vs "Van-superadmin"), so the only
        # collation-agnostic checks are: same names before/after, sorting
        # actually changed the order, and descending is asc's exact reverse.
        admins.sort_by("Admin")
        ascending = admins.row_names()
        assert sorted(ascending) == sorted(original_order), "sorting should reorder, not add/drop admins"
        assert ascending != original_order, "clicking the Admin header should change the row order"

        admins.sort_by("Admin")
        descending = admins.row_names()
        assert descending == list(reversed(ascending)), "clicking Admin header twice should reverse the order"

        admins.sort_by("Admin")
        reset_order = admins.row_names()
        assert reset_order == original_order, "clicking Admin header a third time should restore the original order"

    def test_role_column_is_sortable(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        row_count = admins.row_count()
        assert row_count, "expected at least one admin"

        admins.sort_by("Role")
        roles = [admins.row_cell(i, AdminsPage.COL_ROLE).split("\n")[0].strip() for i in range(row_count)]
        assert roles == sorted(roles, key=str.lower), "clicking Role header once should sort A-Z"

    def test_status_column_is_sortable(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        row_count = admins.row_count()
        assert row_count, "expected at least one admin"

        admins.sort_by("Status")
        statuses = [admins.row_cell(i, AdminsPage.COL_STATUS) for i in range(row_count)]
        assert statuses == sorted(statuses, key=str.lower), "clicking Status header once should sort A-Z"


class TestDataContent:
    def test_status_values_are_from_known_set(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        row_count = admins.row_count()
        assert row_count, "expected at least one admin"

        for i in range(row_count):
            status = admins.row_cell(i, AdminsPage.COL_STATUS)
            assert status in AdminsPage.STATUS_VALUES, f"row {i} has unexpected Status {status!r}"

    def test_rows_have_populated_email_and_role(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        row_count = admins.row_count()
        assert row_count, "expected at least one admin"

        for i in range(row_count):
            admin_cell = admins.row_cell(i, AdminsPage.COL_ADMIN)
            assert "@" in admin_cell, f"row {i} Admin cell has no email: {admin_cell!r}"
            role_cell = admins.row_cell(i, AdminsPage.COL_ROLE)
            assert role_cell.strip(), f"row {i} Role is blank"

    def test_last_login_is_either_a_placeholder_or_non_blank_relative_time(self, authenticated_page):
        admins = AdminsPage(authenticated_page)
        admins.goto()
        row_count = admins.row_count()
        assert row_count, "expected at least one admin"

        for i in range(row_count):
            last_login = admins.row_cell(i, AdminsPage.COL_LAST_LOGIN)
            assert last_login, f"row {i} Last Login cell is completely empty (expected '-' or a value)"
            assert "Invalid Date" not in last_login, f"row {i} Last Login shows {last_login!r}"

    def test_self_row_shows_you_badge_and_disables_suspend_and_delete(self, authenticated_page):
        """The signed-in admin's own row should be clearly marked and
        protected from self-suspend/self-delete -- verified live this is
        both a UX guard (buttons disabled) and enforced server-side (409
        SelfActionNotAllowed if bypassed).
        """
        assert ADMIN_EMAIL, "TEST_ADMIN_EMAIL must be set for this check"
        admins = AdminsPage(authenticated_page)
        admins.goto()

        self_row = admins.row_for_email(ADMIN_EMAIL)
        assert self_row.count(), f"expected to find the signed-in admin's own row ({ADMIN_EMAIL!r})"

        expect(self_row.get_by_text("You", exact=True)).to_be_visible()
        expect(self_row.get_by_role("button", name="Suspend", exact=True)).to_be_disabled()
        expect(self_row.get_by_role("button", name="Delete", exact=True)).to_be_disabled()
