"""
ndsm_tools.py
=============

Generate an nDSM (DSM − DTM) by fetching Bavaria’s **DGM1** via **WCS 2.0.1**
for your DSM’s area of interest (AOI), aligning the DTM to the DSM grid, and
then subtracting.

Features
--------
- Builds AOI from a DSM’s extent (any CRS), reprojects to **EPSG:25832**, and applies a small buffer.
- Downloads **DGM1** via **INSPIRE WCS 2.0.1** (`EL.ElevationGridCoverage`) as GeoTIFF.
- Robust WCS request (tries `E/N` and `X/Y` axis labels; optional `SCALESIZE` to ~1 m).
- Aligns the DTM exactly to the DSM grid (same CRS, transform, width/height).
- Computes **nDSM = DSM − aligned DTM** with nodata-safe math.

Requirements
------------
`requests`, `rasterio`, `shapely`, `numpy`

Credentials
-----------
This WCS requires login. Provide credentials via environment variables:
- `LDBV_USER`
- `LDBV_PASS`
…or pass them to `run_pipeline(..., user=..., password=...)`. If missing and
`allow_prompt=True`, the module will prompt interactively.

Public API (functions)
----------------------
- `get_credentials(user=None, password=None, allow_prompt=True) -> (user, pass)`
- `dsm_aoi_bounds_25832(dsm_path, buffer_m=2.0) -> (minx, miny, maxx, maxy)`
- `wcs_download_dgm1(minx, miny, maxx, maxy, out_path, user, password, pixel_m=1.0, ...) -> out_path`
- `align_to_dsm_grid(src_path, dsm_path, out_path, resampling="bilinear", nodata=-9999.0) -> out_path`
- `compute_ndsm(dsm_path, dtm_aligned_path, ndsm_out_path, nodata=-9999.0) -> out_path`
- `run_pipeline(dsm_path, dtm_save_path, ndsm_save_path=None, buffer_m=2.0, pixel_m=1.0, user=None, password=None, allow_prompt=True) -> (aligned_dtm_path, ndsm_path|None)`

"""

from typing import Tuple, Optional
import os
import getpass
import numpy as np
import requests
from requests.auth import HTTPBasicAuth
import rasterio as rio
from rasterio.warp import transform_bounds, reproject, Resampling
from shapely.geometry import box

# INSPIRE DGM1 WCS endpoint (requires credentials from LDBV)
WCS_URL = "https://geoservices.bayern.de/pro/wcs/dgm/v1/wcs_inspire_dgm1?"


def get_credentials(user: Optional[str] = None,
                    password: Optional[str] = None,
                    allow_prompt: bool = True) -> Tuple[str, str]:
    """
    Return (user, password). Falls back to env (LDBV_USER/LDBV_PASS).
    If still missing and allow_prompt=True, prompt interactively.
    """
    u = user or os.environ.get("LDBV_USER")
    p = password or os.environ.get("LDBV_PASS")
    if (not u or not p) and allow_prompt:
        if not u:
            u = input("LDBV username: ")
        if not p:
            p = getpass.getpass("LDBV password: ")
    if not u or not p:
        raise RuntimeError("Missing credentials. Set LDBV_USER/LDBV_PASS or pass user/password.")
    return u, p


def dsm_aoi_bounds_25832(dsm_path: str, buffer_m: float = 2.0) -> Tuple[float, float, float, float]:
    """
    Read DSM bounds and transform to EPSG:25832; add a buffer (meters).
    Returns (minx, miny, maxx, maxy).
    """
    with rio.open(dsm_path) as dsm:
        b = transform_bounds(dsm.crs, "EPSG:25832", *dsm.bounds, densify_pts=21)
    minx, miny, maxx, maxy = box(*b).buffer(buffer_m).bounds
    return (minx, miny, maxx, maxy)


def wcs_download_dgm1(minx: float, miny: float, maxx: float, maxy: float,
                      out_path: str,
                      user: str, password: str,
                      pixel_m: float = 1.0,
                      axis_labels=(("E", "N"), ("X", "Y")),
                      include_scalesize: bool = True,
                      timeout: int = 300) -> str:
    """
    Download Bavaria's DGM1 as GeoTIFF via WCS 2.0.1 for the given AOI.
    Tries common axis labels and (optionally) SCALESIZE for ~1 m pixels.
    Returns the written out_path, or raises RuntimeError on failure.
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    auth = HTTPBasicAuth(user, password)

    dx, dy = (maxx - minx), (maxy - miny)
    nx = max(1, int(round(dx / pixel_m))) if include_scalesize else None
    ny = max(1, int(round(dy / pixel_m))) if include_scalesize else None

    last_err = None

    for axes in axis_labels:
        params = [
            ("SERVICE", "WCS"),
            ("REQUEST", "GetCoverage"),
            ("VERSION", "2.0.1"),
            ("COVERAGEID", "EL.ElevationGridCoverage"),
            ("SUBSETTINGCRS", "EPSG:25832"),
            ("OUTPUTCRS", "EPSG:25832"),
            ("SUBSET", f"{axes[0]}({minx},{maxx})"),
            ("SUBSET", f"{axes[1]}({miny},{maxy})"),
            ("FORMAT", "image/tiff;application=geotiff"),
        ]
        if include_scalesize and nx and ny:
            params.append(("SCALESIZE", f"{axes[0]}({nx})"))
            params.append(("SCALESIZE", f"{axes[1]}({ny})"))

        r = requests.get(WCS_URL, params=params, auth=auth, stream=True, timeout=timeout)
        ctype = r.headers.get("content-type", "")
        if r.status_code == 200 and ("tiff" in ctype or "geotiff" in ctype):
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    if chunk:
                        f.write(chunk)
            return out_path
        else:
            last_err = f"WCS 2.0 failed with axes {axes}: status={r.status_code} type={ctype} msg={r.text[:500]}"

    # Fallback: retry once without SCALESIZE (server chooses native resolution)
    if include_scalesize:
        return wcs_download_dgm1(minx, miny, maxx, maxy, out_path, user, password,
                                 pixel_m=pixel_m, axis_labels=axis_labels,
                                 include_scalesize=False, timeout=timeout)

    raise RuntimeError(last_err or "WCS download failed")


def align_to_dsm_grid(src_path: str, dsm_path: str, out_path: str,
                      resampling: str = "bilinear",
                      nodata: float = -9999.0) -> str:
    """
    Reproject/resample src raster to match DSM's exact grid (CRS, transform, size).
    Returns out_path.
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    resampling_map = {
        "nearest": Resampling.nearest,
        "bilinear": Resampling.bilinear,
        "cubic": Resampling.cubic,
    }
    rsp = resampling_map.get(resampling, Resampling.bilinear)

    with rio.open(dsm_path) as dsm, rio.open(src_path) as src:
        dst_profile = dsm.profile.copy()
        dst_profile.update(dtype="float32", count=1, nodata=nodata,
                           compress="deflate", predictor=3, zlevel=6)
        data = np.full((dsm.height, dsm.width), nodata, dtype="float32")
        reproject(
            source=rio.band(src, 1),
            destination=data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dsm.transform,
            dst_crs=dsm.crs,
            dst_nodata=nodata,
            resampling=rsp,
        )
        with rio.open(out_path, "w", **dst_profile) as dst:
            dst.write(data, 1)
    return out_path


def compute_ndsm(dsm_path: str, dtm_aligned_path: str, ndsm_out_path: str,
                 nodata: float = -9999.0) -> str:
    """
    Write nDSM = DSM - aligned DTM to ndsm_out_path.
    """
    os.makedirs(os.path.dirname(ndsm_out_path) or ".", exist_ok=True)
    with rio.open(dsm_path) as dsm, rio.open(dtm_aligned_path) as dtm:
        dsm_arr = dsm.read(1).astype("float32")
        dtm_arr = dtm.read(1).astype("float32")
        mask = ((dsm_arr == dsm.nodata) | (dtm_arr == dtm.nodata) |
                np.isnan(dsm_arr) | np.isnan(dtm_arr))
        out = np.where(mask, nodata, dsm_arr - dtm_arr)
        prof = dsm.profile.copy()
        prof.update(dtype="float32", nodata=nodata,
                    compress="deflate", predictor=3, zlevel=6)
        with rio.open(ndsm_out_path, "w", **prof) as dst:
            dst.write(out, 1)
    return ndsm_out_path


def run_pipeline(dsm_path: str,
                 dtm_save_path: str,
                 ndsm_save_path: Optional[str] = None,
                 buffer_m: float = 2.0,
                 pixel_m: float = 1.0,
                 user: Optional[str] = None,
                 password: Optional[str] = None,
                 allow_prompt: bool = True) -> Tuple[str, Optional[str]]:
    """
    Orchestrate: AOI -> WCS download -> align -> (optional) nDSM.
    Returns (aligned_dtm_path, ndsm_path or None).
    """
    user, password = get_credentials(user, password, allow_prompt=allow_prompt)
    print("[1/4] Computing AOI from DSM (EPSG:25832)…")
    minx, miny, maxx, maxy = dsm_aoi_bounds_25832(dsm_path, buffer_m)
    print(f"      AOI: {minx:.3f}, {miny:.3f}, {maxx:.3f}, {maxy:.3f} (buffer {buffer_m} m)")
    print("[2/4] Downloading DGM1 via WCS 2.0.1…")
    wcs_download_dgm1(minx, miny, maxx, maxy, dtm_save_path, user, password, pixel_m=pixel_m)
    print(f"      Saved DTM: {dtm_save_path}")
    aligned_path = os.path.splitext(dtm_save_path)[0] + "_aligned_to_DSM.tif"
    print("[3/4] Aligning DTM to DSM grid…")
    align_to_dsm_grid(dtm_save_path, dsm_path, aligned_path, resampling="bilinear")
    ndsm_path_written = None
    if ndsm_save_path:
        print("[4/4] Computing nDSM = DSM − DTM…")
        ndsm_path_written = compute_ndsm(dsm_path, aligned_path, ndsm_save_path)
        print(f"      Saved nDSM: {ndsm_path_written}")
    else:
        print("      Skipping nDSM creation (no path provided).")
    return aligned_path, ndsm_path_written
