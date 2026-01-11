## norway-api-emitter

Streams live BarentsWatch AIS updates and publishes each validated message to NATS.

Each incoming JSON line is validated and normalized to the `almanach.AisMessage` schema, then encoded as MessagePack and published on a per-vessel subject.

Published subject pattern:

- `${NATS_SUBJECT}.${mmsi}` (default: `raw_ais.<mmsi>`)

### Environment variables

- `BARENTSWATCH_AIS_TOKEN` (required)
- `NATS_URL` (optional, default: `nats://127.0.0.1:4222`)
- `NATS_SUBJECT` (optional, default: `raw_ais`)
- `FLUSH_INTERVAL` (optional, default: `5.0`) — seconds between `nc.flush()` calls
- `LOG_LEVEL` (optional, default: `INFO`)

Notes:

- Invalid/partial lines from the upstream stream are skipped.
- Field names are normalized (e.g. `latitude` → `lat`, `speedOverGround` → `speed`, …) before publishing.

### Run

This project is typically run as a long-lived process.

#### Using `uv`

```zsh
uv run python main.py
```

#### Using `pip`/venv

```zsh
python -m venv .venv
source .venv/bin/activate
pip install -e .
python main.py
```

#### Environment

```zsh
export BARENTSWATCH_AIS_TOKEN='...'
export NATS_URL='nats://127.0.0.1:4222'
export NATS_SUBJECT='raw_ais'
export FLUSH_INTERVAL='5.0'
export LOG_LEVEL='INFO'

python main.py
```

### Subscribe (NATS CLI)

```zsh
# If you have the `nats` CLI installed
nats sub 'raw_ais.*' -s nats://127.0.0.1:4222
```

### Payload

Messages are published as MessagePack (`almanach.to_msgpack`) of the validated AIS model.
