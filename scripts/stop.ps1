# NZ 华人高协 CRM — 停止本地开发服务（释放 8000 / 5173 / 5174 端口）

$ErrorActionPreference = "SilentlyContinue"

function Stop-Port([int]$Port) {
    $pids = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $pids) {
        if ($pid -and $pid -ne 0) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "已停止端口 $Port 上的进程 (PID $pid)"
        }
    }
}

Write-Host "停止后端与前端开发服务..." -ForegroundColor Cyan
Stop-Port 8000
Stop-Port 5173
Stop-Port 5174
Write-Host "完成。数据库容器仍在运行；若要停止数据库: docker compose down" -ForegroundColor Green
