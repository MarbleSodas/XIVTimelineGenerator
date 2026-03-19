from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, ProgressBar, Button
from textual.containers import Container
from textual.binding import Binding
import asyncio
from concurrent.futures import ThreadPoolExecutor


class FetchingScreen(Screen):
    CSS = """
    # fetch-container {
        align: center middle;
        height: 100%;
    }
    # status-text {
        padding: 1 2;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Fetching reports...", id="status-text"),
            ProgressBar(id="overall-progress"),
            id="fetch-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        asyncio.create_task(self.run_fetch())

    async def run_fetch(self):
        from fflogs.client import FFLogsClient
        from fflogs.encounters import EncounterLoader

        loader = EncounterLoader()
        client = FFLogsClient()
        selected_codes = getattr(self.app, 'selected_encounters', [])

        if not selected_codes:
            self.app.pop_screen()
            return

        encounters = [loader.get_by_code(c) for c in selected_codes]
        encounters = [e for e in encounters if e is not None]

        all_reports: dict[str, list] = {}
        total_steps = len(encounters)
        current_step = 0

        status = self.query_one("#status-text", Static)
        overall = self.query_one("#overall-progress", ProgressBar)

        for enc in encounters:
            status.update(f"Fetching {enc.code}... (0/30)")
            try:
                loop = asyncio.get_event_loop()
                def fetch():
                    return client.get_reports(enc, limit=30)
                with ThreadPoolExecutor() as executor:
                    reports = await loop.run_in_executor(executor, fetch)
            except Exception as e:
                reports = []
                status.update(f"Error fetching {enc.code}: {e}")

            all_reports[enc.code] = reports
            current_step += 1
            overall.update(progress=int(current_step / total_steps * 100))
            status.update(f"Fetched {len(reports)} reports for {enc.code}")

        self.app.fetched_reports = all_reports
        self.app.push_screen("results")
