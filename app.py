# app.py — Modernized GUI with improved UX and visual appeal
# - Raster workflow (no DB): nDSM -> treetops -> watershed
# - Full pipeline (DB) with enhanced UI
# - Advanced path picker with Windows file dialogs
# - Interactive visualization with progress indicators
# - Modern styling with better color scheme and typography

import os
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from skimage.segmentation import find_boundaries
import tempfile
import time
from datetime import datetime
import io
import zipfile

# Optional (only needed for Full pipeline tab)
import pyodbc

from peakfinder.pipeline import (
    RunConfig,
    compute_ndsm_only,
    segment_trees_arrays,
    run_everything,
    plot_pixel_matches_for_parzelle,
)
from peakfinder.modules.tree_tops import detect_tree_tops
from peakfinder.modules.field_data import fetch_corners_and_trees, find_ground_lines, transform_trees_all
from peakfinder.modules.merge import match_stems_to_treetops, process_unmatched_stems
from peakfinder.modules.segmentation import segment_trees, match_and_visualize_updated2


# =====================================================
# Modern Styling & Configuration
# =====================================================
st.set_page_config(
    page_title="Peakfinder – UAV Tree Height Analysis",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com",
        "Report a bug": "https://github.com",
        "About": "Peakfinder v2.0 – Professional UAV-based Tree Height Analysis"
    }
)

# Modern color scheme with enhanced palette
COLORS = {
    "primary": "#2C7A7B",      # Teal
    "primary_dark": "#1F5757",
    "primary_light": "#E0F2F1",
    "success": "#059669",       # Emerald green
    "warning": "#F59E0B",       # Amber
    "danger": "#DC2626",        # Red
    "info": "#0EA5E9",          # Sky blue
    "light": "#F8FAFC",
    "card_bg": "#FFFFFF",
    "text_primary": "#1E293B",
    "text_secondary": "#64748B",
    "border": "#E2E8F0",
    "hover": "#F1F5F9",
}

# Advanced CSS styling for modern, professional appearance
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    :root {{
        --primary-color: {COLORS['primary']};
        --success-color: {COLORS['success']};
        --warning-color: {COLORS['warning']};
        --danger-color: {COLORS['danger']};
    }}
    
    /* Overall styling */
    .main {{
        background: linear-gradient(135deg, {COLORS['light']} 0%, #FFFFFF 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    
    .block-container {{
        padding-top: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 1400px;
    }}
    
    /* Headers and typography */
    h1 {{
        color: {COLORS['text_primary']};
        font-weight: 700;
        margin-bottom: 0.5rem;
        font-size: 2.75rem;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['primary_dark']} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    
    h2 {{
        color: {COLORS['text_primary']};
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 3px solid {COLORS['primary']};
        padding-bottom: 0.75rem;
        font-size: 1.875rem;
        letter-spacing: -0.01em;
    }}
    
    h3 {{
        color: {COLORS['text_primary']};
        font-weight: 600;
        font-size: 1.25rem;
        margin-top: 1rem;
    }}
    
    /* Status badges */
    .status-badge {{
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 24px;
        font-size: 0.875rem;
        font-weight: 600;
        margin-right: 0.75rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }}
    
    .status-success {{
        background: linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%);
        color: #065F46;
        border: 1px solid #6EE7B7;
    }}
    
    .status-warning {{
        background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
        color: #92400E;
        border: 1px solid #FCD34D;
    }}
    
    .status-info {{
        background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%);
        color: #1E40AF;
        border: 1px solid #93C5FD;
    }}
    
    /* Cards and sections */
    .card {{
        background: {COLORS['card_bg']};
        border-left: 5px solid {COLORS['primary']};
        padding: 1.75rem;
        border-radius: 12px;
        margin: 1.25rem 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.3s ease;
        border: 1px solid {COLORS['border']};
    }}
    
    .card:hover {{
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        transform: translateY(-2px);
    }}
    
    .info-box {{
        background: linear-gradient(135deg, {COLORS['primary_light']} 0%, #F0FDFA 100%);
        border-left: 5px solid {COLORS['info']};
        padding: 1.25rem;
        border-radius: 8px;
        margin: 0.75rem 0;
        border: 1px solid #99F6E4;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }}
    
    /* Buttons */
    .stButton > button {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['primary_dark']} 100%);
        color: white;
        font-weight: 600;
        border-radius: 8px;
        border: none;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(44, 122, 123, 0.3);
        font-size: 0.95rem;
        letter-spacing: 0.01em;
    }}
    
    .stButton > button:hover {{
        background: linear-gradient(135deg, {COLORS['primary_dark']} 0%, {COLORS['primary']} 100%);
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(44, 122, 123, 0.4);
    }}
    
    .stButton > button:active {{
        transform: translateY(-1px);
    }}
    
    /* Primary button variant */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {COLORS['success']} 0%, #047857 100%);
        box-shadow: 0 4px 6px -1px rgba(5, 150, 105, 0.3);
    }}
    
    .stButton > button[kind="primary"]:hover {{
        background: linear-gradient(135deg, #047857 0%, {COLORS['success']} 100%);
        box-shadow: 0 10px 15px -3px rgba(5, 150, 105, 0.4);
    }}
    
    /* Text inputs */
    .stTextInput > div > div > input {{
        border-radius: 8px;
        border: 2px solid {COLORS['border']};
        padding: 0.75rem;
        transition: all 0.2s ease;
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: {COLORS['primary']};
        box-shadow: 0 0 0 3px {COLORS['primary_light']};
    }}
    
    /* Sliders */
    .stSlider {{
        margin: 1.25rem 0;
    }}
    
    .stSlider > div > div > div > div {{
        background-color: {COLORS['primary']};
    }}
    
    /* Number inputs */
    .stNumberInput > div > div > input {{
        border-radius: 8px;
        border: 2px solid {COLORS['border']};
        padding: 0.75rem;
    }}
    
    .stNumberInput > div > div > input:focus {{
        border-color: {COLORS['primary']};
        box-shadow: 0 0 0 3px {COLORS['primary_light']};
    }}
    
    /* Checkboxes */
    .stCheckbox {{
        padding: 0.5rem 0;
    }}
    
    /* Divider */
    .divider {{
        border-top: 2px solid {COLORS['border']};
        margin: 2.5rem 0;
    }}
    
    /* Caption and helper text */
    .stCaption {{
        color: {COLORS['text_secondary']};
        font-size: 0.95rem;
        font-weight: 400;
    }}
    
    .helper-text {{
        font-size: 0.875rem;
        color: {COLORS['text_secondary']};
        margin: 0.5rem 0;
        line-height: 1.6;
    }}
    
    /* Expanders */
    .streamlit-expanderHeader {{
        background-color: {COLORS['hover']};
        border-radius: 8px;
        font-weight: 600;
        color: {COLORS['text_primary']};
    }}
    
    /* Metric cards */
    [data-testid="stMetricValue"] {{
        font-size: 2.25rem;
        font-weight: 700;
        color: {COLORS['primary']};
    }}
    
    [data-testid="stMetricLabel"] {{
        font-size: 1rem;
        color: {COLORS['text_secondary']};
        font-weight: 500;
    }}
    
    /* Dataframes */
    .stDataFrame {{
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        overflow: hidden;
    }}
    
    /* Download button */
    .stDownloadButton > button {{
        background: linear-gradient(135deg, {COLORS['info']} 0%, #0284C7 100%);
        box-shadow: 0 4px 6px -1px rgba(14, 165, 233, 0.3);
    }}
    
    .stDownloadButton > button:hover {{
        background: linear-gradient(135deg, #0284C7 0%, {COLORS['info']} 100%);
        box-shadow: 0 10px 15px -3px rgba(14, 165, 233, 0.4);
    }}
    
    /* Success/Error/Warning messages */
    .stSuccess {{
        background-color: #D1FAE5;
        border-left: 5px solid {COLORS['success']};
        border-radius: 8px;
        padding: 1rem;
    }}
    
    .stError {{
        background-color: #FEE2E2;
        border-left: 5px solid {COLORS['danger']};
        border-radius: 8px;
        padding: 1rem;
    }}
    
    .stWarning {{
        background-color: #FEF3C7;
        border-left: 5px solid {COLORS['warning']};
        border-radius: 8px;
        padding: 1rem;
    }}
    
    .stInfo {{
        background-color: #DBEAFE;
        border-left: 5px solid {COLORS['info']};
        border-radius: 8px;
        padding: 1rem;
    }}
    
    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {COLORS['card_bg']} 0%, {COLORS['light']} 100%);
        border-right: 1px solid {COLORS['border']};
    }}
    
    /* Header styling */
    .header-container {{
        background: linear-gradient(135deg, {COLORS['card_bg']} 0%, {COLORS['light']} 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        border: 1px solid {COLORS['border']};
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
    
    /* Step headers */
    .step-header {{
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
    }}
    
    .step-number {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['primary_dark']} 100%);
        color: white;
        width: 2.5rem;
        height: 2.5rem;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(44, 122, 123, 0.3);
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Header with branding
st.markdown('<div class="header-container">', unsafe_allow_html=True)
col_header1, col_header2 = st.columns([3, 1])
with col_header1:
    st.title("🌲 Peakfinder")
    st.caption("🚁 UAV-Based Tree Height Analysis • Advanced Raster & Database Workflows")
with col_header2:
    st.markdown(f"""
    <div style="text-align: right; padding-top: 1rem;">
        <div style="font-size: 0.85rem; color: {COLORS['text_secondary']}; font-weight: 500;">
            Updated<br>{datetime.now().strftime('%Y-%m-%d')}<br>{datetime.now().strftime('%H:%M')}
        </div>
    </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# Windows File Dialogs & Path Management
# =====================================================
def _tk_dialog_open_file(title: str, filetypes):
    """Open file dialog with Windows native interface."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        root.destroy()
        return path or ""
    except Exception as e:
        st.error(f"❌ File dialog unavailable: {str(e)[:50]}")
        return ""


def _tk_dialog_save_file(title: str, defaultextension: str = ".tif", filetypes=None):
    """Save file dialog with Windows native interface."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.asksaveasfilename(
            title=title,
            defaultextension=defaultextension,
            filetypes=filetypes or [("GeoTIFF", "*.tif *.tiff"), ("All files", "*.*")],
        )
        root.destroy()
        return path or ""
    except Exception as e:
        st.error(f"❌ Save dialog unavailable: {str(e)[:50]}")
        return ""


def _open_folder(p: str):
    """Open folder in Windows Explorer."""
    try:
        if not p:
            st.warning("📁 No path selected")
            return
        folder = os.path.dirname(p)
        if folder and os.path.exists(folder):
            os.startfile(folder)
        else:
            st.warning("📁 Folder does not exist yet")
    except Exception as e:
        st.error(f"❌ Could not open folder: {str(e)[:50]}")


def _open_file(p: str):
    """Open file in default application."""
    try:
        if p and os.path.exists(p):
            os.startfile(p)
        else:
            st.warning("📄 File does not exist")
    except Exception as e:
        st.error(f"❌ Could not open file: {str(e)[:50]}")


def path_picker(
    label: str,
    key: str,
    default: str = "",
    mode: str = "open",
    help_text: str | None = None,
    show_folder: bool = True,
    show_open: bool = True,
    show_status: bool = True,
):
    """
    Enhanced path picker with intuitive UI.
    Shows path, Browse button, folder open, and file open options.
    """
    if key not in st.session_state:
        st.session_state[key] = default

    # Display current path
    st.session_state[key] = st.text_input(
        label,
        value=st.session_state[key],
        help=help_text or ("Open existing file" if mode == "open" else "Choose output location"),
        placeholder="C:\\path\\to\\file.tif" if mode == "open" else "C:\\path\\to\\output.tif"
    )

    # Action buttons in a row: use fixed 4-column layout for consistent button sizing
    # This ensures Browse buttons are always ~25% width regardless of which optional buttons are shown
    btn_cols = st.columns([1, 1, 1, 1], gap="small")

    # Browse / Save button (first column)
    with btn_cols[0]:
        if mode == "open":
            if st.button("📂 Browse", key=f"browse_{key}", use_container_width=True):
                p = _tk_dialog_open_file(f"Select {label}", [("GeoTIFF", "*.tif *.tiff"), ("All files", "*.*")])
                if p:
                    st.session_state[key] = p
                    st.rerun()
        else:
            if st.button("💾 Save As", key=f"save_{key}", use_container_width=True):
                p = _tk_dialog_save_file(f"Save {label} as…", defaultextension=".tif")
                if p:
                    st.session_state[key] = p
                    st.rerun()

    # Folder button (column 1, optional)
    if show_folder:
        with btn_cols[1]:
            if st.button("📁 Folder", key=f"folder_{key}", use_container_width=True):
                _open_folder(st.session_state[key])

    # Open button (column 2, optional)
    if show_open:
        with btn_cols[2]:
            if st.button("📄 Open", key=f"open_{key}", use_container_width=True):
                _open_file(st.session_state[key])

    # Status badge (column 3, optional)
    if show_status:
        with btn_cols[3]:
            if st.session_state[key] and os.path.exists(st.session_state[key]):
                st.markdown('<span class="status-badge status-success">✓ Exists</span>', unsafe_allow_html=True)
            elif st.session_state[key]:
                st.markdown('<span class="status-badge status-warning">⚠ Not found</span>', unsafe_allow_html=True)

    return st.session_state[key]


@st.cache_data(show_spinner=False)
def _read_raster_preview(path: str, max_dim: int = 1200):
    """Efficiently load raster preview for visualization."""
    with rasterio.open(path) as src:
        arr = src.read(1).astype("float32")
        nodata = src.nodata
        profile = src.profile

    if nodata is not None:
        arr = np.where(arr == nodata, np.nan, arr)

    h, w = arr.shape
    step = int(max(1, max(h, w) / max_dim))
    arr_small = arr[::step, ::step]
    return arr_small, (h, w), step, profile


def _stretch(arr: np.ndarray, p_low: float, p_high: float) -> np.ndarray:
    """Apply percentile-based contrast stretch to array."""
    a = arr.astype("float32")
    if a.size == 0 or np.all(np.isnan(a)):
        return a
    lo = float(np.nanpercentile(a, p_low))
    hi = float(np.nanpercentile(a, p_high))
    if (not np.isfinite(lo)) or (not np.isfinite(hi)) or hi <= lo:
        return a
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0)


def export_segmentation_as_geojson(labels, transform, matching_results, output_format="geojson"):
    """
    Export segmentation labels as GeoJSON features with metadata from matching results.
    Each polygon represents a segment with attributes from the matching results.
    
    Args:
        labels: 2D array of segment labels
        transform: rasterio Affine transform
        matching_results: List of dicts with matching info (Parzelle, Nr, heights, etc.)
        output_format: 'geojson' (default) for ArcGIS compatibility
    
    Returns:
        GeoJSON string
    """
    try:
        from skimage.measure import find_contours
        from rasterio.features import shapes
        import json
        
        # Create a mapping from segment ID to metadata from matching results
        segment_metadata = {}
        for result in matching_results:
            # Find which segment this stem belongs to
            parzelle = result.get("Parzelle")
            nr = result.get("Nr")
            match = result.get("match")
            height = result.get("UAV_Tree_Height_segment")
            
            # We'll need to look up segment ID - it's implicit in the labels
            # For now, create metadata dict indexed by any matched segments
            if match == 1:  # Only include matched stems
                key = (int(parzelle) if parzelle is not None else 0, 
                       int(nr) if nr is not None else 0)
                segment_metadata[key] = {
                    "Parzelle": int(parzelle) if parzelle is not None else 0,
                    "Nr": int(nr) if nr is not None else 0,
                    "Height": float(height) if height is not None else None,
                    "Match": match,
                    "Stem_X": float(result.get("Stem_UTM_X", 0)),
                    "Stem_Y": float(result.get("Stem_UTM_Y", 0)),
                    "Treetop_X": float(result.get("Treetop_UTM_X", 0)) if result.get("Treetop_UTM_X") else None,
                    "Treetop_Y": float(result.get("Treetop_UTM_Y", 0)) if result.get("Treetop_UTM_Y") else None,
                }
        
        # Extract segment polygons using rasterio.features.shapes
        features = []
        for shape_geom, segment_id in shapes(labels.astype('int32'), transform=transform):
            seg_id = int(segment_id)
            if seg_id == 0:  # Skip background
                continue
            
            # Find matching metadata for this segment
            # Search through results for any stem in this segment
            properties = {
                "Segment_ID": seg_id,
                "Parzelle": None,
                "Nr": None,
                "Height": None,
                "Match": 0,
                "Stem_X": None,
                "Stem_Y": None,
                "Treetop_X": None,
                "Treetop_Y": None,
            }
            
            # Find matching result for this segment
            for result in matching_results:
                if result.get("match") == 1:  # Only matched stems
                    properties.update({
                        "Parzelle": int(result.get("Parzelle", 0)),
                        "Nr": int(result.get("Nr", 0)),
                        "Height": float(result.get("UAV_Tree_Height_segment", 0)) if result.get("UAV_Tree_Height_segment") else None,
                        "Match": result.get("match", 0),
                        "Stem_X": float(result.get("Stem_UTM_X", 0)),
                        "Stem_Y": float(result.get("Stem_UTM_Y", 0)),
                        "Treetop_X": float(result.get("Treetop_UTM_X", 0)) if result.get("Treetop_UTM_X") else None,
                        "Treetop_Y": float(result.get("Treetop_UTM_Y", 0)) if result.get("Treetop_UTM_Y") else None,
                    })
                    break  # Use first match found
            
            features.append({
                "type": "Feature",
                "geometry": shape_geom,
                "properties": properties
            })
        
        # Create FeatureCollection
        geojson_dict = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return json.dumps(geojson_dict, indent=2)
    
    except Exception as e:
        st.error(f"❌ Error exporting segmentation: {str(e)}")
        return None


def export_segmentation_as_shapefile_zip(labels, transform, crs, matching_results):
    """
    Export segmentation labels as an ESRI Shapefile (zipped) with metadata
    from matching results. Returns in-memory zip bytes suitable for download.

    Logic for attributes: the segment that includes a given stem belongs to
    that tree; attributes are taken from that matched stem's record.
    """
    try:
        import shapefile  # pyshp
        from rasterio.features import shapes
        import rasterio
    except Exception as e:
        st.error("Shapefile export requires the 'shapefile' package. Install with: pip install shapefile")
        return None

    try:
        # Build mapping from segment_id -> matching record (for matched stems)
        seg_meta = {}
        for r in matching_results or []:
            if r.get("match") == 1:
                try:
                    rr, cc = rasterio.transform.rowcol(transform, r["Stem_UTM_X"], r["Stem_UTM_Y"]) 
                    if 0 <= rr < labels.shape[0] and 0 <= cc < labels.shape[1]:
                        sid = int(labels[rr, cc])
                        if sid > 0 and sid not in seg_meta:
                            seg_meta[sid] = r
                except Exception:
                    continue

        # Prepare temporary directory and base filenames
        tmpdir = tempfile.mkdtemp(prefix="seg_shp_")
        base = "Segmentation"
        shp_path = os.path.join(tmpdir, base + ".shp")
        shx_path = os.path.join(tmpdir, base + ".shx")
        dbf_path = os.path.join(tmpdir, base + ".dbf")
        prj_path = os.path.join(tmpdir, base + ".prj")

        # Create writer
        w = shapefile.Writer(shp_path, shapeType=shapefile.POLYGON)
        w.autoBalance = 1

        # Define DBF fields (<=10 char names due to DBF limits)
        w.field("Segment_ID", "N", 10)
        w.field("Parzelle", "N", 10)
        w.field("Nr", "N", 10)
        w.field("Height", "F", 10, 2)
        w.field("Match", "N", 1)
        w.field("Stem_X", "F", 18, 3)
        w.field("Stem_Y", "F", 18, 3)
        w.field("Top_X", "F", 18, 3)
        w.field("Top_Y", "F", 18, 3)

        # Iterate shapes from labeled raster
        for geom, seg_id in shapes(labels.astype("int32"), transform=transform):
            sid = int(seg_id)
            if sid == 0:
                continue

            if not isinstance(geom, dict) or "type" not in geom or "coordinates" not in geom:
                continue

            parts = []  # list of rings
            if geom["type"] == "Polygon":
                for ring in geom["coordinates"]:
                    parts.append([(float(x), float(y)) for (x, y) in ring])
            elif geom["type"] == "MultiPolygon":
                for poly in geom["coordinates"]:
                    for ring in poly:
                        parts.append([(float(x), float(y)) for (x, y) in ring])
            else:
                continue

            if not parts:
                continue

            # Write geometry and attributes
            w.poly(parts=parts)
            m = seg_meta.get(sid, {})
            w.record(
                Segment_ID=sid,
                Parzelle=int(m.get("Parzelle", 0)) if m.get("Parzelle") is not None else 0,
                Nr=int(m.get("Nr", 0)) if m.get("Nr") is not None else 0,
                Height=float(m.get("UAV_Tree_Height_segment", 0)) if m.get("UAV_Tree_Height_segment") is not None else None,
                Match=int(m.get("match", 0)),
                Stem_X=float(m.get("Stem_UTM_X", 0)) if m.get("Stem_UTM_X") is not None else None,
                Stem_Y=float(m.get("Stem_UTM_Y", 0)) if m.get("Stem_UTM_Y") is not None else None,
                Top_X=float(m.get("Treetop_UTM_X", 0)) if m.get("Treetop_UTM_X") is not None else None,
                Top_Y=float(m.get("Treetop_UTM_Y", 0)) if m.get("Treetop_UTM_Y") is not None else None,
            )

        w.close()

        # Write .prj
        try:
            if crs is not None:
                try:
                    wkt = crs.to_wkt()  # rasterio CRS
                except Exception:
                    wkt = str(crs)
                with open(prj_path, "w", encoding="utf-8") as f:
                    f.write(wkt)
        except Exception:
            pass

        # Zip all components
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in (shp_path, shx_path, dbf_path):
                if os.path.exists(p):
                    zf.write(p, arcname=os.path.basename(p))
            if os.path.exists(prj_path):
                zf.write(prj_path, arcname=os.path.basename(prj_path))
        mem_zip.seek(0)
        return mem_zip.getvalue()

    except Exception as e:
        st.error(f"❌ Error creating Shapefile: {str(e)}")
        return None


def _stretch(arr: np.ndarray, p_low: float, p_high: float) -> np.ndarray:
    """Apply percentile-based contrast stretch to array."""
    a = arr.astype("float32")
    if a.size == 0 or np.all(np.isnan(a)):
        return a
    lo = float(np.nanpercentile(a, p_low))
    hi = float(np.nanpercentile(a, p_high))
    if (not np.isfinite(lo)) or (not np.isfinite(hi)) or hi <= lo:
        return a
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0)


def raster_viewer(path: str, title: str, key_prefix: str = "viewer"):
    """
    Display raster with interactive percentile stretch slider.
    Includes metadata display and statistics.
    """
    if not path or not os.path.exists(path):
        st.info(f"📄 {title}: file not found")
        return

    try:
        arr_small, (h, w), step, profile = _read_raster_preview(path)
    except Exception as e:
        st.error(f"Error reading raster: {str(e)[:100]}")
        return

    # Slider state
    range_key = f"{key_prefix}_prange"
    if range_key not in st.session_state:
        st.session_state[range_key] = (2.0, 98.0)

    p_low, p_high = st.session_state[range_key]
    if p_high <= p_low:
        p_high = min(100.0, p_low + 0.5)

    disp = _stretch(arr_small, p_low=p_low, p_high=p_high)

    # Header section with enhanced styling
    st.markdown('<div class="card">', unsafe_allow_html=True)
    col_title, col_meta1, col_meta2 = st.columns([2, 1, 1])
    
    with col_title:
        st.markdown(f"### {title}")
    
    with col_meta1:
        st.markdown(
            f'<div style="text-align: center; padding: 0.5rem; background: {COLORS["primary_light"]}; border-radius: 8px;">'
            f'<div style="font-size: 0.75rem; color: {COLORS["text_secondary"]}; font-weight: 600;">DIMENSIONS</div>'
            f'<div style="font-size: 1.1rem; font-weight: 700; color: {COLORS["primary"]};">{h:,} × {w:,}</div>'
            f'<div style="font-size: 0.75rem; color: {COLORS["text_secondary"]};">pixels</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    with col_meta2:
        if profile:
            try:
                res = profile.get('transform')[0]
                st.markdown(
                    f'<div style="text-align: center; padding: 0.5rem; background: {COLORS["primary_light"]}; border-radius: 8px;">'
                    f'<div style="font-size: 0.75rem; color: {COLORS["text_secondary"]}; font-weight: 600;">RESOLUTION</div>'
                    f'<div style="font-size: 1.1rem; font-weight: 700; color: {COLORS["primary"]};">{res:.3f}</div>'
                    f'<div style="font-size: 0.75rem; color: {COLORS["text_secondary"]};">m/px</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            except:
                pass

    # Display image with border
    st.markdown('<div style="border: 2px solid ' + COLORS["border"] + '; border-radius: 8px; overflow: hidden; margin: 1rem 0;">', unsafe_allow_html=True)
    st.image(disp, use_column_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Stretch slider
    st.slider(
        "🎨 Contrast Stretch (percentiles)",
        0.0, 100.0,
        value=(float(p_low), float(p_high)),
        step=0.5,
        key=range_key,
    )

    # Additional metadata
    if profile:
        col_crs, col_count = st.columns([2, 1])
        with col_crs:
            crs_str = str(profile.get('crs', 'N/A'))
            if len(crs_str) > 50:
                crs_str = crs_str[:47] + "..."
            st.markdown(f"<span style='color: {COLORS['text_secondary']}; font-size: 0.875rem;'><strong>CRS:</strong> {crs_str}</span>", unsafe_allow_html=True)
        with col_count:
            st.markdown(f"<span style='color: {COLORS['text_secondary']}; font-size: 0.875rem;'><strong>Bands:</strong> {profile.get('count', 'N/A')}</span>", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# Session State Management
# =====================================================
for k in ["ndsm_use", "treetops_df", "treetops_fig", "seg_fig", "seg_labels_max", "seg_n_tops"]:
    if k not in st.session_state:
        st.session_state[k] = None


# =====================================================
# Main Workflow: Tabs
# =====================================================
st.markdown("---")
main = st.container()


# =========================================================
# TAB 1: Raster Workflow (Enhanced)
# =========================================================
with main:
    # ============== STEP 1: Path Setup ==============
    st.markdown('<div class="step-header"><div class="step-number">1</div><h2 style="border: none; margin: 0; padding: 0;">File Paths</h2></div>', unsafe_allow_html=True)
    st.caption("📂 Define input and output paths • Use 'Browse' to select files with ease")
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.markdown("**Input File**")
        dsm_path = path_picker(
            "📥 DSM (Digital Surface Model)",
            "dsm_path",
            default=r"D:\\Drohnendaten\\...\\DSM.tif",
            mode="open",
            show_folder=False,
            show_open=False,
            help_text="Original UAV-derived DSM (required)"
        )

        st.divider()

        st.markdown("**Output Files**")
        # DTM output path (visible): Browse button only (no Folder/Open/Status)
        dtm_path = path_picker(
            "📤 DTM (Digital Terrain Model)",
            "dtm_path",
            default=r"D:\\Drohnendaten\\...\\DTM.tif",
            mode="save",
            show_folder=False,
            show_open=False,
            show_status=False,
            help_text="Interpolated terrain model (output)"
        )

        # nDSM path: Browse button + status badge for consistency
        ndsm_path = path_picker(
            "📤 nDSM (normalized Digital Surface Model)",
            "ndsm_path",
            default=r"D:\\Drohnendaten\\...\\nDSM.tif",
            mode="open",
            show_folder=False,
            show_open=False,
            show_status=True,
            help_text="DSM - DTM. Can also load existing nDSM"
        )

        st.markdown('</div>', unsafe_allow_html=True)
    
    # Quick setup buttons with improved styling
    st.markdown("#### ⚡ Quick Actions")
    col_quick1, col_quick2, col_quick3 = st.columns([2, 2, 2], gap="small")
    with col_quick1:
        if st.button("🔄 Auto-fill from DSM", use_container_width=True, key="autofill_paths"):
            if dsm_path and os.path.exists(dsm_path):
                base = os.path.splitext(dsm_path)[0]
                st.session_state["dtm_path"] = base.replace("_DSM", "_DTM") + ".tif"
                st.session_state["ndsm_path"] = base.replace("_DSM", "_nDSM") + ".tif"
                st.success("✓ Paths auto-filled successfully")
            else:
                st.error("⚠️ Select an existing DSM first")

    st.markdown("---")
    
    # ============== STEP 2: nDSM Creation ==============
    st.markdown('<div class="step-header"><div class="step-number">2</div><h2 style="border: none; margin: 0; padding: 0;">Create or Load nDSM</h2></div>', unsafe_allow_html=True)
    st.caption("🌐 Generate normalized Digital Surface Model or load existing")
    
    col_ndsm_left, col_ndsm_right = st.columns([1, 1], gap="large")
    
    with col_ndsm_left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Configuration**")
        
        compute_ndsm = st.checkbox("🌐 Compute nDSM (download DGM1 via WCS)", value=True, 
                                    help="If unchecked, will use existing nDSM file")
        
        if compute_ndsm:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown("**LDBV Credentials** (required for WCS download)")
            ldbv_user = st.text_input("LDBV username", value="", key="ndsm_ldbv_user")
            ldbv_pass = st.text_input("LDBV password", value="", type="password", key="ndsm_ldbv_pass")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            ldbv_user, ldbv_pass = None, None
        
        buffer_m = st.slider("AOI buffer (meters)", 0.0, 10.0, 2.0, 0.5, 
                             help="Expand area of interest by this distance")
        pixel_m = st.slider("DGM resolution (meters)", 0.25, 2.0, 1.0, 0.25,
                           help="Target pixel size for DGM")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_ndsm_right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Execute**")
        
        run_ndsm = st.button("▶ Run nDSM Step", type="primary", use_container_width=True)
        
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        if run_ndsm:
            if compute_ndsm:
                if not (ldbv_user and ldbv_pass):
                    st.error("❌ LDBV credentials required")
                elif not (dsm_path and os.path.exists(dsm_path)):
                    st.error("❌ Select an existing DSM file")
                elif not ndsm_path:
                    st.error("❌ Choose output path for nDSM")
                else:
                    cfg = RunConfig(
                        dsn_name="", versuch_id=0,
                        dsm_path=dsm_path, dtm_path=dtm_path, ndsm_path=ndsm_path,
                        compute_ndsm=True,
                        buffer_m=float(buffer_m), pixel_m=float(pixel_m),
                        ldbv_user=ldbv_user.strip(),
                        ldbv_pass=ldbv_pass,
                        neighborhood_size=100, min_height_threshold=10.0, sigma=2.0,
                        max_distance=2.0, radius_unmatched=5.0,
                        use_segmentation=True, seg_use_subset=True,
                        seg_subset_size_m=200.0, seg_ground_threshold=5.0,
                        seg_sigma_for_treetops=10.0, seg_sigma_for_segmentation=1.0,
                        seg_min_distance=5, seg_threshold_abs=5.0,
                        seg_compactness=0.2, seg_min_area_threshold=1500,
                        output_csv_path=None,
                    )
                    try:
                        with st.spinner("⏳ Computing nDSM (may take a few minutes)..."):
                            _aligned_dtm, ndsm_out = compute_ndsm_only(cfg, progress=None, log=None)
                        st.session_state["ndsm_use"] = ndsm_out
                        st.success("✅ nDSM computed successfully")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)[:100]}")
            else:
                if not (ndsm_path and os.path.exists(ndsm_path)):
                    st.error("❌ nDSM file not found")
                else:
                    st.session_state["ndsm_use"] = ndsm_path
                    st.success("✅ Using existing nDSM")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # nDSM Preview
    ndsm_use = st.session_state.get("ndsm_use") or (ndsm_path if ndsm_path and os.path.exists(ndsm_path) else None)
    if ndsm_use:
        st.divider()
        raster_viewer(ndsm_use, "📊 nDSM Preview", key_prefix="ndsm_main")
    
    st.markdown("---")
    
    # ============== STEP 3: Fetch Field Positions (DB) ==============
    st.markdown('<div class="step-header"><div class="step-number">3</div><h2 style="border: none; margin: 0; padding: 0;">Fetch Field Positions (DB)</h2></div>', unsafe_allow_html=True)
    st.caption("🗄️ Load field-measured stem positions from database and visualize all plots")

    col_db_a, col_db_b = st.columns([1, 1], gap="small")
    with col_db_a:
        dsn_input = st.text_input("ODBC DSN (for DB)", value="", key="step5_dsn")
    with col_db_b:
        versuch_input = st.number_input("Versuch ID", min_value=1, value=1, step=1, key="step5_versuch")

    fetch_db = st.button("▶ Fetch Field Data", use_container_width=False, key="fetch_field")

    if fetch_db:
        try:
            with st.spinner("🗄️ Fetching DB points and transforming to UTM…"):
                corners, trees_local = fetch_corners_and_trees(dsn_input, int(versuch_input))
                if corners is None or trees_local is None:
                    st.error("❌ Failed to fetch from database")
                else:
                    ground_lines = find_ground_lines(corners)
                    stems_utm = transform_trees_all(trees_local, ground_lines)
                    st.session_state["stems_utm"] = stems_utm
                    st.session_state["corners"] = corners
                    st.success(f"✅ Fetched {len(stems_utm)} stems and {len(corners)} plot corners from DB")
                    
                    # Visualize all plots: corners + stems
                    try:
                        fig = plt.figure(figsize=(8, 6))
                        ax = fig.add_subplot(111)
                        
                        # Extract corner coordinates
                        corner_x = [p[2] for p in corners]
                        corner_y = [p[3] for p in corners]
                        
                        # Extract stem coordinates
                        stem_x = [t[2] for t in stems_utm]
                        stem_y = [t[3] for t in stems_utm]
                        
                        # Plot all corners as blue squares
                        ax.scatter(corner_x, corner_y, color="blue", label="Plot Corners", marker="s", s=25)
                        
                        # Plot all stems as purple dots
                        ax.scatter(stem_x, stem_y, color="purple", label="Tree Stems", alpha=0.7, s=25)
                        
                        ax.set_xlabel("UTM_x")
                        ax.set_ylabel("UTM_y")
                        num_corners = len(corners)
                        num_stems = len(stems_utm)
                        ax.set_title(f"All Plots: {num_stems} Tree Stems, {num_corners} Plot Corners")
                        ax.legend()
                        ax.grid(True)
                        
                        # Store figure in session state for persistence
                        st.session_state["step5_fig"] = fig
                        
                        st.pyplot(fig, use_container_width=True)
                        st.info(f"📊 Summary: {num_stems} tree stems, {num_corners} plot corners found in database")
                        plt.close(fig)
                    except Exception as e:
                        st.error(f"❌ Visualization error: {str(e)[:120]}")
        except Exception as e:
            st.error(f"❌ DB error: {str(e)[:120]}")

    # Display persisted Step 3 visualization
    if st.session_state.get("step5_fig") is not None and not fetch_db:
        try:
            st.pyplot(st.session_state["step5_fig"], use_container_width=True)
        except:
            pass

    st.markdown("---")
    
    # ============== STEP 4: Marker-Based Watershed Segmentation ==============
    st.markdown('<div class="step-header"><div class="step-number">4</div><h2 style="border: none; margin: 0; padding: 0;">Marker-Based Watershed Segmentation</h2></div>', unsafe_allow_html=True)
    st.caption("🌳 Delineate individual tree crowns using detected treetops as markers")
    
    col_seg_left, col_seg_right = st.columns([1, 1], gap="large")
    
    with col_seg_left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        with st.expander("⚙️ Segmentation Parameters", expanded=True):
            seg_use_subset = st.checkbox("Use center subset (faster)", value=False, help="Enable to process only a center subset of the nDSM for faster testing. Disable for full extent processing.")
            seg_subset_size_m = st.slider("Subset size (m)", 50.0, 1000.0, 200.0, 25.0, help="Size of the center subset in meters. Increase for testing larger areas, decrease for quicker iterations during parameter tuning.")
            seg_use_db_extent = st.checkbox("Use DB extent (stems & corners)", value=True, help="Use the AOI derived from Step 3 (DB stems/corners) for the segmentation window")
            seg_aoi_buffer_m = st.slider("AOI buffer (m)", 0.0, 100.0, 10.0, 1.0, help="Buffer to expand DB-derived AOI when creating subset. Increase if trees near the edge are cut off.")
            seg_show_stems = st.checkbox("Show field stem positions", value=True, help="Display field stem positions (from Step 3) in the segmentation visualization. Useful for visual comparison between field data and detected tree crowns.")
            seg_ground_threshold = st.slider("Ground threshold (m)", 0.0, 20.0, 5.0, 0.5, help="Minimum height above ground to be considered vegetation. Increase to filter out shrubs and low vegetation, decrease if missing small trees.")
            seg_sigma_for_treetops = st.slider("Sigma for treetops", 0.0, 30.0, 10.0, 0.5, help="Gaussian smoothing for treetop detection. For larger tree crowns, increase to merge nearby peaks. For small, dense crowns, decrease to detect more individual peaks.")
            seg_sigma_for_segmentation = st.slider("Sigma for segmentation", 0.0, 10.0, 1.0, 0.25, help="Gaussian smoothing for watershed segmentation. Increase to create smoother, larger segments (suitable for large crowns). Decrease for more detailed, smaller segments (suitable for small crowns).")
            seg_min_distance = st.slider("Min distance (px)", 1, 50, 5, 1, help="Minimum distance between detected treetops in pixels. Increase if crowns are being over-segmented (too many peaks detected), decrease to separate closely spaced trees.")
            seg_threshold_abs = st.slider("Peak threshold (m)", 0.0, 30.0, 5.0, 0.5, help="Minimum height of a peak to be considered a treetop. Increase to filter out shorter trees and noise, decrease if tall trees are being missed.")
            seg_min_area_threshold = st.slider("Min segment area (px²)", 0, 10000, 1500, 50, help="Minimum segment size in pixels. Increase to filter out small, spurious segments (suitable for large crowns). Decrease if small tree crowns are being removed.")
            seg_compactness = st.slider("Watershed compactness", 0.0, 2.0, 0.2, 0.05, help="Controls segment shape regularity. Increase for more circular, compact segments (useful for round crowns). Decrease for irregular, natural crown shapes.")
        
        run_seg = st.button("▶ Run Segmentation", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_seg_right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        if run_seg:
            ndsm_use = st.session_state.get("ndsm_use")
            if not ndsm_use:
                st.error("❌ Run nDSM step first")
            else:
                try:
                    with st.spinner("🔄 Running watershed segmentation..."):
                        subset_path = ndsm_use
                        # If user requested DB extent and DB data exist, build a spatial subset around stems/corners
                        if seg_use_db_extent:
                            stems_utm = st.session_state.get("stems_utm")
                            corners = st.session_state.get("corners") or []
                            coords = []
                            if corners:
                                coords.extend([(p[2], p[3]) for p in corners])
                            if stems_utm:
                                coords.extend([(t[2], t[3]) for t in stems_utm])

                            if coords:
                                xs = [c[0] for c in coords]
                                ys = [c[1] for c in coords]
                                minx, maxx = min(xs) - float(seg_aoi_buffer_m), max(xs) + float(seg_aoi_buffer_m)
                                miny, maxy = min(ys) - float(seg_aoi_buffer_m), max(ys) + float(seg_aoi_buffer_m)
                                try:
                                    with rasterio.open(ndsm_use) as src:
                                        window = rasterio.windows.from_bounds(minx, miny, maxx, maxy, transform=src.transform)
                                        window = window.round_offsets().round_shape()
                                        if window.width > 0 and window.height > 0:
                                            ndsm_subset = src.read(1, window=window)
                                            subset_transform = src.window_transform(window)
                                            tmp_path = os.path.join(tempfile.gettempdir(), f"ndsm_subset_{int(time.time())}.tif")
                                            profile = src.profile.copy()
                                            profile.update({
                                                "height": ndsm_subset.shape[0],
                                                "width": ndsm_subset.shape[1],
                                                "transform": subset_transform,
                                                "count": 1
                                            })
                                            with rasterio.open(tmp_path, "w", **profile) as dst:
                                                dst.write(ndsm_subset, 1)
                                            subset_path = tmp_path
                                except Exception:
                                    subset_path = ndsm_use

                        labels, treetop_coords, ndsm_subset, transform, fig_seg = segment_trees_arrays(
                            ndsm_path=subset_path,
                            ground_threshold=float(seg_ground_threshold),
                            sigma_for_treetops=float(seg_sigma_for_treetops),
                            sigma_for_segmentation=float(seg_sigma_for_segmentation),
                            min_distance=int(seg_min_distance),
                            threshold_abs=float(seg_threshold_abs),
                            exclude_border=True,
                            connectivity=1,
                            compactness=float(seg_compactness),
                            watershed_line=False,
                            subset_size_meters=float(seg_subset_size_m),
                            min_area_threshold=int(seg_min_area_threshold),
                            use_subset=bool(seg_use_subset),
                            stems_utm=st.session_state.get("stems_utm") if seg_show_stems else None,
                        )
                        # Store CRS for shapefile export later
                        try:
                            with rasterio.open(subset_path) as _src_crs:
                                st.session_state["seg_crs"] = _src_crs.crs
                        except Exception:
                            st.session_state["seg_crs"] = None
                    st.session_state["seg_fig"] = fig_seg
                    st.session_state["seg_fig"] = fig_seg
                    st.session_state["seg_labels_max"] = int(labels.max())
                    st.session_state["seg_n_tops"] = int(len(treetop_coords))
                    # store segmentation arrays for downstream matching/visualization
                    st.session_state["seg_labels_array"] = labels
                    st.session_state["seg_treetop_coords"] = treetop_coords
                    st.session_state["seg_ndsm_subset"] = ndsm_subset
                    st.session_state["seg_transform"] = transform
                    # placeholder for segmentation match results (will be merged with DB stems later)
                    st.session_state["seg_results"] = None
                    st.success(f"✅ Segmentation complete: {int(labels.max())} segments")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)[:100]}")
        
        if st.session_state.get("seg_fig") is not None:
            st.pyplot(st.session_state["seg_fig"], use_container_width=True)
            plt.close(st.session_state["seg_fig"])
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Summary stats
    if st.session_state.get("seg_labels_max") is not None:
        st.divider()
        st.markdown("### 📊 Segmentation Summary")
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.metric("🌲 Tree Segments", st.session_state['seg_labels_max'])
        with col_stat2:
            st.metric("🎯 Detected Treetops", st.session_state['seg_n_tops'])
    
    st.markdown("---")
    st.markdown(
        f'<div style="background: linear-gradient(135deg, {COLORS["primary_light"]} 0%, #E0F2F1 100%); '
        f'border-left: 5px solid {COLORS["info"]}; padding: 1.25rem; border-radius: 8px; '
        f'border: 1px solid {COLORS["border"]};">'
        f'<div style="display: flex; align-items: center; gap: 0.75rem;">'
        f'<span style="font-size: 1.5rem;">💡</span>'
        f'<span style="color: {COLORS["text_primary"]}; font-weight: 500;">'
        f'<strong>Tip:</strong> If results look odd, the issue is likely data quality '
        f'(DTM interpolation, nodata values, CRS/units).</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # ============== STEP 5: Segment-Based Matching (using Step 4 segmentation) ==============
    st.markdown('<div class="step-header"><div class="step-number">5</div><h2 style="border: none; margin: 0; padding: 0;">Segment-Based Matching</h2></div>', unsafe_allow_html=True)
    st.caption("🎯 Match field stems with UAV treetops using the segmentation from Step 4")

    run_step5_matching = st.button("▶ Run Matching (Step 4 Segments)", use_container_width=False, key="run_step5_matching")

    if run_step5_matching:
        stems_utm = st.session_state.get("stems_utm")
        seg_labels = st.session_state.get("seg_labels_array")
        seg_treetops = st.session_state.get("seg_treetop_coords")
        seg_ndsm = st.session_state.get("seg_ndsm_subset")
        seg_transform = st.session_state.get("seg_transform")

        if not stems_utm:
            st.error("❌ Run Step 3 first to fetch field data")
        elif seg_labels is None or seg_treetops is None:
            st.error("❌ Run Step 4 first to perform segmentation")
        else:
            try:
                with st.spinner("🔄 Matching stems with Step 4 segmentation…"):
                    # Perform matching using Step 4 segmentation results
                    results_step5 = match_and_visualize_updated2(
                        labels=seg_labels,
                        treetop_coords=seg_treetops,
                        stem_coords=stems_utm,
                        ndsm=seg_ndsm,
                        transform=seg_transform
                    )

                    st.session_state["matching_results_step5"] = results_step5
                    st.session_state["match_labels_step5"] = seg_labels
                    st.session_state["match_ndsm_step5"] = seg_ndsm
                    st.session_state["match_transform_step5"] = seg_transform

                    # Count results
                    matched = sum(1 for r in results_step5 if r["match"] == 1)
                    unmatched = sum(1 for r in results_step5 if r["match"] == 0)
                    no_segment = sum(1 for r in results_step5 if r["match"] == 2)

                    st.success(f"✅ Matching completed: {matched} matched, {unmatched} unmatched, {no_segment} without segment")
            except Exception as e:
                st.error(f"❌ Matching error: {str(e)[:150]}")

        # Display visualization if matching was done
        matching_results_step5 = st.session_state.get("matching_results_step5")
        if matching_results_step5:
            try:
                with st.spinner("📊 Creating visualization…"):
                    labels = st.session_state.get("match_labels_step5")
                    ndsm_full = st.session_state.get("match_ndsm_step5")
                    transform_full = st.session_state.get("match_transform_step5")
                    
                    # Apply contrast stretch for visualization only (0.5-99.5 percentile for better detail)
                    ndsm_viz = _stretch(ndsm_full, 0.5, 99.5)
                    
                    # Create nDSM visualization with color-coded stems
                    fig, ax = plt.subplots(figsize=(10, 10))
                    
                    ax.imshow(ndsm_viz, cmap='gray', origin='upper')
                    # Overlay red segment boundaries
                    try:
                        from skimage import segmentation as sk_seg
                        boundaries_mask = sk_seg.mark_boundaries(np.zeros_like(labels, dtype=float), labels, color=(1, 0, 0))
                        boundary_display = np.zeros_like(ndsm_viz, dtype=float)
                        boundary_display[boundaries_mask[:, :, 0] > 0] = 1.0
                        ax.imshow(boundary_display, cmap='Reds', alpha=0.8, origin='upper', interpolation='nearest', vmin=0, vmax=1)
                    except Exception:
                        pass
                    ax.set_title("Segment-Based Matching Visualization", fontsize=14)
                    
                    # Plot stems with different colors based on match status
                    matched_stems = [r for r in matching_results_step5 if r["match"] == 1]
                    unmatched_stems = [r for r in matching_results_step5 if r["match"] == 0]
                    no_segment_stems = [r for r in matching_results_step5 if r["match"] == 2]
                    
                    # Plot matched stems (green)
                    if matched_stems:
                        for r in matched_stems:
                            row, col = rasterio.transform.rowcol(transform_full, r["Stem_UTM_X"], r["Stem_UTM_Y"])
                            if 0 <= row < ndsm_full.shape[0] and 0 <= col < ndsm_full.shape[1]:
                                ax.scatter(col, row, color="green", s=12, edgecolors="black", linewidth=0.25, marker='o', zorder=5)
                    
                    # Plot unmatched stems (red)
                    if unmatched_stems:
                        for r in unmatched_stems:
                            row, col = rasterio.transform.rowcol(transform_full, r["Stem_UTM_X"], r["Stem_UTM_Y"])
                            if 0 <= row < ndsm_full.shape[0] and 0 <= col < ndsm_full.shape[1]:
                                ax.scatter(col, row, color="red", s=12, edgecolors="black", linewidth=0.25, marker='o', zorder=5)
                    
                    # Plot stems without segment (purple)
                    if no_segment_stems:
                        for r in no_segment_stems:
                            row, col = rasterio.transform.rowcol(transform_full, r["Stem_UTM_X"], r["Stem_UTM_Y"])
                            if 0 <= row < ndsm_full.shape[0] and 0 <= col < ndsm_full.shape[1]:
                                ax.scatter(col, row, color="purple", s=12, edgecolors="black", linewidth=0.25, marker='o', zorder=5)
                    
                    # Add custom legend
                    ax.scatter([], [], color="green", s=12, edgecolors="black", linewidth=0.25, marker='o', label="Matched Stems")
                    ax.scatter([], [], color="red", s=12, edgecolors="black", linewidth=0.25, marker='o', label="Unmatched Stems")
                    ax.scatter([], [], color="purple", s=12, edgecolors="black", linewidth=0.25, marker='o', label="Stems without Segment")
                    
                    ax.set_axis_off()
                    ax.legend(fontsize=5, loc='upper left')
                    
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)
            except Exception as e:
                st.error(f"❌ Visualization error: {str(e)[:150]}")

            # Export results as CSV
            try:
                df_results = pd.DataFrame(matching_results_step5)
                csv_bytes = df_results.to_csv(index=False).encode("utf-8")
                
                st.divider()
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("### 📥 Matching Results")
                st.dataframe(df_results, use_container_width=True)
                
                # CSV export button
                st.download_button(
                    "⬇️ Download Step5_matching.csv",
                    data=csv_bytes,
                    file_name="Step5_matching.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.markdown('</div>', unsafe_allow_html=True)

                    
            except Exception as e:
                st.error(f"❌ CSV export error: {str(e)[:150]}")

    st.markdown("---")

    # ============== STEP 6: Height Distribution Analysis ==============
    st.markdown('<div class="step-header"><div class="step-number">6</div><h2 style="border: none; margin: 0; padding: 0;">Height Distribution Analysis</h2></div>', unsafe_allow_html=True)
    st.caption("📊 Analyze the height distribution of successfully matched trees")

    col_analysis_left, col_analysis_right = st.columns([1, 1], gap="large")
    
    with col_analysis_left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        with st.expander("⚙️ Visualization Parameters", expanded=True):
            bin_size = st.slider("Height bin size (m)", 1.0, 10.0, 5.0, 0.5, help="Size of height classes for the histogram. Decrease for more detailed distribution, increase for broader overview.")
            show_only_matched = st.checkbox("Show only matched trees", value=True, help="Display only successfully matched trees (green markers from Step 5). Uncheck to see all stems including unmatched ones.")
            show_stats_table = st.checkbox("Show statistics table", value=True, help="Display detailed statistics including count, mean, median, min, max, and standard deviation.")
        
        run_analysis = st.button("▶ Run Analysis", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_analysis_right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        if run_analysis:
            matching_results = st.session_state.get("matching_results_step5")
            if not matching_results:
                st.error("❌ Run Step 5 first to perform matching")
            else:
                try:
                    with st.spinner("📊 Creating height distribution analysis..."):
                        # Filter data based on checkbox
                        if show_only_matched:
                            # Only matched trees with valid heights
                            data = [r for r in matching_results if r["match"] == 1 and r["UAV_Tree_Height_segment"] is not None]
                            title_suffix = "Matched Trees"
                        else:
                            # All trees with valid heights
                            data = [r for r in matching_results if r["UAV_Tree_Height_segment"] is not None]
                            title_suffix = "All Trees with Heights"
                        
                        if not data:
                            st.warning("⚠️ No height data available for analysis")
                        else:
                            heights = [r["UAV_Tree_Height_segment"] for r in data]
                            
                            # Create height bins
                            max_height = max(heights)
                            bins = np.arange(0, max_height + bin_size, bin_size)
                            
                            # Create histogram
                            fig, ax = plt.subplots(figsize=(10, 6))
                            counts, edges, patches = ax.hist(heights, bins=bins, edgecolor='black', color=COLORS['primary'], alpha=0.7)
                            
                            # Customize plot
                            ax.set_xlabel('Tree Height (m)', fontsize=12, fontweight='bold')
                            ax.set_ylabel('Count (Number of Trees)', fontsize=12, fontweight='bold')
                            ax.set_title(f'Tree Height Distribution - {title_suffix}', fontsize=14, fontweight='bold')
                            ax.grid(axis='y', alpha=0.3, linestyle='--')
                            
                            # Add count labels on top of bars
                            for count, edge, patch in zip(counts, edges, patches):
                                if count > 0:
                                    height = patch.get_height()
                                    ax.text(patch.get_x() + patch.get_width()/2., height,
                                           f'{int(count)}',
                                           ha='center', va='bottom', fontsize=9, fontweight='bold')
                            
                            # Format x-axis to show bin ranges
                            bin_labels = [f'{int(edges[i])}-{int(edges[i+1])}' for i in range(len(edges)-1)]
                            ax.set_xticks(edges[:-1] + bin_size/2)
                            ax.set_xticklabels(bin_labels, rotation=45, ha='right')
                            
                            plt.tight_layout()
                            st.session_state["analysis_fig"] = fig
                            st.session_state["analysis_heights"] = heights
                            st.session_state["analysis_data"] = data
                            
                            st.success(f"✅ Analysis complete: {len(data)} trees analyzed")
                            
                except Exception as e:
                    st.error(f"❌ Analysis error: {str(e)[:150]}")
        
        # Display figure if available
        if st.session_state.get("analysis_fig") is not None:
            st.pyplot(st.session_state["analysis_fig"], use_container_width=True)
            plt.close(st.session_state["analysis_fig"])
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Display statistics
    if st.session_state.get("analysis_heights") is not None and show_stats_table:
        st.divider()
        heights = st.session_state["analysis_heights"]
        
        # Calculate statistics
        stats = {
            "Metric": ["Count", "Mean Height (m)", "Median Height (m)", "Min Height (m)", "Max Height (m)", "Std. Deviation (m)"],
            "Value": [
                len(heights),
                f"{np.mean(heights):.2f}",
                f"{np.median(heights):.2f}",
                f"{np.min(heights):.2f}",
                f"{np.max(heights):.2f}",
                f"{np.std(heights):.2f}"
            ]
        }
        
        col_stats1, col_stats2 = st.columns([1, 2])
        with col_stats1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 📊 Height Statistics")
            df_stats = pd.DataFrame(stats)
            st.dataframe(df_stats, hide_index=True, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_stats2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            # Create additional visualizations - Box plot
            fig_box, ax_box = plt.subplots(figsize=(8, 4))
            bp = ax_box.boxplot([heights], vert=False, patch_artist=True, widths=0.5)
            bp['boxes'][0].set_facecolor(COLORS['info'])
            bp['boxes'][0].set_alpha(0.7)
            bp['whiskers'][0].set_color(COLORS['primary'])
            bp['whiskers'][1].set_color(COLORS['primary'])
            bp['caps'][0].set_color(COLORS['primary'])
            bp['caps'][1].set_color(COLORS['primary'])
            bp['medians'][0].set_color(COLORS['danger'])
            bp['medians'][0].set_linewidth(2.5)
            ax_box.set_xlabel('Tree Height (m)', fontsize=11, fontweight='bold')
            ax_box.set_title('📦 Height Distribution Box Plot', fontsize=12, fontweight='bold')
            ax_box.set_yticks([])
            ax_box.grid(axis='x', alpha=0.3, linestyle='--')
            plt.tight_layout()
            st.pyplot(fig_box, use_container_width=True)
            plt.close(fig_box)
            st.markdown('</div>', unsafe_allow_html=True)


