# Offline LAN Games Helper - Windows

Offline LAN Games Helper is a safe Windows GUI utility for LAN/offline multiplayer games that you legally own. It helps with LAN IP discovery, Windows Firewall rules, normal game launching, game-specific tutorials, exported guides, and official dedicated server tools where a real supported server option exists.

This project is not affiliated with Steam, Valve, Paradox, Epic Games, Rockstar, Riot Games, Mojang, Microsoft, Apple, or any game publisher.

## Supported Platform

- Windows 10/11
- Built app: `dist\Offline LAN Games Helper.exe`
- Source app: Python + tkinter

## What The App Does

- Shows the host PC hostname and private LAN IPv4 addresses.
- Warns when multiple LAN/VPN adapters may confuse IP selection.
- Copies the selected host IP.
- Detects game executables from common paths and Steam libraries.
- Saves manually selected paths in `user_config.json`.
- Launches selected games normally.
- Adds/removes only the Windows Firewall rules created by this helper.
- Shows English tutorials, ports, notes, troubleshooting, and privacy text.
- Exports Markdown LAN/server guides.
- Helps with official dedicated server tools only when supported.

## What The App Cannot Do

- It cannot turn online-only games into LAN games.
- It cannot emulate matchmaking, account services, Steam, Epic, Paradox, or other online services.
- It cannot bypass DRM, launchers, authentication, game ownership checks, anti-cheat, or licenses.
- It cannot create cracks, loaders, Steam emulators, patched executables, hooks, injectors, modified game files, or offline-service emulators.
- It cannot modify original game files.
- It cannot create a dedicated server for games that only support in-game hosting.

## Run From Source

Open PowerShell in this folder:

```powershell
cd "C:\Users\liuqi\Desktop\Windows OfflineLan Helper"
.\.venv\Scripts\python.exe .\lan_games_helper.py
```

If `.venv` does not exist yet:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

The app itself uses only the Python standard library. `pillow` and `pyinstaller` are build-time dependencies.

## Build The EXE

Run:

```powershell
cd "C:\Users\liuqi\Desktop\Windows OfflineLan Helper"
.\build_exe.ps1
```

The build script uses PyInstaller with:

```powershell
pyinstaller --onefile --windowed --noconsole --name "Offline LAN Games Helper" --icon "assets\offline_lan_helper.ico" lan_games_helper.py
```

The script also checks that the generated `.spec` contains `console=False`, generates the icon if needed, and copies `games.json`, `user_config.json`, `README.md`, `PRIVACY.md`, and `LICENSE` beside the executable.

Output:

```text
C:\Users\liuqi\Desktop\Windows OfflineLan Helper\dist\Offline LAN Games Helper.exe
```

The executable is built as a GUI app and should not open a terminal window.

## Download From GitHub Releases

When a release is published, download the Windows executable from the repository's GitHub Releases page. Use the release asset named similar to:

```text
Offline LAN Games Helper.exe
```

Download only releases published by The0Cosmo or a trusted project maintainer. Do not download repacked copies from unofficial sites.

## Run As Administrator

Administrator rights are required only for Windows Firewall changes.

1. Right-click the built `.exe` or PowerShell.
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

`Remove Firewall Rules` removes only rules with those names. It does not touch unrelated Windows Firewall rules.

## Server Tools

Server Tools can only:

- open official download pages;
- use official SteamCMD app IDs if verified and listed;
- launch official dedicated server executables;
- let the user select local server files;
- export instructions.

Server Tools cannot create fake servers, emulate online services, bypass authentication, patch game files, or download from unofficial sources.

If server support is unavailable, the app shows:

```text
No supported dedicated server is available for this game. Host from inside the game if supported.
```

If a game has no official dedicated server, use in-game hosting.

## Add Custom Games

Use `Add Custom Game` only for legitimate games with real offline/LAN or local hosting support. Custom games are saved in `user_config.json`; the app does not edit built-in `games.json`.

## Privacy

Offline LAN Games Helper works locally on your device. It does not collect, sell, share, or upload personal data. It may read local network information such as your LAN IP address and adapter names only to show them inside the app.

See [PRIVACY.md](PRIVACY.md) for details.

## License

Copyright (c) 2026 The0Cosmo. All rights reserved.

This software is for personal, non-commercial use only. See [LICENSE](LICENSE) for the full license terms.

## Why Online-Only Games Are Excluded

Some games depend on online matchmaking, account services, proprietary lobbies, or anti-cheat services. This helper cannot replace those services.

Examples intentionally excluded include VALORANT, osu!, Grand Theft Auto V, Cyberpunk 2077, Paradox Launcher v2, BombSquad, Crab Game, Muck, Human: Fall Flat, The Escapists 2, and launcher-only entries.

## Troubleshooting

- Make sure all players are on the same LAN or VPN LAN.
- Make sure everyone uses the same game version, compatible mods, and compatible DLC setup.
- Copy the host IP from the same adapter/network used by the clients.
- If multiple VPN/LAN adapters are listed, try the IP from the active LAN/VPN.
- Verify that clients can ping the host IP.
- Temporarily disabling the firewall can help diagnose a firewall issue, but re-enable it after testing.
- For dedicated servers, read the official server documentation for config files, saves, and ports.
