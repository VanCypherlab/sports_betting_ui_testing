from collections import Counter

import pytest
from playwright.sync_api import expect

from pages.admins_page import AdminsPage
from pages.roles_page import RolesPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestRolesPage:
    def test_page_loads(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        expect(roles.table).to_be_visible()

    def test_search_does_not_crash(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        roles.search("admin")
        expect(roles.heading).to_be_visible()


class TestFilterFunctionality:
    def test_status_filter_only_shows_selected_status(self, authenticated_page):
        """Every Status option that currently has roles should filter to only that status."""
        roles = RolesPage(authenticated_page)
        roles.goto()
        baseline_count = roles.row_count()
        assert baseline_count, "expected at least one role"

        checked_any = False
        for status in RolesPage.STATUS_FILTER_OPTIONS:
            roles.filter_by_status(status)
            row_count = roles.row_count()
            if row_count == 0:
                roles.clear_all_filters()
                continue
            for i in range(row_count):
                assert roles.row_cell(i, RolesPage.COL_STATUS) == status, (
                    f"row {i} has Status {roles.row_cell(i, RolesPage.COL_STATUS)!r}, expected {status!r}"
                )
            assert row_count <= baseline_count
            checked_any = True
            roles.clear_all_filters()
        assert checked_any, "no Status option currently has any roles to check"

    def test_status_filter_with_no_matches_shows_empty_state(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        baseline_count = roles.row_count()
        assert baseline_count, "expected at least one role"

        checked_any = False
        for status in RolesPage.STATUS_FILTER_OPTIONS:
            roles.filter_by_status(status)
            if roles.row_count() == 0:
                expect(roles.page.get_by_text("No roles match the current filters")).to_be_visible()
                checked_any = True
            roles.clear_all_filters()
        if not checked_any:
            pytest.skip("every Status option currently has at least one role -- no empty state to check")

    def test_scope_filter_only_shows_selected_scope(self, authenticated_page):
        """Global roles should show a "Global" Scope badge; Limited roles
        should show anything else (Merchant/Site/Limited) -- verified live,
        the Limited filter is `scopeType !== 'global'`, a broader bucket
        than just the literal "Limited" label.
        """
        roles = RolesPage(authenticated_page)
        roles.goto()
        baseline_count = roles.row_count()
        assert baseline_count, "expected at least one role"

        checked_any = False
        for scope in RolesPage.SCOPE_FILTER_OPTIONS:
            roles.filter_by_scope(scope)
            row_count = roles.row_count()
            if row_count == 0:
                roles.clear_all_filters()
                continue
            for i in range(row_count):
                cell = roles.row_cell(i, RolesPage.COL_SCOPE)
                if scope == "Global":
                    assert cell == "Global", f"row {i} has Scope {cell!r}, expected 'Global'"
                else:
                    assert cell != "Global", f"row {i} has Scope {cell!r}, expected non-Global (Limited filter)"
            assert row_count <= baseline_count
            checked_any = True
            roles.clear_all_filters()
        assert checked_any, "no Scope option currently has any roles to check"

    def test_search_narrows_by_name_or_description(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        baseline_count = roles.row_count()
        assert baseline_count, "expected at least one role"

        role_name = roles.row_cell(0, RolesPage.COL_ROLE).split("\n")[0].strip()
        roles.search(role_name)
        row_count = roles.row_count()
        assert row_count, f"expected at least one role matching {role_name!r}"

        roles.search("zzz-no-such-role-should-match-nothing")
        assert roles.row_count() == 0
        expect(roles.page.get_by_text("No roles match the current filters")).to_be_visible()

    def test_clear_all_resets_filters(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        baseline_count = roles.row_count()
        assert baseline_count, "expected at least one role"

        roles.filter_by_status("Inactive")
        roles.clear_all_filters()

        assert roles.row_count() == baseline_count
        expect(roles.clear_all_button).not_to_be_visible()


class TestSorting:
    def test_role_column_sorts_ascending_then_descending_then_resets(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        original_order = roles.row_names()
        assert len(original_order) > 1, "expected more than one role to meaningfully test sorting"

        roles.sort_by("Role")
        ascending = roles.row_names()
        assert ascending == sorted(ascending, key=str.lower), "clicking Role header once should sort A-Z"

        roles.sort_by("Role")
        descending = roles.row_names()
        assert descending == sorted(descending, key=str.lower, reverse=True), (
            "clicking Role header twice should sort Z-A"
        )

        roles.sort_by("Role")
        reset_order = roles.row_names()
        assert reset_order == original_order, "clicking Role header a third time should restore the original order"

    def test_admins_column_is_sortable(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        row_count = roles.row_count()
        assert row_count, "expected at least one role"

        roles.sort_by("Admins")
        counts = [int(roles.row_cell(i, RolesPage.COL_ADMINS)) for i in range(row_count)]
        assert counts == sorted(counts), "clicking Admins header once should sort ascending"

    def test_status_column_is_sortable(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        row_count = roles.row_count()
        assert row_count, "expected at least one role"

        roles.sort_by("Status")
        statuses = [roles.row_cell(i, RolesPage.COL_STATUS) for i in range(row_count)]
        assert statuses == sorted(statuses, key=str.lower), "clicking Status header once should sort A-Z"


class TestDataContent:
    def test_status_values_are_from_known_set(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        row_count = roles.row_count()
        assert row_count, "expected at least one role"

        for i in range(row_count):
            status = roles.row_cell(i, RolesPage.COL_STATUS)
            assert status in RolesPage.STATUS_VALUES, f"row {i} has unexpected Status {status!r}"

    def test_scope_values_are_from_known_set(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        row_count = roles.row_count()
        assert row_count, "expected at least one role"

        for i in range(row_count):
            scope = roles.row_cell(i, RolesPage.COL_SCOPE)
            assert scope in RolesPage.SCOPE_VALUES, f"row {i} has unexpected Scope {scope!r}"

    def test_rows_have_populated_name_and_permission_summary(self, authenticated_page):
        roles = RolesPage(authenticated_page)
        roles.goto()
        row_count = roles.row_count()
        assert row_count, "expected at least one role"

        for i in range(row_count):
            name = roles.row_cell(i, RolesPage.COL_ROLE).split("\n")[0].strip()
            assert name, f"row {i} Role name is blank"
            summary = roles.row_cell(i, RolesPage.COL_PERMISSION_SUMMARY)
            assert summary.strip(), f"row {i} Permission Summary is blank"

    def test_admin_count_matches_admins_actually_assigned_to_each_role(self, authenticated_page):
        """Cross-check the Roles list's Admins column against the actual
        number of admins currently assigned to each role, per the Admins list.
        """
        admins = AdminsPage(authenticated_page)
        admins.goto()
        admin_row_count = admins.row_count()
        assert admin_row_count, "expected at least one admin"

        role_counts = Counter()
        for i in range(admin_row_count):
            role_name = admins.row_cell(i, AdminsPage.COL_ROLE).split("\n")[0].strip()
            role_counts[role_name] += 1

        roles = RolesPage(authenticated_page)
        roles.goto()
        row_count = roles.row_count()
        assert row_count, "expected at least one role"

        checked_any = False
        for i in range(row_count):
            role_name = roles.row_cell(i, RolesPage.COL_ROLE).split("\n")[0].strip()
            if role_name not in role_counts:
                continue
            expected = role_counts[role_name]
            actual = int(roles.row_cell(i, RolesPage.COL_ADMINS))
            assert actual == expected, (
                f"role {role_name!r}: Roles list shows Admins={actual}, but the Admins list currently "
                f"has {expected} admin(s) assigned to this role"
            )
            checked_any = True
        assert checked_any, "no role with assigned admins was available to cross-check"
