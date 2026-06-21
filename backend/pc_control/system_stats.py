"""
Real system stats for MJ dashboard.
Uses PowerShell to get CPU, RAM, Disk, GPU, Network info.
No pip dependencies needed.
"""

import subprocess
import json


def get_system_stats() -> dict:
    """Get real system stats using PowerShell."""
    ps_script = '''
$cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
$os = Get-CimInstance Win32_OperatingSystem
$ramTotal = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$ramFree = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$ramUsed = [math]::Round($ramTotal - $ramFree, 1)
$ramPercent = [math]::Round(($ramUsed / $ramTotal) * 100, 0)

$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$diskTotal = [math]::Round($disk.Size / 1GB, 0)
$diskFree = [math]::Round($disk.FreeSpace / 1GB, 0)
$diskUsed = $diskTotal - $diskFree
$diskPercent = [math]::Round(($diskUsed / $diskTotal) * 100, 0)

$battery = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue
$batteryPercent = if ($battery) { $battery.EstimatedChargeRemaining } else { -1 }
$charging = if ($battery) { $battery.BatteryStatus -eq 2 } else { $false }

$uptime = (Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
$uptimeStr = "{0}d {1}h {2}m" -f $uptime.Days, $uptime.Hours, $uptime.Minutes

$result = @{
    cpu = [int]$cpu
    ram_percent = [int]$ramPercent
    ram_used = $ramUsed
    ram_total = $ramTotal
    disk_percent = [int]$diskPercent
    disk_used = $diskUsed
    disk_total = $diskTotal
    disk_free = $diskFree
    battery = [int]$batteryPercent
    charging = [bool]$charging
    uptime = $uptimeStr
}

$result | ConvertTo-Json -Compress
'''

    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=10
        )
        if r.stdout.strip():
            return json.loads(r.stdout.strip())
    except Exception as e:
        pass

    # Fallback
    return {
        "cpu": -1, "ram_percent": -1, "ram_used": 0, "ram_total": 0,
        "disk_percent": -1, "disk_used": 0, "disk_total": 0, "disk_free": 0,
        "battery": -1, "charging": False, "uptime": "unknown"
    }
