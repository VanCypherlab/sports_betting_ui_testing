import re


class BottomNavigation:
    """Shared nav-click helper (frontend-miniapp: src/containers/BottomNavigation.vue).

    Tabs are role="menuitem" motion.button elements, not <a> tags, so
    navigation between them is a click, not a page.goto().
    """

    def __init__(self, page):
        self.page = page

    def go_to(self, tab_name: str):
        # The Bet tab's aria-label gains a dynamic suffix when the account has
        # active bets (e.g. "Bet (3 active bets)"), so match on a name that
        # starts with tab_name rather than requiring an exact match.
        self.page.get_by_role("menuitem", name=re.compile(rf"^{re.escape(tab_name)}\b")).click()
