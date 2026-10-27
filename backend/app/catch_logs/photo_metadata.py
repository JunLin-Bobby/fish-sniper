import math
import struct
from datetime import datetime

from PIL import Image

from app.catch_logs.photo_schemas import PhotoMetadata


def _coordinate(values: object, reference: object, maximum: int) -> float:
    """將 EXIF 度分秒轉成有限座標，拒絕格式錯誤與超出範圍的值。"""

    degrees, minutes, seconds = [float(part) for part in values]
    if not all(math.isfinite(part) for part in (degrees, minutes, seconds)):
        raise ValueError()
    if degrees < 0 or not 0 <= minutes < 60 or not 0 <= seconds < 60:
        raise ValueError()
    if reference not in ("N", "S", "E", "W"):
        raise ValueError()
    result = degrees + minutes / 60 + seconds / 3600
    if result > maximum:
        raise ValueError()
    return -result if reference in ("S", "W") else result


def extract_photo_metadata(image: Image.Image) -> PhotoMetadata:
    """在去除 EXIF 前擷取候選時間與 GPS；缺漏或無效資訊不阻擋有效照片。"""

    result = PhotoMetadata()
    try:
        exif = image.getexif()
        details = exif.get_ifd(34665) if 34665 in exif else exif
        raw_time = details.get(36867)
        if raw_time:
            local = datetime.strptime(str(raw_time), "%Y:%m:%d %H:%M:%S")
            result.local_captured_at = local.isoformat()
            offset = details.get(36881)
            if offset:
                aware = datetime.fromisoformat(local.isoformat() + str(offset))
                if aware.tzinfo is not None:
                    result.captured_at = aware
    except (
        ValueError,
        TypeError,
        KeyError,
        OSError,
        OverflowError,
        AttributeError,
        IndexError,
        struct.error,
    ):
        pass
    try:
        gps = image.getexif().get_ifd(34853)
        if gps:
            if gps[1] not in ("N", "S") or gps[3] not in ("E", "W"):
                raise ValueError()
            result.latitude = _coordinate(gps[2], gps[1], 90)
            result.longitude = _coordinate(gps[4], gps[3], 180)
    except (
        ValueError,
        TypeError,
        KeyError,
        OSError,
        OverflowError,
        ZeroDivisionError,
        AttributeError,
        IndexError,
        struct.error,
    ):
        result.latitude = result.longitude = None
    return result
