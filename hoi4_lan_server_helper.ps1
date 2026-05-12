<#
.SYNOPSIS
    Safe Windows LAN host helper for legitimate Hearts of Iron IV multiplayer.

.DESCRIPTION
    Hearts of Iron IV does not provide an official headless dedicated server.
    This helper configures the host PC for LAN play and can launch the game
    normally so the user can go to Multiplayer -> Host.

    The script does not inject, patch, hook, or modify HOI4 game files.
#>

[CmdletBinding()]
param(
    # Optional manual path to hoi4.exe when it is not in a common Steam path.
    [Parameter()]
    [string]$GamePath,

    # Add inbound Windows Firewall allow rules for hoi4.exe.
    [Parameter()]
    [switch]$AddFirewall,

    # With -AddFirewall, also add inbound TCP/UDP rules for ports 1630-1641.
    [Parameter()]
    [switch]$Ports,

    # Remove only firewall rules created by this helper.
    [Parameter()]
    [switch]$RemoveFirewall,

    # Launch hoi4.exe normally.
    [Parameter()]
    [switch]$Launch,

    # Generate README.md beside this script.
    [Parameter()]
    [switch]$WriteReadme
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$HelperName = 'HOI4 LAN Server Helper'
$ExecutableRuleNames = @(
    "$HelperName - hoi4.exe TCP",
    "$HelperName - hoi4.exe UDP"
)
$PortRuleNames = @(
    "$HelperName - Paradox Ports TCP 1630-1641",
    "$HelperName - Paradox Ports UDP 1630-1641"
)

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-ScriptDirectory {
    if ($PSScriptRoot) {
        return $PSScriptRoot
    }

    return (Get-Location).Path
}

function Resolve-Hoi4Path {
    param(
        [string]$ManualPath
    )

    $candidatePaths = @()

    if (-not [string]::IsNullOrWhiteSpace($ManualPath)) {
        $candidatePaths += $ManualPath
    }

    $candidatePaths += @(
        'C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV\hoi4.exe',
        'C:\Program Files\Steam\steamapps\common\Hearts of Iron IV\hoi4.exe'
    )

    foreach ($candidate in $candidatePaths) {
        $resolved = Resolve-Path -LiteralPath $candidate -ErrorAction SilentlyContinue
        if (-not $resolved) {
            continue
        }

        if (-not (Test-Path -LiteralPath $resolved.Path -PathType Leaf)) {
            continue
        }

        if ([IO.Path]::GetFileName($resolved.Path) -ieq 'hoi4.exe') {
            return $resolved.Path
        }

        throw "The supplied path exists but does not point to hoi4.exe: $($resolved.Path)"
    }

    return $null
}

function Get-PreferredLanIPv4Address {
    $addresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -ne '127.0.0.1' -and
            $_.IPAddress -notlike '169.254.*' -and
            $_.PrefixOrigin -ne 'WellKnown'
        }

    $preferred = $addresses | Where-Object {
        $_.IPAddress -like '192.168.*' -or
        $_.IPAddress -like '10.*' -or
        $_.IPAddress -match '^172\.(1[6-9]|2[0-9]|3[0-1])\.'
    } | Sort-Object InterfaceMetric, InterfaceIndex | Select-Object -First 1

    if ($preferred) {
        return $preferred.IPAddress
    }

    $fallback = $addresses | Sort-Object InterfaceMetric, InterfaceIndex | Select-Object -First 1
    if ($fallback) {
        return $fallback.IPAddress
    }

    return $null
}

function Require-AdministratorForFirewallChanges {
    if (-not (Test-IsAdministrator)) {
        throw @'
Firewall changes require Administrator privileges.
Open PowerShell as Administrator, then run this script again.
'@
    }
}

function Remove-ExistingRuleByDisplayName {
    param(
        [Parameter(Mandatory)]
        [string]$DisplayName
    )

    Get-NetFirewallRule -DisplayName $DisplayName -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule
}

function Remove-HelperFirewallRules {
    Require-AdministratorForFirewallChanges

    $ruleNames = $ExecutableRuleNames + $PortRuleNames
    $removedCount = 0

    foreach ($ruleName in $ruleNames) {
        $rules = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
        foreach ($rule in $rules) {
            Remove-NetFirewallRule -Name $rule.Name
            $removedCount++
        }
    }

    Write-Host "Removed $removedCount firewall rule(s) created by this helper."
}

function Add-Hoi4ExecutableFirewallRules {
    param(
        [Parameter(Mandatory)]
        [string]$Hoi4Path
    )

    Require-AdministratorForFirewallChanges

    $rules = @(
        @{
            DisplayName = $ExecutableRuleNames[0]
            Direction   = 'Inbound'
            Action      = 'Allow'
            Program     = $Hoi4Path
            Protocol    = 'TCP'
            Profile     = 'Private'
        },
        @{
            DisplayName = $ExecutableRuleNames[1]
            Direction   = 'Inbound'
            Action      = 'Allow'
            Program     = $Hoi4Path
            Protocol    = 'UDP'
            Profile     = 'Private'
        }
    )

    foreach ($rule in $rules) {
        Remove-ExistingRuleByDisplayName -DisplayName $rule.DisplayName
        New-NetFirewallRule @rule | Out-Null
        Write-Host "Added firewall rule: $($rule.DisplayName)"
    }
}

function Add-ParadoxPortFirewallRules {
    Require-AdministratorForFirewallChanges

    $rules = @(
        @{
            DisplayName = $PortRuleNames[0]
            Direction   = 'Inbound'
            Action      = 'Allow'
            Protocol    = 'TCP'
            LocalPort   = '1630-1641'
            Profile     = 'Private'
        },
        @{
            DisplayName = $PortRuleNames[1]
            Direction   = 'Inbound'
            Action      = 'Allow'
            Protocol    = 'UDP'
            LocalPort   = '1630-1641'
            Profile     = 'Private'
        }
    )

    foreach ($rule in $rules) {
        Remove-ExistingRuleByDisplayName -DisplayName $rule.DisplayName
        New-NetFirewallRule @rule | Out-Null
        Write-Host "Added firewall rule: $($rule.DisplayName)"
    }
}

function Write-HelperReadme {
    $readmePath = Join-Path -Path (Get-ScriptDirectory) -ChildPath 'README.md'

    $content = @'
# Hearts of Iron IV LAN Server Helper

This is a safe Windows LAN host helper for legitimate Hearts of Iron IV multiplayer. It does not modify HOI4 game files. It only helps identify the host PC's LAN IPv4 address, configure Windows Firewall rules created by this helper, and optionally launch HOI4 normally.

HOI4 has no official headless dedicated server. The "server" is the host player's multiplayer lobby. This helper does not create a standalone server process.

Cracks, bypasses, modified executables, and unauthorized copies are unsupported.

## Host Steps

1. Run this helper as admin:

```powershell
.\hoi4_lan_server_helper.ps1 -AddFirewall -Ports -Launch
```

2. In HOI4 go to Multiplayer -> Host.
3. Stay in the lobby.

## Client Steps

1. Join the same LAN or VPN LAN.
2. Open HOI4.
3. Go to Multiplayer.
4. Use Scan LAN / Refresh LAN.
5. If LAN scan fails and the game console supports it, try:

```text
connect HOST_LAN_IP
```

Replace `HOST_LAN_IP` with the LAN IPv4 address printed by the helper.

## Server ID vs LAN IP

Server ID is not the same as LAN IP. A Server ID may require Paradox/online services and may not work fully offline. For LAN troubleshooting, use the host PC's LAN IPv4 address, usually a private address such as `192.168.x.x`, `10.x.x.x`, or `172.16.x.x` to `172.31.x.x`.

## Version, Checksum, Mods, and DLC

All players need the same game version, same checksum, same mods, and a compatible DLC setup. A mismatch can prevent joining even when the network is configured correctly.

## Usage

Show detected game path and LAN IPv4 address without changing firewall settings:

```powershell
.\hoi4_lan_server_helper.ps1
```

Use a manual HOI4 executable path:

```powershell
.\hoi4_lan_server_helper.ps1 -GamePath "C:\Path\To\hoi4.exe"
```

Add Windows Firewall inbound allow rules for `hoi4.exe` TCP and UDP:

```powershell
.\hoi4_lan_server_helper.ps1 -AddFirewall
```

Add `hoi4.exe` firewall rules plus Paradox multiplayer port rules for TCP/UDP `1630-1641`:

```powershell
.\hoi4_lan_server_helper.ps1 -AddFirewall -Ports
```

Launch HOI4 normally:

```powershell
.\hoi4_lan_server_helper.ps1 -Launch
```

Remove only firewall rules created by this helper:

```powershell
.\hoi4_lan_server_helper.ps1 -RemoveFirewall
```

This does not need to find `hoi4.exe`; it only removes the helper's own named firewall rules.

Regenerate this README beside the script:

```powershell
.\hoi4_lan_server_helper.ps1 -WriteReadme
```

## Administrator Requirement

Windows Firewall changes require Administrator privileges. If you use `-AddFirewall`, `-Ports`, or `-RemoveFirewall`, open PowerShell as Administrator first.

## Firewall Rules Created

`-RemoveFirewall` removes only rules with these display names:

- `HOI4 LAN Server Helper - hoi4.exe TCP`
- `HOI4 LAN Server Helper - hoi4.exe UDP`
- `HOI4 LAN Server Helper - Paradox Ports TCP 1630-1641`
- `HOI4 LAN Server Helper - Paradox Ports UDP 1630-1641`

## Troubleshooting

- Temporarily test with firewall disabled only to diagnose, then re-enable it.
- Verify host and clients can ping each other.
- Verify everyone is on the same network or VPN.
- Verify no duplicate VPN adapters are confusing the LAN IP selection.
- Verify everyone has matching game version, checksum, mods, and compatible DLC setup.
'@

    Set-Content -LiteralPath $readmePath -Value $content -Encoding UTF8
    Write-Host "Wrote README: $readmePath"
}

try {
    if ($Ports -and -not $AddFirewall) {
        throw 'The -Ports option must be used with -AddFirewall, for example: .\hoi4_lan_server_helper.ps1 -AddFirewall -Ports'
    }

    $lanAddress = Get-PreferredLanIPv4Address

    Write-Host $HelperName
    Write-Host 'Safe mode: this helper does not modify Hearts of Iron IV game files.'
    Write-Host 'HOI4 has no official headless dedicated server; the host player uses Multiplayer -> Host.'
    Write-Host ''

    if ($lanAddress) {
        Write-Host "Host LAN IPv4 address: $lanAddress"
    }
    else {
        Write-Warning 'No non-loopback LAN IPv4 address was found.'
    }

    if ($WriteReadme) {
        Write-HelperReadme
    }

    if ($AddFirewall -or $RemoveFirewall) {
        Require-AdministratorForFirewallChanges
    }

    # Removing helper-created firewall rules does not depend on the game path.
    # Resolve hoi4.exe only for actions that need it, or for the normal info view.
    $needsHoi4Path = $AddFirewall -or $Launch -or -not $RemoveFirewall
    $hoi4Path = $null

    if ($needsHoi4Path) {
        $hoi4Path = Resolve-Hoi4Path -ManualPath $GamePath

        if ($hoi4Path) {
            Write-Host "Detected HOI4 executable: $hoi4Path"
        }
        else {
            Write-Warning 'Could not find hoi4.exe in common Steam paths. Use -GamePath "C:\Path\To\hoi4.exe".'
        }
    }

    if ($RemoveFirewall) {
        Remove-HelperFirewallRules
    }

    if ($AddFirewall) {
        if (-not $hoi4Path) {
            throw 'Cannot add firewall rules because hoi4.exe was not found. Use -GamePath "C:\Path\To\hoi4.exe".'
        }

        Add-Hoi4ExecutableFirewallRules -Hoi4Path $hoi4Path

        if ($Ports) {
            Add-ParadoxPortFirewallRules
        }
    }

    if ($Launch) {
        if (-not $hoi4Path) {
            throw 'Cannot launch HOI4 because hoi4.exe was not found. Use -GamePath "C:\Path\To\hoi4.exe".'
        }

        Write-Host "Launching HOI4 normally: $hoi4Path"
        Start-Process -FilePath $hoi4Path -WorkingDirectory (Split-Path -Path $hoi4Path -Parent)
    }

    Write-Host ''
    Write-Host 'Host steps: in HOI4 go to Multiplayer -> Host, then stay in the lobby.'
    Write-Host 'Client steps: use Multiplayer -> Scan LAN / Refresh LAN.'
    if ($lanAddress) {
        Write-Host "If LAN scan fails and console connect is supported, clients can try: connect $lanAddress"
    }
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
