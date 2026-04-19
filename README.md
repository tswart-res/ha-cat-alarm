# ha-cat-alarm

A Home Assistant automation that monitors a front door contact sensor and announces repeated warnings on an Alexa Echo Dot when the door is left open. Useful for keeping cats inside.

Runs in Docker on a Raspberry Pi 4B. The automation logic is written in Python using AppDaemon.

## Hardware Required

- Raspberry Pi 4B (2GB+ RAM recommended)
- TP-Link Tapo T100 smart hub
- TP-Link Tapo T110 door/window contact sensor
- Amazon Echo Dot (any generation)
- Telegram account (optional, for notifications)

## How It Works

When the door opens, a 20-second timer starts. If the door is still open when the timer fires, Alexa announces a warning. The warning repeats every 20 seconds with an escalating duration count until the door closes. Closing the door at any point cancels the timer immediately.

## Architecture

```
Raspberry Pi 4B
├── homeassistant container (port 8123)
│   ├── TP-Link Tapo integration (T110 sensor via T100 hub)
│   ├── Alexa Devices integration (native HA)
│   └── Telegram notifications (optional)
└── appdaemon container (port 5050)
    └── cat_alarm.py (Python automation)
```

Both containers use port mapping by default. On a Raspberry Pi, switch to `network_mode: host` in `docker-compose.yml` for reliable mDNS/Zeroconf device discovery.

## Quick Start

On a Raspberry Pi with Docker and Git installed:

```bash
git clone https://github.com/YOUR_USERNAME/ha-cat-alarm.git
cd ha-cat-alarm
bash scripts/setup.sh
```

Then follow the steps below.

## Step-by-Step Setup

### 1. Configure environment

```bash
cp .env.example .env
nano .env
```

Set `TZ` to your timezone (e.g. `Europe/London`). Leave `HA_TOKEN` blank for now.

```bash
cp homeassistant/secrets.yaml.example homeassistant/secrets.yaml
nano homeassistant/secrets.yaml
```

Fill in your home coordinates and name.

```bash
cp appdaemon/secrets.yaml.example appdaemon/secrets.yaml
```

Leave the entity IDs as placeholders for now. You will fill them in after adding integrations.

### 2. Start Home Assistant

```bash
docker compose up homeassistant -d
```

Open Home Assistant at `http://<YOUR_IP>:8123` and complete the onboarding wizard.

### 3. Add TP-Link Tapo integration

1. Settings > Devices & Services > Add Integration
2. Search "TP-Link Tapo"
3. Enter the T100 hub IP address (assign it a static DHCP lease in your router)
4. The T110 sensor appears as a new device

Note: If the hub was recently firmware-updated and shows a connection error, open the Tapo app, go to Me > Third-Party Services, and enable it. A firmware update in late 2024 disabled this by default.

### 4. Add Alexa Devices integration

Home Assistant has a native Alexa Devices integration that handles TTS announcements.

1. Settings > Devices & Services > Add Integration
2. Search "Alexa Devices"
3. Sign in with your Amazon account
4. Your Echo Dot appears with notify entities

The integration creates two notify entities per device:
- `notify.device_name_speak` for TTS (use this one)
- `notify.device_name_announce` for announcements with a chime

### 5. Configure Telegram notifications (optional)

1. Message @BotFather on Telegram and send `/newbot`
2. Copy the bot token it gives you
3. Message @userinfobot to get your numeric chat ID
4. Settings > Devices & Services > Add Integration > Telegram bot
5. Enter the bot token and chat ID

### 6. Create a Home Assistant access token

1. Profile (bottom-left avatar) > Security tab
2. Long-Lived Access Tokens > Create Token
3. Name it "AppDaemon" and copy the token
4. Edit `.env` and set `HA_TOKEN=<your token>`

### 7. Set your entity IDs

In Home Assistant: Developer Tools (wrench icon) > States tab.

Find and note:
- Door sensor: a `binary_sensor.*` entity with device_class door
- Echo Dot notify service: a `notify.*_speak` entity

Edit `appdaemon/secrets.yaml`:

```yaml
door_sensor: binary_sensor.your_actual_sensor_id
alexa_announce_service: notify.your_device_name_speak
```

To add Telegram, also set:

```yaml
telegram_notify_service: notify.telegram
```

And uncomment the matching line in `appdaemon/apps/apps.yaml`.

### 8. Start all services

```bash
docker compose up -d
```

### 9. Verify it is working

```bash
docker compose logs -f appdaemon
```

You should see:

```
[CatAlarm] Initialized. Monitoring binary_sensor.your_sensor_id.
```

Open the door. After 20 seconds Alexa announces a warning. Keep it open and warnings repeat every 20 seconds with an increasing duration count. Close it and they stop.

## Configuration

Entity IDs live in `appdaemon/secrets.yaml` (gitignored). Timing and messages are in `appdaemon/apps/apps.yaml`.

| Setting | Default | Description |
|---------|---------|-------------|
| door_sensor | set in secrets.yaml | Entity ID of the T110 contact sensor |
| alexa_announce_service | set in secrets.yaml | Notify entity for the Echo Dot |
| telegram_notify_service | set in secrets.yaml | Telegram notify service (optional) |
| initial_delay | 20 | Seconds after door opens before first warning |
| repeat_interval | 20 | Seconds between repeated warnings |
| warning_message | see apps.yaml | TTS message ({duration} = elapsed seconds) |
| telegram_message | see apps.yaml | Telegram message ({duration} = elapsed seconds) |

## Raspberry Pi deployment notes

Switch `docker-compose.yml` to host networking for LAN device discovery:

```yaml
services:
  homeassistant:
    network_mode: host
    # remove the ports: section
  appdaemon:
    network_mode: host
    # remove the ports: section
```

Set a static DHCP lease for the T100 hub in your router so its IP does not change after reboots.

Use a fast SD card (A2-rated) or a USB SSD. Home Assistant writes to SQLite frequently and will wear out a cheap SD card within months.

## Troubleshooting

### AppDaemon can not connect to Home Assistant

Check that `HA_TOKEN` in `.env` is a valid long-lived token.

```bash
docker compose ps
docker compose logs appdaemon
```

AppDaemon logs show "Authenticated" or "Failed to authenticate" on startup.

### Door sensor not triggering

Check the entity ID in `appdaemon/secrets.yaml` matches exactly what appears in Developer Tools > States.

Open and close the door. The sensor state should toggle between `on` and `off`.

After editing `secrets.yaml`, restart AppDaemon:

```bash
docker compose restart appdaemon
```

### Alexa not speaking

Verify the entity ID in `appdaemon/secrets.yaml`. It should be the `_speak` variant, not `_announce`.

Test manually in Developer Tools > Actions:
- Action: `notify.send_message`
- Data: `{"message": "test", "entity_id": "notify.your_device_name_speak"}`

If that works from HA but not from the automation, check AppDaemon logs for errors.

### TP-Link showing 403 errors after firmware update

Open the Tapo app, go to Me > Third-Party Services, and toggle it on. A 2024 firmware update disabled third-party access by default.

### Telegram not sending

Check that the Telegram bot integration is listed under Settings > Devices & Services.

Test in Developer Tools > Actions:
- Action: `notify.send_message`
- Data: `{"message": "test", "entity_id": "notify.telegram"}`

### Checking AppDaemon logs

```bash
docker compose logs -f appdaemon
tail -f appdaemon/logs/appdaemon.log
```

## Reloading after code changes

```bash
docker compose restart appdaemon
```

## Project structure

```
ha-cat-alarm/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── homeassistant/
│   ├── configuration.yaml
│   ├── secrets.yaml.example
│   └── automations.yaml
├── appdaemon/
│   ├── appdaemon.yaml
│   ├── secrets.yaml.example
│   ├── logs/
│   └── apps/
│       ├── apps.yaml
│       └── cat_alarm.py
├── scripts/
│   └── setup.sh
└── README.md
```

## License

MIT
