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
import time
import webbrowser
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_NAME = "Offline LAN Games Helper"
APP_TITLE = "Offline LAN Games Helper - Windows"
APP_VERSION = "1.2.0"
FIREWALL_PREFIX = "Offline LAN Helper"
SAFETY_WARNING = (
    "This app does not emulate servers or bypass online services. "
    "Online-only games are intentionally excluded."
)
PAYPAL_DONATION_URL = "https://paypal.me/The0Cosmo"
GITHUB_SPONSORS_URL = "https://github.com/sponsors/The0Cosmo"
DONATION_OFFLINE_MESSAGE = "Donation links require an internet connection. You can copy the link and open it later."
HIDHIDE_OFFICIAL_URL = "https://docs.nefarius.at/projects/HidHide/"
DS4WINDOWS_OFFICIAL_URL = "https://github.com/Ryochan7/DS4Windows/releases"
PROCESS_CATEGORIES = {
    "nucleuscoop.exe": "Local multiplayer tool",
    "prismlauncher.exe": "Launcher",
    "javaw.exe": "Minecraft Java / Java game instance",
    "java.exe": "Minecraft Java / Java game instance",
    "minecraft.exe": "Minecraft",
    "ds4windows.exe": "Controller mapper",
    "hidhideclient.exe": "Controller visibility tool",
    "steam.exe": "Launcher",
}
HIDHIDE_CHECKLIST = """Recommended HidHide setup:
1. Open DS4Windows.
2. Set Output Controller to Xbox 360.
3. Open HidHide Configuration Client.
4. In Applications, add DS4Windows.exe so DS4Windows can see the real controller.
5. In Devices, select the real PlayStation controller.
6. Enable device hiding.
7. Reconnect the controller.
8. Open joy.cpl and confirm only the virtual Xbox controller is visible to normal apps.
9. Start Nucleus Co-op.
10. Assign the virtual Xbox controller to the correct player."""
DS4WINDOWS_CHECKLIST = """DS4Windows recommended profile:
- Output Controller: Xbox 360
- Hide real controller using HidHide
- Avoid showing both real PS controller and virtual Xbox controller
- Disable Steam Input if it creates duplicate input"""
MINECRAFT_NUCLEUS_CHECKLIST = """For Minecraft Java with Nucleus Co-op, Controlify may read controller input globally across all Minecraft instances. If one controller controls every instance, remove Controlify and use DS4Windows + HidHide, or use keyboard/mouse for one player and controller for another.

Checklist:
- Remove Controlify if it controls all instances
- Do not use Controlify and MidnightControls together
- Use one Minecraft instance per player
- Use Nucleus Co-op assignment screen
- Use HidHide to hide real controller
- Use virtual Xbox controller for the controller player"""
INPUT_ISOLATION_SAFETY_TEXT = """Input Isolation Helper is guidance-only.

It does not inject code into processes.
It does not hook keyboard, mouse, or controller input globally.
It does not block input to processes directly.
It does not create or install drivers.
It does not modify game memory or game files.
It does not bypass anti-cheat, DRM, launchers, authentication, or ownership checks.
Use it only for legitimate local/offline/LAN multiplayer."""
PRIVACY_TEXT = """
Privacy Policy

Offline LAN Games Helper is designed to work locally on your device.

Data Collection
- This app does not collect, sell, share, or upload personal data.

Network Information
- The app may read your hostname, local/private IPv4 addresses, and network adapter names.
- This information is shown only inside the app so you can set up LAN/offline multiplayer.
- LAN tests only use IP addresses entered or selected by you. The app does not scan random IP ranges or the internet.

Local Configuration
- The app may save selected game paths, custom games, selected server paths, selected controller tool paths, local input notes, and exported guides.
- These files stay on your device.

Settings and Language
- The app may save local preferences such as selected language, theme, UI scale, selected paths, hidden tools, enabled tools, default invite mode, and offline mode.
- These settings stay on your device and are not uploaded.

Tool Manager
- The app may save which optional helper tools are hidden or disabled.
- These preferences stay on your device and are not uploaded.

Invite Export
- The app may generate invite text using the selected local IP address, port, game name, and optional password entered by you.
- Invite text is copied or exported only when you click the related button.
- The app does not upload invite text.

Local Detection and Cache
- The app may cache local game detection results and UI preferences to improve performance.
- This data stays on your device and is not uploaded.
- The app does not scan the entire disk aggressively.

Internet Access
- Normal LAN helper features should not require internet access.
- If Server Tools opens official download pages or uses official tools such as SteamCMD, those tools may connect to official services.
- Official download pages, SteamCMD, update checks if added later, and donation links use the internet only after you click the relevant button.
- This app has no telemetry, analytics, or background uploads.

Donations
- The app may include optional donation links such as PayPal.Me or GitHub Sponsors.
- The app does not process payments, collect payment information, or contact donation services automatically.
- Donation links open in your default web browser only when you click them.

Input Isolation Helper
- The Windows version may show local running processes and local controller tool status to help you configure local multiplayer input.
- This information stays on your device.
- The app may save local input setup profiles and isolation test results in user_config.json.
- The app does not upload process lists, controller information, or personal data.
- The app does not inject into processes, block input directly, or modify games.

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
BACKUP_ROOT = APP_DIR / "backups"
KIWI_LOGO_PATH = RESOURCE_DIR / "assets" / "kiwi_logo.png"
WINDOW_ICON_PATH = RESOURCE_DIR / "assets" / "offline_lan_helper.ico"

OPTIONAL_TOOLS = {
    "firewall_helper": "Firewall Helper",
    "server_tools": "Server Tools",
    "controller_tools": "Controller Tools",
    "hidhide_helper": "HidHide Helper",
    "ds4windows_helper": "DS4Windows Helper",
    "nucleus_helper": "Nucleus Co-op Helper",
    "input_isolation": "Input Isolation Helper",
    "backup_tools": "Backup Tools",
    "invite_export": "Invite Export",
    "custom_games": "Custom Games",
    "lan_test": "LAN Test",
    "support": "Support section",
}
CORE_PAGES = {"settings", "about", "privacy", "tool_manager"}
INVITE_MODE_IDS = ["ip_only", "ip_port_only", "short", "full"]
GAME_FILTER_IDS = ["all", "installed", "favorites", "dedicated_server", "in_game_host"]
UI_SCALE_VALUES = ["90%", "100%", "110%", "125%", "150%"]
DEFAULT_CONFIG = {
    "paths": {},
    "server_paths": {},
    "server_install_dirs": {},
    "steamcmd_path": "",
    "save_folders": {},
    "mod_folders": {},
    "server_log_paths": {},
    "offline_mode": False,
    "input_isolation_notes": [],
    "input_isolation_profiles": {},
    "ds4windows_path": "",
    "hidhide_client_path": "",
    "hidhide_cli_path": "",
    "language": "en",
    "theme": "light",
    "show_safety_warnings": True,
    "remember_last_selected_game": True,
    "last_selected_game": "",
    "nucleus_coop_path": "",
    "prism_launcher_path": "",
    "default_export_folder": "",
    "default_backup_folder": "",
    "custom_games": [],
    "enabled_tools": {tool_id: True for tool_id in OPTIONAL_TOOLS},
    "hidden_tools": [],
    "hide_unused_tools_automatically": False,
    "favorite_games": [],
    "hidden_games": [],
    "manual_installed_games": [],
    "installed_cache": {},
    "detection_cache_updated": "",
    "default_game_filter": "all",
    "show_hidden_games": False,
    "default_invite_mode": "short",
    "include_lan_vpn_note": True,
    "ui_scale": "100%",
    "compact_mode": False,
    "animations": True,
}

TRANSLATIONS = {
    "en": {
        "app_title": "Offline LAN Games Helper - Windows",
        "settings": "Settings",
        "language": "Language",
        "theme": "Theme",
        "light": "Light",
        "dark": "Dark",
        "system": "System default",
        "offline_mode": "Offline Mode: hide or block optional internet/download actions",
        "safety_warning": SAFETY_WARNING,
        "search": "Search",
        "search_placeholder": "Search games",
        "game_list": "Games",
        "add_custom_game": "Add Custom Game",
        "refresh_ip": "Refresh IP",
        "copy_ip": "Copy Host IP",
        "detect_path": "Detect Game Path",
        "manual_select_game": "Manual Select Game",
        "launch_game": "Launch Game",
        "add_firewall": "Add Firewall Rules",
        "remove_firewall": "Remove Firewall Rules",
        "export_tutorial": "Export Tutorial",
        "actions": "Actions",
        "log_status": "Log / Status",
        "clear_log": "Clear Log",
        "host_network": "Host Network",
        "selected_ip": "Selected IP:",
        "privacy_local": "This app works locally and does not collect or upload personal data.",
        "support_project": "Support the Project",
        "donate": "Donate with PayPal",
        "sponsor": "Sponsor on GitHub",
        "copy_donation": "Copy Donation Link",
        "privacy": "Privacy",
        "open_privacy": "Open Privacy Policy",
        "about": "About",
        "author": "Creator: KiwiLiu",
        "license_summary": "Personal, non-commercial use only. See LICENSE for full terms.",
        "default_behavior": "Default Behavior",
        "show_safety_warnings": "Show safety warnings",
        "remember_last_game": "Remember last selected game",
        "paths": "Paths",
        "default_export_folder": "Default export folder",
        "default_backup_folder": "Default backup folder",
        "select": "Select",
        "open_github_windows": "Open Windows GitHub Repository",
        "settings_saved": "Settings saved.",
        "tutorial": "Tutorial",
        "network": "Network / IP",
        "firewall_permissions": "Firewall / Permissions",
        "game_path": "Game Path",
        "server_tools": "Server Tools",
        "lan_test": "LAN Test",
        "invite": "Invite",
        "backups": "Backups",
        "mods": "Mods",
        "input_isolation": "Input Isolation",
        "input_isolation_setup": "Input Isolation Setup",
        "troubleshooting": "Troubleshooting",
        "support": "Support",
        "status_ready": "Ready.",
        "home": "Home",
        "games": "Games",
        "firewall": "Firewall",
        "controller_tools": "Controller Tools",
        "show_log": "Show Log",
        "hide_log": "Hide Log",
        "creator_line": f"Created by KiwiLiu  |  GitHub: The0Cosmo",
        "appearance": "Appearance",
        "ui_scale": "UI scale",
        "compact_mode": "Compact mode",
        "animations": "Animations",
        "tool_manager": "Tool Manager",
        "show_tool": "Show Tool",
        "hide_tool": "Hide Tool",
        "enable_tool": "Enable Tool",
        "disable_tool": "Disable Tool",
        "restore_all_tools": "Restore All Tools",
        "suggest_unused_tools": "Suggest Unused Tools",
        "show_all_tools": "Show All Tools",
        "hide_unused_tools_automatically": "Hide unused tools automatically",
        "hidden_tools_can_be_restored": "Hidden tools can be restored at any time.",
        "tool_manager_safety": "This only changes the app interface. It does not uninstall external programs or delete games.",
        "tool_manager_description": "Tool Manager lets you hide or disable app features you do not use. It does not uninstall external programs or delete games.",
        "copy_invite": "Copy Invite",
        "export_invite": "Export Invite",
        "copy_ip_only": "Copy IP Only",
        "copy_ip_port_only": "Copy IP:Port Only",
        "copy_join_address": "Copy Join Address",
        "invite_mode": "Invite Mode",
        "ip_only": "IP Only",
        "ip_port_only": "IP:Port Only",
        "short_invite": "Short Invite",
        "full_useful_invite": "Full Useful Invite",
        "server_password": "Server Password",
        "lan_vpn_mode": "LAN/VPN Mode",
        "invite_copied": "Invite copied to clipboard.",
        "invite_exported": "Invite exported successfully.",
        "refresh_games": "Refresh Games",
        "refresh_installed_detection": "Refresh Installed Detection",
        "loading_games": "Loading games...",
        "no_games_found": "No games found.",
        "games_json_error": "games.json could not be loaded.",
        "no_matching_games_found": "No matching games found.",
        "show_all_games": "Show All Games",
        "show_installed_only": "Show Installed Only",
        "favorites": "Favorites",
        "dedicated_server": "Dedicated Server",
        "in_game_host": "In-Game Hosting",
        "no_installed_detected": "No installed supported games were detected. Showing all supported games.",
        "clear_search": "Clear",
        "storage_cleanup": "Storage / Cleanup",
        "delete_exported_guides": "Delete exported guides",
        "delete_temp_logs": "Delete temporary logs",
        "clear_detection_cache": "Clear detection cache",
        "reset_local_settings": "Reset local settings",
        "game_list_settings": "Game List",
        "default_filter": "Default filter",
        "invite_export_settings": "Invite Export",
        "include_lan_vpn_note": "Include LAN/VPN note",
        "show_hidden_games": "Show hidden games",
        "reset_hidden_games": "Reset hidden games",
        "refresh_detection": "Refresh detection",
        "settings_core_note": "Settings, About, Privacy, and Tool Manager are core pages and cannot be hidden.",
    },
    "it": {
        "app_title": "Offline LAN Games Helper - Windows",
        "settings": "Impostazioni",
        "language": "Lingua",
        "theme": "Tema",
        "light": "Chiaro",
        "dark": "Scuro",
        "system": "Predefinito di sistema",
        "offline_mode": "Modalita offline: nasconde o blocca azioni internet/download opzionali",
        "safety_warning": "Questa app non emula server e non aggira servizi online. I giochi solo online sono esclusi.",
        "search": "Cerca",
        "search_placeholder": "Cerca giochi",
        "game_list": "Giochi",
        "add_custom_game": "Aggiungi gioco personalizzato",
        "refresh_ip": "Aggiorna IP",
        "copy_ip": "Copia IP host",
        "detect_path": "Rileva percorso gioco",
        "manual_select_game": "Seleziona gioco manualmente",
        "launch_game": "Avvia gioco",
        "add_firewall": "Aggiungi regole firewall",
        "remove_firewall": "Rimuovi regole firewall",
        "export_tutorial": "Esporta tutorial",
        "actions": "Azioni",
        "log_status": "Log / Stato",
        "clear_log": "Pulisci log",
        "host_network": "Rete host",
        "selected_ip": "IP selezionato:",
        "privacy_local": "Questa app funziona localmente e non raccoglie o carica dati personali.",
        "support_project": "Supporta il progetto",
        "donate": "Dona con PayPal",
        "sponsor": "Sponsorizza su GitHub",
        "copy_donation": "Copia link donazione",
        "privacy": "Privacy",
        "open_privacy": "Apri informativa privacy",
        "about": "Informazioni",
        "author": "Creatore: KiwiLiu",
        "license_summary": "Solo uso personale e non commerciale. Vedi LICENSE per i termini completi.",
        "default_behavior": "Comportamento predefinito",
        "show_safety_warnings": "Mostra avvisi di sicurezza",
        "remember_last_game": "Ricorda ultimo gioco selezionato",
        "paths": "Percorsi",
        "default_export_folder": "Cartella export predefinita",
        "default_backup_folder": "Cartella backup predefinita",
        "select": "Seleziona",
        "open_github_windows": "Apri repository GitHub Windows",
        "settings_saved": "Impostazioni salvate.",
        "tutorial": "Tutorial",
        "network": "Rete / IP",
        "firewall_permissions": "Firewall / Permessi",
        "game_path": "Percorso gioco",
        "server_tools": "Strumenti server",
        "lan_test": "Test LAN",
        "invite": "Invito",
        "backups": "Backup",
        "mods": "Mod",
        "input_isolation": "Isolamento input",
        "input_isolation_setup": "Configurazione isolamento input",
        "troubleshooting": "Risoluzione problemi",
        "support": "Supporto",
        "status_ready": "Pronto.",
        "home": "Home",
        "games": "Giochi",
        "firewall": "Firewall",
        "controller_tools": "Strumenti controller",
        "show_log": "Mostra log",
        "hide_log": "Nascondi log",
        "creator_line": f"Creato da KiwiLiu  |  GitHub: The0Cosmo",
        "appearance": "Aspetto",
        "ui_scale": "Scala interfaccia",
        "compact_mode": "Modalita compatta",
        "animations": "Animazioni",
        "tool_manager": "Gestore strumenti",
        "show_tool": "Mostra strumento",
        "hide_tool": "Nascondi strumento",
        "enable_tool": "Abilita strumento",
        "disable_tool": "Disabilita strumento",
        "restore_all_tools": "Ripristina tutti gli strumenti",
        "suggest_unused_tools": "Suggerisci strumenti non usati",
        "show_all_tools": "Mostra tutti gli strumenti",
        "hide_unused_tools_automatically": "Nascondi automaticamente strumenti non usati",
        "hidden_tools_can_be_restored": "Gli strumenti nascosti possono essere ripristinati in qualsiasi momento.",
        "tool_manager_safety": "Questo cambia solo l'interfaccia dell'app. Non disinstalla programmi esterni e non cancella giochi.",
        "tool_manager_description": "Gestore strumenti permette di nascondere o disabilitare funzioni dell'app non usate. Non disinstalla programmi esterni e non cancella giochi.",
        "copy_invite": "Copia invito",
        "export_invite": "Esporta invito",
        "copy_ip_only": "Copia solo IP",
        "copy_ip_port_only": "Copia IP:Porta",
        "copy_join_address": "Copia indirizzo di accesso",
        "invite_mode": "Modalita invito",
        "ip_only": "Solo IP",
        "ip_port_only": "Solo IP:Porta",
        "short_invite": "Invito breve",
        "full_useful_invite": "Invito utile completo",
        "server_password": "Password server",
        "lan_vpn_mode": "Modalita LAN/VPN",
        "invite_copied": "Invito copiato negli appunti.",
        "invite_exported": "Invito esportato correttamente.",
        "refresh_games": "Aggiorna giochi",
        "refresh_installed_detection": "Aggiorna rilevamento installati",
        "loading_games": "Caricamento giochi...",
        "no_games_found": "Nessun gioco trovato.",
        "games_json_error": "Impossibile caricare games.json.",
        "no_matching_games_found": "Nessun gioco corrispondente trovato.",
        "show_all_games": "Mostra tutti i giochi",
        "show_installed_only": "Mostra solo installati",
        "favorites": "Preferiti",
        "dedicated_server": "Server dedicato",
        "in_game_host": "Host nel gioco",
        "no_installed_detected": "Nessun gioco supportato installato rilevato. Mostro tutti i giochi supportati.",
        "clear_search": "Cancella",
        "storage_cleanup": "Archiviazione / Pulizia",
        "delete_exported_guides": "Elimina guide esportate",
        "delete_temp_logs": "Elimina log temporanei",
        "clear_detection_cache": "Cancella cache rilevamento",
        "reset_local_settings": "Reimposta impostazioni locali",
        "game_list_settings": "Lista giochi",
        "default_filter": "Filtro predefinito",
        "invite_export_settings": "Esporta invito",
        "include_lan_vpn_note": "Includi nota LAN/VPN",
        "show_hidden_games": "Mostra giochi nascosti",
        "reset_hidden_games": "Reimposta giochi nascosti",
        "refresh_detection": "Aggiorna rilevamento",
        "settings_core_note": "Impostazioni, Informazioni, Privacy e Gestore strumenti sono pagine principali e non possono essere nascoste.",
    },
}

THEMES = {
    "light": {
        "bg": "#F7FAF5",
        "panel": "#FFFFFF",
        "panel_alt": "#EEF6EA",
        "text": "#1F2933",
        "muted": "#52616B",
        "accent": "#7CB342",
        "accent_dark": "#558B2F",
        "warning": "#F59E0B",
        "error": "#DC2626",
        "success": "#16A34A",
        "warning_bg": "#FFF7E6",
        "warning_fg": "#92400E",
        "success_bg": "#ECFDF3",
        "error_bg": "#FEF2F2",
        "border": "#DDE5D5",
        "button_fg": "#1F2933",
    },
    "dark": {
        "bg": "#111827",
        "panel": "#1F2937",
        "panel_alt": "#263244",
        "text": "#F9FAFB",
        "muted": "#D1D5DB",
        "accent": "#A3E635",
        "accent_dark": "#84CC16",
        "warning": "#FBBF24",
        "error": "#F87171",
        "success": "#4ADE80",
        "warning_bg": "#3A2A0B",
        "warning_fg": "#FBBF24",
        "success_bg": "#12301C",
        "error_bg": "#3B1212",
        "border": "#374151",
        "button_fg": "#F9FAFB",
    },
}


@dataclass
class AddressInfo:
    adapter: str
    ip: str


@dataclass
class ProcessInfo:
    name: str
    pid: int
    path: str
    category: str


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


def first_port_range(ports: list[dict[str, str]]) -> str:
    for port in ports:
        value = str(port.get("range", "")).strip()
        if value:
            return value
    return ""


def first_tcp_port_value(port_range: str) -> int | None:
    match = re.search(r"\d+", port_range)
    if not match:
        return None
    value = int(match.group(0))
    if 1 <= value <= 65535:
        return value
    return None


def validate_single_ipv4(value: str) -> str:
    raw = value.strip()
    if any(token in raw for token in ["/", ",", "-", " "]):
        raise ValueError("Enter one IPv4 address only. IP ranges and scans are not supported.")
    address = ipaddress.ip_address(raw)
    if address.version != 4:
        raise ValueError("Enter an IPv4 address.")
    return str(address)


def safe_extract_zip(archive: zipfile.ZipFile, target: Path) -> None:
    target_root = target.resolve()
    for member in archive.infolist():
        destination = (target / member.filename).resolve()
        if destination != target_root and target_root not in destination.parents:
            raise ValueError(f"Unsafe path in backup archive: {member.filename}")
    archive.extractall(target)


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


def process_category(name: str) -> str:
    return PROCESS_CATEGORIES.get(name.lower(), "Other")


def enumerate_processes() -> list[ProcessInfo]:
    command = (
        "Get-CimInstance Win32_Process | "
        "Select-Object Name,ProcessId,ExecutablePath | "
        "ConvertTo-Json -Compress -Depth 2"
    )
    completed = run_powershell(command, timeout=20)
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    try:
        raw = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    rows = raw if isinstance(raw, list) else [raw]
    processes: list[ProcessInfo] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("Name") or "").strip()
        if not name:
            continue
        try:
            pid = int(row.get("ProcessId") or 0)
        except (TypeError, ValueError):
            pid = 0
        raw_path = row.get("ExecutablePath")
        path = str(raw_path).strip() if raw_path else "Access denied or unavailable"
        processes.append(ProcessInfo(name=name, pid=pid, path=path, category=process_category(name)))
    processes.sort(key=lambda item: (0 if item.category != "Other" else 1, item.name.lower(), item.pid))
    return processes


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
        self.config = merge_config(load_json_file(CONFIG_FILE, DEFAULT_CONFIG))
        self.language = self.config.get("language", "en") if self.config.get("language") in TRANSLATIONS else "en"
        self.theme_name = self.config.get("theme", "light") if self.config.get("theme") in ("light", "dark", "system") else "light"
        self.ui_scale = self.config.get("ui_scale", "100%") if self.config.get("ui_scale") in UI_SCALE_VALUES else "100%"
        self.enabled_tools = dict(self.config.get("enabled_tools", {}))
        for tool_id in OPTIONAL_TOOLS:
            self.enabled_tools.setdefault(tool_id, True)
        self.hidden_tools = set(self.config.get("hidden_tools", []))
        self.favorite_games = set(self.config.get("favorite_games", []))
        self.hidden_games = set(self.config.get("hidden_games", []))
        self.manual_installed_games = set(self.config.get("manual_installed_games", []))
        self.installed_cache = dict(self.config.get("installed_cache", {}))
        self.catalog_load_error = ""
        self.detection_running = False
        self.colors = THEMES[self.effective_theme_name()]
        self.root.title(self.tr("app_title"))
        self.root.geometry("1280x820")
        self.root.minsize(1100, 720)
        self.set_window_icon()
        self.apply_tk_scaling()
        self.configure_style()

        self.builtin_games = self.load_game_catalog()
        self.custom_games = [normalize_game(game, custom=True) for game in self.config.get("custom_games", [])]
        self.games: list[dict[str, Any]] = []
        self.filtered_games: list[dict[str, Any]] = []
        self.games_all: list[dict[str, Any]] = []
        self.games_visible: list[dict[str, Any]] = []
        self.current_game: dict[str, Any] | None = None
        self.selected_game_data: dict[str, Any] | None = None
        self.current_path: str | None = None
        self.current_server_path: str | None = None
        self.game_detail_cache: dict[tuple[str, str], str] = {}
        self.installed_detection_cache: dict[str, bool] = dict(self.installed_cache)
        self.addresses: list[AddressInfo] = []
        self.main_ip = ""
        self.server_processes: dict[str, subprocess.Popen[Any]] = {}
        self.process_rows: list[ProcessInfo] = []
        self.localized_widgets: list[tuple[tk.Widget, str]] = []
        self.tab_widgets: dict[str, ttk.Frame] = {}
        self.tool_tab_map: dict[str, list[str]] = {}
        self.tool_button_map: dict[str, list[tk.Widget]] = {}
        self.action_buttons: dict[str, ttk.Button] = {}
        self.kiwi_photo: tk.PhotoImage | None = None

        self.build_ui()
        self.reload_games()
        self.refresh_network()
        self.refresh_input_processes()

    def effective_theme_name(self) -> str:
        return self.theme_name if self.theme_name in ("light", "dark") else "light"

    def tr(self, key: str) -> str:
        return TRANSLATIONS.get(self.language, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))

    def load_game_catalog(self) -> list[dict[str, Any]]:
        fallback_games = [
            {"name": "Minecraft Java Edition", "platforms": ["Windows"], "lan_status": "In-game host", "exe_names": ["javaw.exe", "MinecraftLauncher.exe"], "host_tutorial": ["Open Multiplayer and host from your installed game/server setup."], "client_tutorial": ["Use Multiplayer -> Direct Connect with HOST_LAN_IP:PORT."], "offline_notes": ["Use same game and mod version for all players."]},
            {"name": "Terraria", "platforms": ["Windows"], "lan_status": "In-game host / dedicated server", "exe_names": ["Terraria.exe"], "host_tutorial": ["Host and Play or run official server executable if installed."], "client_tutorial": ["Join via IP and port from Multiplayer menu."], "offline_notes": ["Use matching game version."]},
            {"name": "Stardew Valley", "platforms": ["Windows"], "lan_status": "Co-op host", "exe_names": ["Stardew Valley.exe"], "host_tutorial": ["Open Co-op and host farm from inside the game."], "client_tutorial": ["Join same LAN/VPN and use co-op join flow."], "offline_notes": ["Use matching game and mod setup."]},
            {"name": "Valheim", "platforms": ["Windows"], "lan_status": "In-game host / official dedicated server", "exe_names": ["valheim.exe"], "host_tutorial": ["Host from game or use official server tools."], "client_tutorial": ["Join via IP:PORT when LAN/server is reachable."], "offline_notes": ["Use matching game version and world setup."]},
        ]
        try:
            raw_games = load_json_file(GAMES_FILE, [])
        except Exception as exc:
            self.catalog_load_error = f"{self.tr('games_json_error')} {exc}"
            return [normalize_game(game) for game in fallback_games]
        if not isinstance(raw_games, list):
            self.catalog_load_error = self.tr("games_json_error")
            return [normalize_game(game) for game in fallback_games]
        self.catalog_load_error = ""
        return [normalize_game(game) for game in raw_games if isinstance(game, dict)]

    def ui_scale_multiplier(self) -> float:
        try:
            return int(str(self.ui_scale).rstrip("%")) / 100
        except ValueError:
            return 1.0

    def scaled_font(self, size: int, weight: str | None = None) -> tuple[Any, ...]:
        scaled_size = max(8, int(round(size * self.ui_scale_multiplier())))
        return ("Segoe UI", scaled_size, weight) if weight else ("Segoe UI", scaled_size)

    def apply_tk_scaling(self) -> None:
        try:
            self.root.tk.call("tk", "scaling", 1.0 * self.ui_scale_multiplier())
        except tk.TclError:
            pass

    def is_tool_enabled(self, tool_id: str) -> bool:
        return bool(self.enabled_tools.get(tool_id, True))

    def is_tool_visible(self, tool_id: str) -> bool:
        return self.is_tool_enabled(tool_id) and tool_id not in self.hidden_tools

    def set_window_icon(self) -> None:
        try:
            if WINDOW_ICON_PATH.exists():
                self.root.iconbitmap(str(WINDOW_ICON_PATH))
        except tk.TclError:
            pass

    def configure_style(self) -> None:
        self.colors = THEMES[self.effective_theme_name()]
        self.root.configure(bg=self.colors["bg"])
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.apply_tk_scaling()
        base_font = self.scaled_font(11)
        heading_font = self.scaled_font(13, "bold")
        self.root.option_add("*Font", base_font)
        self.root.option_add("*TCombobox*Listbox.font", base_font)
        self.style.configure(".", font=base_font, background=self.colors["bg"], foreground=self.colors["text"])
        self.style.configure("TFrame", background=self.colors["bg"])
        self.style.configure("Card.TFrame", background=self.colors["panel"], relief="flat")
        self.style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"])
        self.style.configure("Muted.TLabel", background=self.colors["bg"], foreground=self.colors["muted"])
        self.style.configure("Warning.TLabel", background=self.colors["warning_bg"], foreground=self.colors["warning_fg"], padding=8)
        self.style.configure("Success.TLabel", background=self.colors["success_bg"], foreground=self.colors["success"], padding=8)
        self.style.configure("Error.TLabel", background=self.colors["error_bg"], foreground=self.colors["error"], padding=8)
        self.style.configure("TLabelFrame", background=self.colors["bg"], foreground=self.colors["text"], bordercolor=self.colors["border"])
        self.style.configure("TLabelFrame.Label", background=self.colors["bg"], foreground=self.colors["accent_dark"], font=heading_font)
        self.style.configure("TButton", padding=(12, 8), background=self.colors["panel_alt"], foreground=self.colors["button_fg"], bordercolor=self.colors["border"])
        self.style.map("TButton", background=[("active", self.colors["accent"]), ("pressed", self.colors["accent_dark"])], foreground=[("active", "#ffffff"), ("pressed", "#ffffff")])
        self.style.configure("Accent.TButton", padding=(12, 8), background=self.colors["accent"], foreground="#ffffff")
        self.style.map("Accent.TButton", background=[("active", self.colors["accent_dark"]), ("pressed", self.colors["accent_dark"])], foreground=[("active", "#ffffff")])
        self.style.configure("TCheckbutton", background=self.colors["bg"], foreground=self.colors["text"])
        self.style.configure("TRadiobutton", background=self.colors["bg"], foreground=self.colors["text"])
        self.style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", padding=(12, 7), background=self.colors["panel_alt"], foreground=self.colors["text"])
        self.style.map("TNotebook.Tab", background=[("selected", self.colors["panel"])], foreground=[("selected", self.colors["accent_dark"])])
        self.style.layout("Hidden.TNotebook.Tab", [])
        self.style.configure("Hidden.TNotebook", background=self.colors["bg"], borderwidth=0)
        self.style.configure("Treeview", background=self.colors["panel"], fieldbackground=self.colors["panel"], foreground=self.colors["text"], rowheight=max(28, int(28 * self.ui_scale_multiplier())), bordercolor=self.colors["border"])
        self.style.configure("Treeview.Heading", background=self.colors["panel_alt"], foreground=self.colors["text"], font=self.scaled_font(11, "bold"))

    def style_text_widget(self, widget: tk.Text, *, height: int | None = None) -> None:
        if height is not None:
            widget.configure(height=height)
        widget.configure(
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            selectbackground=self.colors["accent"],
            selectforeground="#ffffff",
            relief=tk.SOLID,
            bd=1,
            padx=10,
            pady=8,
            font=self.scaled_font(11),
        )

    def localize_widget(self, widget: tk.Widget, key: str) -> tk.Widget:
        try:
            widget.configure(text=self.tr(key))
        except tk.TclError:
            pass
        self.localized_widgets.append((widget, key))
        return widget

    def build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(12, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        title_frame = ttk.Frame(header)
        title_frame.grid(row=0, column=0, sticky="w")
        if KIWI_LOGO_PATH.exists():
            try:
                self.kiwi_photo = tk.PhotoImage(file=str(KIWI_LOGO_PATH)).subsample(8, 8)
                ttk.Label(title_frame, image=self.kiwi_photo).grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 10))
            except tk.TclError:
                self.kiwi_photo = None
        self.title_label = ttk.Label(title_frame, text=self.tr("app_title"), font=self.scaled_font(18, "bold"))
        self.title_label.grid(row=0, column=1, sticky="w")
        ttk.Label(title_frame, text=f"v{APP_VERSION}  |  Created by KiwiLiu", style="Muted.TLabel").grid(row=1, column=1, sticky="w")
        self.settings_header_button = ttk.Button(title_frame, text=self.tr("settings"), command=lambda: self.run_ui_action("Open Settings", self.show_settings))
        self.settings_header_button.grid(row=0, column=2, rowspan=2, sticky="ns", padx=(14, 0))
        self.safety_label = ttk.Label(header, text=self.tr("safety_warning"), style="Warning.TLabel", wraplength=760)
        if bool(self.config.get("show_safety_warnings", True)):
            self.safety_label.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.offline_mode_var = tk.BooleanVar(value=bool(self.config.get("offline_mode", False)))
        self.offline_check = ttk.Checkbutton(
            header,
            text=self.tr("offline_mode"),
            variable=self.offline_mode_var,
            command=lambda: self.run_ui_action("Toggle Offline Mode", self.toggle_offline_mode),
        )
        self.offline_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        network = ttk.LabelFrame(header, text=self.tr("host_network"), padding=8)
        self.host_network_frame = network
        network.grid(row=0, column=1, rowspan=3, sticky="ew", padx=(16, 0))
        network.grid_columnconfigure(1, weight=1)
        self.hostname_var = tk.StringVar(value="Hostname:")
        self.main_ip_var = tk.StringVar(value="Primary LAN IPv4:")
        self.adapter_var = tk.StringVar(value="Adapter:")
        self.network_warning_var = tk.StringVar(value="")
        ttk.Label(network, textvariable=self.hostname_var).grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(network, textvariable=self.main_ip_var).grid(row=0, column=1, sticky="w", padx=(0, 12))
        ttk.Label(network, textvariable=self.adapter_var).grid(row=0, column=2, sticky="w")
        self.selected_ip_label = ttk.Label(network, text=self.tr("selected_ip"))
        self.selected_ip_label.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.ip_combo = ttk.Combobox(network, state="readonly", width=56)
        self.ip_combo.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(6, 0))
        self.ip_combo.bind("<<ComboboxSelected>>", lambda _event: self.update_all_tabs())
        ttk.Label(network, textvariable=self.network_warning_var, style="Warning.TLabel").grid(row=2, column=0, columnspan=3, sticky="ew", pady=(5, 0))

        body = ttk.Frame(self.root, padding=(10, 0, 10, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        sidebar = ttk.Frame(body, padding=(0, 0, 10, 0))
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar_frame = sidebar
        self.sidebar_buttons: dict[str, ttk.Button] = {}
        self.sidebar_page_map: dict[str, str] = {}
        self.current_page = "Home"

        nav_items = [
            ("home", "Home", "Home"),
            ("games", "Games", "Games"),
            ("invite_export", "Invite", "Invite"),
            ("server_tools", "Server Tools", "Server Tools"),
            ("lan_test", "LAN Test", "LAN Test"),
            ("firewall_helper", "Firewall", "Firewall / Permissions"),
            ("controller_tools", "Controller Tools", "Input Isolation"),
            ("backup_tools", "Backups", "Backups"),
            ("troubleshooting", "Troubleshooting", "Troubleshooting"),
            ("core", "Settings", "Settings"),
            ("support", "Support", "Support"),
            ("core", "Privacy", "Privacy"),
        ]
        for row, (tool_id, label, page_name) in enumerate(nav_items):
            button = ttk.Button(sidebar, text=label, command=lambda p=page_name: self.show_page(p))
            button.grid(row=row, column=0, sticky="ew", pady=2)
            self.sidebar_buttons[page_name] = button
            self.sidebar_page_map[page_name] = tool_id
        self.creator_label = ttk.Label(sidebar, text=self.tr("creator_line"), style="Muted.TLabel")
        self.creator_label.grid(row=len(nav_items), column=0, sticky="w", pady=(10, 0))

        content = ttk.Frame(body)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self.tabs = ttk.Notebook(content, style="Hidden.TNotebook")
        self.tabs.grid(row=0, column=0, sticky="nsew")
        self.add_home_tab()
        self.add_games_tab()
        self.tutorial_text = self.add_text_tab("Tutorial")
        self.network_text = self.add_text_tab("Network / IP")
        self.firewall_text = self.add_text_tab("Firewall / Permissions")
        self.path_text = self.add_text_tab("Game Path")
        self.server_text = self.add_server_tools_tab()
        self.add_lan_test_tab()
        self.add_invite_tab()
        self.add_backup_tab()
        self.add_mods_tab()
        self.add_input_isolation_tab()
        self.add_input_isolation_setup_tab()
        self.troubleshooting_text = self.add_text_tab("Troubleshooting")
        self.add_settings_tab()
        self.add_support_tab()
        self.privacy_text = self.add_text_tab("Privacy")
        self.tool_tab_map = {
            "firewall_helper": ["Firewall / Permissions"],
            "server_tools": ["Server Tools"],
            "lan_test": ["LAN Test"],
            "invite_export": ["Invite"],
            "backup_tools": ["Backups"],
            "controller_tools": ["Input Isolation", "Input Isolation Setup"],
            "input_isolation": ["Input Isolation", "Input Isolation Setup"],
            "support": ["Support"],
        }
        self.server_buttons: dict[str, ttk.Button] = {}
        self.add_server_button("Open Server Folder", self.open_server_folder, 0)
        self.add_server_button("Select Server Executable", self.select_server_executable, 1)
        self.add_server_button("Launch Server", self.launch_server, 2)
        self.add_server_button("Start Server", self.start_managed_server, 3)
        self.add_server_button("Stop Server", self.stop_managed_server, 4)
        self.add_server_button("Open Server Log", self.open_server_log, 5)
        self.add_server_button("Install with SteamCMD", self.install_with_steamcmd, 6)
        self.add_server_button("Open Official Download Page", self.open_official_download_page, 7)
        self.add_server_button("Export Server Guide", self.export_server_guide, 8)
        self.add_server_button("Select SteamCMD", self.select_steamcmd, 9)

        self.actions_frame = self.game_actions_frame
        self.add_action_button(self.game_actions_frame, "Refresh IP", self.refresh_network, 0)
        self.add_action_button(self.game_actions_frame, "Copy Host IP", self.copy_host_ip, 1)
        self.add_action_button(self.game_actions_frame, "Detect Game Path", self.detect_game_path, 2)
        self.add_action_button(self.game_actions_frame, "Manual Select Game", self.select_game_exe, 3)
        self.add_action_button(self.game_actions_frame, "Launch Game", self.launch_game, 4)
        self.add_action_button(self.game_actions_frame, "Add Firewall Rules", self.add_firewall_rules, 5)
        self.add_action_button(self.game_actions_frame, "Remove Firewall Rules", self.remove_firewall_rules, 6)
        self.add_action_button(self.game_actions_frame, "Export Tutorial", self.export_tutorial, 7)
        self.tool_button_map = {
            "firewall_helper": [
                self.action_buttons["Add Firewall Rules"],
                self.action_buttons["Remove Firewall Rules"],
            ],
            "custom_games": [self.add_custom_button],
        }

        log_frame = ttk.LabelFrame(self.root, text=self.tr("log_status"), padding=6)
        self.log_frame = log_frame
        log_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        log_frame.grid_columnconfigure(0, weight=1)
        header_row = ttk.Frame(log_frame)
        header_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        header_row.grid_columnconfigure(0, weight=1)
        self.log_toggle_button = ttk.Button(header_row, text=self.tr("hide_log"), command=self.toggle_log_visibility)
        self.log_toggle_button.grid(row=0, column=1, sticky="e")
        self.log_box = tk.Text(log_frame, height=5, wrap=tk.WORD)
        self.log_box.grid(row=1, column=0, sticky="ew")
        self.style_text_widget(self.log_box, height=5)
        self.log_box.configure(state=tk.DISABLED)
        self.clear_log_button = ttk.Button(log_frame, text=self.tr("clear_log"), command=self.clear_log)
        self.clear_log_button.grid(row=1, column=1, sticky="ns", padx=(8, 0))
        self.log_visible = True

        self.apply_tool_visibility()
        self.show_page("Home")
        self.apply_language()

    def add_home_tab(self) -> None:
        frame = ttk.Frame(self.tabs, padding=12)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        ttk.Label(frame, text="Home", font=self.scaled_font(16, "bold")).grid(row=0, column=0, sticky="w")
        self.home_text = tk.Text(frame, wrap=tk.WORD, height=16)
        self.home_text.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.style_text_widget(self.home_text, height=16)
        self.home_text.configure(state=tk.DISABLED)
        self.tabs.add(frame, text="Home")
        self.tab_widgets["Home"] = frame

    def add_games_tab(self) -> None:
        frame = ttk.Frame(self.tabs, padding=10)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(2, weight=1)
        ttk.Label(frame, text="Games", font=self.scaled_font(16, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")

        left = ttk.Frame(frame, padding=(0, 8, 12, 0))
        left.grid(row=1, column=0, rowspan=2, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(5, weight=1)
        self.search_label = ttk.Label(left, text=self.tr("search"))
        self.search_label.grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.apply_filter())
        search_row = ttk.Frame(left)
        search_row.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        search_row.grid_columnconfigure(0, weight=1)
        ttk.Entry(search_row, textvariable=self.search_var).grid(row=0, column=0, sticky="ew")
        self.clear_search_button = ttk.Button(search_row, text=self.tr("clear_search"), command=lambda: self.search_var.set(""))
        self.clear_search_button.grid(row=0, column=1, padx=(6, 0))
        self.filter_label = ttk.Label(left, text=self.tr("default_filter"))
        self.filter_label.grid(row=2, column=0, sticky="w")
        self.game_filter_var = tk.StringVar(value=str(self.config.get("default_game_filter", "all")))
        filter_row = ttk.Frame(left)
        filter_row.grid(row=3, column=0, sticky="ew", pady=(4, 8))
        for column in range(5):
            filter_row.grid_columnconfigure(column, weight=1)
        self.filter_buttons: dict[str, ttk.Button] = {}
        quick_filters = ["all", "installed", "favorites", "dedicated_server", "in_game_host"]
        for column, filter_id in enumerate(quick_filters):
            button = ttk.Button(
                filter_row,
                text=self.filter_label_for_key(filter_id),
                command=lambda value=filter_id: self.set_game_filter(value),
            )
            button.grid(row=0, column=column, sticky="ew", padx=2)
            self.filter_buttons[filter_id] = button
        self.update_filter_buttons_visual()
        refresh_row = ttk.Frame(left)
        refresh_row.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        refresh_row.grid_columnconfigure(0, weight=1)
        refresh_row.grid_columnconfigure(1, weight=1)
        self.refresh_games_button = ttk.Button(refresh_row, text=self.tr("refresh_games"), command=lambda: self.run_ui_action("Refresh Games", self.refresh_games))
        self.refresh_games_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.refresh_detection_button = ttk.Button(refresh_row, text=self.tr("refresh_installed_detection"), command=lambda: self.run_ui_action("Refresh Installed Detection", self.refresh_installed_detection))
        self.refresh_detection_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        list_frame = ttk.Frame(left)
        list_frame.grid(row=5, column=0, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        self.game_list = tk.Listbox(
            list_frame,
            exportselection=False,
            activestyle="dotbox",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            selectbackground=self.colors["accent"],
            selectforeground="#ffffff",
            highlightcolor=self.colors["accent"],
            highlightbackground=self.colors["border"],
            relief=tk.SOLID,
            bd=1,
            font=self.scaled_font(12),
        )
        self.game_list.grid(row=0, column=0, sticky="nsew")
        game_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.game_list.yview)
        game_scroll.grid(row=0, column=1, sticky="ns")
        self.game_list.configure(yscrollcommand=game_scroll.set)
        self.game_list.bind("<<ListboxSelect>>", self.on_game_selected)
        self.add_custom_button = ttk.Button(left, text=self.tr("add_custom_game"), style="Accent.TButton", command=lambda: self.run_ui_action("Add Custom Game", self.add_custom_game_dialog))
        self.add_custom_button.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        self.game_status_var = tk.StringVar(value="")
        self.game_status_label = ttk.Label(left, textvariable=self.game_status_var, style="Muted.TLabel", wraplength=290)
        self.game_status_label.grid(row=7, column=0, sticky="ew", pady=(6, 0))

        right = ttk.Frame(frame, padding=(8, 8, 0, 0))
        right.grid(row=1, column=1, rowspan=2, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)
        self.games_page_title = ttk.Label(right, text="Selected game details", font=self.scaled_font(14, "bold"))
        self.games_page_title.grid(row=0, column=0, sticky="w")
        self.game_actions_frame = ttk.LabelFrame(right, text=self.tr("actions"), padding=6)
        self.game_actions_frame.grid(row=1, column=0, sticky="ew", pady=(8, 8))
        for column in range(8):
            self.game_actions_frame.grid_columnconfigure(column, weight=1, uniform="actions")
        self.games_detail_text = tk.Text(right, wrap=tk.WORD)
        self.games_detail_text.grid(row=2, column=0, sticky="nsew")
        self.style_text_widget(self.games_detail_text, height=24)
        self.games_detail_text.configure(state=tk.DISABLED)

        self.tabs.add(frame, text="Games")
        self.tab_widgets["Games"] = frame

    def show_page(self, page_name: str) -> None:
        frame = self.tab_widgets.get(page_name)
        if frame is None:
            return
        self.tabs.select(frame)
        self.current_page = page_name
        for name, button in self.sidebar_buttons.items():
            if name == page_name:
                button.configure(style="Accent.TButton")
            else:
                button.configure(style="TButton")

    def toggle_log_visibility(self) -> None:
        self.log_visible = not self.log_visible
        if self.log_visible:
            self.log_box.grid()
            self.clear_log_button.grid()
            self.log_toggle_button.configure(text=self.tr("hide_log"))
        else:
            self.log_box.grid_remove()
            self.clear_log_button.grid_remove()
            self.log_toggle_button.configure(text=self.tr("show_log"))

    def add_text_tab(self, title: str) -> tk.Text:
        frame = ttk.Frame(self.tabs, padding=8)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        text = tk.Text(frame, wrap=tk.WORD)
        text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.style_text_widget(text)
        text.configure(yscrollcommand=scroll.set, state=tk.DISABLED)
        self.tabs.add(frame, text=title)
        self.tab_widgets[title] = frame
        return text

    def add_server_tools_tab(self) -> tk.Text:
        frame = ttk.Frame(self.tabs, padding=8)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        text = tk.Text(frame, wrap=tk.WORD)
        text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.style_text_widget(text)
        text.configure(yscrollcommand=scroll.set, state=tk.DISABLED)

        self.server_buttons_frame = ttk.Frame(frame, padding=(0, 8, 0, 0))
        self.server_buttons_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        for column in range(6):
            self.server_buttons_frame.grid_columnconfigure(column, weight=1, uniform="server")

        self.tabs.add(frame, text="Server Tools")
        self.tab_widgets["Server Tools"] = frame
        return text

    def add_lan_test_tab(self) -> None:
        frame = ttk.Frame(self.tabs, padding=10)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(5, weight=1)
        ttk.Label(frame, text="LAN Test / Connection Test", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text="Tests one user-entered or selected IP only. This is not a network scanner.").grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 10))
        ttk.Label(frame, text="Target IP").grid(row=2, column=0, sticky="w", pady=4)
        self.lan_test_ip_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.lan_test_ip_var).grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Button(frame, text="Use Selected Host IP", command=lambda: self.run_ui_action("Use Selected Host IP", self.use_selected_ip_for_test)).grid(row=2, column=2, sticky="ew", padx=(8, 0), pady=4)
        ttk.Label(frame, text="TCP Port").grid(row=3, column=0, sticky="w", pady=4)
        self.lan_test_port_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.lan_test_port_var).grid(row=3, column=1, sticky="ew", pady=4)
        ttk.Button(frame, text="Use Game Default Port", command=lambda: self.run_ui_action("Use Game Default Port", self.use_default_port_for_test)).grid(row=3, column=2, sticky="ew", padx=(8, 0), pady=4)
        controls = ttk.Frame(frame)
        controls.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 8))
        ttk.Button(controls, text="Ping IP", command=lambda: self.run_ui_action("Ping IP", self.ping_test)).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(controls, text="Test TCP Port", command=lambda: self.run_ui_action("Test TCP Port", self.tcp_port_test)).grid(row=0, column=1, padx=(0, 6))
        self.lan_test_result = tk.Text(frame, wrap=tk.WORD, height=14)
        self.lan_test_result.grid(row=5, column=0, columnspan=3, sticky="nsew")
        self.style_text_widget(self.lan_test_result, height=14)
        self.lan_test_result.configure(state=tk.DISABLED)
        self.tabs.add(frame, text="LAN Test")
        self.tab_widgets["LAN Test"] = frame

    def add_invite_tab(self) -> None:
        frame = ttk.Frame(self.tabs, padding=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)
        ttk.Label(frame, text="Invite Export", font=self.scaled_font(12, "bold")).grid(row=0, column=0, sticky="w")
        form = ttk.LabelFrame(frame, text="Connection Info", padding=8)
        form.grid(row=1, column=0, sticky="ew", pady=(8, 8))
        for column in range(4):
            form.grid_columnconfigure(column, weight=1)
        self.invite_host_ip_var = tk.StringVar()
        self.invite_port_var = tk.StringVar()
        self.invite_password_var = tk.StringVar()
        self.invite_lan_mode_var = tk.StringVar(value="LAN")
        self.invite_mode_var = tk.StringVar(value=self.invite_mode_label_for_key(str(self.config.get("default_invite_mode", "short"))))
        ttk.Label(form, text="Host IP").grid(row=0, column=0, sticky="w")
        self.invite_ip_combo = ttk.Combobox(form, textvariable=self.invite_host_ip_var)
        self.invite_ip_combo.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(2, 8))
        ttk.Label(form, text="Port").grid(row=0, column=1, sticky="w")
        self.invite_port_combo = ttk.Combobox(form, textvariable=self.invite_port_var)
        self.invite_port_combo.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=(2, 8))
        ttk.Label(form, text=self.tr("server_password")).grid(row=0, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.invite_password_var, show="*").grid(row=1, column=2, sticky="ew", padx=(0, 6), pady=(2, 8))
        ttk.Label(form, text=self.tr("lan_vpn_mode")).grid(row=0, column=3, sticky="w")
        ttk.Combobox(form, textvariable=self.invite_lan_mode_var, values=["LAN", "VPN LAN", "Local server"], state="readonly").grid(row=1, column=3, sticky="ew", pady=(2, 8))
        self.invite_mode_label = ttk.Label(form, text=self.tr("invite_mode"))
        self.invite_mode_label.grid(row=2, column=0, sticky="w")
        self.invite_mode_combo = ttk.Combobox(form, textvariable=self.invite_mode_var, values=self.invite_mode_display_values(), state="readonly")
        self.invite_mode_combo.grid(row=3, column=0, sticky="ew", padx=(0, 6))
        self.invite_mode_combo.bind("<<ComboboxSelected>>", lambda _event: self.update_invite_tab())
        ttk.Button(form, text="Use Selected Host IP", command=lambda: self.run_ui_action("Use Selected Host IP", self.use_selected_ip_for_invite)).grid(row=3, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(form, text="Use Game Default Port", command=lambda: self.run_ui_action("Use Game Default Port", self.use_default_port_for_invite)).grid(row=3, column=2, sticky="ew", padx=(0, 6))
        ttk.Button(form, text="Refresh Invite", command=lambda: self.run_ui_action("Refresh Invite", self.update_invite_tab)).grid(row=3, column=3, sticky="ew")
        controls = ttk.Frame(frame)
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        for column in range(5):
            controls.grid_columnconfigure(column, weight=1)
        ttk.Button(controls, text=self.tr("copy_invite"), command=lambda: self.run_ui_action("Copy Invite", self.copy_invite)).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(controls, text=self.tr("export_invite"), command=lambda: self.run_ui_action("Export Invite", self.export_invite)).grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ttk.Button(controls, text=self.tr("copy_ip_only"), command=lambda: self.run_ui_action("Copy IP Only", self.copy_invite_ip_only)).grid(row=0, column=2, sticky="ew", padx=(0, 5))
        ttk.Button(controls, text=self.tr("copy_ip_port_only"), command=lambda: self.run_ui_action("Copy IP:Port Only", self.copy_invite_ip_port_only)).grid(row=0, column=3, sticky="ew", padx=(0, 5))
        ttk.Button(controls, text=self.tr("copy_join_address"), command=lambda: self.run_ui_action("Copy Join Address", self.copy_join_address)).grid(row=0, column=4, sticky="ew")
        self.invite_text = tk.Text(frame, wrap=tk.WORD, height=18)
        self.invite_text.grid(row=3, column=0, sticky="nsew")
        self.style_text_widget(self.invite_text, height=18)
        self.invite_text.configure(state=tk.DISABLED)
        self.tabs.add(frame, text="Invite")
        self.tab_widgets["Invite"] = frame

    def add_backup_tab(self) -> None:
        frame = ttk.Frame(self.tabs, padding=10)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(4, weight=1)
        ttk.Label(frame, text="World / Save Backup", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text="Select a save folder, create timestamped zip backups, and restore only after confirmation.").grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 10))
        ttk.Label(frame, text="Save folder").grid(row=2, column=0, sticky="w")
        self.save_folder_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.save_folder_var).grid(row=2, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(frame, text="Select Save Folder", command=lambda: self.run_ui_action("Select Save Folder", self.select_save_folder)).grid(row=2, column=2, sticky="ew")
        controls = ttk.Frame(frame)
        controls.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 8))
        ttk.Button(controls, text="Create Backup", command=lambda: self.run_ui_action("Create Backup", self.create_save_backup)).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(controls, text="Restore Backup", command=lambda: self.run_ui_action("Restore Backup", self.restore_save_backup)).grid(row=0, column=1, padx=(0, 6))
        self.backup_text = tk.Text(frame, wrap=tk.WORD, height=12)
        self.backup_text.grid(row=4, column=0, columnspan=3, sticky="nsew")
        self.style_text_widget(self.backup_text, height=12)
        self.backup_text.configure(state=tk.DISABLED)
        self.tabs.add(frame, text="Backups")
        self.tab_widgets["Backups"] = frame

    def add_mods_tab(self) -> None:
        frame = ttk.Frame(self.tabs, padding=10)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(4, weight=1)
        ttk.Label(frame, text="Mod List Export", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text="Export mod file names so players can compare matching mod setups. This app does not download mods.").grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 10))
        ttk.Label(frame, text="Mods folder").grid(row=2, column=0, sticky="w")
        self.mod_folder_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.mod_folder_var).grid(row=2, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(frame, text="Select Mods Folder", command=lambda: self.run_ui_action("Select Mods Folder", self.select_mod_folder)).grid(row=2, column=2, sticky="ew")
        ttk.Button(frame, text="Export Mod List", command=lambda: self.run_ui_action("Export Mod List", self.export_mod_list)).grid(row=3, column=0, sticky="w", pady=(10, 8))
        self.mods_text = tk.Text(frame, wrap=tk.WORD, height=12)
        self.mods_text.grid(row=4, column=0, columnspan=3, sticky="nsew")
        self.style_text_widget(self.mods_text, height=12)
        self.mods_text.configure(state=tk.DISABLED)
        self.tabs.add(frame, text="Mods")
        self.tab_widgets["Mods"] = frame

    def add_input_isolation_tab(self) -> None:
        frame = ttk.Frame(self.tabs, padding=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        ttk.Label(frame, text="Input Isolation Helper", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            frame,
            text="Windows-only local/offline/LAN guidance for Nucleus Co-op, DS4Windows, HidHide, Prism Launcher, and Minecraft Java. No input blocking is applied by this app.",
            style="Warning.TLabel",
            wraplength=980,
            justify=tk.LEFT,
        ).grid(row=0, column=1, sticky="ew", padx=(12, 0))

        notebook = ttk.Notebook(frame)
        notebook.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        self.input_isolation_tabs = notebook

        processes = ttk.Frame(notebook, padding=8)
        processes.grid_columnconfigure(0, weight=1)
        processes.grid_rowconfigure(0, weight=1)
        columns = ("name", "pid", "path", "category")
        self.input_process_tree = ttk.Treeview(processes, columns=columns, show="headings", selectmode="browse")
        for column, heading, width in [
            ("name", "Process name", 180),
            ("pid", "PID", 80),
            ("path", "Executable path", 520),
            ("category", "Type/category", 190),
        ]:
            self.input_process_tree.heading(column, text=heading)
            self.input_process_tree.column(column, width=width, anchor=tk.W if column != "pid" else tk.CENTER)
        self.input_process_tree.grid(row=0, column=0, sticky="nsew")
        process_scroll = ttk.Scrollbar(processes, orient=tk.VERTICAL, command=self.input_process_tree.yview)
        process_scroll.grid(row=0, column=1, sticky="ns")
        self.input_process_tree.configure(yscrollcommand=process_scroll.set)
        self.input_process_tree.bind("<<TreeviewSelect>>", lambda _event: self.load_selected_process_into_notes())
        process_buttons = ttk.Frame(processes)
        process_buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        for column in range(7):
            process_buttons.grid_columnconfigure(column, weight=1, uniform="process_buttons")
        for index, (label, callback) in enumerate(
            [
                ("Refresh Processes", self.refresh_input_processes),
                ("Copy Selected Process Info", self.copy_selected_process_info),
                ("Open File Location", self.open_selected_process_location),
                ("Add Process to Notes", self.add_selected_process_to_notes),
                ("Mark as Game Instance", lambda: self.mark_selected_process_role("Game Instance")),
                ("Mark as Controller Mapper", lambda: self.mark_selected_process_role("Controller Mapper")),
                ("Mark as Launcher", lambda: self.mark_selected_process_role("Launcher")),
            ]
        ):
            ttk.Button(process_buttons, text=label, command=lambda text=label, cb=callback: self.run_ui_action(text, cb)).grid(row=0, column=index, sticky="ew", padx=3, pady=3)
        notebook.add(processes, text="Running Processes")

        notes = ttk.Frame(notebook, padding=8)
        notes.grid_columnconfigure(1, weight=1)
        notes.grid_rowconfigure(8, weight=1)
        self.input_selected_process_var = tk.StringVar(value="Selected process: none")
        self.input_role_var = tk.StringVar()
        self.input_keyboard_var = tk.BooleanVar(value=False)
        self.input_controller_var = tk.BooleanVar(value=False)
        self.input_ignore_ps_var = tk.BooleanVar(value=False)
        self.input_virtual_xbox_var = tk.BooleanVar(value=False)
        ttk.Label(notes, textvariable=self.input_selected_process_var).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(notes, text="Role").grid(row=1, column=0, sticky="w", pady=(8, 4))
        ttk.Entry(notes, textvariable=self.input_role_var).grid(row=1, column=1, columnspan=2, sticky="ew", pady=(8, 4))
        ttk.Checkbutton(notes, text="Should receive keyboard/mouse", variable=self.input_keyboard_var).grid(row=2, column=1, sticky="w")
        ttk.Checkbutton(notes, text="Should receive controller", variable=self.input_controller_var).grid(row=3, column=1, sticky="w")
        ttk.Checkbutton(notes, text="Should ignore real PlayStation controller", variable=self.input_ignore_ps_var).grid(row=4, column=1, sticky="w")
        ttk.Checkbutton(notes, text="Should use virtual Xbox controller", variable=self.input_virtual_xbox_var).grid(row=5, column=1, sticky="w")
        ttk.Label(notes, text="Notes").grid(row=6, column=0, sticky="nw", pady=(8, 4))
        self.input_notes_text = tk.Text(notes, height=5, wrap=tk.WORD)
        self.input_notes_text.grid(row=6, column=1, columnspan=2, sticky="nsew", pady=(8, 4))
        self.style_text_widget(self.input_notes_text, height=5)
        note_buttons = ttk.Frame(notes)
        note_buttons.grid(row=7, column=1, columnspan=2, sticky="ew", pady=(6, 8))
        ttk.Button(note_buttons, text="Save Process Note", command=lambda: self.run_ui_action("Save Process Note", self.save_input_process_note)).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(note_buttons, text="Delete Selected Note", command=lambda: self.run_ui_action("Delete Selected Note", self.delete_selected_input_note)).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(note_buttons, text="Copy All Notes", command=lambda: self.run_ui_action("Copy All Notes", self.copy_all_input_notes)).grid(row=0, column=2, padx=(0, 6))
        self.input_notes_tree = ttk.Treeview(notes, columns=("process", "pid", "role", "input"), show="headings", selectmode="browse")
        for column, heading, width in [
            ("process", "Process", 180),
            ("pid", "PID", 80),
            ("role", "Role", 200),
            ("input", "Input notes", 520),
        ]:
            self.input_notes_tree.heading(column, text=heading)
            self.input_notes_tree.column(column, width=width, anchor=tk.W if column != "pid" else tk.CENTER)
        self.input_notes_tree.grid(row=8, column=0, columnspan=3, sticky="nsew")
        self.input_notes_tree.bind("<<TreeviewSelect>>", lambda _event: self.load_selected_input_note())
        notebook.add(notes, text="Per-Process Notes")

        tools = ttk.Frame(notebook, padding=8)
        tools.grid_columnconfigure(0, weight=1)
        tools.grid_rowconfigure(0, weight=1)
        self.input_tools_text = tk.Text(tools, wrap=tk.WORD)
        self.input_tools_text.grid(row=0, column=0, sticky="nsew")
        self.style_text_widget(self.input_tools_text)
        self.input_tools_text.configure(state=tk.DISABLED)
        tools_buttons = ttk.Frame(tools)
        tools_buttons.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        for column in range(4):
            tools_buttons.grid_columnconfigure(column, weight=1, uniform="input_tools")
        buttons = [
            ("Check HidHide Installed", self.check_hidhide_installed),
            ("Open HidHide Configuration Client", self.open_hidhide_client),
            ("Open HidHide Official Page", lambda: self.open_official_input_tool_page(HIDHIDE_OFFICIAL_URL)),
            ("Copy HidHide Setup Checklist", lambda: self.copy_text_to_clipboard("HidHide setup checklist", HIDHIDE_CHECKLIST)),
            ("Select DS4Windows.exe", self.select_ds4windows_exe),
            ("Open DS4Windows", self.open_ds4windows),
            ("Copy DS4Windows Xbox Output Checklist", lambda: self.copy_text_to_clipboard("DS4Windows checklist", DS4WINDOWS_CHECKLIST)),
            ("Open DS4Windows Official Page", lambda: self.open_official_input_tool_page(DS4WINDOWS_OFFICIAL_URL)),
            ("Open Windows Game Controllers", self.open_windows_game_controllers),
            ("Copy Minecraft / Nucleus Checklist", lambda: self.copy_text_to_clipboard("Minecraft / Nucleus checklist", MINECRAFT_NUCLEUS_CHECKLIST)),
        ]
        for index, (label, callback) in enumerate(buttons):
            row, column = divmod(index, 4)
            ttk.Button(tools_buttons, text=label, command=lambda text=label, cb=callback: self.run_ui_action(text, cb)).grid(row=row, column=column, sticky="ew", padx=3, pady=3)
        notebook.add(tools, text="Tools / Checklists")

        advanced = ttk.Frame(notebook, padding=8)
        advanced.grid_columnconfigure(0, weight=1)
        self.input_advanced_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            advanced,
            text="Show Advanced Mode instructions",
            variable=self.input_advanced_var,
            command=self.toggle_input_advanced_text,
        ).grid(row=0, column=0, sticky="w")
        self.input_advanced_text = tk.Text(advanced, height=12, wrap=tk.WORD)
        self.input_advanced_text.insert(
            "1.0",
            "Advanced Mode only generates instructions. It does not apply input blocking automatically.\n\n"
            "Do not use pywinhook, interception drivers, low-level keyboard hooks, mouse hooks, DLL injection, "
            "or anti-cheat bypass methods. Real per-process input assignment should be handled by Nucleus Co-op "
            "or official/safe external tools such as HidHide and DS4Windows.",
        )
        self.input_advanced_text.configure(state=tk.DISABLED)
        self.style_text_widget(self.input_advanced_text, height=12)
        self.input_advanced_text.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.input_advanced_text.grid_remove()
        notebook.add(advanced, text="Advanced")

        self.tabs.add(frame, text="Input Isolation")
        self.tab_widgets["Input Isolation"] = frame

    def add_input_isolation_setup_tab(self) -> None:
        frame = ttk.Frame(self.tabs, padding=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)
        ttk.Label(frame, text="Input Isolation Setup", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            frame,
            text="Real setup automation is limited to opening safe external tools and saving local profiles. This app does not perform direct per-process input blocking.",
            style="Warning.TLabel",
            wraplength=980,
            justify=tk.LEFT,
        ).grid(row=1, column=0, sticky="ew", pady=(2, 8))

        status = ttk.LabelFrame(frame, text="Tool Status", padding=8)
        status.grid(row=2, column=0, sticky="ew")
        status.grid_columnconfigure(1, weight=1)
        self.ds4_status_var = tk.StringVar(value="DS4Windows.exe: not configured")
        self.hidhide_status_var = tk.StringVar(value="HidHideClient.exe: not detected")
        self.hidhide_cli_status_var = tk.StringVar(value="HidHideCLI.exe: not detected")
        self.isolation_test_status_var = tk.StringVar(value="Last isolation test: not run")
        ttk.Label(status, textvariable=self.ds4_status_var).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(status, textvariable=self.hidhide_status_var).grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Label(status, textvariable=self.hidhide_cli_status_var).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Label(status, textvariable=self.isolation_test_status_var).grid(row=3, column=0, columnspan=2, sticky="w")
        tool_buttons = ttk.Frame(status)
        tool_buttons.grid(row=0, column=2, rowspan=4, sticky="e", padx=(10, 0))
        for index, (label, callback) in enumerate(
            [
                ("Detect Tools", self.detect_input_setup_tools),
                ("Select DS4Windows.exe", self.select_ds4windows_exe),
                ("Select HidHideClient.exe", self.select_hidhide_client_exe),
                ("Open joy.cpl", self.open_windows_game_controllers),
            ]
        ):
            ttk.Button(tool_buttons, text=label, command=lambda text=label, cb=callback: self.run_ui_action(text, cb)).grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=3)

        body = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        body.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        guide_frame = ttk.Frame(body, padding=0)
        guide_frame.grid_columnconfigure(0, weight=1)
        guide_frame.grid_rowconfigure(0, weight=1)
        self.input_setup_text = tk.Text(guide_frame, wrap=tk.WORD)
        self.input_setup_text.grid(row=0, column=0, sticky="nsew")
        self.style_text_widget(self.input_setup_text)
        self.input_setup_text.configure(state=tk.DISABLED)
        body.add(guide_frame, weight=3)

        controls = ttk.Frame(body, padding=(10, 0, 0, 0))
        controls.grid_columnconfigure(0, weight=1)
        setup_buttons = [
            ("Apply Safe Input Isolation Setup", self.apply_safe_input_isolation_setup),
            ("Test Isolation", self.test_input_isolation),
            ("Save Nucleus Minecraft Profile", self.save_nucleus_minecraft_profile),
            ("Copy Generated Setup Steps", self.copy_generated_input_setup_steps),
            ("Open DS4Windows", self.open_ds4windows),
            ("Open HidHide Configuration Client", self.open_hidhide_client),
            ("Open HidHide Official Page", lambda: self.open_official_input_tool_page(HIDHIDE_OFFICIAL_URL)),
            ("Open DS4Windows Official Page", lambda: self.open_official_input_tool_page(DS4WINDOWS_OFFICIAL_URL)),
        ]
        for index, (label, callback) in enumerate(setup_buttons):
            ttk.Button(controls, text=label, command=lambda text=label, cb=callback: self.run_ui_action(text, cb)).grid(row=index, column=0, sticky="ew", pady=3)

        advanced = ttk.LabelFrame(controls, text="Advanced HidHide CLI", padding=8)
        advanced.grid(row=len(setup_buttons), column=0, sticky="ew", pady=(12, 0))
        advanced.grid_columnconfigure(0, weight=1)
        self.advanced_hidhide_cli_var = tk.BooleanVar(value=False)
        self.hidhide_cli_controller_var = tk.StringVar()
        ttk.Checkbutton(
            advanced,
            text="Enable Advanced HidHide CLI instructions",
            variable=self.advanced_hidhide_cli_var,
            command=lambda: self.run_ui_action("Toggle Advanced HidHide CLI", self.update_input_setup_tab),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(advanced, text="Selected controller instance ID").grid(row=1, column=0, sticky="w", pady=(6, 2))
        ttk.Entry(advanced, textvariable=self.hidhide_cli_controller_var).grid(row=2, column=0, sticky="ew")
        ttk.Button(advanced, text="Refresh Controller List", command=lambda: self.run_ui_action("Refresh Controller List", self.refresh_visible_controllers)).grid(row=3, column=0, sticky="ew", pady=(8, 3))
        ttk.Button(advanced, text="Copy CLI Command Preview", command=lambda: self.run_ui_action("Copy CLI Command Preview", self.copy_hidhide_cli_command_preview)).grid(row=4, column=0, sticky="ew", pady=3)
        ttk.Button(advanced, text="Run HidHide CLI Help Only", command=lambda: self.run_ui_action("Run HidHide CLI Help Only", self.run_hidhide_cli_help)).grid(row=5, column=0, sticky="ew", pady=3)
        body.add(controls, weight=1)

        self.tabs.add(frame, text="Input Isolation Setup")
        self.tab_widgets["Input Isolation Setup"] = frame

    def add_settings_tab(self) -> None:
        frame = ttk.Frame(self.tabs, padding=12)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        header = ttk.Frame(frame)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.grid_columnconfigure(1, weight=1)
        if KIWI_LOGO_PATH.exists():
            try:
                self.settings_logo = tk.PhotoImage(file=str(KIWI_LOGO_PATH)).subsample(6, 6)
                ttk.Label(header, image=self.settings_logo).grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))
            except tk.TclError:
                self.settings_logo = None
        self.settings_title_label = ttk.Label(header, text=self.tr("settings"), font=self.scaled_font(16, "bold"))
        self.settings_title_label.grid(row=0, column=1, sticky="w")
        self.settings_privacy_label = ttk.Label(header, text=self.tr("privacy_local"), style="Muted.TLabel", wraplength=760)
        self.settings_privacy_label.grid(row=1, column=1, sticky="w")

        settings_tabs = ttk.Notebook(frame)
        settings_tabs.grid(row=1, column=0, sticky="nsew")

        appearance = ttk.Frame(settings_tabs, padding=10)
        appearance.grid_columnconfigure(1, weight=1)
        settings_tabs.add(appearance, text=self.tr("appearance"))
        self.language_label = ttk.Label(appearance, text=self.tr("language"))
        self.language_label.grid(row=0, column=0, sticky="w", pady=4)
        self.language_var = tk.StringVar(value="Italiano" if self.language == "it" else "English")
        language_combo = ttk.Combobox(appearance, textvariable=self.language_var, values=["English", "Italiano"], state="readonly")
        language_combo.grid(row=0, column=1, sticky="ew", pady=4)
        language_combo.bind("<<ComboboxSelected>>", lambda _event: self.change_language())

        self.theme_label = ttk.Label(appearance, text=self.tr("theme"))
        self.theme_label.grid(row=1, column=0, sticky="w", pady=4)
        theme_names = {"light": self.tr("light"), "dark": self.tr("dark"), "system": self.tr("system")}
        self.theme_display_to_key = {value: key for key, value in theme_names.items()}
        self.theme_var = tk.StringVar(value=theme_names.get(self.theme_name, theme_names["light"]))
        self.theme_combo = ttk.Combobox(appearance, textvariable=self.theme_var, values=list(theme_names.values()), state="readonly")
        self.theme_combo.grid(row=1, column=1, sticky="ew", pady=4)
        self.theme_combo.bind("<<ComboboxSelected>>", lambda _event: self.change_theme())
        self.ui_scale_label = ttk.Label(appearance, text=self.tr("ui_scale"))
        self.ui_scale_label.grid(row=2, column=0, sticky="w", pady=4)
        self.ui_scale_var = tk.StringVar(value=self.ui_scale)
        self.ui_scale_combo = ttk.Combobox(appearance, textvariable=self.ui_scale_var, values=UI_SCALE_VALUES, state="readonly")
        self.ui_scale_combo.grid(row=2, column=1, sticky="ew", pady=4)
        self.ui_scale_combo.bind("<<ComboboxSelected>>", lambda _event: self.change_ui_scale())
        self.show_safety_var = tk.BooleanVar(value=bool(self.config.get("show_safety_warnings", True)))
        self.remember_game_var = tk.BooleanVar(value=bool(self.config.get("remember_last_selected_game", True)))
        self.compact_mode_var = tk.BooleanVar(value=bool(self.config.get("compact_mode", False)))
        self.animations_var = tk.BooleanVar(value=bool(self.config.get("animations", True)))
        self.show_safety_check = ttk.Checkbutton(appearance, text=self.tr("show_safety_warnings"), variable=self.show_safety_var, command=self.save_settings)
        self.show_safety_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=4)
        self.remember_game_check = ttk.Checkbutton(appearance, text=self.tr("remember_last_game"), variable=self.remember_game_var, command=self.save_settings)
        self.remember_game_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        self.compact_check = ttk.Checkbutton(appearance, text=self.tr("compact_mode"), variable=self.compact_mode_var, command=self.save_settings)
        self.compact_check.grid(row=5, column=0, columnspan=2, sticky="w", pady=4)
        self.animations_check = ttk.Checkbutton(appearance, text=self.tr("animations"), variable=self.animations_var, command=self.save_settings)
        self.animations_check.grid(row=6, column=0, columnspan=2, sticky="w", pady=4)

        tools = ttk.Frame(settings_tabs, padding=10)
        tools.grid_columnconfigure(0, weight=1)
        tools.grid_rowconfigure(2, weight=1)
        settings_tabs.add(tools, text=self.tr("tool_manager"))
        self.tool_manager_label = ttk.Label(tools, text=self.tr("tool_manager"), font=self.scaled_font(13, "bold"))
        self.tool_manager_label.grid(row=0, column=0, sticky="w")
        self.tool_manager_desc_label = ttk.Label(tools, text=self.tr("tool_manager_description"), style="Warning.TLabel", wraplength=860, justify=tk.LEFT)
        self.tool_manager_desc_label.grid(row=1, column=0, sticky="ew", pady=(6, 8))
        self.tool_tree = ttk.Treeview(tools, columns=("tool", "state", "visible"), show="headings", height=10)
        self.tool_tree.heading("tool", text="Tool")
        self.tool_tree.heading("state", text="Enabled")
        self.tool_tree.heading("visible", text="Visible")
        self.tool_tree.column("tool", width=360, anchor=tk.W)
        self.tool_tree.column("state", width=120, anchor=tk.CENTER)
        self.tool_tree.column("visible", width=120, anchor=tk.CENTER)
        self.tool_tree.grid(row=2, column=0, sticky="nsew")
        tool_scroll = ttk.Scrollbar(tools, orient=tk.VERTICAL, command=self.tool_tree.yview)
        tool_scroll.grid(row=2, column=1, sticky="ns")
        self.tool_tree.configure(yscrollcommand=tool_scroll.set)
        tool_buttons = ttk.Frame(tools)
        tool_buttons.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        for column in range(6):
            tool_buttons.grid_columnconfigure(column, weight=1)
        self.tool_show_button = ttk.Button(tool_buttons, text=self.tr("show_tool"), command=lambda: self.run_ui_action("Show Tool", self.show_selected_tool))
        self.tool_hide_button = ttk.Button(tool_buttons, text=self.tr("hide_tool"), command=lambda: self.run_ui_action("Hide Tool", self.hide_selected_tool))
        self.tool_enable_button = ttk.Button(tool_buttons, text=self.tr("enable_tool"), command=lambda: self.run_ui_action("Enable Tool", self.enable_selected_tool))
        self.tool_disable_button = ttk.Button(tool_buttons, text=self.tr("disable_tool"), command=lambda: self.run_ui_action("Disable Tool", self.disable_selected_tool))
        self.tool_restore_button = ttk.Button(tool_buttons, text=self.tr("restore_all_tools"), command=lambda: self.run_ui_action("Restore All Tools", self.restore_all_tools))
        self.tool_suggest_button = ttk.Button(tool_buttons, text=self.tr("suggest_unused_tools"), command=lambda: self.run_ui_action("Suggest Unused Tools", self.suggest_unused_tools))
        for index, button in enumerate([self.tool_show_button, self.tool_hide_button, self.tool_enable_button, self.tool_disable_button, self.tool_restore_button, self.tool_suggest_button]):
            button.grid(row=0, column=index, sticky="ew", padx=3)
        self.hide_unused_var = tk.BooleanVar(value=bool(self.config.get("hide_unused_tools_automatically", False)))
        ttk.Checkbutton(tools, text=self.tr("hide_unused_tools_automatically"), variable=self.hide_unused_var, command=self.save_settings).grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Label(tools, text=self.tr("settings_core_note"), style="Muted.TLabel").grid(row=5, column=0, sticky="w", pady=(4, 0))
        self.populate_tool_tree()

        game_invite = ttk.Frame(settings_tabs, padding=10)
        game_invite.grid_columnconfigure(1, weight=1)
        settings_tabs.add(game_invite, text=f"{self.tr('game_list_settings')} / {self.tr('invite_export_settings')}")
        ttk.Label(game_invite, text=self.tr("default_filter")).grid(row=0, column=0, sticky="w", pady=4)
        self.settings_filter_var = tk.StringVar(value=self.filter_label_for_key(str(self.config.get("default_game_filter", "all"))))
        self.settings_filter_combo = ttk.Combobox(game_invite, textvariable=self.settings_filter_var, values=self.filter_display_values(), state="readonly")
        self.settings_filter_combo.grid(row=0, column=1, sticky="ew", pady=4)
        self.settings_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self.change_default_filter_setting())
        self.show_hidden_games_var = tk.BooleanVar(value=bool(self.config.get("show_hidden_games", False)))
        ttk.Checkbutton(game_invite, text=self.tr("show_hidden_games"), variable=self.show_hidden_games_var, command=self.save_settings).grid(row=1, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Button(game_invite, text=self.tr("reset_hidden_games"), command=lambda: self.run_ui_action("Reset Hidden Games", self.reset_hidden_games)).grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Button(game_invite, text=self.tr("refresh_detection"), command=lambda: self.run_ui_action("Refresh Installed Detection", self.refresh_installed_detection)).grid(row=2, column=1, sticky="ew", pady=4, padx=(8, 0))
        self.invite_mode_label = ttk.Label(game_invite, text=self.tr("invite_mode"))
        self.invite_mode_label.grid(row=3, column=0, sticky="w", pady=(16, 4))
        self.default_invite_var = tk.StringVar(value=self.invite_mode_label_for_key(str(self.config.get("default_invite_mode", "short"))))
        self.default_invite_combo = ttk.Combobox(game_invite, textvariable=self.default_invite_var, values=self.invite_mode_display_values(), state="readonly")
        self.default_invite_combo.grid(row=3, column=1, sticky="ew", pady=(16, 4))
        self.default_invite_combo.bind("<<ComboboxSelected>>", lambda _event: self.change_default_invite_mode())
        self.include_lan_note_var = tk.BooleanVar(value=bool(self.config.get("include_lan_vpn_note", True)))
        self.include_lan_note_check = ttk.Checkbutton(game_invite, text=self.tr("include_lan_vpn_note"), variable=self.include_lan_note_var, command=self.save_settings)
        self.include_lan_note_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=4)

        paths = ttk.Frame(settings_tabs, padding=10)
        settings_tabs.add(paths, text=self.tr("paths"))
        paths.grid_columnconfigure(1, weight=1)
        self.ds4_settings_var = tk.StringVar(value=self.config.get("ds4windows_path", ""))
        self.hidhide_settings_var = tk.StringVar(value=self.config.get("hidhide_client_path", ""))
        self.nucleus_settings_var = tk.StringVar(value=self.config.get("nucleus_coop_path", ""))
        self.prism_settings_var = tk.StringVar(value=self.config.get("prism_launcher_path", ""))
        self.export_settings_var = tk.StringVar(value=self.config.get("default_export_folder", ""))
        self.backup_settings_var = tk.StringVar(value=self.config.get("default_backup_folder", ""))
        path_rows = [
            ("DS4Windows path", self.ds4_settings_var, lambda: self.select_exe_setting("ds4windows_path", self.ds4_settings_var, "Select DS4Windows.exe")),
            ("HidHide path", self.hidhide_settings_var, lambda: self.select_exe_setting("hidhide_client_path", self.hidhide_settings_var, "Select HidHideClient.exe")),
            ("Nucleus Co-op path", self.nucleus_settings_var, lambda: self.select_exe_setting("nucleus_coop_path", self.nucleus_settings_var, "Select NucleusCoop.exe")),
            ("Prism Launcher path", self.prism_settings_var, lambda: self.select_exe_setting("prism_launcher_path", self.prism_settings_var, "Select PrismLauncher.exe")),
            (self.tr("default_export_folder"), self.export_settings_var, lambda: self.select_folder_setting("default_export_folder", self.export_settings_var, "Select default export folder")),
            (self.tr("default_backup_folder"), self.backup_settings_var, lambda: self.select_folder_setting("default_backup_folder", self.backup_settings_var, "Select default backup folder")),
        ]
        self.settings_path_labels: list[ttk.Label] = []
        for row, (label, variable, callback) in enumerate(path_rows):
            item_label = ttk.Label(paths, text=label)
            item_label.grid(row=row, column=0, sticky="w", pady=3)
            self.settings_path_labels.append(item_label)
            ttk.Entry(paths, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8, pady=3)
            ttk.Button(paths, text=self.tr("select"), command=lambda cb=callback: self.run_ui_action("Select settings path", cb)).grid(row=row, column=2, sticky="ew", pady=3)

        support = ttk.Frame(settings_tabs, padding=10)
        support.grid_columnconfigure(0, weight=1)
        settings_tabs.add(support, text=f"{self.tr('privacy')} / {self.tr('support')}")
        support.grid_columnconfigure(0, weight=1)
        ttk.Label(
            support,
            text=self.tr("privacy_local"),
            style="Warning.TLabel",
            wraplength=760,
            justify=tk.LEFT,
        ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        ttk.Label(
            support,
            text="Donations are optional and do not unlock extra features.",
            style="Muted.TLabel",
            wraplength=480,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self.settings_paypal_button = ttk.Button(support, text=self.tr("donate"), command=lambda: self.run_ui_action("Donate with PayPal", self.open_paypal_donation))
        self.settings_paypal_button.grid(row=2, column=0, sticky="ew", padx=(0, 5))
        self.settings_sponsor_button = ttk.Button(support, text=self.tr("sponsor"), command=lambda: self.run_ui_action("Sponsor on GitHub", self.open_github_sponsors))
        self.settings_sponsor_button.grid(row=2, column=1, sticky="ew", padx=5)
        self.settings_copy_donation_button = ttk.Button(support, text=self.tr("copy_donation"), command=lambda: self.run_ui_action("Copy Donation Link", self.copy_donation_link))
        self.settings_copy_donation_button.grid(row=2, column=2, sticky="ew", padx=(5, 0))
        ttk.Button(support, text=self.tr("open_privacy"), command=lambda: self.run_ui_action("Open Privacy Policy", self.open_privacy_file)).grid(row=3, column=0, sticky="ew", pady=(12, 0), padx=(0, 5))
        ttk.Button(support, text=self.tr("open_github_windows"), command=lambda: self.run_ui_action("Open GitHub Repository", self.open_windows_repository)).grid(row=3, column=1, sticky="ew", pady=(12, 0), padx=5)

        about = ttk.Frame(settings_tabs, padding=10)
        settings_tabs.add(about, text=self.tr("about"))
        about.grid_columnconfigure(0, weight=1)
        self.about_label = ttk.Label(
            about,
            text=f"{APP_NAME}\nVersion: {APP_VERSION}\n{self.tr('author')}\n{self.tr('license_summary')}",
            justify=tk.LEFT,
            wraplength=520,
        )
        self.about_label.grid(row=0, column=0, sticky="w")

        storage = ttk.Frame(settings_tabs, padding=10)
        storage.grid_columnconfigure(0, weight=1)
        settings_tabs.add(storage, text=self.tr("storage_cleanup"))
        ttk.Label(
            storage,
            text="Cleanup only touches app-generated files such as exported guides, temporary logs, detection cache, and local settings after confirmation. It does not delete games, saves, external programs, or system files.",
            style="Warning.TLabel",
            wraplength=820,
            justify=tk.LEFT,
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(storage, text=self.tr("delete_exported_guides"), command=lambda: self.run_ui_action("Delete Exported Guides", self.delete_exported_guides)).grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Button(storage, text=self.tr("delete_temp_logs"), command=lambda: self.run_ui_action("Delete Temporary Logs", self.delete_temp_logs)).grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Button(storage, text=self.tr("clear_detection_cache"), command=lambda: self.run_ui_action("Clear Detection Cache", self.clear_detection_cache)).grid(row=3, column=0, sticky="ew", pady=4)
        ttk.Button(storage, text=self.tr("reset_local_settings"), command=lambda: self.run_ui_action("Reset Local Settings", self.reset_local_settings)).grid(row=4, column=0, sticky="ew", pady=4)

        self.settings_status_var = tk.StringVar(value=self.tr("status_ready"))
        ttk.Label(frame, textvariable=self.settings_status_var, style="Success.TLabel").grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.tabs.add(frame, text="Settings")
        self.tab_widgets["Settings"] = frame

    def add_support_tab(self) -> None:
        frame = ttk.Frame(self.tabs, padding=10)
        frame.grid_columnconfigure(0, weight=1)
        text = (
            "Offline LAN Games Helper is free to use.\n\n"
            "If this app helped you and you want to support development, you can donate or sponsor the project.\n\n"
            "Donations are optional and do not unlock extra features."
        )
        ttk.Label(frame, text="Support the Project", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text=text, wraplength=760, justify=tk.LEFT).grid(row=1, column=0, sticky="w", pady=(8, 12))
        controls = ttk.Frame(frame)
        controls.grid(row=2, column=0, sticky="w")
        ttk.Button(controls, text="Donate with PayPal", command=lambda: self.run_ui_action("Donate with PayPal", self.open_paypal_donation)).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(controls, text="Sponsor on GitHub", command=lambda: self.run_ui_action("Sponsor on GitHub", self.open_github_sponsors)).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(controls, text="Copy Donation Link", command=lambda: self.run_ui_action("Copy Donation Link", self.copy_donation_link)).grid(row=0, column=2, padx=(0, 6))
        ttk.Label(frame, text=f"PayPal: {PAYPAL_DONATION_URL}\nGitHub Sponsors: {GITHUB_SPONSORS_URL}", style="Muted.TLabel").grid(row=3, column=0, sticky="w", pady=(12, 0))
        self.tabs.add(frame, text="Support")
        self.tab_widgets["Support"] = frame

    def add_action_button(self, parent: ttk.Frame, text: str, callback: Callable[[], None], column: int) -> None:
        button = ttk.Button(parent, text=text, command=lambda: self.run_ui_action(text, callback))
        button.grid(row=0, column=column, sticky="ew", padx=3, pady=3)
        self.action_buttons[text] = button

    def add_server_button(self, text: str, callback: Callable[[], None], index: int) -> None:
        row, column = divmod(index, 6)
        button = ttk.Button(self.server_buttons_frame, text=text, command=lambda: self.run_ui_action(text, callback))
        button.grid(row=row, column=column, sticky="ew", padx=3, pady=3)
        self.server_buttons[text] = button

    def show_settings(self) -> None:
        self.show_page("Settings")

    def filter_display_values(self) -> list[str]:
        return [self.filter_label_for_key(filter_id) for filter_id in GAME_FILTER_IDS]

    def filter_label_for_key(self, filter_id: str) -> str:
        labels = {
            "all": self.tr("show_all_games"),
            "installed": self.tr("show_installed_only"),
            "favorites": self.tr("favorites"),
            "dedicated_server": self.tr("dedicated_server"),
            "in_game_host": self.tr("in_game_host"),
        }
        return labels.get(filter_id, labels["all"])

    def filter_key_from_label(self, label: str) -> str:
        lookup = {self.filter_label_for_key(filter_id): filter_id for filter_id in GAME_FILTER_IDS}
        return lookup.get(label, "all")

    def current_filter_key(self) -> str:
        value = getattr(self, "game_filter_var", tk.StringVar(value="all")).get()
        if value in GAME_FILTER_IDS:
            return value
        return self.filter_key_from_label(value)

    def set_game_filter(self, filter_key: str) -> None:
        if filter_key not in GAME_FILTER_IDS:
            filter_key = "all"
        self.game_filter_var.set(filter_key)
        self.config["default_game_filter"] = filter_key
        save_json_file(CONFIG_FILE, self.config)
        self.update_filter_buttons_visual()
        self.apply_filter()

    def update_filter_buttons_visual(self) -> None:
        current = self.current_filter_key()
        for filter_id, button in getattr(self, "filter_buttons", {}).items():
            button.configure(style="Accent.TButton" if filter_id == current else "TButton")

    def invite_mode_display_values(self) -> list[str]:
        return [self.invite_mode_label_for_key(mode_id) for mode_id in INVITE_MODE_IDS]

    def invite_mode_label_for_key(self, mode_id: str) -> str:
        labels = {
            "ip_only": self.tr("ip_only"),
            "ip_port_only": self.tr("ip_port_only"),
            "short": self.tr("short_invite"),
            "full": self.tr("full_useful_invite"),
        }
        return labels.get(mode_id, labels["short"])

    def invite_mode_key_from_label(self, label: str) -> str:
        lookup = {self.invite_mode_label_for_key(mode_id): mode_id for mode_id in INVITE_MODE_IDS}
        return lookup.get(label, "short")

    def on_filter_changed(self) -> None:
        self.set_game_filter(self.current_filter_key())

    def refresh_games(self) -> None:
        if hasattr(self, "game_status_var"):
            self.game_status_var.set(self.tr("loading_games"))
        self.builtin_games = self.load_game_catalog()
        self.reload_games()
        if self.catalog_load_error:
            messagebox.showerror(APP_TITLE, self.catalog_load_error)
            self.log(self.catalog_load_error)
        else:
            self.log("Game catalog refreshed from games.json.")

    def refresh_installed_detection(self) -> None:
        if self.detection_running:
            self.log("Installed detection is already running.")
            return
        self.detection_running = True
        if hasattr(self, "refresh_detection_button"):
            self.refresh_detection_button.configure(state=tk.DISABLED)
        if hasattr(self, "game_status_var"):
            self.game_status_var.set("Checking installed games...")

        def worker() -> None:
            detected: dict[str, bool] = {}
            for game in list(self.games):
                try:
                    detected[game["name"]] = bool(self.find_game_path(game))
                except Exception:
                    detected[game["name"]] = False
            self.root.after(0, lambda: self.finish_installed_detection(detected))

        threading.Thread(target=worker, daemon=True).start()

    def finish_installed_detection(self, detected: dict[str, bool]) -> None:
        self.installed_cache = detected
        self.installed_detection_cache = dict(detected)
        self.config["installed_cache"] = detected
        self.config["detection_cache_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save_json_file(CONFIG_FILE, self.config)
        self.detection_running = False
        if hasattr(self, "refresh_detection_button"):
            self.refresh_detection_button.configure(state=tk.NORMAL)
        installed_count = sum(1 for value in detected.values() if value)
        self.game_status_var.set(f"Installed detection complete: {installed_count} detected.")
        self.apply_filter()
        self.log(f"Installed detection complete: {installed_count} supported games detected.")

    def apply_tool_visibility(self) -> None:
        for tool_id, tab_titles in self.tool_tab_map.items():
            visible = self.is_tool_visible(tool_id)
            for title in tab_titles:
                frame = self.tab_widgets.get(title)
                if frame is None:
                    continue
                try:
                    if visible:
                        self.tabs.add(frame, text=title)
                    else:
                        self.tabs.hide(frame)
                except tk.TclError:
                    pass
        for tool_id, widgets in self.tool_button_map.items():
            visible = self.is_tool_visible(tool_id)
            for widget in widgets:
                try:
                    if visible:
                        widget.grid()
                    else:
                        widget.grid_remove()
                except tk.TclError:
                    pass
        for page_name, tool_id in getattr(self, "sidebar_page_map", {}).items():
            button = getattr(self, "sidebar_buttons", {}).get(page_name)
            if button is None:
                continue
            page_visible = True
            if tool_id != "core":
                page_visible = self.is_tool_visible(tool_id)
            try:
                if page_visible:
                    button.grid()
                else:
                    button.grid_remove()
                    if self.current_page == page_name:
                        self.show_page("Home")
            except tk.TclError:
                pass
        if hasattr(self, "tool_tree"):
            self.populate_tool_tree()

    def populate_tool_tree(self) -> None:
        if not hasattr(self, "tool_tree"):
            return
        current_selection = self.selected_tool_id()
        self.tool_tree.delete(*self.tool_tree.get_children())
        for tool_id, label in OPTIONAL_TOOLS.items():
            enabled = "Yes" if self.is_tool_enabled(tool_id) else "No"
            visible = "No" if tool_id in self.hidden_tools else "Yes"
            self.tool_tree.insert("", tk.END, iid=tool_id, values=(f"{label} - {tool_id}", enabled, visible))
        if current_selection and current_selection in OPTIONAL_TOOLS:
            self.tool_tree.selection_set(current_selection)

    def selected_tool_id(self) -> str:
        if not hasattr(self, "tool_tree"):
            return ""
        selection = self.tool_tree.selection()
        return selection[0] if selection else ""

    def save_tool_settings(self) -> None:
        self.config["enabled_tools"] = {tool_id: bool(self.enabled_tools.get(tool_id, True)) for tool_id in OPTIONAL_TOOLS}
        self.config["hidden_tools"] = sorted(tool_id for tool_id in self.hidden_tools if tool_id in OPTIONAL_TOOLS)
        save_json_file(CONFIG_FILE, self.config)
        self.apply_tool_visibility()

    def show_selected_tool(self) -> None:
        tool_id = self.selected_tool_id()
        if not tool_id:
            messagebox.showwarning(APP_TITLE, "Select a tool first.")
            return
        self.hidden_tools.discard(tool_id)
        self.save_tool_settings()
        self.log(f"Tool shown: {OPTIONAL_TOOLS.get(tool_id, tool_id)}")

    def hide_selected_tool(self) -> None:
        tool_id = self.selected_tool_id()
        if not tool_id:
            messagebox.showwarning(APP_TITLE, "Select a tool first.")
            return
        self.hidden_tools.add(tool_id)
        self.save_tool_settings()
        self.log(f"Tool hidden: {OPTIONAL_TOOLS.get(tool_id, tool_id)}")

    def enable_selected_tool(self) -> None:
        tool_id = self.selected_tool_id()
        if not tool_id:
            messagebox.showwarning(APP_TITLE, "Select a tool first.")
            return
        self.enabled_tools[tool_id] = True
        self.save_tool_settings()
        self.log(f"Tool enabled: {OPTIONAL_TOOLS.get(tool_id, tool_id)}")

    def disable_selected_tool(self) -> None:
        tool_id = self.selected_tool_id()
        if not tool_id:
            messagebox.showwarning(APP_TITLE, "Select a tool first.")
            return
        self.enabled_tools[tool_id] = False
        self.save_tool_settings()
        self.log(f"Tool disabled: {OPTIONAL_TOOLS.get(tool_id, tool_id)}")

    def restore_all_tools(self) -> None:
        self.hidden_tools.clear()
        for tool_id in OPTIONAL_TOOLS:
            self.enabled_tools[tool_id] = True
        self.save_tool_settings()
        messagebox.showinfo(APP_TITLE, self.tr("hidden_tools_can_be_restored"))
        self.log("All optional tools restored.")

    def suggest_unused_tools(self) -> None:
        suggestions: list[str] = []
        checks = [
            ("hidhide_helper", self.config.get("hidhide_client_path", "") or shutil.which("HidHideClient.exe")),
            ("ds4windows_helper", self.config.get("ds4windows_path", "")),
            ("nucleus_helper", self.config.get("nucleus_coop_path", "")),
        ]
        for tool_id, path in checks:
            if not path or not Path(str(path)).exists():
                suggestions.append(tool_id)
        if not suggestions:
            messagebox.showinfo(APP_TITLE, "No unused Windows helper tools were suggested.")
            self.log("Tool Manager found no unused tools to suggest.")
            return
        message = "Suggested tools to hide because related apps were not found:\n\n" + "\n".join(f"- {OPTIONAL_TOOLS[item]}" for item in suggestions)
        if messagebox.askyesno(APP_TITLE, message + "\n\nHide these app tools now? This will not uninstall anything."):
            self.hidden_tools.update(suggestions)
            self.save_tool_settings()
            self.log("Suggested unused tools hidden.")

    def change_ui_scale(self) -> None:
        self.ui_scale = self.ui_scale_var.get() if self.ui_scale_var.get() in UI_SCALE_VALUES else "100%"
        self.config["ui_scale"] = self.ui_scale
        save_json_file(CONFIG_FILE, self.config)
        self.configure_style()
        self.refresh_scaled_fonts()
        self.apply_theme_to_widgets()
        self.apply_language()
        self.log(f"UI scale changed to {self.ui_scale}.")

    def refresh_scaled_fonts(self) -> None:
        if hasattr(self, "title_label"):
            self.title_label.configure(font=self.scaled_font(18, "bold"))
        if hasattr(self, "games_page_title"):
            self.games_page_title.configure(font=self.scaled_font(14, "bold"))
        if hasattr(self, "settings_title_label"):
            self.settings_title_label.configure(font=self.scaled_font(16, "bold"))
        if hasattr(self, "tool_manager_label"):
            self.tool_manager_label.configure(font=self.scaled_font(13, "bold"))

    def change_default_filter_setting(self) -> None:
        filter_key = self.filter_key_from_label(self.settings_filter_var.get())
        self.set_game_filter(filter_key)

    def change_default_invite_mode(self) -> None:
        mode_key = self.invite_mode_key_from_label(self.default_invite_var.get())
        self.config["default_invite_mode"] = mode_key
        if hasattr(self, "invite_mode_var"):
            self.invite_mode_var.set(self.invite_mode_label_for_key(mode_key))
            self.update_invite_tab()
        save_json_file(CONFIG_FILE, self.config)
        self.log(f"Default invite mode changed to {mode_key}.")

    def reset_hidden_games(self) -> None:
        self.hidden_games.clear()
        self.config["hidden_games"] = []
        save_json_file(CONFIG_FILE, self.config)
        self.apply_filter()
        self.log("Hidden games reset.")

    def delete_exported_guides(self) -> None:
        export_dir = self.export_dir_path()
        if not export_dir.exists():
            self.log("No exported guides folder exists.")
            return
        if not messagebox.askyesno(APP_TITLE, f"Delete app-generated exported guides in:\n{export_dir}?"):
            return
        for path in export_dir.glob("*"):
            if path.is_file():
                path.unlink(missing_ok=True)
        self.log("Exported guides deleted.")

    def delete_temp_logs(self) -> None:
        logs_dir = APP_DIR / "logs"
        if not logs_dir.exists():
            self.log("No logs folder exists.")
            return
        if not messagebox.askyesno(APP_TITLE, f"Delete app-generated logs in:\n{logs_dir}?"):
            return
        for path in logs_dir.glob("*"):
            if path.is_file():
                path.unlink(missing_ok=True)
        self.log("Temporary logs deleted.")

    def clear_detection_cache(self) -> None:
        self.installed_cache = {}
        self.config["installed_cache"] = {}
        self.config["detection_cache_updated"] = ""
        save_json_file(CONFIG_FILE, self.config)
        self.apply_filter()
        self.log("Installed detection cache cleared.")

    def reset_local_settings(self) -> None:
        if not messagebox.askyesno(APP_TITLE, "Reset local app settings? This does not delete games, saves, external programs, or system files."):
            return
        preserve_custom = self.config.get("custom_games", [])
        self.config = merge_config(DEFAULT_CONFIG)
        self.config["custom_games"] = preserve_custom
        save_json_file(CONFIG_FILE, self.config)
        messagebox.showinfo(APP_TITLE, "Local settings were reset. Restart the app to reload all UI state.")
        self.log("Local settings reset; restart recommended.")

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

    def apply_language(self) -> None:
        self.root.title(self.tr("app_title"))
        if hasattr(self, "title_label"):
            self.title_label.configure(text=self.tr("app_title"))
        if hasattr(self, "safety_label"):
            self.safety_label.configure(text=self.tr("safety_warning"))
        if hasattr(self, "offline_check"):
            self.offline_check.configure(text=self.tr("offline_mode"))
        if hasattr(self, "search_label"):
            self.search_label.configure(text=self.tr("search"))
        if hasattr(self, "add_custom_button"):
            self.add_custom_button.configure(text=self.tr("add_custom_game"))
        if hasattr(self, "settings_header_button"):
            self.settings_header_button.configure(text=self.tr("settings"))
        if hasattr(self, "clear_search_button"):
            self.clear_search_button.configure(text=self.tr("clear_search"))
        if hasattr(self, "filter_label"):
            self.filter_label.configure(text=self.tr("default_filter"))
        if hasattr(self, "filter_buttons"):
            for filter_id, button in self.filter_buttons.items():
                button.configure(text=self.filter_label_for_key(filter_id))
            self.update_filter_buttons_visual()
        if hasattr(self, "refresh_games_button"):
            self.refresh_games_button.configure(text=self.tr("refresh_games"))
        if hasattr(self, "refresh_detection_button"):
            self.refresh_detection_button.configure(text=self.tr("refresh_installed_detection"))
        if hasattr(self, "selected_ip_label"):
            self.selected_ip_label.configure(text=self.tr("selected_ip"))
        if hasattr(self, "host_network_frame"):
            self.host_network_frame.configure(text=self.tr("host_network"))
        if hasattr(self, "actions_frame"):
            try:
                self.actions_frame.configure(text=self.tr("actions"))
            except tk.TclError:
                pass
        if hasattr(self, "log_frame"):
            self.log_frame.configure(text=self.tr("log_status"))
        if hasattr(self, "clear_log_button"):
            self.clear_log_button.configure(text=self.tr("clear_log"))
        if hasattr(self, "creator_label"):
            self.creator_label.configure(text=self.tr("creator_line"))
        if hasattr(self, "log_toggle_button"):
            self.log_toggle_button.configure(text=self.tr("hide_log") if getattr(self, "log_visible", True) else self.tr("show_log"))

        button_keys = {
            "Refresh IP": "refresh_ip",
            "Copy Host IP": "copy_ip",
            "Detect Game Path": "detect_path",
            "Manual Select Game": "manual_select_game",
            "Launch Game": "launch_game",
            "Add Firewall Rules": "add_firewall",
            "Remove Firewall Rules": "remove_firewall",
            "Export Tutorial": "export_tutorial",
        }
        for english, key in button_keys.items():
            if english in self.action_buttons:
                self.action_buttons[english].configure(text=self.tr(key))

        sidebar_label_map = {
            "Home": self.tr("home"),
            "Games": self.tr("games"),
            "Invite": self.tr("invite"),
            "Server Tools": self.tr("server_tools"),
            "LAN Test": self.tr("lan_test"),
            "Firewall / Permissions": self.tr("firewall"),
            "Input Isolation": self.tr("controller_tools"),
            "Backups": self.tr("backups"),
            "Troubleshooting": self.tr("troubleshooting"),
            "Settings": self.tr("settings"),
            "Support": self.tr("support"),
            "Privacy": self.tr("privacy"),
        }
        for page_name, button in getattr(self, "sidebar_buttons", {}).items():
            button.configure(text=sidebar_label_map.get(page_name, page_name))

        tab_keys = {
            "Home": "home",
            "Games": "games",
            "Tutorial": "tutorial",
            "Network / IP": "network",
            "Firewall / Permissions": "firewall_permissions",
            "Game Path": "game_path",
            "Server Tools": "server_tools",
            "LAN Test": "lan_test",
            "Invite": "invite",
            "Backups": "backups",
            "Mods": "mods",
            "Input Isolation": "input_isolation",
            "Input Isolation Setup": "input_isolation_setup",
            "Troubleshooting": "troubleshooting",
            "Settings": "settings",
            "Support": "support",
            "Privacy": "privacy",
        }
        for english, key in tab_keys.items():
            frame = self.tab_widgets.get(english)
            if frame is not None:
                self.tabs.tab(frame, text=self.tr(key))

        for widget, key in self.localized_widgets:
            try:
                widget.configure(text=self.tr(key))
            except tk.TclError:
                pass

        if hasattr(self, "settings_title_label"):
            self.settings_title_label.configure(text=self.tr("settings"))
            self.settings_privacy_label.configure(text=self.tr("privacy_local"))
            self.language_label.configure(text=self.tr("language"))
            self.theme_label.configure(text=self.tr("theme"))
            self.show_safety_check.configure(text=self.tr("show_safety_warnings"))
            self.remember_game_check.configure(text=self.tr("remember_last_game"))
            self.settings_paypal_button.configure(text=self.tr("donate"))
            self.settings_sponsor_button.configure(text=self.tr("sponsor"))
            self.settings_copy_donation_button.configure(text=self.tr("copy_donation"))
            self.about_label.configure(text=f"{APP_NAME}\nVersion: {APP_VERSION}\n{self.tr('author')}\n{self.tr('license_summary')}")
            self.settings_status_var.set(self.tr("status_ready"))
            values = [self.tr("light"), self.tr("dark"), self.tr("system")]
            self.theme_combo.configure(values=values)
            theme_label = {"light": self.tr("light"), "dark": self.tr("dark"), "system": self.tr("system")}.get(self.theme_name, self.tr("light"))
            self.theme_var.set(theme_label)
            self.theme_display_to_key = {self.tr("light"): "light", self.tr("dark"): "dark", self.tr("system"): "system"}
            if hasattr(self, "ui_scale_label"):
                self.ui_scale_label.configure(text=self.tr("ui_scale"))
            if hasattr(self, "compact_check"):
                self.compact_check.configure(text=self.tr("compact_mode"))
            if hasattr(self, "animations_check"):
                self.animations_check.configure(text=self.tr("animations"))
            if hasattr(self, "tool_manager_label"):
                self.tool_manager_label.configure(text=self.tr("tool_manager"))
            if hasattr(self, "tool_manager_desc_label"):
                self.tool_manager_desc_label.configure(text=self.tr("tool_manager_description"))
            if hasattr(self, "tool_restore_button"):
                self.tool_restore_button.configure(text=self.tr("restore_all_tools"))
            if hasattr(self, "tool_suggest_button"):
                self.tool_suggest_button.configure(text=self.tr("suggest_unused_tools"))
            if hasattr(self, "tool_show_button"):
                self.tool_show_button.configure(text=self.tr("show_tool"))
            if hasattr(self, "tool_hide_button"):
                self.tool_hide_button.configure(text=self.tr("hide_tool"))
            if hasattr(self, "tool_enable_button"):
                self.tool_enable_button.configure(text=self.tr("enable_tool"))
            if hasattr(self, "tool_disable_button"):
                self.tool_disable_button.configure(text=self.tr("disable_tool"))
            if hasattr(self, "invite_mode_label"):
                self.invite_mode_label.configure(text=self.tr("invite_mode"))
            if hasattr(self, "default_invite_combo"):
                self.default_invite_combo.configure(values=self.invite_mode_display_values())
                self.default_invite_var.set(self.invite_mode_label_for_key(str(self.config.get("default_invite_mode", "short"))))
            if hasattr(self, "include_lan_note_check"):
                self.include_lan_note_check.configure(text=self.tr("include_lan_vpn_note"))
            if hasattr(self, "tool_tree"):
                self.populate_tool_tree()

    def apply_theme_to_widgets(self) -> None:
        def walk(widget: tk.Widget) -> None:
            if isinstance(widget, tk.Text):
                self.style_text_widget(widget)
            elif isinstance(widget, tk.Listbox):
                widget.configure(
                    bg=self.colors["panel"],
                    fg=self.colors["text"],
                    selectbackground=self.colors["accent"],
                    selectforeground="#ffffff",
                    highlightcolor=self.colors["accent"],
                    highlightbackground=self.colors["border"],
                    font=self.scaled_font(12),
                )
            for child in widget.winfo_children():
                walk(child)

        walk(self.root)

    def save_settings(self) -> None:
        self.config["show_safety_warnings"] = bool(getattr(self, "show_safety_var", tk.BooleanVar(value=True)).get())
        self.config["remember_last_selected_game"] = bool(getattr(self, "remember_game_var", tk.BooleanVar(value=True)).get())
        self.config["compact_mode"] = bool(getattr(self, "compact_mode_var", tk.BooleanVar(value=False)).get())
        self.config["animations"] = bool(getattr(self, "animations_var", tk.BooleanVar(value=True)).get())
        self.config["hide_unused_tools_automatically"] = bool(getattr(self, "hide_unused_var", tk.BooleanVar(value=False)).get())
        self.config["show_hidden_games"] = bool(getattr(self, "show_hidden_games_var", tk.BooleanVar(value=False)).get())
        self.config["include_lan_vpn_note"] = bool(getattr(self, "include_lan_note_var", tk.BooleanVar(value=True)).get())
        if self.current_game and self.config["remember_last_selected_game"]:
            self.config["last_selected_game"] = self.current_game["name"]
        save_json_file(CONFIG_FILE, self.config)
        if hasattr(self, "safety_label"):
            if self.config["show_safety_warnings"]:
                self.safety_label.grid(row=1, column=0, sticky="ew", pady=(8, 0))
            else:
                self.safety_label.grid_remove()
        if hasattr(self, "settings_status_var"):
            self.settings_status_var.set(self.tr("settings_saved"))
        self.apply_filter()
        self.log(self.tr("settings_saved"))

    def change_language(self) -> None:
        self.language = "it" if getattr(self, "language_var", tk.StringVar(value="English")).get() == "Italiano" else "en"
        self.config["language"] = self.language
        save_json_file(CONFIG_FILE, self.config)
        self.apply_language()
        self.log(f"Language changed to {'Italian' if self.language == 'it' else 'English'}.")

    def change_theme(self) -> None:
        display = getattr(self, "theme_var", tk.StringVar(value=self.tr("light"))).get()
        self.theme_name = getattr(self, "theme_display_to_key", {}).get(display, "light")
        self.config["theme"] = self.theme_name
        save_json_file(CONFIG_FILE, self.config)
        self.configure_style()
        self.apply_theme_to_widgets()
        self.apply_language()
        self.log(f"Theme changed to {self.theme_name}.")

    def select_exe_setting(self, config_key: str, variable: tk.StringVar, title: str) -> None:
        path = filedialog.askopenfilename(title=title, filetypes=[("Windows executable", "*.exe"), ("All files", "*.*")])
        if not path:
            self.log("Settings path selection canceled.")
            return
        variable.set(path)
        self.config[config_key] = path
        save_json_file(CONFIG_FILE, self.config)
        self.log(f"Saved {config_key}: {path}")

    def select_folder_setting(self, config_key: str, variable: tk.StringVar, title: str) -> None:
        path = filedialog.askdirectory(title=title)
        if not path:
            self.log("Settings folder selection canceled.")
            return
        variable.set(path)
        self.config[config_key] = path
        save_json_file(CONFIG_FILE, self.config)
        self.log(f"Saved {config_key}: {path}")

    def open_privacy_file(self) -> None:
        privacy_path = APP_DIR / "PRIVACY.md"
        if privacy_path.exists():
            os.startfile(str(privacy_path))  # type: ignore[attr-defined]
            self.log(f"Opened privacy policy: {privacy_path}")
            return
        messagebox.showinfo(APP_TITLE, PRIVACY_TEXT)

    def open_windows_repository(self) -> None:
        webbrowser.open("https://github.com/The0Cosmo/Offline-LAN-Games-Helper-Windows")
        self.log("Opened Windows GitHub repository.")

    def export_dir_path(self) -> Path:
        configured = str(self.config.get("default_export_folder", "")).strip()
        return Path(configured) if configured else EXPORT_DIR

    def backup_root_path(self) -> Path:
        configured = str(self.config.get("default_backup_folder", "")).strip()
        return Path(configured) if configured else BACKUP_ROOT

    def set_text(self, widget: tk.Text, content: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.configure(state=tk.DISABLED)

    def reload_games(self) -> None:
        self.custom_games = [normalize_game(game, custom=True) for game in self.config.get("custom_games", [])]
        self.games_all = self.builtin_games + self.custom_games
        self.games = self.games_all
        if self.catalog_load_error and hasattr(self, "game_status_var"):
            self.game_status_var.set(self.catalog_load_error)
        elif not self.games and hasattr(self, "game_status_var"):
            self.game_status_var.set(self.tr("no_games_found"))
        self.apply_filter(select_first=True)

    def apply_filter(self, select_first: bool = False) -> None:
        query = self.search_var.get().strip().lower()
        filter_key = self.current_filter_key() if hasattr(self, "game_filter_var") else "all"
        self.update_filter_buttons_visual()
        previous = self.current_game["name"] if self.current_game else ""
        games = list(self.games)
        if not bool(self.config.get("show_hidden_games", False)):
            games = [game for game in games if game["name"] not in self.hidden_games]
        if query:
            games = [game for game in games if query in game["name"].lower()]
        if filter_key == "installed":
            installed_names = {name for name, installed in self.installed_cache.items() if installed} | self.manual_installed_games
            if installed_names:
                games = [game for game in games if game["name"] in installed_names]
            elif self.games:
                self.game_status_var.set(self.tr("no_installed_detected"))
        elif filter_key == "favorites":
            games = [game for game in games if game["name"] in self.favorite_games]
        elif filter_key == "dedicated_server":
            games = [game for game in games if str(game.get("server_support", "none")) not in {"none", "in_game_host"}]
        elif filter_key == "in_game_host":
            games = [game for game in games if str(game.get("server_support", "none")) == "in_game_host"]
        self.filtered_games = games
        self.games_visible = games
        self.game_list.delete(0, tk.END)
        for game in self.filtered_games:
            suffix = " (custom)" if game.get("custom") else ""
            self.game_list.insert(tk.END, game["name"] + suffix)
        if not self.filtered_games:
            self.current_game = None
            if hasattr(self, "game_status_var"):
                self.game_status_var.set(self.tr("no_matching_games_found") if query else self.tr("no_games_found"))
            self.update_all_tabs()
            return
        if hasattr(self, "game_status_var") and not (filter_key == "installed" and not any(self.installed_cache.values())):
            self.game_status_var.set(f"{len(self.filtered_games)} games shown.")
        index = 0
        remembered = self.config.get("last_selected_game") if self.config.get("remember_last_selected_game", True) else ""
        target_name = remembered if select_first and remembered else previous
        if target_name:
            for i, game in enumerate(self.filtered_games):
                if game["name"] == target_name:
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
        if self.current_game and self.current_game.get("name") == game.get("name"):
            return
        self.current_game = game
        self.selected_game_data = game
        if self.config.get("remember_last_selected_game", True):
            self.config["last_selected_game"] = game["name"]
            save_json_file(CONFIG_FILE, self.config)
        self.current_path = self.config.get("paths", {}).get(game["name"]) or None
        self.current_server_path = self.config.get("server_paths", {}).get(game["name"]) or None
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
        self.update_home_tab()
        self.update_tutorial_tab()
        self.update_network_tab()
        self.update_firewall_tab()
        self.update_path_tab()
        self.update_server_tab()
        self.update_lan_test_tab()
        self.update_invite_tab()
        self.update_backup_tab()
        self.update_mods_tab()
        self.update_input_isolation_tab()
        self.update_input_setup_tab()
        self.update_troubleshooting_tab()
        self.update_privacy_tab()
        self.render_games_page_details()

    def update_home_tab(self) -> None:
        lines = [
            "Offline LAN Games Helper",
            "Created by KiwiLiu",
            "",
            f"Selected game: {self.current_game['name'] if self.current_game else 'none'}",
            f"Primary LAN IPv4: {self.main_ip or 'not detected'}",
            "",
            "Quick actions:",
            "- Use Games to choose a title and launch details.",
            "- Use Invite for short connection info only.",
            "- Use Refresh Installed Detection when needed.",
            "",
            "Safety:",
            "- No DRM bypass, launcher bypass, authentication bypass, anti-cheat bypass, or online-service bypass.",
            "- No game file modification.",
        ]
        self.set_text(self.home_text, "\n".join(lines))

    def render_games_page_details(self) -> None:
        if not getattr(self, "games_detail_text", None):
            return
        game = self.current_game
        if not game:
            self.set_text(self.games_detail_text, "No game selected.")
            return
        cache_key = (game["name"], "static")
        cached = self.game_detail_cache.get(cache_key)
        if cached is None:
            lines = [
                f"Game: {game['name']}",
                f"LAN/offline status: {game['lan_status']}",
                "",
                "Tutorial:",
                self.format_list(game["host_tutorial"]),
                "",
                "Client join:",
                self.format_list(game["client_tutorial"]),
                "",
                "Server info:",
                f"- Server support: {game.get('server_support', 'none')}",
                self.format_ports(game.get("server_ports", [])),
                "",
                "Mods:",
                "- Use Mod List Export to compare files between players.",
                "",
                "Troubleshooting:",
                self.format_list(game["troubleshooting"]),
                "",
                "Safety notes:",
                "- This helper does not transform online-only games into LAN games.",
                "- No DRM/anti-cheat/authentication bypass.",
            ]
            cached = "\n".join(lines)
            self.game_detail_cache[cache_key] = cached
        dynamic_lines = [
            f"Network/IP: {self.selected_ip() or 'HOST_LAN_IP'}",
            f"Executable path: {self.current_path or 'not selected'}",
            "Note: Same LAN/VPN and matching version/mod state required.",
            "",
        ]
        self.games_page_title.configure(text=f"{game['name']} details")
        self.set_text(self.games_detail_text, "\n".join(dynamic_lines) + cached)

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
            f"Server process status: {self.server_status_text(game)}",
            f"SteamCMD path: {self.config.get('steamcmd_path') or 'not selected'}",
            f"SteamCMD app ID: {game.get('steamcmd_app_id') or 'none'}",
            f"Official download page: {game.get('official_download_url') or 'none'}",
            f"Offline Mode: {'enabled' if self.offline_mode_var.get() else 'disabled'}",
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

    def update_lan_test_tab(self) -> None:
        if not getattr(self, "lan_test_ip_var", None):
            return
        if not self.lan_test_ip_var.get() and self.selected_ip():
            self.lan_test_ip_var.set(self.selected_ip())
        if not self.lan_test_port_var.get() and self.current_game:
            port = first_tcp_port_value(first_port_range(self.current_game.get("ports", [])))
            if port:
                self.lan_test_port_var.set(str(port))
        lines = [
            "LAN Test / Connection Test",
            "",
            "Use this tab to test one IP address entered or selected by you.",
            "The helper does not scan IP ranges, the internet, or random addresses.",
            "",
            "Ping checks whether the host answers ICMP.",
            "TCP Port checks whether the selected game/server port accepts TCP connections.",
            "",
            f"Selected game: {self.current_game['name'] if self.current_game else 'none'}",
            f"Default ports: {self.format_ports(self.current_game.get('ports', []) if self.current_game else [])}",
        ]
        self.set_text(self.lan_test_result, "\n".join(lines))

    def update_invite_tab(self) -> None:
        if not getattr(self, "invite_text", None):
            return
        game = self.current_game
        if not game:
            self.set_text(self.invite_text, "No game selected.")
            return
        ip_values = [item.ip for item in self.addresses] or ([self.main_ip] if self.main_ip else [])
        self.invite_ip_combo.configure(values=ip_values)
        if not self.invite_host_ip_var.get().strip():
            self.invite_host_ip_var.set(self.selected_ip() or "HOST_LAN_IP")
        port_values = self.invite_port_values(game)
        self.invite_port_combo.configure(values=port_values)
        if not self.invite_port_var.get().strip() and port_values:
            self.invite_port_var.set(port_values[0])
        self.set_text(self.invite_text, self.build_invite_message(game))

    def update_backup_tab(self) -> None:
        if not getattr(self, "backup_text", None):
            return
        game = self.current_game
        folder = self.config.get("save_folders", {}).get(game["name"]) if game else ""
        self.save_folder_var.set(folder or "")
        lines = [
            "World / Save Backup",
            "",
            "Backups are timestamped .zip files stored under:",
            str(self.backup_root_path() / safe_filename(game["name"])) if game else str(self.backup_root_path()),
            "",
            "Restore extracts a selected backup into the selected save folder only after confirmation.",
            "The helper does not delete original saves during restore.",
        ]
        self.set_text(self.backup_text, "\n".join(lines))

    def update_mods_tab(self) -> None:
        if not getattr(self, "mods_text", None):
            return
        game = self.current_game
        folder = self.config.get("mod_folders", {}).get(game["name"]) if game else ""
        self.mod_folder_var.set(folder or "")
        lines = [
            "Mod List Export",
            "",
            "Select a mods folder to export file names, sizes, and modified dates.",
            "Players can compare exported lists before joining a modded LAN session.",
            "This app does not download or install mods.",
            "",
            f"Selected game: {game['name'] if game else 'none'}",
        ]
        self.set_text(self.mods_text, "\n".join(lines))

    def update_input_isolation_tab(self) -> None:
        if not getattr(self, "input_tools_text", None):
            return
        lines = [
            "Controller Visibility Checklist",
            "",
            "Windows games can see real controllers, virtual controllers, or both. If both are visible, you may get double input or one controller controlling multiple game instances.",
            "",
            "This helper does not block input directly. It helps you open safe configuration tools such as HidHide, DS4Windows, joy.cpl, and Nucleus Co-op.",
            "",
            INPUT_ISOLATION_SAFETY_TEXT,
            "",
            "HidHide Helper",
            HIDHIDE_CHECKLIST,
            "",
            "DS4Windows Helper",
            DS4WINDOWS_CHECKLIST,
            "",
            "Nucleus Co-op / Minecraft Java Helper",
            MINECRAFT_NUCLEUS_CHECKLIST,
            "",
            "joy.cpl Tool",
            "- Use Open Windows Game Controllers to see which controllers Windows currently exposes.",
        ]
        self.set_text(self.input_tools_text, "\n".join(lines))
        self.refresh_input_notes_tree()

    def update_input_setup_tab(self) -> None:
        if not getattr(self, "input_setup_text", None):
            return
        ds4 = self.find_ds4windows_exe()
        hidhide = self.find_hidhide_client()
        cli = self.find_hidhide_cli()
        self.ds4_status_var.set(f"DS4Windows.exe: {ds4 if ds4 else 'not configured or not found'}")
        self.hidhide_status_var.set(f"HidHideClient.exe: {hidhide if hidhide else 'not detected'}")
        self.hidhide_cli_status_var.set(f"HidHideCLI.exe: {cli if cli else 'not detected'}")
        last_test = self.config.get("input_isolation_profiles", {}).get("last_isolation_test", {})
        self.isolation_test_status_var.set(f"Last isolation test: {last_test.get('result', 'not run')}" if last_test else "Last isolation test: not run")
        controller_lines = self.detect_visible_controllers()
        lines = [
            "Apply Safe Input Isolation Setup",
            "",
            "When clicked, the setup action checks DS4Windows and HidHide paths, opens DS4Windows, opens HidHide Configuration Client, opens Windows Game Controllers, and shows this guided checklist.",
            "",
            HIDHIDE_CHECKLIST,
            "",
            "Nucleus Minecraft Profile",
            "Recommended:",
            "- Player 1: keyboard + mouse",
            "- Player 2: virtual Xbox controller from DS4Windows",
            "",
            "Warning:",
            "- Remove Controlify if one controller controls all Minecraft instances.",
            "- Do not use Controlify and MidnightControls together.",
            "",
            "Visible controller/device hints from safe Windows APIs:",
            *(controller_lines or ["- none detected by the safe device query"]),
            "",
            "Advanced HidHide CLI",
            "- Disabled by default.",
            "- Prefer opening HidHide GUI instead of CLI.",
            "- This app does not run CLI device-hiding commands automatically.",
            "- It only previews/copies commands and can run CLI help after confirmation.",
            "- Never target keyboard or mouse devices.",
        ]
        if self.advanced_hidhide_cli_var.get():
            lines.extend(
                [
                    "",
                    "Advanced Mode enabled:",
                    "Only use HidHide CLI if you understand HidHide's official syntax and have selected a real game controller device ID.",
                    f"Selected controller instance ID: {self.hidhide_cli_controller_var.get().strip() or 'none'}",
                    f"CLI command preview: {self.hidhide_cli_command_preview()}",
                ]
            )
        self.set_text(self.input_setup_text, "\n".join(lines))

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
        offline = self.offline_mode_var.get()
        for button in self.server_buttons.values():
            button.state(["!disabled"])
        if support in {"none", "in_game_host"}:
            for name in ["Open Server Folder", "Select Server Executable", "Launch Server", "Start Server", "Stop Server", "Open Server Log", "Install with SteamCMD", "Open Official Download Page"]:
                self.server_buttons[name].state(["disabled"])
        if not game.get("steamcmd_app_id"):
            self.server_buttons["Install with SteamCMD"].state(["disabled"])
        if not game.get("official_download_url"):
            self.server_buttons["Open Official Download Page"].state(["disabled"])
        if offline:
            self.server_buttons["Install with SteamCMD"].state(["disabled"])
            self.server_buttons["Open Official Download Page"].state(["disabled"])
        self.server_buttons["Export Server Guide"].state(["!disabled"])
        self.server_buttons["Select SteamCMD"].state(["!disabled"])

    def toggle_offline_mode(self) -> None:
        self.config["offline_mode"] = bool(self.offline_mode_var.get())
        save_json_file(CONFIG_FILE, self.config)
        self.update_server_tab()
        state = "enabled" if self.offline_mode_var.get() else "disabled"
        self.log(f"Offline Mode {state}. Optional internet/download actions are {'blocked' if self.offline_mode_var.get() else 'available'} when explicitly clicked.")

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
        self.installed_cache[game["name"]] = True
        self.config["installed_cache"] = self.installed_cache
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

    def use_selected_ip_for_test(self) -> None:
        value = self.selected_ip()
        if not value:
            messagebox.showwarning(APP_TITLE, "No private LAN IPv4 address was detected.")
            return
        self.lan_test_ip_var.set(value)
        self.log(f"LAN test target IP set to {value}.")

    def use_default_port_for_test(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        tcp_ports = [p for p in game.get("ports", []) if str(p.get("protocol", "")).upper() == "TCP"]
        port = first_tcp_port_value(first_port_range(tcp_ports or game.get("ports", [])))
        if not port:
            messagebox.showwarning(APP_TITLE, "No default TCP port is listed for this game.")
            return
        self.lan_test_port_var.set(str(port))
        self.log(f"LAN test TCP port set to {port}.")

    def ping_test(self) -> None:
        try:
            target = validate_single_ipv4(self.lan_test_ip_var.get())
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.set_text(self.lan_test_result, f"Pinging {target}...\n")

        def worker() -> None:
            try:
                completed = run_hidden(["ping.exe", "-n", "1", "-w", "1500", target], timeout=5)
                reachable = completed.returncode == 0
                output = completed.stdout.strip() or completed.stderr.strip()
                status = "reachable" if reachable else "not reachable"
                self.root.after(0, lambda: self.set_text(self.lan_test_result, f"Ping result for {target}: {status}\n\n{output}"))
                self.root.after(0, lambda: self.log(f"Ping {target}: {status}."))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror(APP_TITLE, f"Ping failed:\n{exc}"))
                self.root.after(0, lambda: self.log(f"Ping failed for {target}: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def tcp_port_test(self) -> None:
        try:
            target = validate_single_ipv4(self.lan_test_ip_var.get())
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        try:
            port = int(self.lan_test_port_var.get().strip())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror(APP_TITLE, "Enter a TCP port from 1 to 65535.")
            return
        self.set_text(self.lan_test_result, f"Testing TCP {target}:{port}...\n")

        def worker() -> None:
            try:
                with socket.create_connection((target, port), timeout=3):
                    pass
                self.root.after(0, lambda: self.set_text(self.lan_test_result, f"TCP {target}:{port} is reachable."))
                self.root.after(0, lambda: self.log(f"TCP {target}:{port} reachable."))
            except Exception as exc:
                self.root.after(0, lambda: self.set_text(self.lan_test_result, f"TCP {target}:{port} is not reachable.\n\n{exc}"))
                self.root.after(0, lambda: self.log(f"TCP {target}:{port} not reachable: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def invite_port_values(self, game: dict[str, Any]) -> list[str]:
        values: list[str] = []
        for entry in list(game.get("ports", [])) + list(game.get("server_ports", [])):
            port_range = str(entry.get("range", "")).strip()
            if not port_range:
                continue
            first = first_tcp_port_value(port_range)
            for candidate in (first, port_range):
                if candidate and candidate not in values:
                    values.append(str(candidate))
        return values

    def use_selected_ip_for_invite(self) -> None:
        value = self.selected_ip() or "HOST_LAN_IP"
        self.invite_host_ip_var.set(value)
        self.update_invite_tab()

    def use_default_port_for_invite(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        values = self.invite_port_values(game)
        if not values:
            messagebox.showwarning(APP_TITLE, "No default port is listed for this game.")
            return
        self.invite_port_var.set(values[0])
        self.update_invite_tab()

    def current_invite_address(self) -> tuple[str, str, str]:
        ip = self.invite_host_ip_var.get().strip() if hasattr(self, "invite_host_ip_var") else ""
        if not ip:
            ip = self.selected_ip() or "HOST_LAN_IP"
        port = self.invite_port_var.get().strip() if hasattr(self, "invite_port_var") else ""
        port_for_join = first_tcp_port_value(port) or port
        join = f"{ip}:{port_for_join}" if port_for_join else ip
        return ip, port, join

    def short_join_instruction(self, game: dict[str, Any], join_address: str) -> str:
        steps = [str(step).strip() for step in game.get("client_tutorial", []) if str(step).strip()]
        for step in steps:
            lowered = step.lower()
            if "direct" in lowered or "join" in lowered or "lan" in lowered or "ip" in lowered:
                return step.replace("HOST_LAN_IP", join_address)
        return f"Use the game's LAN/direct connect option and enter {join_address}."

    def build_invite_message(self, game: dict[str, Any], mode: str | None = None) -> str:
        mode_id = mode or self.invite_mode_key_from_label(getattr(self, "invite_mode_var", tk.StringVar(value="")).get())
        ip, port, join_address = self.current_invite_address()
        if mode_id == "ip_only":
            return ip
        if mode_id == "ip_port_only":
            return join_address
        how_to_join = self.short_join_instruction(game, join_address)
        note = (
            "Same LAN/VPN and same game/mod version required."
            if bool(self.config.get("include_lan_vpn_note", True))
            else "Same game/mod version required."
        )
        if mode_id == "short":
            return "\n".join(
                [
                    f"Game: {game['name']}",
                    f"Join: {join_address}",
                    f"How to join: {how_to_join}",
                    f"Note: {note}",
                ]
            )
        password = self.invite_password_var.get().strip() if hasattr(self, "invite_password_var") else ""
        lan_mode = self.invite_lan_mode_var.get().strip() if hasattr(self, "invite_lan_mode_var") else ""
        lines = [
            f"Game: {game['name']}",
            f"Join: {join_address}",
        ]
        if port:
            lines.append(f"Port: {port}")
        if password:
            lines.append(f"Password: {password}")
        if lan_mode:
            lines.append(f"Mode: {lan_mode}")
        lines.extend(
            [
                f"How to join: {how_to_join}",
                f"Note: {note}",
            ]
        )
        return "\n".join(lines)

    def copy_invite(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        text = self.build_invite_message(game)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo(APP_TITLE, self.tr("invite_copied"))
        self.log(f"Invite copied for {game['name']}.")

    def copy_invite_ip_only(self) -> None:
        ip, _port, _join = self.current_invite_address()
        self.root.clipboard_clear()
        self.root.clipboard_append(ip)
        self.log(f"Copied invite IP: {ip}")

    def copy_invite_ip_port_only(self) -> None:
        _ip, _port, join = self.current_invite_address()
        self.root.clipboard_clear()
        self.root.clipboard_append(join)
        self.log(f"Copied invite IP:Port: {join}")

    def copy_join_address(self) -> None:
        _ip, _port, join = self.current_invite_address()
        self.root.clipboard_clear()
        self.root.clipboard_append(join)
        self.log(f"Copied join address: {join}")

    def export_invite(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        export_dir = self.export_dir_path()
        export_dir.mkdir(parents=True, exist_ok=True)
        output = export_dir / f"{safe_filename(game['name'])}_Invite.txt"
        output.write_text(self.build_invite_message(game), encoding="utf-8")
        messagebox.showinfo(APP_TITLE, f"{self.tr('invite_exported')}\n{output}")
        self.log(f"Invite exported: {output}")

    def select_save_folder(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        folder = filedialog.askdirectory(title=f"Select save/world folder for {game['name']}")
        if not folder:
            self.log("Save folder selection canceled.")
            return
        self.config.setdefault("save_folders", {})[game["name"]] = folder
        save_json_file(CONFIG_FILE, self.config)
        self.save_folder_var.set(folder)
        self.log(f"Save folder selected for {game['name']}: {folder}")

    def create_save_backup(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        folder = Path(self.save_folder_var.get().strip() or self.config.get("save_folders", {}).get(game["name"], ""))
        if not folder.exists() or not folder.is_dir():
            messagebox.showerror(APP_TITLE, "Select an existing save folder first.")
            return
        destination = self.backup_root_path() / safe_filename(game["name"])
        destination.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        output = destination / f"{safe_filename(folder.name)}_{stamp}.zip"
        self.log(f"Creating backup: {output}")

        def worker() -> None:
            try:
                with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    for path in folder.rglob("*"):
                        if path.is_file():
                            archive.write(path, path.relative_to(folder))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror(APP_TITLE, f"Backup failed:\n{exc}"))
                self.root.after(0, lambda: self.log(f"Backup failed: {exc}"))
                return
            self.root.after(0, lambda: messagebox.showinfo(APP_TITLE, f"Backup created:\n{output}"))
            self.root.after(0, lambda: self.log(f"Backup created: {output}"))

        threading.Thread(target=worker, daemon=True).start()

    def restore_save_backup(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        folder = Path(self.save_folder_var.get().strip() or self.config.get("save_folders", {}).get(game["name"], ""))
        if not folder.exists() or not folder.is_dir():
            messagebox.showerror(APP_TITLE, "Select an existing restore target save folder first.")
            return
        backup = filedialog.askopenfilename(
            title=f"Select backup zip for {game['name']}",
            initialdir=str(self.backup_root_path() / safe_filename(game["name"])),
            filetypes=[("Zip backups", "*.zip"), ("All files", "*.*")],
        )
        if not backup:
            self.log("Restore canceled.")
            return
        if not messagebox.askyesno(
            APP_TITLE,
            "Restore this backup into the selected save folder?\n\n"
            f"Backup: {backup}\nTarget: {folder}\n\n"
            "Existing files with the same names may be overwritten. Original saves are not deleted by this helper.",
        ):
            self.log("Restore canceled by user.")
            return
        def worker() -> None:
            try:
                with zipfile.ZipFile(backup, "r") as archive:
                    safe_extract_zip(archive, folder)
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror(APP_TITLE, f"Restore failed:\n{exc}"))
                self.root.after(0, lambda: self.log(f"Restore failed: {exc}"))
                return
            self.root.after(0, lambda: messagebox.showinfo(APP_TITLE, f"Backup restored into:\n{folder}"))
            self.root.after(0, lambda: self.log(f"Backup restored from {backup} into {folder}."))

        threading.Thread(target=worker, daemon=True).start()

    def select_mod_folder(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        folder = filedialog.askdirectory(title=f"Select mods folder for {game['name']}")
        if not folder:
            self.log("Mods folder selection canceled.")
            return
        self.config.setdefault("mod_folders", {})[game["name"]] = folder
        save_json_file(CONFIG_FILE, self.config)
        self.mod_folder_var.set(folder)
        self.log(f"Mods folder selected for {game['name']}: {folder}")

    def export_mod_list(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        folder = Path(self.mod_folder_var.get().strip() or self.config.get("mod_folders", {}).get(game["name"], ""))
        if not folder.exists() or not folder.is_dir():
            messagebox.showerror(APP_TITLE, "Select an existing mods folder first.")
            return
        files = sorted([path for path in folder.iterdir() if path.is_file()], key=lambda p: p.name.lower())
        export_dir = self.export_dir_path()
        export_dir.mkdir(parents=True, exist_ok=True)
        output = export_dir / f"{safe_filename(game['name'])}_Mod_List.md"
        lines = [
            f"# {game['name']} - Mod List",
            "",
            f"Mods folder: {folder}",
            f"Exported: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Compare this list with every player before joining a modded LAN session.",
            "This helper does not download, install, or update mods.",
            "",
            "## Files",
        ]
        if files:
            for path in files:
                stat = path.stat()
                modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
                lines.append(f"- {path.name} ({stat.st_size} bytes, modified {modified})")
        else:
            lines.append("- no files found")
        output.write_text("\n".join(lines), encoding="utf-8")
        messagebox.showinfo(APP_TITLE, f"Mod list exported:\n{output}")
        self.log(f"Mod list exported: {output}")

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

    def refresh_input_processes(self) -> None:
        self.process_rows = enumerate_processes()
        self.input_process_tree.delete(*self.input_process_tree.get_children())
        for process in self.process_rows:
            self.input_process_tree.insert("", tk.END, values=(process.name, process.pid, process.path, process.category))
        self.log(f"Input Isolation: refreshed {len(self.process_rows)} running processes.")

    def selected_input_process_values(self) -> tuple[str, str, str, str] | None:
        selection = self.input_process_tree.selection()
        if not selection:
            messagebox.showwarning(APP_TITLE, "Select a process first.")
            return None
        values = self.input_process_tree.item(selection[0], "values")
        if len(values) < 4:
            messagebox.showwarning(APP_TITLE, "Selected process information is incomplete.")
            return None
        return str(values[0]), str(values[1]), str(values[2]), str(values[3])

    def load_selected_process_into_notes(self) -> None:
        selection = self.input_process_tree.selection()
        if not selection:
            return
        values = self.input_process_tree.item(selection[0], "values")
        if len(values) < 4:
            return
        name, pid, path, category = map(str, values[:4])
        self.input_selected_process_var.set(f"Selected process: {name} PID {pid} ({category})")
        if not self.input_role_var.get().strip():
            self.input_role_var.set(category if category != "Other" else "")
        if name.lower() in {"javaw.exe", "java.exe", "minecraft.exe"}:
            self.input_keyboard_var.set(True)
        if name.lower() == "ds4windows.exe":
            self.input_controller_var.set(True)
            self.input_virtual_xbox_var.set(True)
        self.log(f"Input Isolation: selected process {name} PID {pid}.")

    def selected_note_text(self) -> str:
        return self.input_notes_text.get("1.0", tk.END).strip()

    def input_state_summary(self) -> str:
        parts = []
        if self.input_keyboard_var.get():
            parts.append("Keyboard + Mouse")
        if self.input_controller_var.get():
            parts.append("Controller")
        if self.input_ignore_ps_var.get():
            parts.append("Ignore real PlayStation controller")
        if self.input_virtual_xbox_var.get():
            parts.append("Use virtual Xbox controller")
        return "; ".join(parts) if parts else "No input target selected"

    def copy_selected_process_info(self) -> None:
        values = self.selected_input_process_values()
        if not values:
            return
        name, pid, path, category = values
        text = f"Process: {name}\nPID: {pid}\nPath: {path}\nCategory: {category}"
        self.copy_text_to_clipboard("selected process info", text)

    def open_selected_process_location(self) -> None:
        values = self.selected_input_process_values()
        if not values:
            return
        _name, _pid, path, _category = values
        if not path or path == "Access denied or unavailable" or not Path(path).exists():
            messagebox.showwarning(APP_TITLE, "Executable path is not available for this process.")
            return
        subprocess.Popen(["explorer.exe", "/select,", path], **create_no_window_kwargs())
        self.log(f"Opened process file location: {path}")

    def add_selected_process_to_notes(self) -> None:
        values = self.selected_input_process_values()
        if not values:
            return
        self.load_selected_process_into_notes()
        if not self.input_role_var.get().strip():
            self.input_role_var.set(values[3] if values[3] != "Other" else "Local multiplayer process")
        self.save_input_process_note()

    def mark_selected_process_role(self, role: str) -> None:
        if not self.selected_input_process_values():
            return
        self.load_selected_process_into_notes()
        self.input_role_var.set(role)
        self.save_input_process_note()

    def save_input_process_note(self) -> None:
        values = self.selected_input_process_values()
        if not values:
            return
        name, pid, path, category = values
        note = {
            "process_name": name,
            "pid": pid,
            "path": path,
            "category": category,
            "role": self.input_role_var.get().strip() or category,
            "keyboard_mouse": bool(self.input_keyboard_var.get()),
            "controller": bool(self.input_controller_var.get()),
            "ignore_real_playstation": bool(self.input_ignore_ps_var.get()),
            "virtual_xbox": bool(self.input_virtual_xbox_var.get()),
            "notes": self.selected_note_text(),
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        notes = [item for item in self.config.get("input_isolation_notes", []) if not (str(item.get("process_name")) == name and str(item.get("pid")) == pid)]
        notes.append(note)
        self.config["input_isolation_notes"] = notes
        save_json_file(CONFIG_FILE, self.config)
        self.refresh_input_notes_tree()
        self.log(f"Input Isolation note saved for {name} PID {pid}.")

    def refresh_input_notes_tree(self) -> None:
        if not getattr(self, "input_notes_tree", None):
            return
        self.input_notes_tree.delete(*self.input_notes_tree.get_children())
        for index, note in enumerate(self.config.get("input_isolation_notes", [])):
            input_bits = []
            if note.get("keyboard_mouse"):
                input_bits.append("Keyboard + Mouse")
            if note.get("controller"):
                input_bits.append("Controller")
            if note.get("ignore_real_playstation"):
                input_bits.append("Ignore real PS")
            if note.get("virtual_xbox"):
                input_bits.append("Virtual Xbox")
            self.input_notes_tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=(
                    note.get("process_name", ""),
                    note.get("pid", ""),
                    note.get("role", ""),
                    "; ".join(input_bits) if input_bits else "No input target selected",
                ),
            )

    def load_selected_input_note(self) -> None:
        selection = self.input_notes_tree.selection()
        if not selection:
            return
        try:
            note = self.config.get("input_isolation_notes", [])[int(selection[0])]
        except (ValueError, IndexError):
            return
        self.input_selected_process_var.set(f"Selected process: {note.get('process_name', '')} PID {note.get('pid', '')} ({note.get('category', '')})")
        self.input_role_var.set(str(note.get("role", "")))
        self.input_keyboard_var.set(bool(note.get("keyboard_mouse")))
        self.input_controller_var.set(bool(note.get("controller")))
        self.input_ignore_ps_var.set(bool(note.get("ignore_real_playstation")))
        self.input_virtual_xbox_var.set(bool(note.get("virtual_xbox")))
        self.input_notes_text.delete("1.0", tk.END)
        self.input_notes_text.insert("1.0", str(note.get("notes", "")))

    def delete_selected_input_note(self) -> None:
        selection = self.input_notes_tree.selection()
        if not selection:
            messagebox.showwarning(APP_TITLE, "Select a note first.")
            return
        if not messagebox.askyesno(APP_TITLE, "Delete the selected local input note?"):
            return
        try:
            index = int(selection[0])
        except ValueError:
            return
        notes = list(self.config.get("input_isolation_notes", []))
        if 0 <= index < len(notes):
            removed = notes.pop(index)
            self.config["input_isolation_notes"] = notes
            save_json_file(CONFIG_FILE, self.config)
            self.refresh_input_notes_tree()
            self.log(f"Deleted input note for {removed.get('process_name', 'process')}.")

    def build_input_notes_export(self) -> str:
        lines = [
            "# Input Isolation Notes",
            "",
            INPUT_ISOLATION_SAFETY_TEXT,
            "",
        ]
        for note in self.config.get("input_isolation_notes", []):
            lines.extend(
                [
                    f"## {note.get('process_name', '')} PID {note.get('pid', '')}",
                    "",
                    f"Path: {note.get('path', '')}",
                    f"Category: {note.get('category', '')}",
                    f"Role: {note.get('role', '')}",
                    f"Input: {self.input_note_summary(note)}",
                    "",
                    str(note.get("notes", "")),
                    "",
                ]
            )
        return "\n".join(lines).strip()

    def input_note_summary(self, note: dict[str, Any]) -> str:
        parts = []
        if note.get("keyboard_mouse"):
            parts.append("Keyboard + Mouse")
        if note.get("controller"):
            parts.append("Controller")
        if note.get("ignore_real_playstation"):
            parts.append("Ignore real PlayStation controller")
        if note.get("virtual_xbox"):
            parts.append("Use virtual Xbox controller")
        return "; ".join(parts) if parts else "No input target selected"

    def copy_all_input_notes(self) -> None:
        self.copy_text_to_clipboard("input isolation notes", self.build_input_notes_export())

    def copy_text_to_clipboard(self, label: str, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo(APP_TITLE, f"Copied {label}.")
        self.log(f"Copied {label}.")

    def find_ds4windows_exe(self) -> Path | None:
        configured = self.config.get("ds4windows_path", "")
        if configured and Path(configured).exists():
            return Path(configured)
        for process in self.process_rows:
            if process.name.lower() == "ds4windows.exe" and process.path != "Access denied or unavailable":
                path = Path(process.path)
                if path.exists():
                    return path
        return None

    def hidhide_client_candidates(self) -> list[Path]:
        candidates = [
            Path(r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideClient.exe"),
            Path(r"C:\Program Files\Nefarius Software Solutions\HidHide\HidHideClient.exe"),
            Path(r"C:\Program Files (x86)\Nefarius Software Solutions\HidHide\x64\HidHideClient.exe"),
        ]
        configured = self.config.get("hidhide_client_path", "")
        if configured:
            candidates.insert(0, Path(configured))
        command = (
            "$paths=@(); "
            "$keys=@('HKLM:\\SOFTWARE\\Nefarius Software Solutions e.U.\\Nefarius Software Solutions e.U. HidHide',"
            "'HKCR:\\SOFTWARE\\Nefarius Software Solutions e.U.\\Nefarius Software Solutions e.U. HidHide'); "
            "foreach($key in $keys){ try { $p=(Get-ItemProperty -Path $key -Name Path -ErrorAction Stop).Path; if($p){$paths += $p} } catch {} }; "
            "$paths | ConvertTo-Json -Compress"
        )
        completed = run_powershell(command, timeout=10)
        if completed.returncode == 0 and completed.stdout.strip():
            try:
                raw = json.loads(completed.stdout)
                values = raw if isinstance(raw, list) else [raw]
                for value in values:
                    if not value:
                        continue
                    path = Path(str(value))
                    candidates.append(path / "HidHideClient.exe" if path.is_dir() or not path.suffix else path)
            except json.JSONDecodeError:
                pass
        return candidates

    def find_hidhide_client(self) -> Path | None:
        for candidate in self.hidhide_client_candidates():
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate
            except OSError:
                continue
        return None

    def hidhide_cli_candidates(self) -> list[Path]:
        candidates = []
        configured = self.config.get("hidhide_cli_path", "")
        if configured:
            candidates.append(Path(configured))
        for client in self.hidhide_client_candidates():
            candidates.append(client.with_name("HidHideCLI.exe"))
        candidates.extend(
            [
                Path(r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe"),
                Path(r"C:\Program Files\Nefarius Software Solutions\HidHide\HidHideCLI.exe"),
                Path(r"C:\Program Files (x86)\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe"),
            ]
        )
        return candidates

    def find_hidhide_cli(self) -> Path | None:
        for candidate in self.hidhide_cli_candidates():
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate
            except OSError:
                continue
        return None

    def check_hidhide_installed(self) -> None:
        client = self.find_hidhide_client()
        if client:
            messagebox.showinfo(APP_TITLE, f"HidHide Configuration Client found:\n{client}")
            self.log(f"HidHide found: {client}")
            return
        messagebox.showwarning(APP_TITLE, "HidHide Configuration Client was not found in common locations. Use the official page button for setup information.")
        self.log("HidHide not found in common locations.")

    def open_hidhide_client(self) -> None:
        client = self.find_hidhide_client()
        if not client:
            messagebox.showwarning(APP_TITLE, "HidHide Configuration Client was not found. Install HidHide from the official Nefarius page, then try again.")
            return
        os.startfile(str(client))  # type: ignore[attr-defined]
        self.log(f"Opened HidHide Configuration Client: {client}")

    def select_hidhide_client_exe(self) -> None:
        path = filedialog.askopenfilename(title="Select HidHideClient.exe", filetypes=[("HidHideClient.exe", "HidHideClient.exe"), ("Windows executable", "*.exe"), ("All files", "*.*")])
        if not path:
            self.log("HidHideClient selection canceled.")
            return
        if Path(path).name.lower() != "hidhideclient.exe":
            messagebox.showerror(APP_TITLE, "Please select HidHideClient.exe.")
            return
        self.config["hidhide_client_path"] = path
        cli = Path(path).with_name("HidHideCLI.exe")
        if cli.exists():
            self.config["hidhide_cli_path"] = str(cli)
        save_json_file(CONFIG_FILE, self.config)
        self.update_input_setup_tab()
        self.log(f"Saved HidHideClient path: {path}")

    def select_ds4windows_exe(self) -> None:
        path = filedialog.askopenfilename(title="Select DS4Windows.exe", filetypes=[("DS4Windows.exe", "DS4Windows.exe"), ("Windows executable", "*.exe"), ("All files", "*.*")])
        if not path:
            self.log("DS4Windows selection canceled.")
            return
        if Path(path).name.lower() != "ds4windows.exe":
            messagebox.showerror(APP_TITLE, "Please select DS4Windows.exe.")
            return
        self.config["ds4windows_path"] = path
        save_json_file(CONFIG_FILE, self.config)
        self.update_input_setup_tab()
        self.log(f"Saved DS4Windows path: {path}")

    def open_ds4windows(self) -> None:
        detected = self.find_ds4windows_exe()
        if not detected:
            messagebox.showwarning(APP_TITLE, "Select DS4Windows.exe first.")
            return
        self.config["ds4windows_path"] = str(detected)
        save_json_file(CONFIG_FILE, self.config)
        os.startfile(str(detected))  # type: ignore[attr-defined]
        self.log(f"Opened DS4Windows: {detected}")

    def open_windows_game_controllers(self) -> None:
        subprocess.Popen(["control.exe", "joy.cpl"], **create_no_window_kwargs())
        self.log("Opened Windows Game Controllers (joy.cpl).")

    def open_official_input_tool_page(self, url: str) -> None:
        if self.offline_mode_var.get():
            messagebox.showinfo(APP_TITLE, "Offline Mode is enabled. Optional official tool pages are disabled.")
            self.log("Official input tool page blocked by Offline Mode.")
            return
        webbrowser.open(url)
        self.log(f"Opened official input tool page: {url}")

    def detect_input_setup_tools(self) -> None:
        self.refresh_input_processes()
        ds4 = self.find_ds4windows_exe()
        hidhide = self.find_hidhide_client()
        cli = self.find_hidhide_cli()
        if ds4:
            self.config["ds4windows_path"] = str(ds4)
        if hidhide:
            self.config["hidhide_client_path"] = str(hidhide)
        if cli:
            self.config["hidhide_cli_path"] = str(cli)
        save_json_file(CONFIG_FILE, self.config)
        self.update_input_setup_tab()
        self.log("Input setup tool detection completed.")

    def detect_visible_controllers(self) -> list[str]:
        command = (
            "Get-CimInstance Win32_PnPEntity | "
            "Where-Object { $_.Name -match 'controller|gamepad|xbox|dualshock|dualsense|wireless controller' } | "
            "Select-Object Name,PNPDeviceID,Status | ConvertTo-Json -Compress -Depth 2"
        )
        completed = run_powershell(command, timeout=20)
        if completed.returncode != 0 or not completed.stdout.strip():
            return []
        try:
            raw = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return []
        rows = raw if isinstance(raw, list) else [raw]
        lines = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("Name") or "Unknown device")
            status = str(row.get("Status") or "unknown")
            device_id = str(row.get("PNPDeviceID") or "")
            lines.append(f"- {name} [{status}] {device_id}")
        return lines

    def refresh_visible_controllers(self) -> None:
        controllers = self.detect_visible_controllers()
        if controllers:
            if not self.hidhide_cli_controller_var.get().strip():
                first = controllers[0].split("] ", 1)[-1].strip()
                self.hidhide_cli_controller_var.set(first)
            messagebox.showinfo(APP_TITLE, f"Detected {len(controllers)} controller-like device entries. The setup text has been refreshed.")
            self.log(f"Detected {len(controllers)} controller-like device entries.")
        else:
            messagebox.showinfo(APP_TITLE, "No controller-like devices were detected by the safe Windows device query.")
            self.log("No controller-like devices detected by safe query.")
        self.update_input_setup_tab()

    def generated_input_setup_steps(self) -> str:
        return "\n\n".join(
            [
                "Apply Safe Input Isolation Setup",
                HIDHIDE_CHECKLIST,
                "Nucleus Minecraft Profile:\n- Player 1: keyboard + mouse\n- Player 2: virtual Xbox controller from DS4Windows\n- Remove Controlify if one controller controls all Minecraft instances.\n- Do not use Controlify and MidnightControls together.",
                INPUT_ISOLATION_SAFETY_TEXT,
            ]
        )

    def apply_safe_input_isolation_setup(self) -> None:
        ds4 = self.find_ds4windows_exe()
        if not ds4:
            messagebox.showwarning(APP_TITLE, "DS4Windows.exe path is not configured. Select DS4Windows.exe first.")
            return
        hidhide = self.find_hidhide_client()
        if not hidhide:
            messagebox.showwarning(APP_TITLE, "HidHideClient.exe was not found. Install HidHide or select HidHideClient.exe first.")
            return
        self.config["ds4windows_path"] = str(ds4)
        self.config["hidhide_client_path"] = str(hidhide)
        self.config.setdefault("input_isolation_profiles", {})["safe_setup"] = {
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ds4windows_path": str(ds4),
            "hidhide_client_path": str(hidhide),
            "steps": HIDHIDE_CHECKLIST,
        }
        save_json_file(CONFIG_FILE, self.config)
        os.startfile(str(ds4))  # type: ignore[attr-defined]
        os.startfile(str(hidhide))  # type: ignore[attr-defined]
        self.open_windows_game_controllers()
        self.set_text(self.input_setup_text, self.generated_input_setup_steps())
        messagebox.showinfo(APP_TITLE, "Opened DS4Windows, HidHide Configuration Client, and Windows Game Controllers. Follow the checklist shown in the setup tab.")
        self.log("Applied safe input isolation setup by opening approved external tools and showing checklist.")

    def test_input_isolation(self) -> None:
        self.open_windows_game_controllers()
        result = "confirmed virtual Xbox only" if messagebox.askyesno(
            APP_TITLE,
            "Look at Windows Game Controllers.\n\nIs only the virtual Xbox controller visible to normal apps?",
        ) else "needs review"
        self.config.setdefault("input_isolation_profiles", {})["last_isolation_test"] = {
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "result": result,
        }
        save_json_file(CONFIG_FILE, self.config)
        self.update_input_setup_tab()
        self.log(f"Isolation test saved: {result}.")

    def save_nucleus_minecraft_profile(self) -> None:
        profile = {
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "game": "Minecraft Java",
            "tool": "Nucleus Co-op",
            "player_1": "Keyboard + Mouse",
            "player_2": "Virtual Xbox controller from DS4Windows",
            "warnings": [
                "Remove Controlify if one controller controls all Minecraft instances.",
                "Do not use Controlify and MidnightControls together.",
            ],
            "safety": "Profile is local notes only. This app does not block input or modify games.",
        }
        self.config.setdefault("input_isolation_profiles", {})["nucleus_minecraft"] = profile
        save_json_file(CONFIG_FILE, self.config)
        self.update_input_setup_tab()
        messagebox.showinfo(APP_TITLE, "Saved local Nucleus Minecraft input profile.")
        self.log("Saved Nucleus Minecraft input profile.")

    def copy_generated_input_setup_steps(self) -> None:
        self.copy_text_to_clipboard("safe input isolation setup steps", self.generated_input_setup_steps())

    def hidhide_cli_command_preview(self) -> str:
        cli = self.find_hidhide_cli()
        if not cli:
            return "HidHideCLI.exe was not found."
        controller_id = self.hidhide_cli_controller_var.get().strip()
        if not self.advanced_hidhide_cli_var.get():
            return f'"{cli}" --help'
        if not controller_id:
            return f'"{cli}" --help  # Select a real game controller instance ID before considering any device-specific CLI command.'
        if any(word in controller_id.lower() for word in ["keyboard", "mouse"]):
            return "Blocked: keyboard and mouse devices must never be targeted."
        return f'"{cli}" --help  # Use HidHide GUI for actual hiding. Selected controller reference: {controller_id}'

    def copy_hidhide_cli_command_preview(self) -> None:
        self.copy_text_to_clipboard("HidHide CLI command preview", self.hidhide_cli_command_preview())

    def run_hidhide_cli_help(self) -> None:
        cli = self.find_hidhide_cli()
        if not cli:
            messagebox.showwarning(APP_TITLE, "HidHideCLI.exe was not found.")
            return
        command_text = f'"{cli}" --help'
        if not messagebox.askyesno(APP_TITLE, f"Run this read-only HidHide CLI help command?\n\n{command_text}\n\nNo device hiding command will be run."):
            self.log("HidHide CLI help canceled by user.")
            return
        completed = run_hidden([str(cli), "--help"], timeout=20)
        output = (completed.stdout or completed.stderr or "").strip()
        if not output:
            fallback = run_hidden([str(cli), "/?"], timeout=20)
            output = (fallback.stdout or fallback.stderr or "").strip()
        self.set_text(self.input_setup_text, f"HidHide CLI help output:\n\n{output or 'No output returned.'}")
        self.log("Ran HidHide CLI help command only.")

    def toggle_input_advanced_text(self) -> None:
        if self.input_advanced_var.get():
            self.input_advanced_text.grid()
        else:
            self.input_advanced_text.grid_remove()

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

    def server_status_text(self, game: dict[str, Any]) -> str:
        process = self.server_processes.get(game["name"])
        if process and process.poll() is None:
            return f"running (PID {process.pid}, started by this app)"
        if process:
            return f"stopped (last exit code {process.returncode})"
        return "stopped"

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

    def start_managed_server(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        if game["server_support"] in {"none", "in_game_host"}:
            messagebox.showinfo(APP_TITLE, "No supported dedicated server is available for this game. Host from inside the game if supported.")
            return
        existing = self.server_processes.get(game["name"])
        if existing and existing.poll() is None:
            messagebox.showinfo(APP_TITLE, f"Server is already running with PID {existing.pid}.")
            return
        path = self.current_server_path or self.find_server_path(game)
        if not path or not Path(path).exists():
            messagebox.showwarning(APP_TITLE, "Select an official local server executable/file first.")
            return
        cwd = str(Path(path).parent)
        try:
            if Path(path).suffix.lower() in {".bat", ".cmd"}:
                args = ["cmd.exe", "/c", path]
            elif Path(path).suffix.lower() == ".jar":
                args = ["java.exe", "-jar", path]
            else:
                args = [path]
            process = subprocess.Popen(args, cwd=cwd, **create_no_window_kwargs())
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not start server:\n{exc}")
            self.log(f"Could not start server: {exc}")
            return
        self.server_processes[game["name"]] = process
        self.update_server_tab()
        self.log(f"Started server for {game['name']} with PID {process.pid}.")

    def stop_managed_server(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        process = self.server_processes.get(game["name"])
        if not process or process.poll() is not None:
            messagebox.showinfo(APP_TITLE, "No server process started by this app is currently running for this game.")
            self.update_server_tab()
            return
        if not messagebox.askyesno(APP_TITLE, f"Stop the server process started by this app?\n\nPID: {process.pid}\nGame: {game['name']}"):
            self.log("Server stop canceled by user.")
            return
        try:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not stop server:\n{exc}")
            self.log(f"Could not stop server: {exc}")
            return
        self.update_server_tab()
        self.log(f"Stopped server process for {game['name']}.")

    def open_server_log(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        configured = self.config.get("server_log_paths", {}).get(game["name"], "")
        candidates: list[Path] = []
        if configured:
            candidates.append(Path(configured))
        base_path = self.current_server_path or self.config.get("server_install_dirs", {}).get(game["name"], "")
        if base_path:
            folder = Path(base_path).parent if Path(base_path).suffix else Path(base_path)
            if folder.exists():
                candidates.extend(sorted(folder.rglob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:5])
                candidates.extend(sorted(folder.rglob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)[:5])
        for path in candidates:
            if path.exists() and path.is_file():
                os.startfile(str(path))  # type: ignore[attr-defined]
                self.log(f"Opened server log: {path}")
                return
        selected = filedialog.askopenfilename(title=f"Select server log for {game['name']}", filetypes=[("Log files", "*.log *.txt"), ("All files", "*.*")])
        if selected:
            self.config.setdefault("server_log_paths", {})[game["name"]] = selected
            save_json_file(CONFIG_FILE, self.config)
            os.startfile(selected)  # type: ignore[attr-defined]
            self.log(f"Opened selected server log: {selected}")
        else:
            self.log("No server log selected.")

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
        if self.offline_mode_var.get():
            messagebox.showinfo(APP_TITLE, "Offline Mode is enabled. Optional SteamCMD downloads are disabled.")
            self.log("SteamCMD install blocked by Offline Mode.")
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
        if self.offline_mode_var.get():
            messagebox.showinfo(APP_TITLE, "Offline Mode is enabled. Optional official download pages are disabled.")
            self.log("Official download page blocked by Offline Mode.")
            return
        url = game.get("official_download_url", "")
        if not url:
            messagebox.showinfo(APP_TITLE, "No official download page is configured for this game.")
            return
        webbrowser.open(url)
        self.log(f"Opened official download page: {url}")

    def open_paypal_donation(self) -> None:
        if self.offline_mode_var.get():
            messagebox.showinfo(APP_TITLE, DONATION_OFFLINE_MESSAGE)
            self.log(DONATION_OFFLINE_MESSAGE)
            return
        webbrowser.open(PAYPAL_DONATION_URL)
        self.log(f"Opened optional donation link: {PAYPAL_DONATION_URL}")

    def open_github_sponsors(self) -> None:
        if self.offline_mode_var.get():
            messagebox.showinfo(APP_TITLE, DONATION_OFFLINE_MESSAGE)
            self.log(DONATION_OFFLINE_MESSAGE)
            return
        webbrowser.open(GITHUB_SPONSORS_URL)
        self.log(f"Opened optional sponsor link: {GITHUB_SPONSORS_URL}")

    def copy_donation_link(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(PAYPAL_DONATION_URL)
        messagebox.showinfo(APP_TITLE, f"Donation link copied:\n{PAYPAL_DONATION_URL}")
        self.log("Copied optional donation link.")

    def export_tutorial(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        export_dir = self.export_dir_path()
        export_dir.mkdir(parents=True, exist_ok=True)
        output = export_dir / f"{safe_filename(game['name'])}_LAN_Tutorial.md"
        output.write_text(self.build_export_text(game, include_server=True), encoding="utf-8")
        messagebox.showinfo(APP_TITLE, f"Tutorial exported:\n{output}")
        self.log(f"Tutorial exported: {output}")

    def export_server_guide(self) -> None:
        game = self.selected_game_required()
        if not game:
            return
        export_dir = self.export_dir_path()
        export_dir.mkdir(parents=True, exist_ok=True)
        output = export_dir / f"{safe_filename(game['name'])}_Server_Guide.md"
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
