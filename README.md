# Photovoltaic Stability Analysis Tool

A comprehensive, interactive Streamlit application for analyzing photovoltaic device stability measurements. This tool processes raw measurement data from .txt files, applies intelligent filtering, performs statistical analysis, and generates publication-quality visualizations.

## 🎯 Features

### Core Functionality
- **Automatic Data Discovery**: Scans directories for stability measurement files
- **Multiple Data Input Methods**: 
  - Load from script folder
  - Custom folder path
  - Upload individual .txt files or .zip archives
- **Robust Data Parsing**: Extracts Jsc, Voc, FF, and PCE values from raw .txt files
- **Smart Filtering**: Apply range-based filters to remove abnormal values
- **Statistical Analysis**: Comprehensive statistics by device, day, and overall
- **Interactive Visualizations**: Multiple plot types with hover information

### Key Parameters Analyzed
- **Jsc** (Short-circuit current density) - mA/cm²
- **Voc** (Open-circuit voltage) - V
- **FF** (Fill Factor) - %
- **PCE** (Power Conversion Efficiency) - %

## 📊 Modular Architecture

The application is organized into three main modules:

### 1. `data_parser.py` - Data Parsing Module
Handles file discovery and raw data extraction:
- `discover_stability_files()`: Recursively find all stability measurement files
- `parse_stability_file()`: Extract measurement data from .txt files
- `build_raw_data_table()`: Compile all raw measurements into a unified DataFrame
- `group_by_device_day()`: Aggregate data by device and measurement day
- `process_uploaded_files()`: Handle .txt and .zip file uploads

**Supported File Format:**
```
<prefix>_Stability (JV)_Stability-D<day>-<device>-<pixel>.txt
Example: 0001_2026-03-28_13.59.47_Stability (JV)_Stability-D14-40-1A.txt
```

### 2. `database.py` - Database & Filtering Module
Manages data storage and filtering operations:
- `StabilityDatabase` class for in-memory data management
- Flexible filtering by parameter ranges
- Statistical calculations
- Data quality reporting
- Export capabilities

**Key Methods:**
- `set_filter()`: Apply range-based filters
- `apply_filters()`: Execute all active filters
- `get_statistics()`: Calculate comprehensive statistics
- `get_filter_recommendations()`: Suggest filter ranges based on data

### 3. `stability_feature_fixed.py` - Streamlit UI
Interactive web interface with five main tabs

## 🚀 Getting Started

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd stability
   ```

2. **Set up Python environment** (if not already done)
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install streamlit pandas plotly
   ```

### Running the Application

```bash
streamlit run stability_feature_fixed.py
```

The app will start on `http://localhost:8501`

## 📱 User Interface

### Tab 1: 📈 Analysis
Main visualization dashboard showing stability trends.
- **Device Selection**: Choose which devices to analyze
- **Display Modes**: 
  - "Show all measurement points" - Display every individual measurement
  - Default - Show maximum values per day
- **Plots**: 
  - PCE vs Day
  - Jsc vs Day
  - Voc vs Day
  - Fill Factor vs Day

### Tab 2: 📋 Raw Data
Browse complete raw measurement data with filtering.
- **Device Filter**: Select specific devices to view
- **Pagination**: Adjust rows per page (10, 25, 50, 100)
- **Quick Stats**: View mean and std dev for each parameter

### Tab 3: 🔍 Filtering
Define acceptable value ranges for each parameter.

**Filter Controls:**
```
Jsc:  Min _____ Max _____ (Recommended range shown)
Voc:  Min _____ Max _____ 
FF:   Min _____ Max _____ 
PCE:  Min _____ Max _____
```

**Features:**
- Auto-calculated recommended ranges (mean ± 2σ)
- Real-time filtering statistics
- Records removed / removal percentage tracking
- Device and day distribution metrics

### Tab 4: 📊 Statistics
Comprehensive statistical summary:
- **Overall Statistics**: Mean, median, std dev, min, max for each parameter
- **By Device**: Aggregated statistics for each device
- **By Day**: Statistics grouped by measurement day

### Tab 5: 💾 Export
Download processed data in multiple formats:
- Raw data (CSV)
- Filtered data (CSV)
- By Device aggregation (CSV)
- By Day aggregation (CSV)
- Data quality report

## 🔧 Usage Examples

### Example 1: Load Data from Custom Folder
1. Start the app
2. In sidebar, select "Custom Folder"
3. Enter path: `/home/user/pv_measurements/`
4. App automatically discovers all .txt files
5. Navigate to "Analysis" tab to view trends

### Example 2: Filter Abnormal Values
1. Go to "Filtering" tab
2. Set PCE range: 5-30%
3. Set Jsc range: 20-50 mA/cm²
4. Click "Apply Filters"
5. View quality report showing removed records
6. Navigate to other tabs to see filtered results

### Example 3: Export Analysis Results
1. Apply desired filters
2. Go to "Export" tab
3. Download "Filtered Data (CSV)" for raw measurements
4. Download "By Day (CSV)" for aggregated trends
5. Use in Excel/Python for further analysis

## 📊 Data Quality & Filtering

The tool includes intelligent filtering to remove measurement outliers:

**Recommended Filter Ranges:**
```
PCE:  5-30%     (Power Conversion Efficiency)
Jsc:  5-50 mA/cm²  (Current Density)
Voc:  0.5-1.5 V    (Voltage)
FF:   50-85%    (Fill Factor)
```

**Adjust these based on your specific devices and measurement conditions**

## 🎨 UI Enhancements

- **Color-coded tabs** with emoji indicators
- **Interactive plots** with hover tooltips
- **Responsive layout** that adapts to screen size
- **Real-time metrics** showing data quality
- **Professional styling** with colored sections

## 📈 Data Pipeline

```
Raw .txt Files
     ↓
   Data Parser (data_parser.py)
     ↓
Raw Data Table (device, pixel, day, scan, jsc, voc, ff, pce)
     ↓
Database Layer (database.py)
     ↓
Filtering & Aggregation
     ↓
Streamlit UI (stability_feature_fixed.py)
     ↓
Interactive Visualizations & Reports
```

## 🔍 File Parsing Details

The data parser looks for measurements in two formats:

1. **Tabular Format**: Expects header row with "Scan", "Jsc", "Voc", "FF", "PCE/Efficiency"
2. **Fallback Format**: Uses regex to extract PCE values if tabular format not found

**Supported Column Names:**
- Jsc, JSC, jsc, Jsc (mA/cm²)
- Voc, VOC, voc, Voc (V)
- FF, ff, FillFactor
- PCE, pce, Efficiency, efficiency

## ⚙️ Configuration

### Environment Variables
```bash
STREAMLIT_AUTORUN=1  # Auto-run mode for headless execution
```

### Streamlit Config
Edit `.streamlit/config.toml` for customization:
```toml
[theme]
primaryColor = "#0084d6"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
```

## 🐛 Troubleshooting

### Issue: Files not detected
- **Solution**: Ensure files match pattern `*_Stability (JV)_Stability-D<day>-<device>-<pixel>.txt`
- Check file permissions
- Try uploading files directly

### Issue: No data extracted
- **Solution**: Check file format contains tabular data with headers
- Verify Jsc, Voc, FF, PCE columns exist
- Try uploading a single file to debug

### Issue: Filters not working
- **Solution**: Ensure min_value < max_value
- Check that values are within actual data range
- Click "Apply Filters" button (not just Enter)

### Issue: Slow performance with large files
- **Solution**: Use filtering to reduce data size
- Export and re-import aggregated data
- Consider splitting data by device

## 📝 Example Data Format

Expected .txt file structure:
```
Scan  Jsc(mA/cm²)  Voc(V)  FF(%)  PCE(%)
1     42.3         0.92    78.5   30.5
2     41.8         0.91    79.2   30.1
3     43.1         0.93    77.8   31.2
...
```

## 🚀 Performance Tips

- **Large Datasets**: Use filtering early to reduce memory usage
- **Multiple Devices**: Consider analyzing one at a time
- **Export Format**: CSV exports are lightweight for further analysis
- **Plot Rendering**: Fewer devices = faster rendering

## 🔐 Data Privacy

- All data processing happens locally
- No data is sent to external servers
- Use folder-based uploads for sensitive data
- Export results are stored locally

## 📚 Technical Stack

- **Streamlit**: Web application framework
- **Pandas**: Data manipulation and analysis
- **Plotly**: Interactive visualizations
- **Python 3.12+**: Core language

## 🤝 Contributing

Improvements welcome! Areas for enhancement:
- Additional statistical methods
- Advanced filtering (moving average, outlier detection)
- Batch processing capabilities
- Database backend integration
- Real-time data streaming

## 📄 License

This project is licensed under MIT License

## 🙋 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the example data format
3. Enable debug mode for more details

## 🎓 Learning Resources

- [Streamlit Documentation](https://docs.streamlit.io)
- [Pandas Data Analysis](https://pandas.pydata.org)
- [Plotly Visualization](https://plotly.com/python/)

---

**Version:** 2.0 (Modular Architecture)  
**Last Updated:** 2026-04-15  
**Status:** Production Ready ✅
