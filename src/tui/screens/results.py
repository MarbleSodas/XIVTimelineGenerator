from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Button, Static
from textual.containers import Container, Horizontal
from textual.binding import Binding


class ResultsScreen(Screen):
    CSS = """
    # results-container {
        height: 1fr;
    }
    # table-info {
        padding: 0 2;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(id="table-info"),
            DataTable(id="results-table"),
            Horizontal(
                Button("Back", id="btn-back"),
                id="nav-buttons",
            ),
            id="results-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns(
            "Report ID",
            "Date",
            "Duration",
            "Guild",
            "Boss",
        )

        fetched = getattr(self.app, 'fetched_reports', {})
        total = 0
        for code, reports in fetched.items():
            total += len(reports)
            for r in reports:
                table.add_row(
                    r.id,
                    r.date.strftime("%Y-%m-%d %H:%M"),
                    f"{r.duration / 1000:.1f}s",
                    r.guild_name or "—",
                    code,
                )

        info = self.query_one("#table-info", Static)
        boss_names = ", ".join(fetched.keys())
        info.update(f"{total} reports for {boss_names}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
