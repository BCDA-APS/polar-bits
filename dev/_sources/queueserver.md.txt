# QueueServer

The Bluesky QueueServer (QS) lets operators queue and execute scan plans
remotely without an interactive Python session. Each beamline has its own
QS host process and configuration.

## QS Configuration Files

| Beamline | Config file | Launch script |
|----------|------------|---------------|
| 4IDB | `src/id4_b_qserver/qs-config.yml` | `src/id4_b_qserver/qs_host.sh` |
| 4IDG | `src/id4_g_qserver/qs-config.yml` | `src/id4_g_qserver/qs_host.sh` |
| 4IDH | `src/id4_h_qserver/qs-config.yml` | `src/id4_h_qserver/qs_host.sh` |
| Raman | `src/id4_raman_qserver/qs-config.yml` | `src/id4_raman_qserver/qs_host.sh` |
| Shared | `src/id4_common_qserver/` | — |

---

## Starting / Stopping the QS Host

Use the `qs_host.sh` script for your beamline. The `restart` command is the
normal way to (re)start — it stops any running instance first, then starts
fresh in a `screen` session in the background.

```bash
# 4IDB example:
./src/id4_b_qserver/qs_host.sh restart
./src/id4_b_qserver/qs_host.sh status
./src/id4_b_qserver/qs_host.sh stop
```

All available commands:

```
Usage: qs_host.sh {start|stop|restart|status|checkup|console|run} [NAME]

    COMMANDS
        console   attach to process console if process is running in screen
        checkup   check that process is running, restart if not
        restart   restart process
        run       run process in console (not screen)
        start     start process
        status    report if process is running
        stop      stop process
```

### Install `screen` (if not present)

```bash
sudo apt install screen
```

---

## GUI Client

Launch the queue-monitor GUI from any terminal with the Conda environment
activated:

```bash
queue-monitor &
```

---

## Running Directly (without screen)

```bash
cd ./src/id4_b_qserver
start-re-manager --config=./qs-config.yml
```

---

## QS Context Detection

`startup.py` detects when it is running inside the QueueServer and adjusts
behavior automatically (no interactive prompts, no shutter suspenders, no
`%matplotlib` magic):

```python
from apsbits.utils.helper_functions import running_in_queueserver

if running_in_queueserver():
    # import everything for remote plan submission
    import bluesky.plans as bp
    import bluesky.plan_stubs as bps
else:
    # interactive session setup
    ...
```

---

## Redis Backend

The QS uses Redis (localhost:6379) for inter-process communication. Redis must
be running before starting the QS host:

```bash
redis-server &
```

Or via systemd on beamline servers:

```bash
systemctl status redis
```

---

## `qs-config.yml` Key Settings

```yaml
# IPython kernel backend
worker_class: bluesky_queueserver.manager.worker.IPythonWorker

# Startup scripts loaded by the worker
startup_script: path/to/startup.py

# Redis connection
redis_addr: localhost:6379

# Plan allow-list (empty = allow all)
allowed_plans_and_devices: []
```

See the [Bluesky QueueServer documentation](https://blueskyproject.io/bluesky-queueserver/manager_config.html)
for the full `qs-config.yml` reference.
