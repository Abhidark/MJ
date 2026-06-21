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

$processCount = (Get-Process).Count

# GPU stats via nvidia-smi (works for NVIDIA GPUs)
$gpuName = "N/A"
$gpuUtil = -1
$gpuTemp = -1
$gpuMemUsed = 0
$gpuMemTotal = 0
$gpuMemPercent = -1
try {
    $nvOut = & "nvidia-smi" --query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>$null
    if ($nvOut) {
        $parts = $nvOut.Split(",") | ForEach-Object { $_.Trim() }
        $gpuName = $parts[0]
        $gpuUtil = [int]$parts[1]
        $gpuTemp = [int]$parts[2]
        $gpuMemUsed = [int]$parts[3]
        $gpuMemTotal = [int]$parts[4]
        if ($gpuMemTotal -gt 0) { $gpuMemPercent = [math]::Round(($gpuMemUsed / $gpuMemTotal) * 100, 0) }
    }
} catch {}

# Network speed (bytes sent/received)
$net = Get-CimInstance Win32_PerfFormattedData_Tcpip_NetworkInterface | Select-Object -First 1
$netDown = if ($net) { [math]::Round($net.BytesReceivedPerSec / 1KB, 0) } else { 0 }
$netUp = if ($net) { [math]::Round($net.BytesSentPerSec / 1KB, 0) } else { 0 }

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
    process_count = $processCount
    gpu_name = $gpuName
    gpu_util = [int]$gpuUtil
    gpu_temp = [int]$gpuTemp
    gpu_mem_used = $gpuMemUsed
    gpu_mem_total = $gpuMemTotal
    gpu_mem_percent = [int]$gpuMemPercent
    net_down_kbs = $netDown
    net_up_kbs = $netUp
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
        "battery": -1, "charging": False, "uptime": "unknown",
        "process_count": 0, "gpu_name": "N/A", "gpu_util": -1, "gpu_temp": -1,
        "gpu_mem_used": 0, "gpu_mem_total": 0, "gpu_mem_percent": -1,
        "net_down_kbs": 0, "net_up_kbs": 0
    }


def get_top_processes(limit: int = 25) -> list:
    """Get top processes sorted by RAM usage using PowerShell."""
    ps_script = f'''
$procs = Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First {limit} | ForEach-Object {{
    [PSCustomObject]@{{
        name = $_.ProcessName
        pid = $_.Id
        cpu = [math]::Round($_.CPU, 1)
        ram_mb = [math]::Round($_.WorkingSet64 / 1MB, 1)
        status = if ($_.Responding) {{ "Running" }} else {{ "Not Responding" }}
    }}
}}
$procs | ConvertTo-Json -Compress
'''
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=10
        )
        if r.stdout.strip():
            data = json.loads(r.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            return data
    except Exception:
        pass
    return []
