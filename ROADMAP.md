# Implementation Roadmap

## ✅ Completed: GUI Modernization

The main task is done! Your app now has:
- Professional color scheme (Fluent Design)
- Better visual hierarchy and card-based layout
- Emoji icons for quick scanning
- Improved error messages and status feedback
- Better organized workflow steps
- Enhanced data visualization
- Responsive design

**File:** `app.py` (completely redesigned)

---

## 📋 Recommended Improvements (In Priority Order)

### Phase 1: Critical (Do First)
These improve stability and maintainability:

#### 1. Error Handling & Logging [1-2 hours]
**Why:** Currently errors are hidden; makes debugging hard
```python
# Add to app.py:
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('peakfinder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('peakfinder')

# Then wrap all try/except blocks:
try:
    result = compute_ndsm_only(cfg)
except Exception as e:
    logger.exception(f"nDSM computation failed")
    st.error(f"❌ Error: {str(e)[:100]}")
```

**Files to update:**
- `app.py` - All function calls
- `peakfinder/modules/*.py` - Add try/except logging

#### 2. Fix requirements.txt [30 minutes]
**Why:** `skimage==0.0` is invalid; could break installations
```bash
# Run this:
pip freeze > requirements_current.txt

# Then manually audit and create clean version:
matplotlib==3.9.4
numpy==1.23.5
pandas>=1.5.0
pyodbc==5.1.0
rasterio==1.3.10
scikit-image==0.23.2  # Not skimage==0.0!
scipy==1.10.1
streamlit>=1.28.0
```

#### 3. Add Type Hints [2-3 hours]
**Why:** Makes code self-documenting and enables IDE autocomplete
```python
# Before:
def _read_raster_preview(path, max_dim=1200):
    ...
    return arr_small, (h, w), step, profile

# After:
from typing import Tuple, Dict, Any
def _read_raster_preview(path: str, max_dim: int = 1200) -> Tuple[np.ndarray, Tuple[int, int], int, Dict[str, Any]]:
    ...
    return arr_small, (h, w), step, profile
```

**Files to update (in order):**
1. `app.py` - Helper functions
2. `peakfinder/modules/tree_tops.py`
3. `peakfinder/modules/segmentation.py`
4. `peakfinder/pipeline.py`

---

### Phase 2: Important (Do Next)
These improve code quality:

#### 4. Add Docstrings [2-3 hours]
**Why:** Code is self-explanatory; easier to maintain
```python
def detect_tree_tops(ndsm_file: str, neighborhood_size: int = 50, 
                     min_height_threshold: float = 10, 
                     sigma: float = 2) -> Tuple[List[Tuple], plt.Figure, Any]:
    """
    Detect tree tops from an nDSM raster and convert to UTM coordinates.
    
    Uses local maxima detection with optional Gaussian smoothing to identify
    tree top locations in the normalized Digital Surface Model.
    
    Parameters
    ----------
    ndsm_file : str
        Path to the nDSM raster file (GeoTIFF format)
    neighborhood_size : int, optional
        Size of neighborhood for local maxima detection in pixels (default: 50)
    min_height_threshold : float, optional
        Minimum height threshold in meters (default: 10)
    sigma : float, optional
        Gaussian smoothing standard deviation (default: 2)
    
    Returns
    -------
    tuple
        - List of (x_utm, y_utm, height) coordinates
        - matplotlib Figure with visualization
        - matplotlib Axes object
    
    Raises
    ------
    FileNotFoundError
        If ndsm_file does not exist
    rasterio.errors.RasterioIOError
        If file is not a valid raster
    
    Examples
    --------
    >>> coords, fig, ax = detect_tree_tops('dem.tif', neighborhood_size=100, min_height_threshold=5)
    >>> len(coords)
    42
    """
    ...
```

#### 5. Input Validation [1-2 hours]
**Why:** Prevents crashes from invalid input
```python
# Create peakfinder/utils/validation.py
def validate_raster_path(path: str) -> Tuple[bool, str]:
    """Validate that path points to a readable raster file."""
    if not path:
        return False, "Path is empty"
    if not os.path.exists(path):
        return False, f"File not found: {path}"
    
    try:
        with rasterio.open(path) as src:
            if src.count < 1:
                return False, "Raster has no bands"
    except Exception as e:
        return False, f"Invalid raster: {str(e)[:50]}"
    
    return True, "Valid"

# Use in app.py:
is_valid, msg = validate_raster_path(dsm_path)
if not is_valid:
    st.error(f"❌ {msg}")
    st.stop()
```

#### 6. Configuration Module [1 hour]
**Why:** Makes defaults easier to change
```python
# Create peakfinder/config.py
from dataclasses import dataclass

@dataclass
class Defaults:
    NEIGHBORHOOD_SIZE: int = 100
    MIN_HEIGHT_THRESHOLD: float = 10.0
    SIGMA: float = 2.0
    BUFFER_M: float = 2.0
    PIXEL_M: float = 1.0
    RASTER_PREVIEW_MAX_DIM: int = 1200
    
    # Segmentation defaults
    SEG_GROUND_THRESHOLD: float = 5.0
    SEG_MIN_AREA: int = 1500
    SEG_COMPACTNESS: float = 0.2

# Use in app.py:
from peakfinder.config import Defaults
neighborhood_size = st.slider(..., value=Defaults.NEIGHBORHOOD_SIZE)
```

---

### Phase 3: Nice-to-Have (Polish)
These improve robustness:

#### 7. Unit Tests [3-4 hours]
**Why:** Catch bugs early; safe refactoring
```python
# Create tests/test_tree_tops.py
import pytest
from peakfinder.modules.tree_tops import detect_tree_tops

def test_detect_tree_tops_returns_correct_format():
    """Test that detect_tree_tops returns expected format."""
    # Use a small test raster
    coords, fig, ax = detect_tree_tops("tests/data/test_ndsm.tif")
    
    assert isinstance(coords, list)
    assert len(coords) > 0
    assert len(coords[0]) == 3  # (x, y, z)
    assert fig is not None

def test_detect_tree_tops_respects_height_threshold():
    """Test that min_height_threshold filters results."""
    coords_low = detect_tree_tops("tests/data/test_ndsm.tif", min_height_threshold=1.0)
    coords_high = detect_tree_tops("tests/data/test_ndsm.tif", min_height_threshold=50.0)
    
    assert len(coords_high) <= len(coords_low)
```

#### 8. Progress Callbacks [1-2 hours]
**Why:** Users know long operations are working
```python
# Update pipeline.py functions to accept progress callback:
def compute_ndsm_only(cfg: RunConfig, progress=None, log=None):
    """
    progress: Optional[Callable[[int, str], None]]
        Callback for progress updates: progress(percent, message)
    """
    if progress:
        progress(10, "Loading DSM...")
    
    # ... processing ...
    
    if progress:
        progress(50, "Computing DTM...")
    
    # ... more processing ...
    
    if progress:
        progress(100, "Complete!")

# Use in app.py:
def on_progress(percent: int, message: str):
    st.progress(percent / 100)
    st.caption(message)

compute_ndsm_only(cfg, progress=on_progress)
```

#### 9. CLI Support [2 hours]
**Why:** Can run from command line (good for scripting)
```python
# Create peakfinder/cli.py
import click

@click.command()
@click.option('--dsm', required=True, help='Path to DSM file')
@click.option('--output-dir', required=True, help='Output directory')
@click.option('--neighborhood-size', default=100, type=int)
def process(dsm: str, output_dir: str, neighborhood_size: int):
    """Run peakfinder processing from command line."""
    cfg = RunConfig(
        dsm_path=dsm,
        ndsm_path=f"{output_dir}/nDSM.tif",
        dtm_path=f"{output_dir}/DTM.tif",
        neighborhood_size=neighborhood_size,
        # ... more config
    )
    
    result = run_everything(cfg)
    
    click.echo(f"✅ Complete! Results: {output_dir}")

if __name__ == '__main__':
    process()

# Then users can run:
# python -m peakfinder.cli --dsm input.tif --output-dir ./results
```

#### 10. Setup.py & Package Publishing [2 hours]
**Why:** Easy installation: `pip install peakfinder`
```python
# Create setup.py
from setuptools import setup, find_packages

setup(
    name="peakfinder",
    version="1.0.0",
    description="UAV-based tree height analysis",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.28.0",
        "matplotlib==3.9.4",
        "numpy==1.23.5",
        "rasterio==1.3.10",
    ],
    extras_require={
        "dev": ["pytest>=7.0", "black", "flake8"],
    },
    entry_points={
        "console_scripts": [
            "peakfinder=peakfinder.cli:process",
        ],
    },
)
```

---

## Time & Effort Summary

| Phase | Item | Time | Impact |
|-------|------|------|--------|
| 1️⃣ | Error Handling & Logging | 1-2h | 🔴 Critical |
| 1️⃣ | Fix requirements.txt | 30m | 🔴 Critical |
| 1️⃣ | Add Type Hints | 2-3h | 🔴 Critical |
| 2️⃣ | Add Docstrings | 2-3h | 🟡 Important |
| 2️⃣ | Input Validation | 1-2h | 🟡 Important |
| 2️⃣ | Configuration Module | 1h | 🟡 Important |
| 3️⃣ | Unit Tests | 3-4h | 🟢 Nice |
| 3️⃣ | Progress Callbacks | 1-2h | 🟢 Nice |
| 3️⃣ | CLI Support | 2h | 🟢 Nice |
| 3️⃣ | Setup.py | 2h | 🟢 Nice |
| **Total** | | **15-20h** | |

---

## Quick Start for Phase 1

If you want to do improvements immediately:

### Step 1: Fix requirements.txt (5 minutes)
```bash
cd c:\Users\lwfeckesim\04_peakfinder
pip freeze > requirements_new.txt
```
Then edit `requirements_new.txt` to fix `skimage==0.0` → `scikit-image==0.23.2`

### Step 2: Add basic logging (15 minutes)
Add this to top of `app.py`:
```python
import logging
logger = logging.getLogger('peakfinder')
```

And wrap risky operations:
```python
try:
    with st.spinner("..."):
        result = compute_ndsm_only(cfg)
    st.success("✅ Complete")
except Exception as e:
    logger.error(f"Operation failed: {e}")
    st.error(f"❌ Error: {str(e)[:100]}")
```

### Step 3: Add basic type hints (30 minutes)
Start with helper functions in `app.py`:
```python
def _read_raster_preview(path: str, max_dim: int = 1200) -> Tuple[np.ndarray, Tuple[int, int], int, Dict]:
    ...
```

---

## Files to Create

```
peakfinder/
├── config.py           # Configuration defaults (NEW)
└── utils/              # Utilities package (NEW)
    ├── __init__.py
    ├── validation.py   # Input validation
    └── path_utils.py   # Path utilities

tests/                  # Test suite (NEW)
├── __init__.py
├── test_tree_tops.py
└── data/
    └── test_ndsm.tif   # Small test raster

IMPROVEMENTS.md         # Detailed recommendations (NEW)
GUI_CHANGES.md         # GUI changes summary (NEW)
setup.py               # Package setup (OPTIONAL)
```

---

## Resources

- **Type hints:** https://docs.python.org/3/library/typing.html
- **NumPy docstring style:** https://numpydoc.readthedocs.io/
- **Pytest:** https://docs.pytest.org/
- **Click CLI:** https://click.palletsprojects.com/
- **Streamlit:** https://docs.streamlit.io/

---

## Summary

Your GUI is now **production-ready** visually! ✅

The recommendations above are for **code quality & maintainability** - they're not required for functionality, but highly recommended for a professional project.

Start with Phase 1 if you want to improve robustness. Everything else is polish.

