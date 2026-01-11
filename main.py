import asyncio
import logging
import os

import httpx
import nats
from almanach import AisMessage, to_msgpack
from pydantic import ValidationError, model_validator

logger = logging.getLogger(__name__)

RENAMES = {
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


async def main():
    token = os.environ.get("BARENTSWATCH_AIS_TOKEN")
    if not token:
        raise SystemExit("Missing env var BARENTSWATCH_AIS_TOKEN")

    nats_url = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")
    nats_subject = os.environ.get("NATS_SUBJECT", "raw_ais")
    flush_interval = float(os.environ.get("FLUSH_INTERVAL", "5.0"))

    url = "https://live.ais.barentswatch.no/live/v1/combined?modelType=Full&modelFormat=Json"

    nc = await nats.connect(servers=[nats_url])
    flush_task = asyncio.create_task(periodic_flush(nc, flush_interval))

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=None)) as client:
            async with client.stream(
                "GET", url, headers={"Authorization": f"Bearer {token}"}
            ) as r:
                logger.info("Connected to BarentsWatch AIS stream")
                async for line in r.aiter_lines():
                    try:
                        msg = ApiAisMessage.model_validate_json(line)
                    except ValidationError:
                        continue

                    logger.info(f"Publishing '{msg.msg_uuid}'...")
                    await nc.publish(f"{nats_subject}.{msg.mmsi}", to_msgpack(msg))
    finally:
        flush_task.cancel()
        await nc.drain()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
