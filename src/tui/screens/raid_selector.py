from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Tree, Button, Header, Footer
from textual.containers import Container, Horizontal
from textual.binding import Binding
import yaml

from fflogs.encounters import EncounterLoader


class RaidSelectorScreen(Screen):
    CSS = ""


    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "select", "Select"),
    ]

    def __init__(self, loader: EncounterLoader | None = None):
        super().__init__()
        self.loader = loader or EncounterLoader()

    def compose(self) -> ComposeResult:
        yield Header()
        tree = Tree("XIV Timeline Generator", id="raid-tree")
        yield tree
        yield Horizontal(
            Button("Select", id="btn-select", variant="primary", disabled=True),
            Button("Quit", id="btn-quit"),
            id="nav-buttons",
        )
        yield Footer()

    def on_mount(self) -> None:
        tree = self.query_one("#raid-tree", Tree)
        root = tree.root
        root.expand()

        expansions_map = {
            "Dawntrail": ("dawntrail", ["AAC Light-heavyweight", "AAC Cruiserweight", "AAC Heavyweight"]),
            "Endwalker": ("endwalker", ["Asphodelos", "Abyssos", "Anabaseios"]),
            "Shadowbringers": ("shadowbringers", ["Eden's Gate", "Eden's Verse", "Eden's Promise"]),
            "Stormblood": ("stormblood", ["Omega: Deltascape", "Omega: Sigmascape", "Omega: Alphascape"]),
        }

        for exp_name, (exp_key, tier_names) in expansions_map.items():
            exp_node = root.add(exp_name, expand=True)
            yaml_path = self.loader.data_dir / f"{exp_key}.yaml"
            if not yaml_path.exists():
                continue
            data = yaml.safe_load(yaml_path.read_text())

            for tier in data.get("tiers", []):
                if tier["name"] not in tier_names:
                    continue
                tier_node = exp_node.add(f"{tier['name']} ({tier['short_name']})", expand=False)
                tier_encounters = []
                for enc in tier["encounters"]:
                    enc_obj = next((e for e in self.loader.load_expansion(exp_key) if e.code == enc["code"]), None)
                    if enc_obj:
                        tier_node.add_leaf(f"{enc['code']} — {enc['boss_name']}", data=enc_obj)
                        tier_encounters.append(enc_obj)
                tier_node._tier_encounters = tier_encounters
                tier_node._tier_name = tier["name"]

            for ult in data.get("ultimates", []):
                enc_obj = next((e for e in self.loader.load_expansion(exp_key) if e.code == ult["code"]), None)
                if enc_obj:
                    ult_name = ult["full_name"].split("(")[0].strip()
                    ult_node = exp_node.add(f"{ult_name} (ULT)", expand=False)
                    ult_node.add_leaf(ult["code"], data=enc_obj)
                    ult_node._tier_encounters = [enc_obj]
                    ult_node._tier_name = ult_name

        self._tree = tree

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        self.query_one("#btn-select", Button).disabled = False

    def action_select(self) -> None:
        tree = self.query_one("#raid-tree", Tree)
        node = tree.selected_node
        if node.data and hasattr(node.data, 'code'):
            parent = node.parent
            if hasattr(parent, '_tier_encounters'):
                self.app.selected_tier_name = parent._tier_name
                self.app.selected_tier_encounters = parent._tier_encounters
                self.app.selected_encounter = node.data
                self.app.push_screen("boss_selector")
