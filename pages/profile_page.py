import re

from playwright.sync_api import Page

from pages.base_page import BackofficePage


class ProfilePage(BackofficePage):
    """Page Object for the self-service profile page (backoffice-ui: src/resources/profile)."""

    URL_PATH = "/profile"
    HEADING_TEXT = "Profile"

    # Matches a permission badge label, e.g. "matches: full" -- verified
    # live against the PermissionLevel values the UI renders.
    PERMISSION_BADGE_PATTERN = re.compile(r"^\w+: (full|elevated|standard|limited|none)$")

    def __init__(self, page: Page):
        super().__init__(page)
        self.change_password_button = page.get_by_role("button", name="Change password", exact=True)
        self.sign_out_button = page.get_by_role("button", name="Sign Out", exact=True)

        # UserProfileCard: label paragraph, then the value as the very next sibling <p>.
        self.email_value = page.get_by_text("Email", exact=True).locator("xpath=following-sibling::p[1]")
        self.last_login_value = page.get_by_text("Last Login", exact=True).locator("xpath=following-sibling::p[1]")

        # ActivityStats: the value <p> renders BEFORE its label <p> in the same block.
        self.total_actions_value = page.get_by_text("Total Actions", exact=True).locator(
            "xpath=preceding-sibling::p[1]"
        )
        self.sessions_today_value = page.get_by_text("Sessions Today", exact=True).locator(
            "xpath=preceding-sibling::p[1]"
        )

        self.no_recent_activity_text = page.get_by_text("No recent activity", exact=True)

    def open_change_password(self):
        self.change_password_button.click()
        self.page.wait_for_timeout(800)

    def permission_badges(self) -> list[str]:
        """Every "domain: level" permission badge shown on the profile card
        (e.g. "matches: full"), read live -- the top-5 set shown varies by
        which role is signed in.
        """
        badges = self.page.get_by_text(self.PERMISSION_BADGE_PATTERN)
        return [badges.nth(i).inner_text() for i in range(badges.count())]
