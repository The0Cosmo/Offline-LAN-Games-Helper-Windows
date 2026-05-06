"""
Offline LAN Games Helper - Windows

Safe Windows GUI helper for legitimate offline/LAN multiplayer games.

Allowed behavior:
- show LAN IP information,
- show game-specific offline/LAN tutorials,
- launch games normally,
- add/remove Windows Firewall rules created by this helper,
- help users use official dedicated server tools, official download pages,
  SteamCMD app IDs explicitly listed in games.json, or user-provided local files,
- export tutorials.

This app does not bypass DRM, launchers, authentication, ownership checks,
anti-cheat, or licenses. It does not create cracks, loaders, Steam emulators,
patched executables, hooks, injectors, modified game files, or offline-service
emulators.
"""

from __future__ import annotations

import ctypes
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_NAME = "Offline LAN Games Helper"
APP_TITLE = "Offline LAN Games Helper - Windows"
FIREWALL_PREFIX = "Offline LAN Helper"
SAFETY_WARNING = (
    "This app does not emulate servers or bypass online services. "
    "Online-only games are intentionally excluded."
)
PRIVACY_TEXT = """
Privacy Policy

Offline LAN Games Helper is designed to work locally on your device.

Data Collection
- This app does not collect, sell, share, or upload personal data.

Network Information
- The app may read your hostname, local/private IPv4 addresses, and network adapter names.
- This information is shown only inside the app so you can set up LAN/offline multiplayer.

Local Configuration
- The app may save selected game paths, custom games, selected server paths, and exported guides.
- These files stay on your device.

Internet Access
- Normal LAN helper features should not require internet access.
- If Server Tools opens official download pages or uses official tools such as SteamCMD, those tools may connect to official services.

No DRM or Account Bypass
- This app does not bypass DRM, launchers, authentication, game ownership checks, anti-cheat, or online services.

Third-Party Services
- This project is not affiliated with Steam, Valve, Paradox, Epic Games, Rockstar, Riot Games, Mojang, Microsoft, Apple, or any game publisher.

Contact
- For privacy questions, contact The0Cosmo via GitHub.
""".strip()

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = APP_DIR

GAMES_FILE = APP_DIR / "games.json"
BUNDLED_GAMES_FILE = RESOURCE_DIR / "games.json"
CONFIG_FILE = APP_DIR / "user_config.json"
EXPORT_DIR = APP_DIR / "exported_guides"
SERVER_ROOT = APP_DIR / "servers"
DEFAULT_CONFIG = {
    "paths": {},
    "server_paths": {},
    "server_install_dirs": {},
    "steamcmd_path": "",
    "custom_games": [],
}


@dataclass
class AddressInfo:
    adapter: str
    ip: str


def is_windows() -> bool:
    return os.name == "nt"


def create_no_window_kwargs() -> dict[str, Any]:
    if not is_windows():
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "startupinfo": startupinfo,
    }


def run_hidden(args: list[str], timeout: int = 30, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        text=True,
        capture_output=True,
        timeout=timeout,
        cwd=cwd,
        errors="replace",
        **create_no_window_kwargs(),
    )


def is_admin() -> bool:
    if not is_windows():
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def is_private_lan_ipv4(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return (
        address.version == 4
        and address.is_private
        and not address.is_loopback
        and not address.is_link_local
    )


def ip_preference_score(value: str) -> int:
    if value.startswith("192.168."):
        return 0
    if value.startswith("10."):
        return 1
    if re.match(r"^172\.(1[6-9]|2[0-9]|3[0-1])\.", value):
        return 2
    return 3


def load_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json_file(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def merge_config(raw: Any) -> dict[str, Any]:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if isinstance(raw, dict):
        for key in config:
            if key in raw and isinstance(raw[key], type(config[key])):
                config[key] = raw[key]
    return config


def ensure_runtime_files() -> None:
    if not GAMES_FILE.exists() and BUNDLED_GAMES_FILE.exists():
        shutil.copyfile(BUNDLED_GAMES_FILE, GAMES_FILE)
    if not CONFIG_FILE.exists():
        save_json_file(CONFIG_FILE, DEFAULT_CONFIG)


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "game"


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


def run_powershell(command: str, timeout: int = 40) -> subprocess.CompletedProcess[str]:
    return run_hidden(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        timeout=timeout,
    )


def parse_ipconfig(output: str) -> list[AddressInfo]:
    addresses: list[AddressInfo] = []
    adapter = "Unknown adapter"
    for raw_line in output.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if not raw_line.startswith(" ") and stripped.endswith(":"):
            adapter = stripped[:-1]
            continue
        if "IPv4" not in stripped:
            continue
        match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", stripped)
        if match and is_private_lan_ipv4(match.group(1)):
            addresses.append(AddressInfo(adapter, match.group(1)))
    return addresses


def get_network_addresses() -> list[AddressInfo]:
    addresses: list[AddressInfo] = []
    try:
        completed = run_hidden(["ipconfig"], timeout=10)
        if completed.stdout:
            addresses.extend(parse_ipconfig(completed.stdout))
    except Exception:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if is_private_lan_ipv4(ip):
                addresses.append(AddressInfo("Hostname lookup", ip))
    except Exception:
        pass
    unique: dict[str, AddressInfo] = {}
    for item in addresses:
        unique.setdefault(item.ip, item)
    return sorted(unique.values(), key=lambda item: (ip_preference_score(item.ip), item.ip))


def steam_library_roots() -> list[Path]:
    steam_roots = [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]
    roots: list[Path] = []
    for steam_root in steam_roots:
        steamapps = steam_root / "steamapps"
        if steamapps.exists():
            roots.append(steam_root)
        vdf = steamapps / "libraryfolders.vdf"
        if not vdf.exists():
            continue
        try:
            text = vdf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in re.finditer(r'"path"\s+"([^"]+)"', text):
            library_path = Path(match.group(1).replace("\\\\", "\\"))
            if library_path.exists():
                roots.append(library_path)
    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        try:
            key = str(root.resolve()).lower()
        except OSError:
            key = str(root).lower()
        if key not in seen:
            unique.append(root)
            seen.add(key)
    return unique


def normalize_game(game: dict[str, Any], custom: bool = False) -> dict[str, Any]:
    fields = {
        "name": "Unnamed Game",
        "platforms": ["Windows"],
        "lan_status": "",
        "exe_names": [],
        "common_paths_windows": [],
        "common_paths_macos": [],
        "steam_folders": [],
        "launch_uri": "",
        "ports": [],
        "host_tutorial": [],
        "client_tutorial": [],
        "offline_notes": [],
        "troubleshooting": [],
        "launch_notes": [],
        "server_support": "none",
        "server_notes": [],
        "server_files": [],
        "steamcmd_app_id": "",
        "server_executable_names": [],
        "server_common_paths_windows": [],
        "server_common_paths_macos": [],
        "server_install_steps": [],
        "server_launch_command_windows": "",
        "server_launch_command_macos": "",
        "server_config_files": [],
        "server_ports": [],
        "official_download_url": "",
        "custom": custom,
    }
    normalized = fields | game
    normalized["custom"] = custom
    return normalized


def parse_ports(raw: str) -> list[dict[str, str]]:
    ports: list[dict[str, str]] = []
    for chunk in re.split(r"[,;\n]+", raw):
        item = chunk.strip()
        if not item:
            continue
        match = re.match(r"^(TCP|UDP)\s*[: ]\s*([0-9]+(?:-[0-9]+)?)$", item, re.IGNORECASE)
        if not match:
            raise ValueError(f"Invalid port entry: {item}. Use TCP:7777 or UDP:2456-2458.")
        ports.append({"protocol": match.group(1).upper(), "range": match.group(2)})
    return ports


def join_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


class OfflineLanGamesHelper:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1280x820")
        self.root.minsize(1040, 680)

        self.config = merge_config(load_json_file(CONFIG_FILE, DEFAULT_CONFIG))
        self.builtin_games = [normalize_game(game) for game in load_json_file(GAMES_FILE, [])]
        self.custom_games = [normalize_game(game, custom=True) for game in self.config.get("custom_games", [])]
        self.games: list[dict[str, Any]] = []
        self.filtered_games: list[dict[str, Any]] = []
        self.current_game: dict[str, Any] | None = None
        self.current_path: str | None = None
        self.current_server_path: str | None = None
        self.addresses: list[AddressInfo] = []
        self.main_ip = ""

        self.build_ui()
        self.reload_games()
        self.refresh_network()

    def build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=1, minsize=270)
        self.root.grid_columnconfigure(1, weight=4)
        self.root.grid_rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(10, 8))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 17, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=SAFETY_WARNING, foreground="#9a3412").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        network = ttk.LabelFrame(header, text="Host Network", padding=8)
        network.grid(row=0, column=1, rowspan=2, sticky="ew", padx=(16, 0))
        network.grid_columnconfigure(1, weight=1)
        self.hostname_var = tk.StringVar(value="Hostname:")
        self.main_ip_var = tk.StringVar(value="Primary LAN IPv4:")
        self.adapter_var = tk.StringVar(value="Adapter:")
        self.network_warning_var = tk.StringVar(value="")
        ttk.Label(network, textvariable=self.hostname_var).grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(network, textvariable=self.main_ip_var).grid(row=0, column=1, sticky="w", padx=(0, 12))
        ttk.Label(network, textvariable=self.adapter_var).grid(row=0, column=2, sticky="w")
        ttk.Label(network, text="Selected IP:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.ip_combo = ttk.Combobox(network, state="readonly", width=56)
        self.ip_combo.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Label(network, textvariable=self.network_warning_var, foreground="#9a3412").grid(row=2, column=0, columnspan=3, sticky="w", pady=(5, 0))

        left = ttk.Frame(self.root, padding=(10, 0, 6, 8))
        left.grid(row=1, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)
        ttk.Label(left, text="Search").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.apply_filter())
        ttk.Entry(left, textvariable=self.search_var).grid(row=1, column=0, sticky="ew", pady=(4, 8))
        list_frame = ttk.Frame(left)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        self.game_list = tk.Listbox(list_frame, exportselection=False, activestyle="dotbox")
        self.game_list.grid(row=0, column=0, sticky="nsew")
        game_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.game_list.yview)
        game_scroll.grid(row=0, column=1, sticky="ns")
        self.game_list.configure(yscrollcommand=game_scroll.set)
        self.game_list.bind("<<ListboxSelect>>", self.on_game_selected)
        ttk.Button(left, text="Add Custom Game", command=lambda: self.run_ui_action("Add Custom Game", self.add_custom_game_dialog)).grid(row=3, column=0, sticky="ew", pady=(8, 0))

        right = ttk.Frame(self.root, padding=(6, 0, 10, 8))
        right.grid(row=1, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)
        self.tabs = ttk.Notebook(right)
        self.tabs.grid(row=0, column=0, sticky="nsew")
        self.tutorial_text = self.add_text_tab("Tutorial")
        self.network_text = self.add_text_tab("Network / IP")
        self.firewall_text = self.add_text_tab("Firewall / Permissions")
        self.path_text = self.add_text_tab("Game Path")
        self.server_text = self.add_server_tools_tab()
        self.troubleshooting_text = self.add_text_tab("Troubleshooting")
        self.privacy_text = self.add_text_tab("Privacy")
        self.server_buttons: dict[str, ttk.Button] = {}
        self.add_server_button("Open Server Folder", self.open_server_folder, 0)
        self.add_server_button("Select Server Executable", self.select_server_executable, 1)
        self.add_server_button("Launch Server", self.launch_server, 2)
        self.add_server_button("Install with SteamCMD", self.install_with_steamcmd, 3)
        self.add_server_button("Open Official Download Page", self.open_official_download_page, 4)
        self.add_server_button("Export Server Guide", self.export_server_guide, 5)
        self.add_server_button("Select SteamCMD", self.select_steamcmd, 6)

        actions = ttk.LabelFrame(self.root, text="Actions", padding=8)
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 6))
        for column in range(8):
            actions.grid_columnconfigure(column, weight=1, uniform="actions")
        self.add_action_button(actions, "Refresh IP", self.refresh_network, 0)
        self.add_action_button(actions, "Copy Host IP", self.copy_host_ip, 1)
        self.add_action_button(actions, "Detect Game Path", self.detect_game_path, 2)
        self.add_action_button(actions, "Manual Select Game", self.select_game_exe, 3)
        self.add_action_button(actions, "Launch Game", self.launch_game, 4)
        self.add_action_button(actions, "Add Firewall Rules", self.add_firewall_rules, 5)
        self.add_action_button(actions, "Remove Firewall Rules", self.remove_firewall_rules, 6)
        self.add_action_button(actions, "Export Tutorial", self.export_tutorial, 7)

        log_frame = ttk.LabelFrame(self.root, text="Log / Status", padding=6)
        log_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        log_frame.grid_columnconfigure(0, weight=1)
        self.log_box = tk.Text(log_frame, height=5, wrap=tk.WORD)
        self.log_box.grid(row=0, column=0, sticky="ew")
        self.log_box.configure(state=tk.DISABLED)
        ttk.Button(log_frame, text="Clear Log", command=self.clear_log).grid(row=0, column=1, sticky="ns", padx=(8, 0))

    def add_text_tab(self, title: str) -> tk.Text:
        frame = ttk.Frame(self.tabs, padding=8)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        text = tk.Text(frame, wrap=tk.WORD)
        text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=scroll.set, state=tk.DISABLED)
        self.tabs.add(frame, text=title)
        return text

    def add_server_tools_tab(self) -> tk.Text:
        frame = ttk.Frame(self.tabs, padding=8)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        text = tk.Text(frame, wrap=tk.WORD)
        text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=scroll.set, state=tk.DISABLED)

        self.server_buttons_frame = ttk.Frame(frame, padding=(0, 8, 0, 0))
        self.server_buttons_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        for column in range(6):
            self.server_buttons_frame.grid_columnconfigure(column, weight=1, uniform="server")

        self.tabs.add(frame, text="Server Tools")
        return text

    def add_action_button(self, parent: ttk.Frame, text: str, callback: Callable[[], None], column: int) -> None:
        ttk.Button(parent, text=text, command=lambda: self.run_ui_action(text, callback)).grid(row=0, column=column, sticky="ew", padx=3, pady=3)

    def add_server_button(self, text: str, callback: Callable[[], None], index: int) -> None:
        row, column = divmod(index, 6)
        button = ttk.Button(self.server_buttons_frame, text=text, command=lambda: self.run_ui_action(text, callback))
        button.grid(row=row, column=column, sticky="ew", padx=3, pady=3)
        self.server_buttons[text] = button

    def run_ui_action(self, action_name: str, callback: Callable[[], None]) -> None:
        self.log(f"Clicked: {action_name}")
        try:
            callback()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"{action_name} failed:\n{exc}")
            self.log(f"ERROR in {action_name}: {exc}")

    def log(self, message: str) -> None:
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def clear_log(self) -> None:
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def set_text(self, widget: tk.Text, content: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.configure(state=tk.DISABLED)

    def reload_games(self) -> None:
        self.custom_games = [normalize_game(game, custom=True) for game in self.config.get("custom_games", [])]
        self.games = self.builtin_games + self.custom_games
        self.apply_filter(select_first=True)

    def apply_filter(self, select_first: bool = False) -> None:
        query = self.search_var.get().strip().lower()
        previous = self.current_game["name"] if self.current_game else ""
        self.filtered_games = [game for game in self.games if query in game["name"].lower()]
        self.game_list.delete(0, tk.END)
        for game in self.filtered_games:
            suffix = " (custom)" if game.get("custom") else ""
            self.game_list.insert(tk.END, game["name"] + suffix)
        if not self.filtered_games:
            self.current_game = None
            self.update_all_tabs()
            return
        index = 0
        if not select_first and previous:
            for i, game in enumerate(self.filtered_games):
                if game["name"] == previous:
                    index = i
                    break
        self.game_list.selection_set(index)
        self.on_game_selected()

    def selected_game(self) -> dict[str, Any] | None:
        selection = self.game_list.curselection()
        if not selection:
            return None
        return self.filtered_games[selection[0]]

    def on_game_selected(self, _event: tk.Event | None = None) -> None:
        game = self.selected_game()
        if not game:
            return
        self.current_game = game
        self.current_path = self.config.get("paths", {}).get(game["name"]) or self.find_game_path(game)
        self.current_server_path = self.config.get("server_paths", {}).get(game["name"]) or self.find_server_path(game)
        self.update_all_tabs()
        self.log(f"Selected game: {game['name']}")

    def selected_ip(self) -> str:
        selected = self.ip_combo.get().strip()
        return selected.split(" - ", 1)[0] if selected else self.main_ip

    def refresh_network(self) -> None:
        self.addresses = get_network_addresses()
        hostname = socket.gethostname()
        self.hostname_var.set(f"Hostname: {hostname}")
        if self.addresses:
            main = self.addresses[0]
            self.main_ip = main.ip
            self.main_ip_var.set(f"Primary LAN IPv4: {main.ip}")
            self.adapter_var.set(f"Adapter: {main.adapter}")
            values = [f"{item.ip} - {item.adapter}" for item in self.addresses]
            self.ip_combo.configure(values=values)
            self.ip_combo.set(values[0])
        else:
            self.main_ip = ""
            self.main_ip_var.set("Primary LAN IPv4: not detected")
            self.adapter_var.set("Adapter: not detected")
            self.ip_combo.configure(values=[])
            self.ip_combo.set("")
        self.network_warning_var.set(
            "Warning: multiple LAN/VPN adapters detected. Use the IP on the same network as other players."
            if len(self.addresses) > 1 else ""
        )
        self.update_network_tab()
        self.log("Network/IP refreshed.")

    def update_all_tabs(self) -> None:
        self.update_tutorial_tab()
        self.update_network_tab()
        self.update_firewall_tab()
        self.update_path_tab()
        self.update_server_tab()
        self.update_troubleshooting_tab()
        self.update_privacy_tab()

    def update_tutorial_tab(self) -> None:
        game = self.current_game
        if not game:
            self.set_text(self.tutorial_text, "No game selected.")
            return
        lines = [
            f"Game: {game['name']}",
            f"Platforms: {', '.join(game['platforms'])}",
            f"LAN/offline status: {game['lan_status']}",
            "",
            "Host steps:",
            self.format_list(game["host_tutorial"]),
            "",
            "Client steps:",
            self.format_list(game["client_tutorial"]),
            "",
            "Firewall ports:",
            self.format_ports(game["ports"]),
            "",
            "Version/mod notes:",
            self.format_list(game["offline_notes"]),
            "",
            "Launch notes:",
            self.format_list(game["launch_notes"]),
            "",
            "Safety:",
            "- This app does not transform online-only games into LAN games.",
            "- This app does not bypass DRM, launchers, authentication, licenses, ownership checks, or anti-cheat.",
            "- This app does not modify game files.",
        ]
        self.set_text(self.tutorial_text, "\n".join(lines))

    def update_network_tab(self) -> None:
        lines = [
            f"Hostname: {socket.gethostname()}",
            f"Primary LAN IPv4: {self.main_ip or 'not detected'}",
            "",
            "All detected private IPv4 addresses:",
        ]
        if self.addresses:
            for item in self.addresses:
                marker = " (primary)" if item.ip == self.main_ip else ""
                lines.append(f"- {item.ip}{marker} - {item.adapter}")
        else:
            lines.append("- none detected")
        if len(self.addresses) > 1:
            lines.extend(["", "Warning:", "Multiple LAN/VPN adapters were detected. Copy the IP from the same network used by other players."])
        lines.extend(["", "Use the Copy Host IP button to copy the selected IP."])
        self.set_text(self.network_text, "\n".join(lines))

    def update_firewall_tab(self) -> None:
        game = self.current_game
        if not game:
            self.set_text(self.firewall_text, "No game selected.")
            return
        lines = [
            f"Selected game: {game['name']}",
            f"Selected EXE: {self.current_path or 'not detected'}",
            "",
            "Rules created by this helper:",
            self.format_list(self.firewall_rule_names(game)),
            "",
            "Behavior:",
            "- Add/remove firewall rules require Administrator.",
            "- If the app is not elevated, it shows a popup and keeps running.",
            "- Rules are added only for the selected game.",
            "- Remove Firewall Rules removes only rules with the names above.",
        ]
        self.set_text(self.firewall_text, "\n".join(lines))

    def update_path_tab(self) -> None:
        game = self.current_game
        if not game:
            self.set_text(self.path_text, "No game selected.")
            return
        lines = [
            f"Game: {game['name']}",
            f"Detected/selected executable: {self.current_path or 'not detected'}",
            f"Launch URI: {game.get('launch_uri') or 'none'}",
            "",
            "Executable names searched:",
            self.format_list(game["exe_names"]),
            "",
            "Common Windows paths searched:",
            self.format_list(game["common_paths_windows"]),
            "",
            "Steam folders searched:",
            self.format_list(game.get("steam_folders", [])),
            "",
            "Manual paths are saved in user_config.json.",
        ]
        self.set_text(self.path_text, "\n".join(lines))

    def update_server_tab(self) -> None:
        game = self.current_game
        if not game:
            self.set_text(self.server_text, "No game selected.")
            return
        support = game["server_support"]
        if support == "none":
            support_text = "No supported dedicated server is available for this game. Use in-game hosting if available."
        elif support == "in_game_host":
            support_text = "Host from inside the game."
        else:
            support_text = support
        lines = [
            f"Game: {game['name']}",
            f"Server support: {support_text}",
            f"Selected server executable/file: {self.current_server_path or 'not selected'}",
            f"SteamCMD path: {self.config.get('steamcmd_path') or 'not selected'}",
            f"SteamCMD app ID: {game.get('steamcmd_app_id') or 'none'}",
            f"Official download page: {game.get('official_download_url') or 'none'}",
            "",
            "Server notes:",
            self.format_list(game["server_notes"]),
            "",
            "Required files/tools:",
            self.format_list(game["server_files"]),
            "",
            "Install/download instructions:",
            self.format_list(game["server_install_steps"]),
            "",
            "Launch command notes:",
            f"- {game.get('server_launch_command_windows') or 'Launch the selected official server executable/file normally.'}",
            "",
            "Server ports:",
            self.format_ports(game["server_ports"]),
            "",
            "Config files:",
            self.format_list(game["server_config_files"]),
        ]
        self.set_text(self.server_text, "\n".join(lines))
        self.update_server_button_states()

    def update_troubleshooting_tab(self) -> None:
        game = self.current_game
        if not game:
            self.set_text(self.troubleshooting_text, "No game selected.")
            return
        lines = [
            f"Game: {game['name']}",
            "",
            "Troubleshooting:",
            self.format_list(game["troubleshooting"]),
            "",
            "General checklist:",
            "- Verify host and clients are on the same LAN or VPN LAN.",
            "- Verify clients can ping the host.",
            "- Verify Windows Firewall allows the game/server.",
            "- Verify matching game version, mods, DLC, and required content.",
            "- Use the correct IP if multiple LAN/VPN adapters exist.",
            "- Do not use this app for online-only or matchmaking-only games.",
        ]
        self.set_text(self.troubleshooting_text, "\n".join(lines))

    def update_privacy_tab(self) -> None:
        self.set_text(self.privacy_text, PRIVACY_TEXT)

    def update_server_button_states(self) -> None:
        game = self.current_game
        if not game:
            for button in self.server_buttons.values():
                button.state(["disabled"])
            return
        support = game["server_support"]
        for button in self.server_buttons.values():
            button.state(["!disabled"])
        if support in {"none", "in_game_host"}:
            for name in ["Open Server Folder", "Select Server Executable", "Launch Server", "Install with SteamCMD", "Open Official Download Page"]:
                self.server_buttons[name].state(["disabled"])
        if not game.get("steamcmd_app_id"):
            self.server_buttons["Install with SteamCMD"].state(["disabled"])
        if not game.get("official_download_url"):
            self.server_buttons["Open Official Download Page"].state(["disabled"])
        self.server_buttons["Export Server Guide"].state(["!disabled"])
        self.server_buttons["Select SteamCMD"].state(["!disabled"])

    @staticmethod
    def format_list(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "- none"

    @staticmethod
    def format_ports(ports: list[dict[str, str]]) -> str:
        return "\n".join(f"- {p.get('protocol', '').upper()} {p.get('range', '')}" for p in ports) if ports else "- none listed or varies by configuration"

    def find_game_path(self, game: dict[str, Any]) -> str | None:
        candidates = [expand_path(raw) for raw in game.get("common_paths_windows", [])]
        for root in steam_library_roots():
            common = root / "steamapps" / "common"
            for folder in game.get("steam_folders", []):
                for exe_name in game.get("exe_names", []):
                    candidates.append(common / folder / exe_name)
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return str(candidate)
        return None

    def find_server_path(self, game: dict[str, Any]) -> str | None:
        candidates = [expand_path(raw) for raw in game.get("server_common_paths_windows", [])]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return None

    def detect_game_path(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        found = self.find_game_path(game)
        if not found:
            messagebox.showwarning(APP_TITLE, "Game path was not detected. Use Manual Select Game.")
            self.log(f"No executable detected for {game['name']}.")
            return
        self.set_game_path(game, found)
        messagebox.showinfo(APP_TITLE, f"Detected:\n{found}")
        self.log(f"Detected path for {game['name']}: {found}")

    def select_game_exe(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        path = filedialog.askopenfilename(title=f"Select executable for {game['name']}", filetypes=[("Windows executable", "*.exe"), ("All files", "*.*")])
        if not path:
            self.log("Manual game selection canceled.")
            return
        if Path(path).suffix.lower() != ".exe":
            messagebox.showerror(APP_TITLE, "Please select a Windows .exe file.")
            return
        self.set_game_path(game, path)
        messagebox.showinfo(APP_TITLE, f"Saved game path:\n{path}")

    def set_game_path(self, game: dict[str, Any], path: str) -> None:
        self.config.setdefault("paths", {})[game["name"]] = path
        save_json_file(CONFIG_FILE, self.config)
        self.current_path = path
        self.update_all_tabs()

    def copy_host_ip(self) -> None:
        value = self.selected_ip()
        if not value:
            messagebox.showwarning(APP_TITLE, "No private LAN IPv4 address was detected.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        messagebox.showinfo(APP_TITLE, f"Copied host IP:\n{value}")
        self.log(f"Copied host IP: {value}")

    def launch_game(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        target = self.current_path or self.find_game_path(game)
        if target and Path(target).exists():
            os.startfile(target)  # type: ignore[attr-defined]
            self.log(f"Launched {game['name']} normally: {target}")
            return
        launch_uri = game.get("launch_uri", "")
        if launch_uri:
            os.startfile(launch_uri)  # type: ignore[attr-defined]
            self.log(f"Launched {game['name']} with URI: {launch_uri}")
            return
        messagebox.showwarning(APP_TITLE, "No executable path detected. Use Detect Game Path or Manual Select Game.")

    def selected_game_required(self) -> dict[str, Any] | None:
        game = self.selected_game()
        if not game:
            messagebox.showwarning(APP_TITLE, "Select a game first.")
            return None
        return game

    def ports_by_protocol(self, game: dict[str, Any], key: str = "ports") -> dict[str, list[str]]:
        grouped = {"TCP": [], "UDP": []}
        for port in game.get(key, []):
            protocol = str(port.get("protocol", "")).upper()
            port_range = str(port.get("range", "")).strip()
            if protocol in grouped and port_range:
                grouped[protocol].append(port_range)
        return grouped

    def firewall_rule_names(self, game: dict[str, Any]) -> list[str]:
        return [
            f"{FIREWALL_PREFIX} - {game['name']} - EXE TCP",
            f"{FIREWALL_PREFIX} - {game['name']} - EXE UDP",
            f"{FIREWALL_PREFIX} - {game['name']} - Ports TCP",
            f"{FIREWALL_PREFIX} - {game['name']} - Ports UDP",
        ]

    def require_admin_for_firewall(self) -> bool:
        if is_admin():
            return True
        messagebox.showerror(APP_TITLE, "Run as Administrator to change Windows Firewall rules.")
        self.log("Firewall action blocked: Run as Administrator to change Windows Firewall rules.")
        return False

    def add_firewall_rules(self) -> None:
        game = self.selected_game_required()
        if not game or not self.require_admin_for_firewall():
            return
        path = self.current_path or self.find_game_path(game)
        grouped_ports = self.ports_by_protocol(game)
        commands: list[str] = []
        if path and Path(path).exists():
            for protocol in ("TCP", "UDP"):
                name = f"{FIREWALL_PREFIX} - {game['name']} - EXE {protocol}"
                commands.append(f"Get-NetFirewallRule -DisplayName {ps_quote(name)} -ErrorAction SilentlyContinue | Remove-NetFirewallRule")
                commands.append(
                    "New-NetFirewallRule "
                    f"-DisplayName {ps_quote(name)} -Direction Inbound -Action Allow "
                    f"-Program {ps_quote(path)} -Protocol {protocol} -Profile Private | Out-Null"
                )
        for protocol, ranges in grouped_ports.items():
            if not ranges:
                continue
            name = f"{FIREWALL_PREFIX} - {game['name']} - Ports {protocol}"
            commands.append(f"Get-NetFirewallRule -DisplayName {ps_quote(name)} -ErrorAction SilentlyContinue | Remove-NetFirewallRule")
            commands.append(
                "New-NetFirewallRule "
                f"-DisplayName {ps_quote(name)} -Direction Inbound -Action Allow "
                f"-Protocol {protocol} -LocalPort {ps_quote(','.join(ranges))} -Profile Private | Out-Null"
            )
        if not commands:
            messagebox.showerror(APP_TITLE, "No executable path or port list is available for this game.")
            return
        completed = run_powershell("; ".join(commands))
        if completed.returncode != 0:
            messagebox.showerror(APP_TITLE, completed.stderr.strip() or "Firewall command failed.")
            self.log(completed.stderr.strip() or "Firewall command failed.")
            return
        messagebox.showinfo(APP_TITLE, f"Firewall rules added for {game['name']}.")
        self.log(f"Firewall rules added for {game['name']}.")

    def remove_firewall_rules(self) -> None:
        game = self.selected_game_required()
        if not game or not self.require_admin_for_firewall():
            return
        commands = [f"Get-NetFirewallRule -DisplayName {ps_quote(name)} -ErrorAction SilentlyContinue | Remove-NetFirewallRule" for name in self.firewall_rule_names(game)]
        completed = run_powershell("; ".join(commands))
        if completed.returncode != 0:
            messagebox.showerror(APP_TITLE, completed.stderr.strip() or "Firewall remove failed.")
            self.log(completed.stderr.strip() or "Firewall remove failed.")
            return
        messagebox.showinfo(APP_TITLE, f"Firewall rules removed for {game['name']}.")
        self.log(f"Firewall rules removed for {game['name']}.")

    def open_server_folder(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        path = self.current_server_path or self.config.get("server_install_dirs", {}).get(game["name"]) or str(SERVER_ROOT / safe_filename(game["name"]))
        folder = Path(path).parent if Path(path).suffix else Path(path)
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(str(folder))  # type: ignore[attr-defined]
        self.log(f"Opened server folder: {folder}")

    def select_server_executable(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        path = filedialog.askopenfilename(title=f"Select official server executable/file for {game['name']}", filetypes=[("Server files", "*.exe *.bat *.cmd *.jar *.*"), ("All files", "*.*")])
        if not path:
            self.log("Server executable selection canceled.")
            return
        self.config.setdefault("server_paths", {})[game["name"]] = path
        save_json_file(CONFIG_FILE, self.config)
        self.current_server_path = path
        self.update_server_tab()
        messagebox.showinfo(APP_TITLE, f"Saved server file:\n{path}")

    def launch_server(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        support = game["server_support"]
        if support in {"none", "in_game_host"}:
            messagebox.showinfo(APP_TITLE, "No supported dedicated server is available for this game. Host from inside the game if supported.")
            return
        path = self.current_server_path or self.find_server_path(game)
        if not path or not Path(path).exists():
            messagebox.showwarning(APP_TITLE, "Select an official local server executable/file first.")
            return
        os.startfile(path)  # type: ignore[attr-defined]
        self.log(f"Launched server file normally: {path}")

    def select_steamcmd(self) -> None:
        path = filedialog.askopenfilename(title="Select steamcmd.exe", filetypes=[("steamcmd.exe", "steamcmd.exe"), ("Windows executable", "*.exe"), ("All files", "*.*")])
        if not path:
            self.log("SteamCMD selection canceled.")
            return
        if Path(path).name.lower() != "steamcmd.exe":
            messagebox.showerror(APP_TITLE, "Please select steamcmd.exe.")
            return
        self.config["steamcmd_path"] = path
        save_json_file(CONFIG_FILE, self.config)
        self.update_server_tab()
        messagebox.showinfo(APP_TITLE, f"Saved SteamCMD path:\n{path}")

    def install_with_steamcmd(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        app_id = str(game.get("steamcmd_app_id", "")).strip()
        if not app_id:
            messagebox.showinfo(APP_TITLE, "This game entry does not include a verified official SteamCMD app ID.")
            return
        steamcmd = self.config.get("steamcmd_path") or ""
        if not steamcmd or not Path(steamcmd).exists():
            messagebox.showwarning(APP_TITLE, "Select steamcmd.exe first.")
            return
        install_dir = filedialog.askdirectory(title=f"Choose install folder for {game['name']} server", initialdir=str(SERVER_ROOT))
        if not install_dir:
            self.log("SteamCMD install canceled.")
            return
        if not messagebox.askyesno(APP_TITLE, f"Install official SteamCMD app {app_id} to:\n{install_dir}\n\nSteamCMD will run normally. Continue?"):
            self.log("SteamCMD install canceled by user.")
            return
        self.config.setdefault("server_install_dirs", {})[game["name"]] = install_dir
        save_json_file(CONFIG_FILE, self.config)
        args = [steamcmd, "+force_install_dir", install_dir, "+login", "anonymous", "+app_update", app_id, "validate", "+quit"]
        threading.Thread(target=self.run_steamcmd_install, args=(args, game["name"]), daemon=True).start()

    def run_steamcmd_install(self, args: list[str], game_name: str) -> None:
        self.log(f"SteamCMD install started for {game_name}.")
        try:
            completed = run_hidden(args, timeout=3600)
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror(APP_TITLE, f"SteamCMD failed:\n{exc}"))
            self.root.after(0, lambda: self.log(f"SteamCMD failed: {exc}"))
            return
        output = (completed.stdout or "") + (completed.stderr or "")
        for line in output.splitlines()[-80:]:
            self.root.after(0, lambda text=line: self.log(text))
        if completed.returncode == 0:
            self.root.after(0, lambda: messagebox.showinfo(APP_TITLE, f"SteamCMD install completed for {game_name}."))
        else:
            self.root.after(0, lambda: messagebox.showerror(APP_TITLE, f"SteamCMD exited with code {completed.returncode}. Check the log."))

    def open_official_download_page(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        url = game.get("official_download_url", "")
        if not url:
            messagebox.showinfo(APP_TITLE, "No official download page is configured for this game.")
            return
        webbrowser.open(url)
        self.log(f"Opened official download page: {url}")

    def export_tutorial(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        EXPORT_DIR.mkdir(exist_ok=True)
        output = EXPORT_DIR / f"{safe_filename(game['name'])}_LAN_Tutorial.md"
        output.write_text(self.build_export_text(game, include_server=True), encoding="utf-8")
        messagebox.showinfo(APP_TITLE, f"Tutorial exported:\n{output}")
        self.log(f"Tutorial exported: {output}")

    def export_server_guide(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        EXPORT_DIR.mkdir(exist_ok=True)
        output = EXPORT_DIR / f"{safe_filename(game['name'])}_Server_Guide.md"
        output.write_text(self.build_server_export_text(game), encoding="utf-8")
        messagebox.showinfo(APP_TITLE, f"Server guide exported:\n{output}")
        self.log(f"Server guide exported: {output}")

    def build_export_text(self, game: dict[str, Any], include_server: bool) -> str:
        lines = [
            f"# {game['name']} - Offline/LAN Tutorial",
            "",
            f"Host IP: {self.selected_ip() or 'not detected'}",
            f"LAN/offline status: {game['lan_status']}",
            "",
            "## Host Steps",
            self.format_list(game["host_tutorial"]),
            "",
            "## Client Steps",
            self.format_list(game["client_tutorial"]),
            "",
            "## Firewall Ports",
            self.format_ports(game["ports"]),
            "",
            "## Notes",
            self.format_list(game["offline_notes"]),
            "",
            "## Troubleshooting",
            self.format_list(game["troubleshooting"]),
        ]
        if include_server:
            lines.extend(["", self.build_server_export_text(game)])
        lines.extend(["", "## Safety", "- No DRM bypass, cracks, launchers bypass, authentication bypass, anti-cheat bypass, or file modification."])
        return "\n".join(lines)

    def build_server_export_text(self, game: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"# {game['name']} - Server Tools Guide",
                "",
                f"Server support: {game['server_support']}",
                "",
                "## Server Notes",
                self.format_list(game["server_notes"]),
                "",
                "## Required Files / Tools",
                self.format_list(game["server_files"]),
                "",
                "## Install / Download Steps",
                self.format_list(game["server_install_steps"]),
                "",
                "## Server Ports",
                self.format_ports(game["server_ports"]),
                "",
                "## Config Files",
                self.format_list(game["server_config_files"]),
                "",
                "## Safety",
                "- Use only official tools, official download pages, official SteamCMD app IDs listed in games.json, or user-provided local files.",
                "- This helper does not emulate online services or bypass authentication.",
            ]
        )

    def add_custom_game_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Custom Game")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.minsize(700, 640)
        for col in (1, 2):
            dialog.grid_columnconfigure(col, weight=1)
        for row in (6, 7, 8):
            dialog.grid_rowconfigure(row, weight=1)
        name_var = tk.StringVar()
        exe_var = tk.StringVar()
        ports_var = tk.StringVar()
        support_var = tk.StringVar(value="manual_files")
        server_var = tk.StringVar()
        ttk.Label(dialog, text="Game name").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        ttk.Entry(dialog, textvariable=name_var).grid(row=0, column=1, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(dialog, text="Executable path").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        ttk.Entry(dialog, textvariable=exe_var).grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        ttk.Button(dialog, text="Browse", command=lambda: self.browse_into(exe_var, True)).grid(row=1, column=2, sticky="ew", padx=10, pady=5)
        ttk.Label(dialog, text="Ports").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        ttk.Entry(dialog, textvariable=ports_var).grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(dialog, text="Format: TCP:7777, UDP:2456-2458").grid(row=3, column=1, columnspan=2, sticky="w", padx=10)
        ttk.Label(dialog, text="Server support").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        ttk.Combobox(dialog, textvariable=support_var, state="readonly", values=["none", "in_game_host", "official_dedicated", "steamcmd", "manual_files", "official_download_page"]).grid(row=4, column=1, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(dialog, text="Server executable/file").grid(row=5, column=0, sticky="w", padx=10, pady=5)
        ttk.Entry(dialog, textvariable=server_var).grid(row=5, column=1, sticky="ew", padx=10, pady=5)
        ttk.Button(dialog, text="Browse", command=lambda: self.browse_into(server_var, False)).grid(row=5, column=2, sticky="ew", padx=10, pady=5)
        ttk.Label(dialog, text="Host tutorial").grid(row=6, column=0, sticky="nw", padx=10, pady=5)
        host_text = tk.Text(dialog, height=5, wrap=tk.WORD)
        host_text.grid(row=6, column=1, columnspan=2, sticky="nsew", padx=10, pady=5)
        ttk.Label(dialog, text="Client tutorial").grid(row=7, column=0, sticky="nw", padx=10, pady=5)
        client_text = tk.Text(dialog, height=5, wrap=tk.WORD)
        client_text.grid(row=7, column=1, columnspan=2, sticky="nsew", padx=10, pady=5)
        ttk.Label(dialog, text="Notes").grid(row=8, column=0, sticky="nw", padx=10, pady=5)
        notes_text = tk.Text(dialog, height=5, wrap=tk.WORD)
        notes_text.grid(row=8, column=1, columnspan=2, sticky="nsew", padx=10, pady=5)
        footer = ttk.Frame(dialog, padding=10)
        footer.grid(row=9, column=0, columnspan=3, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        ttk.Button(footer, text="Save Custom Game", command=lambda: self.save_custom_game(dialog, name_var, exe_var, ports_var, support_var, server_var, host_text, client_text, notes_text)).grid(row=0, column=1, padx=4)
        ttk.Button(footer, text="Cancel", command=dialog.destroy).grid(row=0, column=2, padx=4)

    def browse_into(self, var: tk.StringVar, exe_only: bool) -> None:
        filetypes = [("Windows executable", "*.exe"), ("All files", "*.*")] if exe_only else [("Server files", "*.exe *.bat *.cmd *.jar *.*"), ("All files", "*.*")]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            var.set(path)

    def save_custom_game(self, dialog: tk.Toplevel, name_var: tk.StringVar, exe_var: tk.StringVar, ports_var: tk.StringVar, support_var: tk.StringVar, server_var: tk.StringVar, host_text: tk.Text, client_text: tk.Text, notes_text: tk.Text) -> None:
        name = name_var.get().strip()
        exe = exe_var.get().strip()
        server = server_var.get().strip()
        if not name:
            messagebox.showerror(APP_TITLE, "Game name is required.")
            return
        if exe and (not Path(exe).exists() or Path(exe).suffix.lower() != ".exe"):
            messagebox.showerror(APP_TITLE, "Executable path must point to an existing .exe file.")
            return
        if server and not Path(server).exists():
            messagebox.showerror(APP_TITLE, "Server file path must exist.")
            return
        try:
            ports = parse_ports(ports_var.get())
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        notes = join_lines(notes_text.get("1.0", tk.END)) or ["Custom user entry. Use only legitimate games with real offline/LAN support."]
        custom = normalize_game(
            {
                "name": name,
                "platforms": ["Windows"],
                "lan_status": "Custom user entry. Verify real offline/LAN support before use.",
                "exe_names": [Path(exe).name] if exe else [],
                "common_paths_windows": [exe] if exe else [],
                "ports": ports,
                "host_tutorial": join_lines(host_text.get("1.0", tk.END)) or ["Add host instructions for this LAN/offline game."],
                "client_tutorial": join_lines(client_text.get("1.0", tk.END)) or ["Add client instructions for this LAN/offline game."],
                "offline_notes": notes,
                "troubleshooting": ["Verify host and clients are on the same LAN/VPN.", "Verify Windows Firewall allows the game/server."],
                "launch_notes": ["Custom game. This helper launches the selected executable normally."],
                "server_support": support_var.get(),
                "server_notes": notes,
                "server_files": [Path(server).name] if server else [],
                "server_executable_names": [Path(server).name] if server else [],
                "server_common_paths_windows": [server] if server else [],
                "server_install_steps": ["Use official or user-provided local server files only."],
                "server_ports": ports,
            },
            custom=True,
        )
        self.config.setdefault("custom_games", []).append(custom)
        if exe:
            self.config.setdefault("paths", {})[name] = exe
        if server:
            self.config.setdefault("server_paths", {})[name] = server
        save_json_file(CONFIG_FILE, self.config)
        dialog.destroy()
        self.reload_games()
        self.log(f"Custom game added: {name}")


def main() -> int:
    ensure_runtime_files()
    if not GAMES_FILE.exists():
        messagebox.showerror(APP_TITLE, f"Missing game catalog:\n{GAMES_FILE}")
        return 1
    root = tk.Tk()
    OfflineLanGamesHelper(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
