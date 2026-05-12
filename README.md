# Offline LAN Games Helper - Windows

Offline LAN Games Helper is a safe Windows GUI utility for LAN/offline multiplayer games that you legally own. It helps with LAN IP discovery, Windows Firewall rules, normal game launching, game-specific tutorials, exported guides, and official dedicated server tools where a real supported server option exists.

Created by **KiwiLiu**.

Support the project:
- PayPal: https://paypal.me/The0Cosmo
- GitHub Sponsors: https://github.com/sponsors/The0Cosmo

The current UI uses a cleaner kiwi-green light theme, readable high-contrast text, larger buttons, scrollable tutorial panels, and an original kiwi LAN logo.

This project is not affiliated with Steam, Valve, Paradox, Epic Games, Rockstar, Riot Games, Mojang, Microsoft, Apple, or any game publisher.

## Supported Platform

- Windows 10/11
- Built app: `dist\Offline LAN Games Helper.exe`
- Source app: Python + tkinter

## What The App Does

- Shows the host PC hostname and private LAN IPv4 addresses.
- Warns when multiple LAN/VPN adapters may confuse IP selection.
- Copies the selected host IP.
- Tests one user-entered or selected LAN IP with ping and one TCP port.
- Generates copyable/exportable invite messages for friends.
- Detects game executables from common paths and Steam libraries.
- Saves manually selected paths in `user_config.json`.
- Launches selected games normally.
- Adds/removes only the Windows Firewall rules created by this helper.
- Creates timestamped `.zip` backups of user-selected save folders and restores backups only after confirmation.
- Exports mod file lists for Minecraft Java and other modded games so players can compare setups.
- Helps diagnose local input conflicts with a Windows-only Input Isolation Helper.
- Shows English tutorials, ports, notes, troubleshooting, and privacy text.
- Provides English and Italian UI labels from the Settings page.
- Exports Markdown LAN/server guides.
- Helps with official dedicated server tools only when supported, including status for server processes started by this app.

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

## Offline Mode

After the app is downloaded and installed, normal LAN-helper features work offline. Optional server downloads and online-only games require internet and are not handled by this app.

Use the `Offline Mode` toggle to hide or block optional internet/download actions. LAN IP detection, tutorials, path selection, launching installed games, LAN tests, backups, mod-list export, invite export, and guide export still work offline.

## New UI, Settings, and Language

The app includes a `Settings` tab with:

- language selection: English or Italiano;
- theme selection: Light, Dark, or System default;
- default Offline Mode behavior;
- safety warning visibility;
- remember last selected game;
- Windows-only paths for DS4Windows, Nucleus Co-op, and Prism Launcher;
- default export and backup folders;
- privacy, support, repository, version, author, and license information.

Settings are saved locally in `user_config.json` and are never uploaded.

## Tool Manager

The app includes a Tool Manager in Settings that lets users hide or disable helper tools they do not use.

This only changes the app interface. It does not uninstall external programs, delete games, delete saves, or remove system files.

Hidden tools can be restored at any time from Settings.

Optional tools that can be hidden or disabled include Firewall Helper, Server Tools, Controller Tools, HidHide Helper, DS4Windows Helper, Nucleus Co-op Helper, Input Isolation Helper, Backup Tools, Invite Export, Custom Games, LAN Test, and the main Support tab.

Settings, About, Privacy, and Tool Manager are core pages and cannot be hidden.

## Optimized UI

The app uses a cleaner sidebar layout. Game tools are separated from core pages, and `Settings`, `Support`, and `Privacy` are not mixed into game-detail tabs.

The compact log panel is now separated at the bottom with `Show Log / Hide Log` and `Clear Log`.

## Fast Game Loading

The app loads `games.json` once at startup and keeps the parsed game catalog in memory.

It does not scan the whole disk and does not aggressively detect installed games at startup. Supported games are shown immediately. Installed-game detection is local and runs only when the user clicks `Refresh Installed Detection`.

Use `Refresh Games` to reload the catalog manually after editing `games.json`.

## Responsive UI

The interface uses a minimal kiwi-inspired light/dark palette, scrollable long-text panels, a minimum window size, and a UI scale setting. It is designed to stay readable on resized windows and high-DPI displays.

## Always Visible Settings

`Settings` is a core sidebar page and always remains visible.

`Settings`, `About`, `Privacy`, and `Tool Manager` are core pages and cannot be hidden by Tool Manager.

## Kiwi Logo

The app icon and About/Settings logo are generated locally by `make_icon.py` as original kiwi-themed artwork:

```text
assets\kiwi_logo.png
assets\offline_lan_helper.ico
```

The icon does not use copyrighted game, launcher, PayPal, Steam, Paradox, Riot, Rockstar, or store logos.

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

The Server Tools tab also shows whether a dedicated server process started by this app is running or stopped. `Start Server` starts only the selected official server executable/file. `Stop Server` asks for confirmation and only stops a server process that this app started for the selected game. It does not kill unrelated processes.

## LAN Test / Connection Test

Use `LAN Test` to test one IP address that you enter or select. The app can:

- ping the target IP;
- test one TCP port;
- use the selected game's default ports from `games.json` when listed.

This is not a scanner. It does not scan the internet, random IP ranges, or LAN ranges.

## Invites

Invite Export creates a short shareable message with only useful connection information.

Available invite modes:

- IP Only
- IP:Port Only
- Short Invite
- Full Useful Invite

Invite Export can copy the IP only, copy IP:Port, copy the join address, copy the invite, or export a short `.txt` file. It can include a server password only when the user manually enters one.

Invite Export does not include long tutorials, license text, privacy text, donation links, or unrelated setup instructions.

## Backups

Use `Backups` to select a world/save folder and create timestamped `.zip` backups in:

```text
backups\GAME_NAME
```

Restore requires confirmation. Restoring can overwrite files with matching names, but the helper does not delete original saves.

## Mod List Export

Use `Mods` to select a mods folder and export file names, sizes, and modified dates. Share the exported list with other players so everyone can compare mod setups before joining a modded LAN session.

The app does not download, install, or update mods.

## Input Isolation Helper

The Input Isolation Helper helps users diagnose controller and input conflicts for local multiplayer tools such as Nucleus Co-op, DS4Windows, HidHide, Prism Launcher, and Minecraft Java.

It can show running processes, open local tools, and provide checklists.

It does not inject into games, hook input, block input directly, bypass anti-cheat, or modify game files.

The helper can:

- list running processes with process name, PID, executable path when Windows allows access, and a detected category;
- copy selected process information;
- open a selected process file location when the path is available;
- save local per-process input notes in `user_config.json`;
- save local per-game/per-process input setup profiles;
- apply a safe setup flow by opening DS4Windows, HidHide Configuration Client, and Windows Game Controllers;
- test isolation by opening `joy.cpl` and asking you to confirm what is visible;
- save a recommended Nucleus Co-op / Minecraft Java profile;
- open `joy.cpl` so you can see which controllers Windows exposes;
- open HidHide, DS4Windows, and official documentation pages only when you click those buttons;
- copy safe HidHide, DS4Windows, and Minecraft Java / Nucleus Co-op checklists.

This app does not apply OS-level input blocking. Real per-process input assignment should be handled by Nucleus Co-op or official/safe external tools such as HidHide and DS4Windows.

### Input Isolation Setup

Use `Input Isolation Setup` for a guided safe setup flow:

1. Select or detect `DS4Windows.exe`.
2. Detect or select `HidHideClient.exe`.
3. Click `Apply Safe Input Isolation Setup`.
4. The app opens DS4Windows, HidHide Configuration Client, and `joy.cpl`.
5. Follow the checklist shown in the app.

The app does not silently modify HidHide rules. Advanced HidHide CLI support is disabled by default and only provides command previews or read-only CLI help after confirmation. Prefer the HidHide GUI for actual device hiding.

## Add Custom Games

Use `Add Custom Game` only for legitimate games with real offline/LAN or local hosting support. Custom games are saved in `user_config.json`; the app does not edit built-in `games.json`.

## Support / Donate

Offline LAN Games Helper is free to use.

If the app helped you and you want to support development, you can donate here:

- PayPal: https://paypal.me/The0Cosmo
- GitHub Sponsors: https://github.com/sponsors/The0Cosmo

Donations are optional and do not unlock extra features.

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
