# Peakfinder - Quick Start Guide

## 🚀 Get Started in 2 Minutes

### 1. Run the App
```bash
cd <path_to_peakfinder>
streamlit run app.py
```

The app opens in your browser automatically!

### 2. Upload a File
Click **📂 Browse** next to "DSM (input)" and select your GeoTIFF file.

The status badge will show **✓ Exists** when valid.

### 3. Auto-Fill Outputs
Click **🔄 Auto-fill from DSM** to create output paths automatically.

### 4. Create nDSM or Load Existing
- **Check the box** if you want to compute a new nDSM (requires LDBV credentials)
- **Uncheck** if you already have one and just want to load it
- Click **▶ Run nDSM Step**

### 5. Detect Tree Tops
Adjust the sliders if needed, then click **▶ Detect Tree Tops**

Results show as a map + data table below.

### 6. Run Segmentation
Click **▶ Run Segmentation** to delineate individual tree crowns.

The results show segment count and visualization.

### 7. Download Results
Click **⬇️ CSV** to export your tree data for analysis in Excel/GIS.

---

## 📋 What's New (Compared to Before)

| Feature | Before | Now |
|---------|--------|-----|
| **Colors** | Basic blue | Professional Fluent Design |
| **Layout** | Plain linear | Card-based, organized |
| **Icons** | None | Emoji icons everywhere |
| **Status** | Plain text | Colored badges |
| **Errors** | Generic | Helpful with context |
| **Guidance** | Minimal | Step-by-step with help |
| **Results** | Tables only | Metrics + tables + tabs |

---

## 🎨 Visual Walkthrough

```
┌──────────────────────────────────────────┐
│     🌲 PEAKFINDER - UAV Tree Analysis    │
└──────────────────────────────────────────┘

STEP 1️⃣ - FILE PATHS
  📥 Select input DSM file
  📤 Choose where to save outputs
  [🔄 Auto-fill]

STEP 2️⃣ - CREATE nDSM
  Configure download options
  [▶ Run nDSM Step]
  Shows preview when done ✅

STEP 3️⃣ - DETECT TREE TOPS
  Adjust detection parameters
  [▶ Detect Tree Tops]
  View results on map
  Download as CSV

STEP 4️⃣ - SEGMENTATION
  Configure segmentation
  [▶ Run Segmentation]
  View individual tree crowns
  Summary statistics 📊
```

---

## ⚙️ Key Parameters Explained

### Step 2 - nDSM Creation
- **Compute nDSM:** Check if starting from scratch
- **AOI buffer:** Expand search area (meters)
- **DGM resolution:** Target pixel size (coarser = faster)

### Step 3 - Tree Top Detection
- **Neighborhood:** Search area size (larger = fewer, bigger trees)
- **Min height:** Ignore small features (meters)
- **Gaussian smoothing:** Reduce noise (higher = smoother)

### Step 4 - Segmentation
- **Use subset:** Process only center area (much faster)
- **Subset size:** Area to process (meters)
- **Min segment area:** Ignore tiny segments (pixels²)

---

## 🆘 Troubleshooting

### "File not found" Error
- Check the path is correct
- Use **📂 Browse** instead of typing
- File must be a GeoTIFF (.tif or .tiff)

### "LDBV credentials required"
- You need to login to German LDBV service
- Get credentials from: https://sgx.geodatenzentrum.de/
- Enter username + password when prompted
- Or uncheck "Compute nDSM" to use existing file

### App looks plain (no colors)
- Clear browser cache (Ctrl+Shift+Delete)
- Close app and restart: `streamlit run app.py`
- Try a different browser

### Operations take too long
- Large rasters are slow - it's normal
- Enable "Use center subset" for faster processing
- Reduce "DGM resolution" (coarser pixels)

---

## 💡 Pro Tips

1. **Browse instead of typing** - Click 📂 button to select files easily

2. **Use Auto-fill** - Click 🔄 to automatically name output files

3. **Watch for status badges** - Green ✓ = ready, Yellow ⚠ = missing

4. **Read help text** - Hover over parameter labels for tips

5. **Check spinners** - Wait for ⏳ to finish before closing

6. **Download early** - Save results as CSV after each step

7. **Expand sections** - Click parameter headers to show/hide options

8. **Adjust contrast** - Use slider below raster preview for better viewing

---

## 📚 Learn More

- **[SUMMARY.md](SUMMARY.md)** - Complete overview
- **[VISUAL_GUIDE.md](VISUAL_GUIDE.md)** - Design reference
- **[GUI_CHANGES.md](GUI_CHANGES.md)** - Feature details
- **[INDEX.md](INDEX.md)** - All documentation

---

## ✨ Features at a Glance

✅ **Path Management**
- Browse files with native Windows dialogs
- Auto-detect file existence
- Quick folder/file opening

✅ **Raster Preview**
- Interactive contrast adjustment
- CRS and resolution display
- Fast downsampling for large files

✅ **Tree Top Detection**
- Visualize detected points
- Download as CSV
- Adjustable parameters

✅ **Watershed Segmentation**
- Delineate individual crowns
- Fast subset processing
- Summary statistics

✅ **Full Pipeline** (Optional)
- Database integration
- Automatic result export
- Multi-page visualization

✅ **Data Export**
- CSV download for all results
- Multiple visualization formats
- Easy sharing with colleagues

---

## 🎯 Quick Workflow

```
1. Load DSM file
   ↓
2. Create nDSM (or load existing)
   ↓
3. View nDSM preview
   ↓
4. Detect tree tops
   ↓
5. Download tree top CSV
   ↓
6. Run segmentation
   ↓
7. Download segment CSV
   ↓
Done! 🎉
```

---

## 🔧 Configuration

### Change Default Paths
Edit `app.py` around line 400:
```python
default=r"D:\your\typical\path\DSM.tif"
```

### Change Colors
Edit `app.py` around line 45:
```python
COLORS = {
    "primary": "#0078D4",  # Change blue
    ...
}
```

### Adjust Slider Ranges
Edit `app.py` in step sections:
```python
st.slider("Label", min, max, default, step)
```

---

## 📞 Support

**Having issues?** Check:
1. This guide (quick fixes at top)
2. [GUI_CHANGES.md](GUI_CHANGES.md#troubleshooting)
3. [IMPROVEMENTS.md](IMPROVEMENTS.md) (code quality)

---

## 🎉 You're All Set!

Your modernized Peakfinder app is ready to use.

Run: `streamlit run app.py`

Enjoy! 🌲

