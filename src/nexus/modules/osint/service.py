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


def _rational_to_float(x: Any) -> Optional[float]:
    # PIL may return IFDRational or tuples
    try:
        return float(x)
    except Exception:
        try:
            num, den = x
            return float(num) / float(den)
        except Exception:
            return None


def _dms_to_decimal(dms, ref: str) -> Optional[float]:
    try:
        d = _rational_to_float(dms[0]) or 0.0
        m = _rational_to_float(dms[1]) or 0.0
        s = _rational_to_float(dms[2]) or 0.0
        val = d + (m / 60.0) + (s / 3600.0)
        if ref in ("S", "W"):
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
            exif = img.getexif()  # PIL Exif object
            if not exif:
                return meta, gps_out

            # Build reverse tag map once
            TAGS = ExifTags.TAGS
            GPSTAGS = ExifTags.GPSTAGS

            # First pass: collect wanted fields by name
            wanted = {
                "Make": "CameraMake",
                "Model": "CameraModel",
                "DateTimeOriginal": "DateTimeOriginal",
                "ExposureTime": "ExposureTime",
                "FNumber": "FNumber",
                "ISOSpeedRatings": "ISO",
                "PhotographicSensitivity": "ISO",
                "FocalLength": "FocalLength",
                "LensModel": "LensModel",
                "Software": "Software",
            }

            gps_raw = None
            for tag_id, value in exif.items():
                name = TAGS.get(tag_id, str(tag_id))
                if name == "GPSInfo":
                    gps_dict = {}
                    for k, v in value.items():
                        gps_name = GPSTAGS.get(k, str(k))
                        gps_dict[gps_name] = v
                    gps_raw = gps_dict
                elif name in wanted:
                    key = wanted[name]
                    # normalize some fields to plain types
                    if name in ("ExposureTime", "FNumber", "FocalLength"):
                        meta[key] = _rational_to_float(value)
                    elif name in ("ISOSpeedRatings", "PhotographicSensitivity"):
                        try:
                            meta[key] = int(value if not isinstance(value, (list, tuple)) else value[0])
                        except Exception:
                            meta[key] = value
                    else:
                        meta[key] = value

            # Date format normalize (YYYY:MM:DD HH:MM:SS -> ISO 8601)
            if "DateTimeOriginal" in meta and isinstance(meta["DateTimeOriginal"], str):
                raw = meta["DateTimeOriginal"].strip()
                try:
                    dt = datetime.datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
                    meta["DateTimeOriginal"] = dt.replace(microsecond=0).isoformat() + "Z"
                except Exception:
                    pass

            # GPS
            if gps_raw:
                lat = lon = None
                if all(k in gps_raw for k in ("GPSLatitude", "GPSLatitudeRef", "GPSLongitude", "GPSLongitudeRef")):
                    lat = _dms_to_decimal(gps_raw["GPSLatitude"], gps_raw["GPSLatitudeRef"])
                    lon = _dms_to_decimal(gps_raw["GPSLongitude"], gps_raw["GPSLongitudeRef"])

                if lat is not None and lon is not None:
                    gps_out = {
                        "lat": round(lat, 7),
                        "lon": round(lon, 7),
                        "alt": _rational_to_float(gps_raw.get("GPSAltitude")) if gps_raw.get("GPSAltitude") else None,
                    }

    except Exception:
        # ignore image parse errors; return minimal metadata
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

    # EXIF for JPEG/TIFF
    if (mime or "").lower() in {"image/jpeg", "image/tiff"} or p.suffix.lower() in {".jpg", ".jpeg", ".tif", ".tiff"}:
        exif_meta, gps = _parse_exif_image(p)
        metadata.update(exif_meta)

    # Build Google Maps link if GPS present
    map_link = None
    if gps and ("lat" in gps and "lon" in gps) and gps["lat"] is not None and gps["lon"] is not None:
        map_link = f"https://www.google.com/maps/search/?api=1&query={gps['lat']},{gps['lon']}"

    out = {
        "file": str(p),
        "file_size_bytes": size,
        "file_mime": mime or "application/octet-stream",
        "hashes": _hashes(p),
        "metadata": metadata,        # includes CameraMake, CameraModel, DateTimeOriginal, ExposureTime, FNumber, ISO, FocalLength, LensModel, Software when present
        "gps": gps,                  # {lat, lon, alt}
        "map_link": map_link,        # null when GPS missing
        "warnings": [],
    }
    return out
