"""
Process Manager for MJ Smart Dashboard.
List running processes, kill process, top CPU/RAM consumers.
"""

import subprocess
import json


def get_top_processes(count: int = 15) -> list:
    """Get top processes by CPU and memory usage."""
    ps = f'''
$procs = Get-Process | Where-Object {{$_.CPU -gt 0}} |
    Sort-Object CPU -Descending |
    Select-Object -First {count} Name, Id,
        @{{N='CPU_Sec';E={{[math]::Round($_.CPU,1)}}}},
        @{{N='RAM_MB';E={{[math]::Round($_.WorkingSet64/1MB,1)}}}}

$procs | ConvertTo-Json -Compress
'''
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
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


def kill_process(pid: int) -> dict:
    """Kill a process by PID."""
    try:
        r = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            return {"success": True, "message": f"Process {pid} kill kar diya."}
        else:
            return {"success": False, "message": f"Process {pid} kill nahi ho paya: {r.stderr.strip()}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def get_network_stats() -> dict:
    """Get network usage stats."""
    ps = '''
$adapters = Get-NetAdapterStatistics -ErrorAction SilentlyContinue |
    Select-Object -First 1 ReceivedBytes, SentBytes

if ($adapters) {
    $recv = [math]::Round($adapters.ReceivedBytes / 1MB, 1)
    $sent = [math]::Round($adapters.SentBytes / 1MB, 1)
    @{received_mb=$recv; sent_mb=$sent} | ConvertTo-Json -Compress
} else {
    @{received_mb=0; sent_mb=0} | ConvertTo-Json -Compress
}
'''
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=10
        )
        if r.stdout.strip():
            return json.loads(r.stdout.strip())
    except Exception:
        pass
    return {"received_mb": 0, "sent_mb": 0}
