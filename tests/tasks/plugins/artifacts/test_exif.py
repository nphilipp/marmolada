import datetime as dt
from unittest import mock
from uuid import uuid1

import pytest
from PIL import ExifTags, Image

from marmolada.tasks.plugins.artifacts import exif


@pytest.mark.parametrize(
    "wrapper_loaded", (False, True), ids=("wrapper-unloaded", "wrapper-loaded")
)
async def test_process(wrapper_loaded, tmp_path, caplog):
    tmp_file = tmp_path / "tmp_file.jpg"
    image = Image.new(mode="RGB", size=(8, 8), color="white")

    _exif = image.getexif()
    _exif[ExifTags.Base.Copyright] = "The current test run"
    now = dt.datetime.now(tz=dt.UTC)
    _exif[ExifTags.Base.DateTime] = now_str = now.strftime("%F %H:%M:%S")
    _exif[ExifTags.Base.Orientation] = 1  # horizontal

    image.save(tmp_file, format="jpeg", exif=_exif)

    db_session = mock.AsyncMock()
    db_session.__str__.return_value = "DB_SESSION"

    db_session.execute.return_value = result = mock.Mock()
    result.scalar_one.return_value = artifact = mock.Mock()
    artifact.full_path = tmp_file
    artifact.metadata_ = {}

    uuid = uuid1()

    with caplog.at_level("DEBUG"), mock.patch.object(exif, "wrapper_ctxvar") as wrapper_ctxvar:
        if wrapper_loaded:
            wrapper_ctxvar.get.return_value = exif.ExifToolWrapper(common_args=["-G"])
        else:
            wrapper_ctxvar.get.return_value = None

        await exif.process(db_session=db_session, uuid=uuid)

    for mapping in ("_exif", "_exif_unconverted"):
        assert artifact.metadata_[mapping]["EXIF:Copyright"] == "The current test run"
        assert artifact.metadata_[mapping]["EXIF:ModifyDate"] == now_str

    assert "horizontal" in artifact.metadata_["_exif"]["EXIF:Orientation"].lower()
    assert artifact.metadata_["_exif_unconverted"]["EXIF:Orientation"] == 1
