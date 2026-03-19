from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static, Checkbox
from textual.containers import Container, VerticalScroll, Horizontal
from textual.binding import Binding


class BossSelectorScreen(Screen):
    CSS = """
    # boss-list {
        height: 1fr;
        padding: 1 2;
    }
    # header-text {
        padding: 1 2;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        tier_name = getattr(self.app, 'selected_tier_name', 'Selected Tier')
        yield Static(f"Select bosses for {tier_name}", id="header-text")
        encounters = getattr(self.app, 'selected_tier_encounters', [])
        with VerticalScroll(id="boss-list"):
            for enc in encounters:
                yield Checkbox(f"{enc.code} — {enc.full_name}", value=False, id=f"cb-{enc.code}")

        yield Horizontal(
            Button("Back", id="btn-back"),
            Button("Fetch Reports", id="btn-fetch", variant="primary", disabled=True),
            id="nav-buttons",
        )
        yield Footer()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        checked = [cb for cb in self.query(Checkbox) if cb.value]
        self.query_one("#btn-fetch", Button).disabled = len(checked) == 0
        self.app.selected_encounters = [cb.id.replace("cb-", "") for cb in checked]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-fetch":
            self.app.push_screen("fetching")
