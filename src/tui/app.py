from textual.app import App as TextualApp
from .screens.raid_selector import RaidSelectorScreen
from .screens.boss_selector import BossSelectorScreen
from .screens.fetching import FetchingScreen
from .screens.results import ResultsScreen


class XIVTimelineApp(TextualApp):
    selected_encounter = None
    selected_encounters: list[str] = []
    selected_tier_name: str = ""
    selected_tier_encounters: list = []
    fetched_reports: dict[str, list] = {}

    def on_mount(self) -> None:
        self.install_screen(RaidSelectorScreen(), name="raid_selector")
        self.install_screen(BossSelectorScreen(), name="boss_selector")
        self.install_screen(FetchingScreen(), name="fetching")
        self.install_screen(ResultsScreen(), name="results")
        self.push_screen("raid_selector")
