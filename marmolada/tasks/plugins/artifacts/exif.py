import asyncio
import logging
from contextvars import ContextVar
from typing import TYPE_CHECKING

from exiftool_wrapper import ExifToolWrapper
from sqlalchemy import select

from ....database.model import Artifact

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

scope = "artifact"
name = "exif"
dependencies = "file-type"

wrapper_ctxvar: ContextVar[ExifToolWrapper | None] = ContextVar("wrapper", default=None)

log = logging.getLogger(__name__)


async def process(*, db_session: "AsyncSession", uuid: "UUID"):
    log.debug("%s/%s: %s", scope, name, uuid)
    artifact: Artifact = (
        await db_session.execute(select(Artifact).filter_by(uuid=uuid))
    ).scalar_one()

    wrapper = wrapper_ctxvar.get()
    if not wrapper:
        wrapper = ExifToolWrapper(common_args=["-G"])
        wrapper_ctxvar.set(wrapper)

    exif_unconverted, exif_converted = await asyncio.gather(
        wrapper.process_json_async(artifact.full_path, args=["-n"]),
        wrapper.process_json_async(artifact.full_path),
    )

    artifact.metadata_["_exif"] = exif_converted
    artifact.metadata_["_exif_unconverted"] = exif_unconverted
