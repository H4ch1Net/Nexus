from __future__ import annotations
from pathlib import Path
import hashlib, mimetypes, datetime
from typing import Any, Dict, Optional

try:
    from PIL import Image, ExifTags
except Exception:
    Image = None
    ExifTags = None


def _hashes(path: Path) -> dict:
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            md5.update(chunk); sha1.update(chunk); sha256.update(chunk)
    return {"md5": md5.hexdigest(), "sha1": sha1.hexdigest(), "sha256": sha256.hexdigest()}


def _to_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, bytes):
        try:
            return x.decode("utf-8", "ignore").strip("\x00").strip()
        except Exception:
            return None
    if isinstance(x, str):
        return x.strip()
    return str(x)


def _rational_to_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        try:
            num, den = x
            return float(num) / float(den)
        except Exception:
            return None


def _dms_to_decimal(dms, ref: Any) -> Optional[float]:
    try:
        d = _rational_to_float(dms[0]) or 0.0
        m = _rational_to_float(dms[1]) or 0.0
        s = _rational_to_float(dms[2]) or 0.0
        val = d + (m / 60.0) + (s / 3600.0)
        ref_s = _to_str(ref) or ""
        if ref_s.upper() in ("S", "W"):
            val = -val
        return val
    except Exception:
        return None


def _parse_exif_image(p: Path) -> tuple[Dict[str, Any], Optional[dict]]:
    if Image is None:
        return {}, None

    meta: Dict[str, Any] = {}
    gps_out: Optional[dict] = None

    try:
        with Image.open(p) as img:
            # Pillow ≥6: getexif(); older: _getexif()
            exif = getattr(img, "getexif", None)
            exif = exif() if callable(exif) else getattr(img, "_getexif", lambda: None)()
            if not exif:
                return meta, gps_out

            TAGS = ExifTags.TAGS
            GPSTAGS = ExifTags.GPSTAGS

            wanted = {
                "Make": "CameraMake",
                "Model": "CameraModel",
                "DateTimeOriginal": "DateTimeOriginal",
                "OffsetTimeOriginal": "OffsetTimeOriginal",  # e.g. +02:00
                "ExposureTime": "ExposureTime",
                "FNumber": "FNumber",
                "ISOSpeedRatings": "ISO",
                "PhotographicSensitivity": "ISO",
                "FocalLength": "FocalLength",
                "LensModel": "LensModel",
                "Software": "Software",
            }

            gps_raw = None
            for tag_id, value in dict(exif).items():
                name = TAGS.get(tag_id, str(tag_id))
                if name == "GPSInfo" and isinstance(value, dict):
                    gps_dict = {}
                    for k, v in value.items():
                        gps_name = GPSTAGS.get(k, str(k))
                        gps_dict[gps_name] = v
                    gps_raw = gps_dict
                elif name in wanted:
                    key = wanted[name]
                    if name in ("ExposureTime", "FNumber", "FocalLength"):
                        meta[key] = _rational_to_float(value)
                    elif name in ("ISOSpeedRatings", "PhotographicSensitivity"):
                        try:
                            meta[key] = int(value if not isinstance(value, (list, tuple)) else value[0])
                        except Exception:
                            meta[key] = value
                    else:
                        s = _to_str(value)
                        if s is not None:
                            meta[key] = s

            # Normalize DateTimeOriginal with optional offset
            dto = meta.get("DateTimeOriginal")
            if isinstance(dto, str):
                raw = dto.strip()
                tz_raw = meta.get("OffsetTimeOriginal")
                try:
                    dt = datetime.datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
                    if isinstance(tz_raw, str) and len(tz_raw) in (5, 6) and tz_raw[0] in "+-":
                        # "+HH:MM" or "+HHMM"
                        hh = int(tz_raw[1:3]); mm = int(tz_raw[-2:])
                        sign = 1 if tz_raw[0] == "+" else -1
                        tz = datetime.timezone(sign * datetime.timedelta(hours=hh, minutes=mm))
                        dt = dt.replace(tzinfo=tz)
                        meta["DateTimeOriginal"] = dt.astimezone(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                    else:
                        # Unknown timezone. Keep local naive ISO without "Z".
                        meta["DateTimeOriginal"] = dt.replace(microsecond=0).isoformat()
                except Exception:
                    pass

            # GPS
            if isinstance(gps_raw, dict):
                lat = lon = alt = None
                if all(k in gps_raw for k in ("GPSLatitude", "GPSLatitudeRef", "GPSLongitude", "GPSLongitudeRef")):
                    lat = _dms_to_decimal(gps_raw["GPSLatitude"], gps_raw["GPSLatitudeRef"])
                    lon = _dms_to_decimal(gps_raw["GPSLongitude"], gps_raw["GPSLongitudeRef"])

                if "GPSAltitude" in gps_raw:
                    alt = _rational_to_float(gps_raw.get("GPSAltitude"))
                    ref = gps_raw.get("GPSAltitudeRef")
                    try:
                        ref_val = int(ref) if ref is not None else 0
                        if alt is not None and ref_val == 1:
                            alt = -alt  # below sea level
                    except Exception:
                        pass

                if lat is not None and lon is not None:
                    gps_out = {
                        "lat": round(lat, 7),
                        "lon": round(lon, 7),
                        "alt": alt,
                    }

    except Exception:
        pass

    return meta, gps_out


def extract_meta(input_path: str) -> dict:
    p = Path(input_path)
    if not p.exists():
        return {}

    size = p.stat().st_size
    mime, _ = mimetypes.guess_type(p.name)

    metadata: Dict[str, Any] = {}
    gps: Optional[dict] = None

    if (mime or "").lower() in {"image/jpeg", "image/tiff"} or p.suffix.lower() in {".jpg", ".jpeg", ".tif", ".tiff"}:
        exif_meta, gps = _parse_exif_image(p)
        metadata.update(exif_meta)

    map_link = None
    if gps and ("lat" in gps and "lon" in gps) and gps["lat"] is not None and gps["lon"] is not None:
        map_link = f"https://www.google.com/maps/search/?api=1&query={gps['lat']},{gps['lon']}"

    return {
        "file": str(p),
        "file_size_bytes": size,
        "file_mime": mime or "application/octet-stream",
        "hashes": _hashes(p),
        "metadata": metadata,
        "gps": gps,
        "map_link": map_link,
        "warnings": [],
    }
