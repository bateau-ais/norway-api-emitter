from pydantic import TypeAdapter
import argparse
import asyncio
import json
import logging
import os

import httpx
import nats
from almanach import AisMessage, to_msgpack
from pydantic import ValidationError, model_validator

logger = logging.getLogger(__name__)

type BatchAIS = list[ApiAisMessage]

RENAMES = {
    "msgtime": "msg_time",
    "latitude": "lat",
    "longitude": "lon",
    "speedOverGround": "speed",
    "courseOverGround": "course",
    "trueHeading": "heading",
    "rateOfTurn": "rot",
    "navigationalStatus": "status",
    "name": "shipname",
    "shipType": "shiptype",
    "callSign": "callsign",
    "imoNumber": "imo",
    "dimensionA": "a",
    "dimensionB": "b",
    "dimensionC": "c",
    "dimensionD": "d",
}


class ApiAisMessage(AisMessage):
    @model_validator(mode="before")
    @classmethod
    def rename_api_fields(cls, data: dict) -> dict:
        return {RENAMES.get(k, k): v for k, v in data.items()}


async def periodic_flush(nc, interval: float):
    """Background task that flushes NATS at regular intervals."""
    while True:
        await asyncio.sleep(interval)
        await nc.flush()
        logger.debug("Flushed NATS client")


async def fetch_and_publish_historical_data(
    client: httpx.AsyncClient,
    nc: nats.NATS,
    token: str,
    since_date: str,
    nats_subject: str,
):
    """Fetch historical AIS data since the given date and publish to NATS."""
    url: str = f"https://live.ais.barentswatch.no/live/v1/latest/combined?since={since_date}&modelType=Full&modelFormat=Json"

    logger.info(f"Fetching historical data since {since_date}...")
    try:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        
        # Parse JSON response
        raw_data = json.loads(r.text)
        
        # Validate each message individually, skipping invalid ones
        for item in raw_data:
            try:
                msg = ApiAisMessage.model_validate(item)
                logger.info(f"Publishing historical message '{msg.msg_uuid}'...")
                await nc.publish(f"{nats_subject}.{msg.mmsi}", to_msgpack(msg))
            except ValidationError as e:  # ignore invalid messages
                continue
        logger.info(f"Finished publishing historical data from {since_date}")

    except httpx.HTTPError as e:
        logger.error(f"Error fetching historical data: {e}")
        raise


async def main(since_date = None):
    token: str | None = os.environ.get("BARENTSWATCH_AIS_TOKEN")
    if not token:
        raise SystemExit("Missing env var BARENTSWATCH_AIS_TOKEN")

    nats_url: str = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")
    nats_subject: str = os.environ.get("NATS_SUBJECT", "raw_ais")
    flush_interval: float = float(os.environ.get("FLUSH_INTERVAL", "5.0"))

    url: str = "https://live.ais.barentswatch.no/live/v1/combined?modelType=Full&modelFormat=Json"
    nc = await nats.connect(servers=[nats_url])
    flush_task = asyncio.create_task(periodic_flush(nc, flush_interval))

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=None)) as client:
            # Fetch and publish historical data if a date is provided
            if since_date:
                await fetch_and_publish_historical_data(
                    client, nc, token, since_date, nats_subject
                )
                await nc.flush()
                logger.info("Starting streaming mode...")

            # Start streaming real-time data
            async with client.stream(
                "GET", url, headers={"Authorization": f"Bearer {token}"}
            ) as r:
                logger.info("Connected to BarentsWatch AIS stream")
                async for line in r.aiter_lines():
                    try:
                        msg = ApiAisMessage.model_validate_json(line)
                    except ValidationError:
                        continue

                    logger.info(f"Publishing live message '{msg.msg_uuid}'...")
                    await nc.publish(f"{nats_subject}.{msg.mmsi}", to_msgpack(msg))
    finally:
        flush_task.cancel()
        await nc.drain()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Fetch AIS data from BarentsWatch and publish to NATS"
    )
    parser.add_argument(
        "-s",
        "--since",
        type=str,
        dest="since_date",
        help="Fetch historical data since this date (format: YYYY-MM-DD). ",
    )
    args = parser.parse_args()

    asyncio.run(main(since_date=args.since_date))
