# Offline LAN Games Helper - Windows

Offline LAN Games Helper is a safe Windows GUI utility for LAN/offline multiplayer games that you legally own. It helps with host IP discovery, Windows Firewall rules, normal game launching, LAN tutorials, and official dedicated server tools where a real supported server option exists.

This app is not a server emulator. It does not bypass DRM, Steam, Epic, Paradox Launcher, authentication, ownership checks, anti-cheat, online services, or licenses. It does not create cracks, loaders, Steam emulators, patched executables, hooks, injectors, modified game files, or offline-service emulators.

## What The App Does

- Shows the host PC hostname and private LAN IPv4 addresses.
- Warns when multiple LAN/VPN adapters may confuse IP selection.
- Lets you copy the selected host IP for friends.
- Detects installed game executables from common paths and Steam libraries.
- Saves manually selected game paths in `user_config.json`.
- Launches selected games normally.
- Adds/removes Windows Firewall rules created only by this helper.
- Shows English LAN tutorials, troubleshooting, ports, and compatibility notes.
- Exports a Markdown guide for the selected game.
- Helps with official dedicated server tools only when supported.

## What The App Cannot Do

- It cannot turn online-only games into LAN games.
- It cannot emulate matchmaking, account services, Steam, Epic, Paradox, or other online services.
- It cannot bypass ownership checks or anti-cheat.
- It cannot modify original game files.
- It cannot create a dedicated server for games that only support in-game hosting.

## Run From Source

Open PowerShell in this folder:

```powershell
cd "C:\Users\liuqi\Desktop\Windows OfflineLan Helper"
.\.venv\Scripts\python.exe .\lan_games_helper.py
```

If `.venv` does not exist yet, create it first:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

The app itself uses only the Python standard library. `pillow` and `pyinstaller` are only needed for icon generation and building the executable.

## Build The Windows EXE

Run:

```powershell
cd "C:\Users\liuqi\Desktop\Windows OfflineLan Helper"
.\build_exe.ps1
```

The build script:

- creates or uses `.venv`;
- installs `pyinstaller` and `pillow`;
- generates `assets\offline_lan_helper.ico` if needed;
- builds with `--onefile --windowed --noconsole`;
- checks that the generated `.spec` uses `console=False`;
- copies `games.json` and `user_config.json` beside the executable.

The final executable is created here:

```text
C:\Users\liuqi\Desktop\Windows OfflineLan Helper\dist\Offline LAN Games Helper.exe
```

The executable is built as a GUI app and should not open a terminal window.

## Administrator Mode

Administrator rights are required only for Windows Firewall changes.

To run as Administrator:

1. Right-click PowerShell or the built `.exe`.
2. Choose `Run as administrator`.
3. Use `Add Firewall Rules` or `Remove Firewall Rules`.

If the app is not elevated, it shows:

```text
Run as Administrator to change Windows Firewall rules.
```

The app should remain open and should not crash.

## Firewall Rules

Rules are added only for the selected game.

Rule names:

```text
Offline LAN Helper - GAME_NAME - EXE TCP
Offline LAN Helper - GAME_NAME - EXE UDP
Offline LAN Helper - GAME_NAME - Ports TCP
Offline LAN Helper - GAME_NAME - Ports UDP
```

`Remove Firewall Rules` removes only rules with those helper-created names. It does not touch unrelated Windows Firewall rules.

## Server Tools

The `Server Tools` tab is intentionally conservative.

Supported server support types:

- `none`: no supported dedicated server; use in-game hosting if available.
- `in_game_host`: host from inside the game.
- `official_dedicated`: launch or select an official dedicated server executable already installed.
- `steamcmd`: install with SteamCMD only if `games.json` contains a verified official app ID and the user selects SteamCMD.
- `manual_files`: use user-provided local official server files.
- `official_download_page`: open the official download page in a browser.

SteamCMD is used normally. The app does not bundle, emulate, patch, or bypass SteamCMD. If a server requires a purchased game or a logged-in account, follow the official game/server documentation.

Servers are installed under:

```text
servers\GAME_NAME
```

Only official SteamCMD app IDs should be added to `games.json`. If an app ID is not verified, leave it blank and use manual files or an official download page instead.

## Add A Custom Game

Use `Add Custom Game` to add a game that is not in `games.json`.

You can enter:

- game name;
- executable path;
- optional ports;
- host tutorial;
- client tutorial;
- server support type;
- optional server executable path;
- notes.

Custom games are saved in `user_config.json`. The app never edits the built-in `games.json` when adding a custom game.

## Export Tutorials

Use `Export Tutorial` to create a Markdown guide in:

```text
exported_guides
```

The guide includes the selected game, host IP, LAN tutorial, server tools notes, firewall ports, and troubleshooting.

## Editing games.json

Each built-in game entry uses this schema:

```json
{
  "name": "Game Name",
  "platforms": ["Windows"],
  "lan_status": "Supported / Local server / In-game host",
  "exe_names": [],
  "common_paths_windows": [],
  "common_paths_macos": [],
  "ports": [],
  "host_tutorial": [],
  "client_tutorial": [],
  "offline_notes": [],
  "troubleshooting": [],
  "launch_notes": [],
  "server_support": "in_game_host",
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
  "official_download_url": ""
}
```

Only add games that have real offline LAN, local hosting, or official dedicated server support. If support is uncertain, do not add the game.

## Why Online-Only Games Are Excluded

Some games depend on online matchmaking, account services, proprietary lobbies, or anti-cheat services. This helper cannot and will not replace those services.

Examples intentionally excluded include VALORANT, osu!, Grand Theft Auto V, Cyberpunk 2077, Paradox Launcher v2, BombSquad, Crab Game, Muck, Human: Fall Flat, The Escapists 2, and launcher-only entries.

## Troubleshooting

- Make sure all players are on the same LAN or VPN LAN.
- Make sure everyone uses the same game version, compatible mods, and compatible DLC setup.
- Copy the host IP from the same adapter/network used by the clients.
- If multiple VPN/LAN adapters are listed, try the IP from the active LAN/VPN.
- Verify that clients can ping the host IP.
- Temporarily disabling the firewall can help diagnose a firewall issue, but re-enable it after testing.
- For dedicated servers, read the official server documentation for config files, saves, and ports.
