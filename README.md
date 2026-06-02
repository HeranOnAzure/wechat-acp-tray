# wechat-acp-tray

Minimal Windows system-tray wrapper for [`wechat-acp`](https://github.com/formulahendry/wechat-acp).

## Install

```powershell
cd wechat-acp-tray
pip install -r requirements.txt
```

Make sure `wechat-acp` is on PATH (`npm install -g wechat-acp`).

## Run (foreground, dev)

```powershell
python tray.py
```

## Run (no console window)

```powershell
pythonw tray.py
```

## Tray menu

- **Start** — runs `wechat-acp --agent <preset> --daemon`
- **Stop** — runs `wechat-acp stop`
- **Restart** — stop + start
- **Show log** — opens `~/.wechat-acp/daemon.log`
- **Open config dir** — opens `~/.wechat-acp/`
- **Refresh** — re-polls status now
- **Quit** — exits the tray (does **not** stop the daemon)

Icon is green when running, gray when stopped. Hovering shows the raw `wechat-acp status` output.

## Configuration

Optional JSON at `~/.wechat-acp/tray-config.json`:

```json
{
  "agent": "copilot",
  "cwd": "D:\\code\\myproject",
  "instance": "",
  "poll_seconds": 5
}
```

## First-time login

The daemon cannot show a QR code. If you have never logged in, run once in a normal terminal:

```powershell
wechat-acp --agent copilot --login
```

Scan the QR, then Ctrl+C and use the tray app afterwards.

## Auto-start on login

Create a shortcut to `pythonw.exe tray.py` and drop it into:

```
shell:startup
```

## Package as single .exe (optional)

```powershell
pip install pyinstaller
pyinstaller --noconsole --onefile --name wechat-acp-tray tray.py
```
