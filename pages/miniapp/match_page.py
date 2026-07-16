from playwright.sync_api import Page


class MatchPage:
    """Page Object for a match's odds/betting page (frontend-miniapp),
    reached by clicking a match card from Home (MainPage.open_first_match).
    """

    def __init__(self, page: Page):
        self.page = page
        self.bet_amount_input = page.locator("input").first
        self.place_bet_button = page.get_by_role("button", name="Place bet", exact=True)

    def select_win_loss_home_odds(self):
        """Click the Win/Loss market's Home-side odds value to open the bet slip.

        Win/Loss odds aren't exposed as role=button (a Vue component with no
        ARIA role) -- verified live: the odds value is a bare
        <span class="betting-card-threeway__odds-number">, directly
        clickable despite the missing role.
        """
        self.page.locator(".betting-card-threeway__odds-number").first.click()

    def place_bet(self, stake: str):
        self.bet_amount_input.fill(stake)
        self.place_bet_button.click()
