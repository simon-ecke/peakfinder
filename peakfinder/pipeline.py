# peakfinder/pipeline.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Any

import os
import numpy as np
import pandas as pd

# Headless backend for Streamlit/server use
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import rasterio
from rasterio.windows import Window

from skimage import segmentation as sk_seg
from skimage import filters, feature, color
from skimage.measure import regionprops
from skimage.segmentation import relabel_sequential

import pyodbc

from peakfinder.modules.ndsm_tools import run_pipeline as ndsm_run_pipeline
from peakfinder.modules.tree_tops import detect_tree_tops
from peakfinder.modules.merge import match_stems_to_treetops, process_unmatched_stems


ProgressCb = Optional[Callable[[int, str], None]]
LogCb = Optional[Callable[[str], None]]


@dataclass
class RunConfig:
    # --- DB ---
    dsn_name: str
    versuch_id: int

    # --- Raster paths ---
    dsm_path: str
    dtm_path: str
    ndsm_path: str

    # --- nDSM creation ---
    compute_ndsm: bool = True
    buffer_m: float = 2.0
    pixel_m: float = 1.0
    ldbv_user: Optional[str] = None
    ldbv_pass: Optional[str] = None

    # --- treetop detection (pixel maxima) ---
    neighborhood_size: int = 100
    min_height_threshold: float = 10.0
    sigma: float = 2.0

    # --- pixel matching ---
    max_distance: float = 2.0
    radius_unmatched: float = 5.0

    # --- segmentation-based heights ---
    use_segmentation: bool = True
    seg_use_subset: bool = True
    seg_subset_size_m: float = 200.0

    seg_ground_threshold: float = 5.0
    seg_sigma_for_treetops: float = 10.0
    seg_sigma_for_segmentation: float = 1.0
    seg_min_distance: int = 5
    seg_threshold_abs: Optional[float] = 5.0
    seg_exclude_border: bool = True
    seg_connectivity: int = 1
    seg_compactness: float = 0.2
    seg_watershed_line: bool = False
    seg_min_area_threshold: int = 1500

    # Optional local write (Streamlit typically uses download button)
    output_csv_path: Optional[str] = None


@dataclass
class RunResult:
    df: pd.DataFrame
    ndsm_path: str
    stats: Dict[str, Any]
    figures: Dict[str, plt.Figure]
    pixel_matches: List[Tuple]   # tuples from match module
    stems_utm: List[Tuple]       # (Parzelle, Nr, utm_x, utm_y)
    corners: List[Tuple]         # (Parzelle, Nr, UTM_x, UTM_y)


# --------------------------
# DB + coordinate utilities
# --------------------------
def fetch_corners_and_trees_odbc(dsn_name: str, versuch_id: int, timeout: int = 10) -> Tuple[List[Tuple], List[Tuple]]:
    """
    Parameterized DB fetch.

    corners: [(Parzelle, Nr, UTM_x, UTM_y), ...]
    trees:   [(Parzelle, Nr, x, y, z), ...]
    """
    conn = pyodbc.connect(f"DSN={dsn_name};", timeout=timeout)
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT Parzelle, Nr, UTM_x, UTM_y
            FROM dbo.Objekte
            WHERE Versuch = ? AND Nr > ? AND UTM_x IS NOT NULL AND UTM_y IS NOT NULL
            ORDER BY Parzelle, Nr;
            """,
            (versuch_id, 10000),
        )
        corners = [tuple(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT Parzelle, Nr, x, y, z
            FROM dbo.Objekte
            WHERE Versuch = ? AND Nr BETWEEN ? AND ? AND x IS NOT NULL AND y IS NOT NULL
            ORDER BY Parzelle, Nr;
            """,
            (versuch_id, 1000, 9999),
        )
        trees = [tuple(r) for r in cur.fetchall()]

        return corners, trees
    finally:
        conn.close()


def find_ground_lines_improved(corner_points: List[Tuple]) -> Dict[int, Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    For each Parzelle: take the two lowest-by-UTM_y points as ground line.
    Then order those two by UTM_x => (lower_left, lower_right).
    """
    from collections import defaultdict

    parz = defaultdict(list)
    for p in corner_points:
        parz[int(p[0])].append(p)

    out = {}
    for parzelle, pts in parz.items():
        if len(pts) < 2:
            continue
        pts_sorted = sorted(pts, key=lambda r: (r[3], r[2]))  # y asc, x asc
        low2 = sorted(pts_sorted[:2], key=lambda r: r[2])      # x asc
        ll = (float(low2[0][2]), float(low2[0][3]))
        lr = (float(low2[1][2]), float(low2[1][3]))
        out[parzelle] = (ll, lr)
    return out


def transform_trees_all(trees_local: List[Tuple], ground_lines: Dict[int, Tuple[Tuple[float, float], Tuple[float, float]]]) -> List[Tuple]:
    """
    Local (x,y) -> UTM using ground line basis vectors.
    Input:  [(Parzelle, Nr, x, y, z), ...]
    Output: [(Parzelle, Nr, utm_x, utm_y), ...]
    """
    out: List[Tuple] = []
    for parzelle, (ll, lr) in ground_lines.items():
        gv = np.array([lr[0] - ll[0], lr[1] - ll[1]], dtype=float)
        gl = float(np.linalg.norm(gv))
        if gl == 0:
            continue
        ug = gv / gl
        perp = np.array([-ug[1], ug[0]])

        pts = [t for t in trees_local if int(t[0]) == int(parzelle)]
        for _, nr, x, y, _z in pts:
            utm_x = ll[0] + float(x) * ug[0] + float(y) * perp[0]
            utm_y = ll[1] + float(x) * ug[1] + float(y) * perp[1]
            out.append((int(parzelle), int(nr), float(utm_x), float(utm_y)))
    return out


# --------------------------
# Plot helpers
# --------------------------
def plot_corners_and_stems(corners: List[Tuple], stems_utm: List[Tuple]) -> plt.Figure:
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111)

    cx = [p[2] for p in corners]
    cy = [p[3] for p in corners]
    sx = [t[2] for t in stems_utm]
    sy = [t[3] for t in stems_utm]

    ax.scatter(cx, cy, marker="s", s=25, label="Plot corners")
    ax.scatter(sx, sy, s=10, alpha=0.7, label="Stems (UTM)")
    ax.set_xlabel("UTM_x")
    ax.set_ylabel("UTM_y")
    ax.set_title("All plots: corners + stems")
    ax.grid(True)
    ax.legend()
    return fig


def plot_pixel_matches_for_parzelle(pixel_matches: List[Tuple], parzelle: int) -> plt.Figure:
    sel = [m for m in pixel_matches if int(m[0]) == int(parzelle)]
    matched = [m for m in sel if m[4] is not None]
    unmatched = [m for m in sel if m[4] is None]

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111)

    if matched:
        ax.scatter([m[2] for m in matched], [m[3] for m in matched], label="Matched stems")
        ax.scatter([m[4] for m in matched], [m[5] for m in matched], label="Matched treetops", marker="x")
    if unmatched:
        ax.scatter([m[2] for m in unmatched], [m[3] for m in unmatched], label="Unmatched stems")

    ax.set_xlabel("UTM_x")
    ax.set_ylabel("UTM_y")
    ax.set_title(f"Pixel matching (Parzelle {parzelle})")
    ax.grid(True)
    ax.legend()
    return fig


# --------------------------
# Segmentation with correct subset transform
# --------------------------
def segment_trees_arrays(
    ndsm_path: str,
    ground_threshold: float,
    sigma_for_treetops: float,
    sigma_for_segmentation: float,
    min_distance: int,
    threshold_abs: Optional[float],
    exclude_border: bool,
    connectivity: int,
    compactness: float,
    watershed_line: bool,
    subset_size_meters: float,
    min_area_threshold: int,
    use_subset: bool,
    stems_utm: Optional[List[Tuple]] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, rasterio.Affine, plt.Figure]:
    """
    Returns: labels, treetop_coords(row,col), ndsm_subset, transform(for subset), fig_overlay
    """
    with rasterio.open(ndsm_path) as src:
        profile = src.profile
        px = abs(profile["transform"][0])
        py = abs(profile["transform"][4])

        if use_subset:
            w = max(1, int(round(subset_size_meters / px)))
            h = max(1, int(round(subset_size_meters / py)))

            full = src.read(1)
            cx = full.shape[1] // 2
            cy = full.shape[0] // 2

            start_x = max(0, cx - w // 2)
            start_y = max(0, cy - h // 2)
            end_x = min(full.shape[1], start_x + w)
            end_y = min(full.shape[0], start_y + h)

            window = Window(start_x, start_y, end_x - start_x, end_y - start_y)
            ndsm = src.read(1, window=window)
            transform = src.window_transform(window)  # IMPORTANT
        else:
            ndsm = src.read(1)
            transform = src.transform

    if threshold_abs is None:
        threshold_abs = ground_threshold

    ndsm_cleaned = np.where(ndsm > ground_threshold, ndsm, 0).astype("float32")
    ndsm_for_treetops = filters.gaussian(ndsm_cleaned, sigma=sigma_for_treetops)
    ndsm_for_seg = filters.gaussian(ndsm_cleaned, sigma=sigma_for_segmentation)
    gradient = filters.sobel(ndsm_for_seg)

    treetop_coords = feature.peak_local_max(
        ndsm_for_treetops,
        min_distance=min_distance,
        threshold_abs=threshold_abs,
        exclude_border=exclude_border,
    )

    markers = np.zeros_like(ndsm, dtype=int)
    for i, (r, c) in enumerate(treetop_coords):
        markers[r, c] = i + 1

    labels = sk_seg.watershed(
        image=gradient,
        markers=markers,
        connectivity=connectivity,
        compactness=compactness,
        watershed_line=watershed_line,
        mask=ndsm_for_seg > 0,
    )

    # remove small segments
    props = regionprops(labels)
    small = [p.label for p in props if p.area < min_area_threshold]
    for s in small:
        labels[labels == s] = 0

    labels = relabel_sequential(labels)[0]
    overlay = color.label2rgb(labels, bg_label=0)

    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111)
    ax.imshow(ndsm, cmap="gray", origin="upper")
    ax.imshow(overlay, alpha=0.4, origin="upper")
    
    # Plot treetops
    if len(treetop_coords) > 0:
        ax.scatter(treetop_coords[:, 1], treetop_coords[:, 0], s=15, edgecolors="black", linewidths=0.3, label="Treetops", color="blue")
    
    # Plot stems from Step 3 (if provided)
    if stems_utm is not None and len(stems_utm) > 0:
        for parzelle, nr, utm_x, utm_y in stems_utm:
            try:
                row, col = rasterio.transform.rowcol(transform, utm_x, utm_y)
                if 0 <= row < ndsm.shape[0] and 0 <= col < ndsm.shape[1]:
                    ax.scatter(col, row, s=12, edgecolors="black", linewidths=0.3, color="red", marker='o')
            except Exception:
                pass
        # Add red marker for legend
        ax.scatter([], [], s=12, edgecolors="black", linewidths=0.3, color="red", marker='o', label="Field Stems")
    
    # Move legend to top-left
    ax.legend(loc='upper left', fontsize=8)
    ax.set_axis_off()
    ax.set_title("Segmentation overlay (subset)" if use_subset else "Segmentation overlay (full)")
    return labels, treetop_coords, ndsm, transform, fig


def segment_match_stems(
    labels: np.ndarray,
    treetop_coords: np.ndarray,
    stems_utm: List[Tuple],
    ndsm: np.ndarray,
    transform: rasterio.Affine,
) -> Tuple[List[Dict[str, Any]], plt.Figure]:
    """
    Match only segments with exactly 1 stem and 1 treetop.
    Height = max nDSM within that segment.
    """
    seg_to_tops: Dict[int, List[Tuple[int, int]]] = {}
    unmatched_tops: List[Tuple[int, int]] = []

    for r, c in treetop_coords:
        sid = int(labels[r, c])
        if sid > 0:
            seg_to_tops.setdefault(sid, []).append((int(r), int(c)))
        else:
            unmatched_tops.append((int(r), int(c)))

    seg_to_stems: Dict[int, List[Tuple[int, int, int, int, float, float]]] = {}
    no_segment: List[Tuple[int, int, int, int, float, float]] = []

    for parzelle, nr, x, y in stems_utm:
        rr, cc = rasterio.transform.rowcol(transform, x, y)
        if 0 <= rr < labels.shape[0] and 0 <= cc < labels.shape[1]:
            sid = int(labels[rr, cc])
            if sid > 0:
                seg_to_stems.setdefault(sid, []).append((rr, cc, int(parzelle), int(nr), float(x), float(y)))
            else:
                no_segment.append((rr, cc, int(parzelle), int(nr), float(x), float(y)))
        else:
            no_segment.append((rr, cc, int(parzelle), int(nr), float(x), float(y)))

    results: List[Dict[str, Any]] = []

    for sid, stems in seg_to_stems.items():
        tops = seg_to_tops.get(sid, [])
        if len(stems) == 1 and len(tops) == 1:
            rr, cc, parz, nr, x, y = stems[0]

            mask = labels == sid
            seg_ndsm = np.where(mask, ndsm, -np.inf)
            mr, mc = np.unravel_index(np.argmax(seg_ndsm), seg_ndsm.shape)
            h = float(ndsm[mr, mc])
            top_x, top_y = rasterio.transform.xy(transform, mr, mc, offset="center")

            results.append({
                "Parzelle": parz,
                "Nr": nr,
                "Stem_UTM_X": x,
                "Stem_UTM_Y": y,
                "Treetop_UTM_X": float(top_x),
                "Treetop_UTM_Y": float(top_y),
                "UAV_Tree_Height_segment": h,
                "match": 1,
            })
        else:
            for rr, cc, parz, nr, x, y in stems:
                results.append({
                    "Parzelle": parz,
                    "Nr": nr,
                    "Stem_UTM_X": x,
                    "Stem_UTM_Y": y,
                    "Treetop_UTM_X": None,
                    "Treetop_UTM_Y": None,
                    "UAV_Tree_Height_segment": None,
                    "match": 0,
                })

    for rr, cc, parz, nr, x, y in no_segment:
        results.append({
            "Parzelle": parz,
            "Nr": nr,
            "Stem_UTM_X": x,
            "Stem_UTM_Y": y,
            "Treetop_UTM_X": None,
            "Treetop_UTM_Y": None,
            "UAV_Tree_Height_segment": None,
            "match": 2,
        })

    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111)
    ax.imshow(ndsm, cmap="gray", origin="upper")
    ax.set_title("Segmentation match categories")
    ax.set_axis_off()

    for r in results:
        rr, cc = rasterio.transform.rowcol(transform, r["Stem_UTM_X"], r["Stem_UTM_Y"])
        if not (0 <= rr < ndsm.shape[0] and 0 <= cc < ndsm.shape[1]):
            continue
        ax.scatter(cc, rr, s=35, edgecolors="black", linewidths=0.3)

    for rr, cc in unmatched_tops:
        ax.scatter(cc, rr, s=35, marker="x", linewidths=1.0)

    return results, fig


# --------------------------
# Main orchestrator
# --------------------------
def run_everything(cfg: RunConfig, progress: ProgressCb = None, log: LogCb = None) -> RunResult:
    def p(pct: int, msg: str):
        if progress:
            progress(int(pct), msg)
        if log:
            log(msg)

    # 1) nDSM
    p(5, "Preparing nDSM…")
    ndsm_path = cfg.ndsm_path

    if cfg.compute_ndsm:
        user = cfg.ldbv_user or os.getenv("LDBV_USER")
        pwd = cfg.ldbv_pass or os.getenv("LDBV_PASS")
        if not user or not pwd:
            raise RuntimeError("Missing LDBV credentials (set in Streamlit or env LDBV_USER/LDBV_PASS).")

        p(10, "Downloading/aligning DGM1 and computing nDSM…")
        _, ndsm_written = ndsm_run_pipeline(
            dsm_path=cfg.dsm_path,
            dtm_save_path=cfg.dtm_path,
            ndsm_save_path=cfg.ndsm_path,
            buffer_m=cfg.buffer_m,
            pixel_m=cfg.pixel_m,
            user=user,
            password=pwd,
            allow_prompt=False,
        )
        ndsm_path = ndsm_written or cfg.ndsm_path

    if not os.path.exists(ndsm_path):
        raise FileNotFoundError(f"nDSM not found: {ndsm_path}")

    # 2) Treetops (pixel maxima)
    p(20, "Detecting treetops (pixel maxima)…")
    treetops, fig_tops, _ax = detect_tree_tops(
        ndsm_path,
        neighborhood_size=int(cfg.neighborhood_size),
        min_height_threshold=float(cfg.min_height_threshold),
        sigma=float(cfg.sigma),
    )

    # 3) DB fetch + stems transform
    p(35, "Fetching field data via ODBC…")
    corners, trees_local = fetch_corners_and_trees_odbc(cfg.dsn_name, int(cfg.versuch_id))

    p(45, "Computing ground lines + transforming stems to UTM…")
    ground_lines = find_ground_lines_improved(corners)
    stems_utm = transform_trees_all(trees_local, ground_lines)

    fig_stems = plot_corners_and_stems(corners, stems_utm)

    # 4) Pixel matching
    p(60, "Pixel matching stems ↔ treetops (Hungarian + cleanup)…")
    pixel_matches = match_stems_to_treetops(stems_utm, treetops, max_distance=float(cfg.max_distance))
    pixel_matches = process_unmatched_stems(pixel_matches, treetops, radius=float(cfg.radius_unmatched))

    matched_pixel_count = sum(1 for m in pixel_matches if m[4] is not None)
    unmatched_pixel_count = sum(1 for m in pixel_matches if m[4] is None)

    pixel_lookup: Dict[Tuple[int, int], float] = {}
    for parz, nr, sx, sy, tx, ty, h in pixel_matches:
        if tx is not None:
            pixel_lookup[(int(parz), int(nr))] = float(h)

    figures: Dict[str, plt.Figure] = {
        "treetops": fig_tops,
        "stems_corners": fig_stems,
    }

    # 5) Segmentation-based heights
    results: List[Dict[str, Any]] = []
    seg_stats = {"seg_matched": 0, "seg_unmatched": 0, "seg_no_segment": 0}

    if cfg.use_segmentation:
        p(75, "Segmenting crowns (watershed)…")
        labels, treetop_coords, ndsm_subset, transform, fig_seg = segment_trees_arrays(
            ndsm_path=ndsm_path,
            ground_threshold=float(cfg.seg_ground_threshold),
            sigma_for_treetops=float(cfg.seg_sigma_for_treetops),
            sigma_for_segmentation=float(cfg.seg_sigma_for_segmentation),
            min_distance=int(cfg.seg_min_distance),
            threshold_abs=cfg.seg_threshold_abs,
            exclude_border=bool(cfg.seg_exclude_border),
            connectivity=int(cfg.seg_connectivity),
            compactness=float(cfg.seg_compactness),
            watershed_line=bool(cfg.seg_watershed_line),
            subset_size_meters=float(cfg.seg_subset_size_m),
            min_area_threshold=int(cfg.seg_min_area_threshold),
            use_subset=bool(cfg.seg_use_subset),
        )
        figures["segmentation_overlay"] = fig_seg

        p(85, "Matching stems within segments (1 stem + 1 treetop per segment)…")
        results, fig_segmatch = segment_match_stems(labels, treetop_coords, stems_utm, ndsm_subset, transform)
        figures["segmentation_match"] = fig_segmatch

        seg_stats["seg_matched"] = sum(1 for r in results if r["match"] == 1)
        seg_stats["seg_unmatched"] = sum(1 for r in results if r["match"] == 0)
        seg_stats["seg_no_segment"] = sum(1 for r in results if r["match"] == 2)
    else:
        results = [{
            "Parzelle": int(p),
            "Nr": int(n),
            "Stem_UTM_X": float(x),
            "Stem_UTM_Y": float(y),
            "Treetop_UTM_X": None,
            "Treetop_UTM_Y": None,
            "UAV_Tree_Height_segment": None,
            "match": 2,
        } for (p, n, x, y) in stems_utm]

    # 6) Merge pixel heights into segment results
    p(92, "Merging pixel heights into results…")
    for r in results:
        key = (int(r["Parzelle"]), int(r["Nr"]))
        r["UAV_Tree_Height_pixel"] = pixel_lookup.get(key, None)

    results = sorted(results, key=lambda x: (x["Parzelle"], x["Nr"]))
    df = pd.DataFrame(results)

    column_order = [
        "Parzelle",
        "Nr",
        "Stem_UTM_X",
        "Stem_UTM_Y",
        "Treetop_UTM_X",
        "Treetop_UTM_Y",
        "UAV_Tree_Height_segment",
        "UAV_Tree_Height_pixel",
        "match",
    ]
    for c in column_order:
        if c not in df.columns:
            df[c] = None
    df = df[column_order]

    if cfg.output_csv_path:
        os.makedirs(os.path.dirname(cfg.output_csv_path) or ".", exist_ok=True)
        df.to_csv(cfg.output_csv_path, index=False)

    stats = {
        "ndsm_path": ndsm_path,
        "stems_total": len(stems_utm),
        "treetops_total": len(treetops),
        "pixel_matched": matched_pixel_count,
        "pixel_unmatched": unmatched_pixel_count,
        **seg_stats,
    }

    p(100, "Done.")
    return RunResult(
        df=df,
        ndsm_path=ndsm_path,
        stats=stats,
        figures=figures,
        pixel_matches=pixel_matches,
        stems_utm=stems_utm,
        corners=corners,
    )


def compute_ndsm_only(cfg: RunConfig, progress: ProgressCb = None, log: LogCb = None) -> Tuple[str, str]:
    """
    Compute aligned DTM + nDSM only (no DB access).
    Returns (aligned_dtm_path, ndsm_path).
    """
    def p(pct: int, msg: str):
        if progress:
            progress(int(pct), msg)
        if log:
            log(msg)

    if not cfg.dsm_path or not cfg.dtm_path or not cfg.ndsm_path:
        raise ValueError("Please provide DSM/DTM/nDSM paths.")

    user = cfg.ldbv_user or os.getenv("LDBV_USER")
    pwd = cfg.ldbv_pass or os.getenv("LDBV_PASS")
    if not user or not pwd:
        raise RuntimeError("Missing LDBV credentials (set in Streamlit or env LDBV_USER/LDBV_PASS).")

    p(10, "Computing AOI + downloading DGM1 + aligning to DSM…")
    aligned_dtm, ndsm_written = ndsm_run_pipeline(
        dsm_path=cfg.dsm_path,
        dtm_save_path=cfg.dtm_path,
        ndsm_save_path=cfg.ndsm_path,
        buffer_m=cfg.buffer_m,
        pixel_m=cfg.pixel_m,
        user=user,
        password=pwd,
        allow_prompt=False,
    )

    ndsm_path = ndsm_written or cfg.ndsm_path
    p(100, "nDSM done.")
    return aligned_dtm, ndsm_path
