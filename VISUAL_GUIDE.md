# Peakfinder GUI Visual Guide

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  🌲 PEAKFINDER                              │
│        UAV-Based Tree Height Analysis                       │
└─────────────────────────────────────────────────────────────┘

┌─ STEP 1️⃣  FILE PATHS ─────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📥 INPUT                                            │   │
│  │  DSM (Digital Surface Model)  [Browse] [Folder]    │   │
│  │                               [Open]   [✓ Exists]  │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📤 OUTPUT                                           │   │
│  │  DTM (output)  [Save As] [Folder] [Open] [⚠ N/A]   │   │
│  │  nDSM (output) [Save As] [Folder] [Open] [✓ OK]    │   │
│  └─────────────────────────────────────────────────────┘   │
│  [🔄 Auto-fill from DSM]                                   │
└───────────────────────────────────────────────────────────┘

┌─ STEP 2️⃣  CREATE/LOAD nDSM ──────────────────────────────┐
│  ┌────────────────────┬─────────────────────────────┐     │
│  │ Configuration      │ Execute                     │     │
│  │ ☐ Compute nDSM     │ [▶ Run nDSM Step]           │     │
│  │ AOI buffer: [——●]  │ Status: ⏳ Processing...    │     │
│  │ DGM res: [——●]     │                             │     │
│  │ LDBV user: [•••]   │ Output:                     │     │
│  │ LDBV pass: [•••]   │ ✅ nDSM computed.           │     │
│  └────────────────────┴─────────────────────────────┘     │
│  ┌─────────────────────────────────────────────────┐       │
│  │  nDSM Preview                                   │       │
│  │  ┌─────────────────────────────────────────┐    │       │
│  │  │     [Raster Visualization Image]        │    │       │
│  │  │     📊 1024 × 1024 px                   │    │       │
│  │  └─────────────────────────────────────────┘    │       │
│  │  Contrast: [------●--------] P2.0 - P98.0       │       │
│  │  CRS: EPSG:32632 • Res: 1.0 m/px                │       │
│  └─────────────────────────────────────────────────┘       │
└───────────────────────────────────────────────────────────┘

┌─ STEP 3️⃣  DETECT TREE TOPS ──────────────────────────────┐
│  ┌────────────────────┬─────────────────────────────┐     │
│  │ Configuration      │ Results                     │     │
│  │ Neighborhood: [●]  │ [Visualization Figure]      │     │
│  │ Min Height: [●]    │ ✅ Detected 42 tree tops    │     │
│  │ Gaussian σ: [●]    │                             │     │
│  │ [▶ Detect]         │ Data Table:                 │     │
│  │                    │ UTM_X    UTM_Y   Height_m   │     │
│  │                    │ 456234.2 5236234.1  24.5    │     │
│  │                    │ 456245.1 5236245.2  23.8    │     │
│  │                    │ ...                         │     │
│  │                    │ [⬇️ CSV Download]           │     │
│  └────────────────────┴─────────────────────────────┘     │
└───────────────────────────────────────────────────────────┘

┌─ STEP 4️⃣  WATERSHED SEGMENTATION ─────────────────────┐
│  ┌────────────────────┬─────────────────────────────┐   │
│  │ ⚙️ Parameters      │ Status                      │   │
│  │ ☐ Use subset       │ [▶ Run Segmentation]       │   │
│  │ Subset size: [●]   │ 🔄 Running watershed...    │   │
│  │ [More Options...]  │ ✅ Segmentation complete   │   │
│  │                    │                             │   │
│  │                    │ [Segmentation Figure]      │   │
│  │                    │                             │   │
│  │                    │ 🌲 42 Segments   🎯 38 Tops│   │
│  └────────────────────┴─────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘

┌─ FULL PIPELINE TAB (DB MODE) ──────────────────────────────┐
│  ┌──────────────────┬─────────────────────────────────┐   │
│  │ Database Config  │ Execute                         │   │
│  │ DSN: [<your_dsn>    ▼] │ [▶ Run Full Pipeline]           │   │
│  │ Versuch ID: [<id>]│ ⏳ Processing...                │   │
│  │                  │ ✅ Complete                     │   │
│  └──────────────────┴─────────────────────────────────┘   │
│                                                             │
│  📊 Summary Stats:  🌲 42 | 🎯 38 | ✓ 35 Matched           │
│                                                             │
│  📋 Results Table: [Data displayed with pagination]        │
│  [⬇️ Download CSV]                                        │
│                                                             │
│  📈 Visualizations:                                        │
│  [🌲 Tops] [📐 Geometry] [🎯 Segmentation] [...]          │
│   ┌─────────────────────────────────────────┐             │
│  │     [Visualization Figure]                │             │
│  └─────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────────┘
```

---

## Color Scheme

```
PRIMARY BLUE (Actions)
████████████████████  #0078D4
Hover: ████████████████████  #006BA6

SUCCESS GREEN (Positive)
████████████████████  #107C10
Background: ████████████████████  #D1E7DD

WARNING YELLOW (Caution)
████████████████████  #FFB900
Background: ████████████████████  #FFF3CD

DANGER RED (Errors)
████████████████████  #D83B01
Background: ████████████████████  #F8D7DA

LIGHT GRAY (Background)
████████████████████  #FAFAF9

DARK TEXT
████████████████████  #323130
```

---

## Interactive Elements

### Buttons
```
[📂 Browse]  ← File dialog
[💾 Save As] ← File save dialog
[📁 Folder]  ← Open in Explorer
[📄 Open]    ← Open file
[▶ Run nDSM Step]  ← Primary action (blue)
[🔄 Auto-fill]     ← Secondary action
```

### Status Indicators
```
✓ Exists   (Green badge)
⚠ Not found (Yellow badge)
⏳ Processing... (Spinner)
✅ Success! (Green checkmark)
❌ Error: ... (Red X)
```

### Sliders
```
Neighborhood size (pixels)
5          100         300
└──────●──────────────┘  ← Selected: 100
```

### Data Tables
```
UTM_X        UTM_Y        Height_m
─────────────────────────────────
456234.20    5236234.10   24.53
456245.10    5236245.20   23.82
456256.05    5236256.35   25.14
...
```

### Cards/Sections
```
╔══════════════════════════════════╗
║ 📥 INPUT                          ║
║ DSM (Digital Surface Model)       ║
║ [Browse] [Folder] [Open] [Exists] ║
╚══════════════════════════════════╝
```

---

## User Journey

### Path Selection Flow
```
┌─ Manual Entry ────────────────────┐
│ Paste path in text input field     │
└───────────────────────────────────┘
        ↓
    [Browse] Button
        ↓
┌─ File Dialog ─────────────────────┐
│ Windows native file picker        │
│ Select GeoTIFF files              │
│ Path auto-fills in text field     │
└───────────────────────────────────┘
        ↓
┌─ Status Display ──────────────────┐
│ ✓ Exists (green badge)            │
│ Ready to use                      │
└───────────────────────────────────┘
```

### Processing Flow
```
User clicks [▶ Run nDSM Step]
    ↓
Input Validation
    ↓ (if error)
❌ Error message → User fixes → Retry
    ↓ (if ok)
⏳ Processing spinner...
    ↓
✅ Success message & Results Display
    ↓
Data ready for next step
```

### Results Display Flow
```
Execution Complete
    ↓
Success Notification: ✅ Computed 42 items
    ↓
Metrics Cards: 🌲 42 | 🎯 38 | ✓ 35
    ↓
Visualization: [Figure display]
    ↓
Data Table: [Results table with pagination]
    ↓
Download: [⬇️ CSV]
```

---

## Typography & Spacing

### Headers
```
🌲 Peakfinder                    (H1 - 2.5rem, bold)
UAV-Based Tree Height Analysis   (Caption - 0.9rem, muted)

## Step 1️⃣ – File Paths          (H2 - 1.8rem, with bottom border)

**Configuration**                 (Bold text for sections)

Helper text                       (0.85rem, muted)
```

### Line Heights
```
Tight:   1rem - For dense tables/lists
Normal:  1.5rem - For most content  
Loose:   2rem - Between major sections
```

### Padding
```
Cards:      1.2rem
Sections:   1.5rem top/bottom
Dividers:   2rem spacing
Buttons:    0.6rem 1.2rem (height × width)
```

---

## Responsive Design

### Desktop (1200px+)
```
✅ Full width content
✅ 2-3 column layouts
✅ All buttons visible
✅ Optimal experience
```

### Tablet (768px - 1200px)
```
⚠️ Slightly condensed
⚠️ 1-2 column layouts
✅ Buttons still accessible
```

### Mobile (< 768px)
```
⚠️ Single column
⚠️ Collapsed sections
⚠️ Stacked buttons
(Not optimized - desktop recommended)
```

---

## Accessibility Features

### Icons
- 📥📤 Input/Output files
- 🌲 Trees
- 🎯 Detection targets
- ⏳ Processing
- ✅❌ Status

### Color Usage
- ✓ Text labels on badges
- ✓ Icons with text labels
- ⚠️ Not color-only indication

### Size & Contrast
- Primary text: 16px on light background
- Secondary text: 14px, slightly muted
- High contrast ratios (WCAG AA)

---

## Dark Mode Support

The CSS is designed to work with Streamlit's dark theme:
- ✅ Light backgrounds become dark
- ✅ Text colors invert
- ✅ All colors remain readable
- ✅ Badges still visible

---

## Performance Optimizations

```
┌─ Raster Loading ────┐
│ Large file (1000MB) │
│ ↓ Downsampling      │
│ ↓ Preview display   │
│ (1200px max dim)    │
│ = Fast (~1s)        │
└─────────────────────┘

┌─ Caching ──────────┐
│ @st.cache_data     │
│ Raster previews    │
│ (3600s TTL)        │
│ = Fast on reload   │
└─────────────────────┘

┌─ Subset Processing ┐
│ Full raster: slow  │
│ Center subset: fast│
│ 200m × 200m area   │
│ = 10-100x speedup  │
└─────────────────────┘
```

---

## Error Message Examples

```
❌ LDBV credentials required
   → User sees: Clear what's needed

❌ File not found: C:\data\DSM.tif
   → User sees: Exact path that failed

❌ Error: Invalid raster
   → User sees: What went wrong

⚠️ File does not exist (yet)
   → User sees: Path will be created
```

---

## Tips & Tricks for Users

1. **Quick Setup:** Click "Auto-fill from DSM" button
2. **Browse Files:** Use Browse button instead of typing paths
3. **Monitor Progress:** Watch spinner for operation status
4. **View Results:** Click tabs to see different visualizations
5. **Download Data:** CSV button for offline analysis
6. **Adjust Display:** Use contrast slider for better raster viewing
7. **Expand Parameters:** Click section header to reveal options

---

## Customization Points

Users can modify in `app.py`:

```python
# Colors (line ~45)
COLORS = {
    "primary": "#0078D4",      # Change blue
    "success": "#107C10",      # Change green
    # ...
}

# Default paths (line ~400+)
default=r"D:\your\path\DSM.tif"

# Slider defaults (line ~450+)
st.slider(..., value=DefaultValue)

# Card styling (CSS section)
.card { ... }
```

---

**This guide provides a complete visual reference for the modernized Peakfinder GUI.**

