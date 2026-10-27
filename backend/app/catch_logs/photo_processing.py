import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from app.catch_logs.photo_metadata import extract_photo_metadata
from app.catch_logs.photo_schemas import CatchPhotoValidationError, PreparedPhoto
from app.core.config import Settings

register_heif_opener(thumbnails=False)


def prepare_photo(content: bytes, settings: Settings) -> PreparedPhoto:
    """驗證實際解碼格式並先讀 metadata，再校正、縮圖及輸出無 EXIF 的 JPEG。"""

    if not content or len(content) > settings.catch_photo_max_bytes:
        raise CatchPhotoValidationError("Photo exceeds the byte limit or is empty.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                if source.format not in {"JPEG", "PNG", "HEIF"}:
                    raise CatchPhotoValidationError("Only JPEG, PNG and HEIC are supported.")
                if source.width * source.height > settings.catch_photo_max_pixels:
                    raise CatchPhotoValidationError("Photo exceeds the pixel limit.")
                if getattr(source, "n_frames", 1) != 1:
                    raise CatchPhotoValidationError(
                        "Animated or multi-image files are unsupported."
                    )
                source.load()
                metadata = extract_photo_metadata(source)
                oriented = ImageOps.exif_transpose(source)
                oriented.thumbnail((settings.catch_photo_max_edge,) * 2)
                rgba = oriented.convert("RGBA")
                # Fresh pixels deliberately omit EXIF, XMP, comments and original GPS.
                output_image = Image.new("RGB", rgba.size, "white")
                output_image.paste(rgba, mask=rgba.getchannel("A"))
                output = BytesIO()
                output_image.save(output, format="JPEG", quality=85, optimize=True)
                if output.tell() > 6 * 1024 * 1024:
                    raise CatchPhotoValidationError("Processed photo exceeds the storage limit.")
                return PreparedPhoto(output.getvalue(), *output_image.size, metadata)
    except CatchPhotoValidationError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise CatchPhotoValidationError("Photo could not be safely decoded.") from error
