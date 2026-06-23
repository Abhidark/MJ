"""
Real system stats for MJ dashboard.
Primary: psutil (fast, reliable).
Fallback: PowerShell (slower but no pip dependency).
GPU: nvidia-smi via subprocess.
"""

import subprocess
import json
import logging

logger = logging.getLogger("mj.stats")

# Try psutil first (much faster than PowerShell)
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def _get_gpu_stats() -> dict:
    """Get GPU stats via nvidia-smi."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0 and r.stdout.strip():
            parts = [p.strip() for p in r.stdout.strip().split(",")]
            mem_used = int(parts[3])
            mem_total = int(parts[4])
            return {
                "gpu_name": parts[0],
                "gpu_util": int(parts[1]),
                "gpu_temp": int(parts[2]),
                "gpu_mem_used": mem_used,
                "gpu_mem_total": mem_total,
                "gpu_mem_percent": round(mem_used / mem_total * 100) if mem_total > 0 else -1,
            }
    except Exception:
        pass
    return {
        "gpu_name": "N/A", "gpu_util": -1, "gpu_temp": -1,
        "gpu_mem_used": 0, "gpu_mem_total": 0, "gpu_mem_percent": -1,
    }


def _get_stats_psutil() -> dict:
    """Fast stats via psutil."""
    import psutil, time

    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\" if hasattr(psutil, '_pswindows') or __import__('os').name == 'nt' else "/")

    # Network
    net = psutil.net_io_counters()
    # We need rate, not total — store and diff
    net_down = 0
    net_up = 0
    if hasattr(_get_stats_psutil, '_last_net'):
        dt = time.time() - _get_stats_psutil._last_time
        if dt > 0:
            net_down = round((net.bytes_recv - _get_stats_psutil._last_net.bytes_recv) / dt / 1024)
            net_up = round((net.bytes_sent - _get_stats_psutil._last_net.bytes_sent) / dt / 1024)
    _get_stats_psutil._last_net = net
    _get_stats_psutil._last_time = time.time()

    # Battery
    battery = psutil.sensors_battery()
    bat_pct = int(battery.percent) if battery else -1
    charging = battery.power_plugged if battery else False

    # Uptime
    boot = psutil.boot_time()
    uptime_secs = time.time() - boot
    days = int(uptime_secs // 86400)
    hours = int((uptime_secs % 86400) // 3600)
    mins = int((uptime_secs % 3600) // 60)
    uptime_str = f"{days}d {hours}h {mins}m"

    result = {
        "cpu": int(cpu),
        "ram_percent": int(ram.percent),
        "ram_used": round(ram.used / (1024**3), 1),
        "ram_total": round(ram.total / (1024**3), 1),
        "disk_percent": int(disk.percent),
        "disk_used": round(disk.used / (1024**3)),
        "disk_total": round(disk.total / (1024**3)),
        "disk_free": round(disk.free / (1024**3)),
        "battery": bat_pct,
        "charging": bool(charging),
        "uptime": uptime_str,
        "process_count": len(psutil.pids()),
        "net_down_kbs": max(0, net_down),
        "net_up_kbs": max(0, net_up),
    }

    # Merge GPU stats
    result.update(_get_gpu_stats())
    return result


def get_system_stats() -> dict:
    """Get real system stats. Uses psutil if available, else PowerShell."""
    # Fast path: psutil
    if HAS_PSUTIL:
        try:
            return _get_stats_psutil()
        except Exception as e:
            logger.warning(f"psutil stats failed: {e}")

    # Slow path: PowerShell
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
            capture_output=True, text=True, timeout=15
        )
        if r.stdout.strip():
            return json.loads(r.stdout.strip())
        else:
            logger.warning(f"PowerShell stats returned empty. stderr: {r.stderr[:200] if r.stderr else 'none'}")
    except subprocess.TimeoutExpired:
        logger.warning("PowerShell stats timed out after 15s")
    except Exception as e:
        logger.warning(f"PowerShell stats failed: {e}")

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
