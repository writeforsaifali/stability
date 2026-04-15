"""
PV Stability Analysis Tool - Restructured Main App
====================================================

New workflow:
1. Parse Data - View data grouped by device (collapsible)
2. Filter Raw Data - Apply filters to remove abnormalities
3. View Statistics - Auto-calculated after filtering
4. Analysis - Interactive time-series plots (PCE, Jsc, Voc, FF)
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_parser import (
    discover_stability_files,
    build_device_data_map,
    build_raw_data_table,
    process_uploaded_files,
)
from database import StabilityDatabase


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="PV Stability Analysis",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <style>
    .device-header {
        background-color: #e8f4f8;
        padding: 12px;
        border-radius: 6px;
        border-left: 4px solid #0084d6;
        margin: 8px 0;
    }
    .stats-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .filter-box {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "db" not in st.session_state:
    st.session_state.db = None

if "raw_data" not in st.session_state:
    st.session_state.raw_data = pd.DataFrame()

if "filtered_data" not in st.session_state:
    st.session_state.filtered_data = pd.DataFrame()

if "device_map" not in st.session_state:
    st.session_state.device_map = {}

if "file_paths" not in st.session_state:
    st.session_state.file_paths = []

if "loaded_files_hash" not in st.session_state:
    st.session_state.loaded_files_hash = None

if "last_data_source" not in st.session_state:
    st.session_state.last_data_source = None


# ============================================================================
# SIDEBAR - DATA LOADING
# ============================================================================

st.sidebar.markdown("# 📂 Load Data")
st.sidebar.markdown("---")

data_source = st.sidebar.radio(
    "Data source:",
    options=["Script Folder", "Custom Folder", "Upload Files"],
    index=0
)

# IMPORTANT: Only rebuild file_paths if data_source changed
data_source_changed = (st.session_state.last_data_source != data_source)
file_paths = []

if data_source_changed or not st.session_state.file_paths:
    # Data source changed or no files loaded yet - rebuild file list
    if data_source == "Script Folder":
        try:
            base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            file_paths = sorted(discover_stability_files(base_dir))
            if file_paths:
                st.sidebar.success(f"✓ Found {len(file_paths)} files")
            else:
                st.sidebar.info("No files found in script folder")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")
    
    elif data_source == "Custom Folder":
        data_dir = st.sidebar.text_input("Enter folder path:", placeholder="/path/to/data")
        if data_dir:
            base = Path(data_dir).expanduser()
            if base.exists() and base.is_dir():
                file_paths = sorted(discover_stability_files(base))
                if file_paths:
                    st.sidebar.success(f"✓ Found {len(file_paths)} files")
                else:
                    st.sidebar.warning("No matching files found")
            else:
                st.sidebar.error(f"Directory not found")
    
    elif data_source == "Upload Files":
        uploaded_files = st.sidebar.file_uploader(
            "Upload files:",
            type=["txt", "zip"],
            accept_multiple_files=True,
        )
        if uploaded_files:
            try:
                file_paths = sorted(process_uploaded_files(uploaded_files))
                st.sidebar.success(f"✓ Processed {len(file_paths)} files")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
    
    # Update session state with new file paths
    st.session_state.file_paths = file_paths
    st.session_state.last_data_source = data_source
else:
    # Data source unchanged - use previously loaded files from session state
    file_paths = st.session_state.file_paths

# ============================================================================
# MAIN APP TITLE
# ============================================================================

st.markdown("# 🔬 Photovoltaic Stability Analysis Tool")
st.markdown("**Restructured workflow:** Parse → Filter → Statistics → Analyze")

if not file_paths:
    st.warning("⚠️ No data files found. Please configure a data source in the sidebar.")
    st.stop()

# ============================================================================
# DATA PROCESSING
# ============================================================================

device_map = build_device_data_map(file_paths)
raw_data = build_raw_data_table(device_map)

st.session_state.device_map = device_map
st.session_state.raw_data = raw_data

# IMPORTANT: Preserve filtered_data across reruns
# Use a more robust approach: only reset on data source change, not on widget changes
if st.session_state.filtered_data.empty:
    # First time: initialize filtered_data
    st.session_state.filtered_data = raw_data.copy()
    st.session_state.loaded_files_hash = hash(tuple(file_paths))
elif data_source_changed:
    # Data source actually changed - reset filtered_data
    st.session_state.filtered_data = raw_data.copy()
    st.session_state.loaded_files_hash = hash(tuple(file_paths))
# else: Widget changed (parameter toggle, device selection, etc.) - DON'T RESET!

if raw_data.empty:
    st.error("❌ No valid data could be extracted.")
    st.stop()

# Initialize database with raw data (will be updated when filters are applied)
db = StabilityDatabase(raw_data)
st.session_state.db = db

# ============================================================================
# MAIN TABS
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "1️⃣ Parse Data",
    "2️⃣ Filter Raw Data",
    "3️⃣ Statistics",
    "4️⃣ Analysis",
])

# ============================================================================
# TAB 1: PARSE DATA - GROUPED BY DEVICE
# ============================================================================

with tab1:
    st.subheader("📊 Parsed Data - Grouped by Device & Day")
    st.markdown("""
    All measurements are organized by device and day. 
    Click to expand each device and then each day to view measurements with timestamps.
    """)
    
    devices = sorted(device_map.keys())
    
    if not devices:
        st.info("No devices found in data.")
    else:
        st.markdown(f"**Total Devices:** {len(devices)}")
        st.markdown(f"**Total Measurements:** {len(raw_data)}")
        
        st.markdown("---")
        
        # Display each device in a collapsible expander
        for device_num in devices:
            device = device_map[device_num]
            num_measurements = len(raw_data[raw_data['device_number'] == device_num])
            
            # Device-level expander
            with st.expander(
                f"📱 **Device {device_num}** ({num_measurements} measurements)",
                expanded=False
            ):
                # List all days in this device
                days = sorted(device.days.keys())
                
                for day_num in days:
                    day_data = device.days[day_num]
                    num_day_measurements = len(day_data.measurements)
                    
                    # Day-level expander (nested inside device)
                    with st.expander(
                        f"📅 **Day {day_num}** - {day_data.variation} ({num_day_measurements} measurements)",
                        expanded=False
                    ):
                        # Day data table
                        day_df = day_data.to_dataframe()
                        if not day_df.empty:
                            day_df['device_number'] = device_num
                            
                            # Display measurements with direction
                            display_cols = ['datetime', 'direction', 'pixel', 'scan', 'jsc', 'voc', 'ff', 'pce']
                            display_df = day_df[display_cols].copy()
                            display_df['datetime'] = display_df['datetime'].astype(str)
                            display_df = display_df.rename(columns={
                                'datetime': 'DateTime',
                                'direction': 'Direction',
                                'pixel': 'Pixel',
                                'scan': 'Scan',
                                'jsc': 'Jsc',
                                'voc': 'Voc',
                                'ff': 'FF',
                                'pce': 'PCE'
                            })
                            
                            st.dataframe(
                                display_df,
                                use_container_width=True,
                                height=300,
                            )
                            
                            # Quick statistics for this day
                            st.markdown("##### Day Statistics (Raw Data):")
                            stat_cols = st.columns(4)
                            
                            for idx, param in enumerate(['jsc', 'voc', 'ff', 'pce']):
                                param_data = day_df[param].dropna()
                                if len(param_data) > 0:
                                    with stat_cols[idx]:
                                        st.metric(
                                            param.upper(),
                                            f"{param_data.mean():.2f}",
                                            f"σ={param_data.std():.2f}"
                                        )

# ============================================================================
# TAB 2: FILTER RAW DATA
# ============================================================================

with tab2:
    st.subheader("🔍 Filter Raw Data")
    st.markdown("Define acceptable ranges for each parameter. Filtered data will be shown below for verification.")
    
    # Get recommendations from raw data
    recommendations = db.get_filter_recommendations()
    
    st.markdown("### Step 1: Set Filter Ranges")
    
    filter_cols = st.columns(4)
    filters_to_apply = {}
    
    params = [
        ("jsc", "Jsc (mA/cm²)", 40),
        ("voc", "Voc (V)", 1),
        ("ff", "FF (%)", 85),
        ("pce", "PCE (%)", 30),
    ]
    
    for idx, (param, label, default_max) in enumerate(params):
        with filter_cols[idx]:
            st.markdown(f"#### {label}")
            
            if param in recommendations:
                rec_min, rec_max = recommendations[param]
                st.caption(f"Recommended: {rec_min:.2f}-{rec_max:.2f}")
                default_min = rec_min
                default_max = rec_max
            else:
                default_min = 0
                default_max = default_max
            
            col_min, col_max = st.columns(2)
            
            with col_min:
                min_val = st.number_input(
                    f"Min",
                    value=default_min,
                    key=f"filter_min_{param}",
                    label_visibility="collapsed"
                )
            
            with col_max:
                max_val = st.number_input(
                    f"Max",
                    value=default_max,
                    key=f"filter_max_{param}",
                    label_visibility="collapsed"
                )
            
            if min_val < max_val and param in raw_data.columns:
                filters_to_apply[param] = (min_val, max_val)
    
    # Apply filters
    st.markdown("---")
    st.markdown("### Step 2: Apply & Verify Filters")
    
    col_apply, col_clear = st.columns(2)
    
    with col_apply:
        if st.button("✅ Apply Filters", use_container_width=True, key="apply_btn"):
            # Apply filters to raw_data
            filtered_raw_data = raw_data.copy()
            
            for param, (min_v, max_v) in filters_to_apply.items():
                filtered_raw_data = filtered_raw_data[
                    (filtered_raw_data[param] >= min_v) & 
                    (filtered_raw_data[param] <= max_v)
                ]
            
            # Store in session state
            st.session_state.filtered_data = filtered_raw_data
            
            # Rebuild database with filtered data
            db_filtered = StabilityDatabase(filtered_raw_data)
            st.session_state.db = db_filtered
            
            st.success(f"✓ Filters applied! {len(filtered_raw_data)} / {len(raw_data)} records kept")
    
    with col_clear:
        if st.button("❌ Clear Filters", use_container_width=True, key="clear_btn"):
            st.session_state.filtered_data = raw_data.copy()
            db_new = StabilityDatabase(raw_data)
            st.session_state.db = db_new
            st.info("Filters cleared.")
            st.rerun()
    
    # Show filtered data by device and day
    st.markdown("---")
    st.markdown("### Step 3: Verify Filtered Data by Device & Day")
    
    # Use filtered data from session state
    filtered_data_current = st.session_state.get('filtered_data', raw_data).copy()
    
    if filtered_data_current.empty:
        st.warning("No data matches the current filters.")
    else:
        devices_with_data = sorted(filtered_data_current['device_number'].unique())
        
        for device_num in devices_with_data:
            device_data_filtered = filtered_data_current[filtered_data_current['device_number'] == device_num]
            days_in_device = sorted(device_data_filtered['day'].unique())
            
            with st.expander(f"📱 Device {device_num} ({len(device_data_filtered)} records)", expanded=False):
                for day_num in days_in_device:
                    day_filtered = device_data_filtered[device_data_filtered['day'] == day_num]
                    variation = day_filtered['variation'].iloc[0] if not day_filtered.empty else "Unknown"
                    
                    with st.expander(f"📅 Day {day_num} - {variation} ({len(day_filtered)} records)"):
                        # Display filtered data for this day
                        display_cols = ['datetime', 'direction', 'pixel', 'jsc', 'voc', 'ff', 'pce']
                        display_filtered = day_filtered[display_cols].copy()
                        display_filtered['datetime'] = display_filtered['datetime'].astype(str)
                        display_filtered = display_filtered.rename(columns={
                            'datetime': 'DateTime',
                            'direction': 'Direction',
                            'pixel': 'Pixel',
                            'jsc': 'Jsc',
                            'voc': 'Voc',
                            'ff': 'FF',
                            'pce': 'PCE'
                        })
                        
                        st.dataframe(
                            display_filtered,
                            use_container_width=True,
                            height=250,
                        )
    

# ============================================================================
# TAB 3: STATISTICS
# ============================================================================

with tab3:
    st.subheader("📈 Statistics (From Filtered Data)")
    
    # Use filtered data from session state
    filtered_data_for_stats = st.session_state.get('filtered_data', raw_data)
    
    if filtered_data_for_stats.empty:
        st.warning("No statistics available. Check your filters.")
    else:
        # Overall statistics
        st.markdown("### Overall Statistics")
        
        stat_cols = st.columns(4)
        param_list = ["jsc", "voc", "ff", "pce"]
        param_labels = ["Jsc (mA/cm²)", "Voc (V)", "FF (%)", "PCE (%)"]
        
        for idx, (param, label) in enumerate(zip(param_list, param_labels)):
            if param in filtered_data_for_stats.columns:
                param_data = filtered_data_for_stats[param].dropna()
                if len(param_data) > 0:
                    with stat_cols[idx]:
                        st.markdown(f"#### {label}")
                        st.text(f"Mean: {param_data.mean():.3f}")
                        st.text(f"Median: {param_data.median():.3f}")
                        st.text(f"Std: {param_data.std():.3f}")
                        st.text(f"Min: {param_data.min():.3f}")
                        st.text(f"Max: {param_data.max():.3f}")
                        st.text(f"Count: {len(param_data)}")
        
        # Device breakdown
        st.markdown("---")
        st.markdown("### Statistics by Device")
        
        if not filtered_data_for_stats.empty:
            devices_in_data = sorted(filtered_data_for_stats['device_number'].unique())
            
            device_tabs = st.tabs([f"Device {d}" for d in devices_in_data])
            
            for idx, device_num in enumerate(devices_in_data):
                with device_tabs[idx]:
                    device_data = filtered_data_for_stats[filtered_data_for_stats['device_number'] == device_num]
                    
                    device_stats = st.columns(4)
                    
                    for param_idx, param in enumerate(['jsc', 'voc', 'ff', 'pce']):
                        param_data = device_data[param].dropna()
                        if len(param_data) > 0:
                            with device_stats[param_idx]:
                                st.metric(
                                    param.upper(),
                                    f"{param_data.mean():.2f}",
                                    f"n={len(param_data)}"
                                )
                    
                    # Best pixel analysis for this device
                    st.markdown("---")
                    st.markdown("##### 📍 Best Pixel Performance (by PCE)")
                    
                    if 'pixel' in device_data.columns and 'pce' in device_data.columns:
                        # Find best pixel by average PCE
                        pixel_pce = device_data.groupby('pixel')['pce'].agg(['mean', 'std', 'count']).reset_index()
                        pixel_pce = pixel_pce.sort_values('mean', ascending=False)
                        
                        if not pixel_pce.empty:
                            best_pixel = pixel_pce.iloc[0]
                            
                            px_col1, px_col2, px_col3 = st.columns(3)
                            
                            with px_col1:
                                st.metric(
                                    "🏆 Best Pixel",
                                    f"{best_pixel['pixel']}",
                                    f"PCE: {best_pixel['mean']:.2f}%"
                                )
                            
                            with px_col2:
                                st.metric(
                                    "Std Dev",
                                    f"{best_pixel['std']:.2f}",
                                )
                            
                            with px_col3:
                                st.metric(
                                    "Measurements",
                                    f"{int(best_pixel['count'])}",
                                )
                            
                            # Show all pixels ranking
                            with st.expander("📊 All Pixels Ranking"):
                                ranking_df = pixel_pce[['pixel', 'mean', 'std', 'count']].copy()
                                ranking_df = ranking_df.rename(columns={
                                    'pixel': 'Pixel',
                                    'mean': 'Avg PCE (%)',
                                    'std': 'Std Dev',
                                    'count': 'Count'
                                })
                                ranking_df['Rank'] = range(1, len(ranking_df) + 1)
                                ranking_df = ranking_df[[
                                    'Rank', 'Pixel', 'Avg PCE (%)', 'Std Dev', 'Count'
                                ]]
                                st.dataframe(ranking_df, use_container_width=True)

# ============================================================================
# TAB 4: ANALYSIS - INTERACTIVE PLOTS
# ============================================================================

with tab4:
    st.subheader("📊 Analysis - Time Series Plots")
    
    # Use filtered data from session state
    filtered_data_for_analysis = st.session_state.get('filtered_data', raw_data)
    
    if filtered_data_for_analysis.empty:
        st.warning("No data available. Check your filters.")
    else:
        devices_list = sorted(filtered_data_for_analysis['device_number'].unique())
        
        # Analysis mode selection (Parameter vs Pixel)
        analysis_tabs = st.tabs(["📈 Parameter Analysis", "📍 Pixel Stability"])
        
        # ============================================================================
        # ANALYSIS TAB 1: PARAMETER ANALYSIS (Original functionality)
        # ============================================================================
        
        with analysis_tabs[0]:
            # Device selection
            col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            selected_devices = st.multiselect(
                "Select devices to analyze:",
                options=devices_list,
                default=devices_list if devices_list else [],
            )
        
        with col2:
            parameter = st.radio(
                "Parameter:",
                options=["PCE", "Jsc", "Voc", "FF"],
                index=0,
            )
        
        with col3:
            plot_mode = st.radio(
                "Plot Mode:",
                options=["Default", "Normalized"],
                index=0,
            )
        
        if not selected_devices:
            st.warning("Please select at least one device.")
        else:
            # Map parameter to column name
            param_map = {
                "PCE": "pce",
                "Jsc": "jsc",
                "Voc": "voc",
                "FF": "ff",
            }
            param_col = param_map[parameter]
            
            # Get data for selected devices from filtered data
            plot_data_all = filtered_data_for_analysis[filtered_data_for_analysis['device_number'].isin(selected_devices)].copy()
            
            if plot_data_all.empty or param_col not in plot_data_all.columns:
                st.error(f"No valid data for {parameter}.")
            else:
                # Remove NaN values from pce column (used for selecting best)
                plot_data_all = plot_data_all[plot_data_all['pce'].notna()].copy()
                
                if plot_data_all.empty:
                    st.warning(f"No valid PCE values found to select best measurements.")
                else:
                    # Select BEST (max PCE) for each device per day
                    plot_data_best = plot_data_all.loc[plot_data_all.groupby(['device_number', 'day'])['pce'].idxmax()]
                    plot_data_best = plot_data_best[plot_data_best[param_col].notna()].copy()
                    plot_data_best = plot_data_best.sort_values('datetime')
                    
                    if plot_data_best.empty:
                        st.warning(f"No valid {parameter} values found in best measurements.")
                    else:
                        # Calculate total hours from start of dataset
                        min_datetime = plot_data_best['datetime'].min()
                        plot_data_best['hours_from_start'] = (plot_data_best['datetime'] - min_datetime).dt.total_seconds() / 3600
                        
                        # Apply normalization if selected
                        if plot_mode == "Normalized":
                            # Normalize parameter relative to first measurement value (by device)
                            # This shows degradation/change from baseline
                            plot_data_best['plot_value'] = plot_data_best[param_col]
                            norm_info_parts = []
                            
                            for device_num in selected_devices:
                                device_mask = plot_data_best['device_number'] == device_num
                                device_data = plot_data_best[device_mask]
                                
                                if not device_data.empty:
                                    # Get first (earliest) measurement for this device
                                    first_idx = device_data['datetime'].idxmin()
                                    first_value = device_data.loc[first_idx, param_col]
                                    
                                    if first_value > 0:
                                        # Normalize: value / first_value (ratio relative to baseline)
                                        plot_data_best.loc[device_mask, 'plot_value'] = device_data[param_col] / first_value
                                        norm_info_parts.append(f"Device {device_num}: baseline={first_value:.3f}")
                            
                            norm_info = f"(Normalized relative to first value - " + ", ".join(norm_info_parts) + ")"
                        else:
                            plot_data_best['plot_value'] = plot_data_best[param_col]
                            norm_info = ""
                        
                        st.info(f"📊 Showing BEST PCE for each device per day ({len(plot_data_best)} measurements) {norm_info}")
                        
                        # Create interactive plot
                        fig = go.Figure()
                        
                        # Add trace for each device
                        for device_num in selected_devices:
                            device_data = plot_data_best[plot_data_best['device_number'] == device_num]
                            
                            if not device_data.empty:
                                # Create hover text with day information
                                hover_text = []
                                for idx, row in device_data.iterrows():
                                    if plot_mode == "Normalized":
                                        text = f"<b>Device {device_num}</b><br>" + \
                                               f"Time: {row['datetime']}<br>" + \
                                               f"Hours from start: {row['hours_from_start']:.1f}h<br>" + \
                                               f"Day: {int(row['day'])}<br>" + \
                                               f"Direction: {row['direction']}<br>" + \
                                               f"{parameter} (normalized): {row['plot_value']:.3f}<br>" + \
                                               f"{parameter} (original): {row[param_col]:.3f}"
                                    else:
                                        text = f"<b>Device {device_num}</b><br>" + \
                                               f"Time: {row['datetime']}<br>" + \
                                               f"Hours from start: {row['hours_from_start']:.1f}h<br>" + \
                                               f"Day: {int(row['day'])}<br>" + \
                                               f"Direction: {row['direction']}<br>" + \
                                               f"{parameter}: {row[param_col]:.3f}"
                                    hover_text.append(text)
                                
                                fig.add_trace(go.Scatter(
                                    x=device_data['hours_from_start'],
                                    y=device_data['plot_value'],
                                    mode='lines+markers',
                                    name=f'Device {device_num}',
                                    customdata=hover_text,
                                    hovertemplate='%{customdata}<extra></extra>',
                                ))
                        
                        # Update layout
                        param_label = {
                            "jsc": "Jsc (mA/cm²)",
                            "voc": "Voc (V)",
                            "ff": "FF (%)",
                            "pce": "PCE (%)",
                        }[param_col]
                        
                        if plot_mode == "Normalized":
                            yaxis_title = f"{param_label} (Relative to First Value)"
                            plot_title = f"{parameter} vs Time - Normalized by First Value (Best PCE per Device/Day)"
                        else:
                            yaxis_title = param_label
                            plot_title = f"{parameter} vs Time (Best PCE per Device/Day)"
                        
                        fig.update_layout(
                            title=plot_title,
                            xaxis_title="Hours from Start",
                            yaxis_title=yaxis_title,
                            hovermode='x unified',
                            height=500,
                            template='plotly_white',
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Display data table
                        with st.expander("📋 Show Best Measurements Data"):
                            display_cols = ['device_number', 'day', 'direction', 'datetime', 'pixel', 'jsc', 'voc', 'ff', 'pce']
                            display_df = plot_data_best[display_cols].copy()
                            display_df['datetime'] = display_df['datetime'].astype(str)
                            
                            # Add normalized value column if in normalized mode
                            if plot_mode == "Normalized":
                                display_df['normalized_value'] = plot_data_best['plot_value']
                            
                            display_df = display_df.rename(columns={
                                'device_number': 'Device',
                                'day': 'Day',
                                'direction': 'Direction',
                                'datetime': 'DateTime',
                                'pixel': 'Pixel',
                                'jsc': 'Jsc',
                                'voc': 'Voc',
                                'ff': 'FF',
                                'pce': 'PCE',
                                'normalized_value': f'{parameter} (Relative to 1st)'
                            })
                            
                            st.dataframe(
                                display_df,
                                use_container_width=True,
                                height=400,
                            )
        
        # ============================================================================
        # ANALYSIS TAB 2: PIXEL STABILITY
        # ============================================================================
        
        with analysis_tabs[1]:
            st.markdown("### 📍 Pixel Stability Analysis")
            st.markdown("Analyze performance across different pixels (A, B, C, D) for selected devices - showing BEST measurements only.")
            
            # Device selection and settings for pixel analysis
            col_px1, col_px2, col_px3, col_px4 = st.columns([2, 1, 1, 1])
            
            with col_px1:
                selected_devices_px = st.multiselect(
                    "Select devices for pixel analysis:",
                    options=devices_list,
                    default=devices_list if devices_list else [],
                    key="pixel_devices"
                )
            
            with col_px2:
                pixel_mode = st.radio(
                    "Pixel View:",
                    options=["Overlay All", "Individual"],
                    index=0,
                    key="pixel_view_mode"
                )
            
            with col_px3:
                param_px = st.radio(
                    "Parameter:",
                    options=["PCE", "Jsc", "Voc", "FF"],
                    index=0,
                    key="pixel_param"
                )
            
            with col_px4:
                plot_mode_px = st.radio(
                    "Plot Mode:",
                    options=["Default", "Normalized"],
                    index=0,
                    key="pixel_plot_mode"
                )
            
            if not selected_devices_px:
                st.warning("Please select at least one device.")
            else:
                # Get pixel stability data
                pixel_data = filtered_data_for_analysis[filtered_data_for_analysis['device_number'].isin(selected_devices_px)].copy()
                
                if pixel_data.empty:
                    st.warning("No pixel data available for selected devices.")
                else:
                    # Map parameter to column name
                    param_px_col = {"PCE": "pce", "Jsc": "jsc", "Voc": "voc", "FF": "ff"}[param_px]
                    
                    # Get unique pixels
                    unique_pixels = sorted(pixel_data['pixel'].unique())
                    
                    # Remove NaN values from pce column (used for selecting best)
                    pixel_data = pixel_data[pixel_data['pce'].notna()].copy()
                    
                    # Select BEST (max PCE) for each device per day per pixel
                    pixel_data_best = pixel_data.loc[pixel_data.groupby(['device_number', 'day', 'pixel'])['pce'].idxmax()].copy()
                    pixel_data_best = pixel_data_best[pixel_data_best[param_px_col].notna()].copy()
                    
                    # Calculate hours from start of dataset
                    min_datetime = pixel_data_best['datetime'].min()
                    pixel_data_best['hours_from_start'] = (pixel_data_best['datetime'] - min_datetime).dt.total_seconds() / 3600
                    pixel_data_best = pixel_data_best.sort_values('datetime')
                    
                    # Apply normalization if selected
                    if plot_mode_px == "Normalized":
                        # Normalize parameter relative to first measurement value (by device and pixel)
                        pixel_data_best['plot_value'] = pixel_data_best[param_px_col]
                        norm_info_px = []
                        
                        for device_num in selected_devices_px:
                            for pixel in unique_pixels:
                                device_pixel_mask = (pixel_data_best['device_number'] == device_num) & (pixel_data_best['pixel'] == pixel)
                                device_pixel_data = pixel_data_best[device_pixel_mask]
                                
                                if not device_pixel_data.empty:
                                    # Get first (earliest) measurement for this device-pixel combo
                                    first_idx = device_pixel_data['datetime'].idxmin()
                                    first_value = device_pixel_data.loc[first_idx, param_px_col]
                                    
                                    if first_value > 0:
                                        # Normalize: value / first_value
                                        pixel_data_best.loc[device_pixel_mask, 'plot_value'] = device_pixel_data[param_px_col] / first_value
                                        norm_info_px.append(f"Dev{device_num}-Px{pixel}: baseline={first_value:.3f}")
                        
                        norm_info_str = f"(Normalized relative to first value - " + ", ".join(norm_info_px[:3]) + ("..." if len(norm_info_px) > 3 else "") + ")"
                    else:
                        pixel_data_best['plot_value'] = pixel_data_best[param_px_col]
                        norm_info_str = ""
                    
                    st.info(f"📊 Showing BEST PCE for each device/day/pixel ({len(pixel_data_best)} measurements) {norm_info_str}")
                    
                    if pixel_mode == "Overlay All":
                        # Plot all pixels overlaid for each device
                        for device_num in selected_devices_px:
                            device_pixel_data = pixel_data_best[pixel_data_best['device_number'] == device_num]
                            
                            if not device_pixel_data.empty:
                                st.markdown(f"#### Device {device_num}")
                                
                                fig_px = go.Figure()
                                
                                # Add trace for each pixel
                                for pixel in unique_pixels:
                                    pixel_device_data = device_pixel_data[device_pixel_data['pixel'] == pixel].copy()
                                    
                                    if not pixel_device_data.empty:
                                        param_data = pixel_device_data[param_px_col].dropna()
                                        
                                        if len(param_data) > 0:
                                            hover_text = []
                                            for idx, row in pixel_device_data.iterrows():
                                                if plot_mode_px == "Normalized":
                                                    text = f"<b>Device {device_num} - Pixel {pixel}</b><br>" + \
                                                           f"Time: {row['datetime']}<br>" + \
                                                           f"Hours from start: {row['hours_from_start']:.1f}h<br>" + \
                                                           f"Day: {int(row['day'])}<br>" + \
                                                           f"Direction: {row['direction']}<br>" + \
                                                           f"{param_px} (normalized): {row['plot_value']:.3f}<br>" + \
                                                           f"{param_px} (original): {row[param_px_col]:.3f}"
                                                else:
                                                    text = f"<b>Device {device_num} - Pixel {pixel}</b><br>" + \
                                                           f"Time: {row['datetime']}<br>" + \
                                                           f"Hours from start: {row['hours_from_start']:.1f}h<br>" + \
                                                           f"Day: {int(row['day'])}<br>" + \
                                                           f"Direction: {row['direction']}<br>" + \
                                                           f"{param_px}: {row[param_px_col]:.3f}"
                                                hover_text.append(text)
                                            
                                            fig_px.add_trace(go.Scatter(
                                                x=pixel_device_data['hours_from_start'],
                                                y=pixel_device_data['plot_value'],
                                                mode='lines+markers',
                                                name=f'Pixel {pixel}',
                                                customdata=hover_text,
                                                hovertemplate='%{customdata}<extra></extra>',
                                            ))
                                
                                # Update layout
                                param_label_px = {
                                    "jsc": "Jsc (mA/cm²)",
                                    "voc": "Voc (V)",
                                    "ff": "FF (%)",
                                    "pce": "PCE (%)",
                                }[param_px_col]
                                
                                if plot_mode_px == "Normalized":
                                    yaxis_title_px = f"{param_label_px} (Relative to First Value)"
                                    plot_title_px = f"Device {device_num} - Pixel Stability ({param_px}) - Normalized"
                                else:
                                    yaxis_title_px = param_label_px
                                    plot_title_px = f"Device {device_num} - Pixel Stability ({param_px})"
                                
                                fig_px.update_layout(
                                    title=plot_title_px,
                                    xaxis_title="Hours from Start",
                                    yaxis_title=yaxis_title_px,
                                    hovermode='x unified',
                                    height=400,
                                    template='plotly_white',
                                )
                                
                                st.plotly_chart(fig_px, use_container_width=True)
                    
                    else:  # Individual pixel view
                        st.markdown("#### Individual Pixel Performance")
                        
                        # Pixel selector
                        pixel_selector = st.selectbox("Select pixel to view:", unique_pixels)
                        
                        pixel_individual_data = pixel_data_best[pixel_data_best['pixel'] == pixel_selector].copy()
                        
                        if not pixel_individual_data.empty:
                            fig_ind = go.Figure()
                            
                            for device_num in selected_devices_px:
                                device_px_data = pixel_individual_data[pixel_individual_data['device_number'] == device_num].copy()
                                
                                if not device_px_data.empty:
                                    hover_text = []
                                    for idx, row in device_px_data.iterrows():
                                        if plot_mode_px == "Normalized":
                                            text = f"<b>Device {device_num} - Pixel {pixel_selector}</b><br>" + \
                                                   f"Time: {row['datetime']}<br>" + \
                                                   f"Hours from start: {row['hours_from_start']:.1f}h<br>" + \
                                                   f"Day: {int(row['day'])}<br>" + \
                                                   f"Direction: {row['direction']}<br>" + \
                                                   f"{param_px} (normalized): {row['plot_value']:.3f}<br>" + \
                                                   f"{param_px} (original): {row[param_px_col]:.3f}"
                                        else:
                                            text = f"<b>Device {device_num} - Pixel {pixel_selector}</b><br>" + \
                                                   f"Time: {row['datetime']}<br>" + \
                                                   f"Hours from start: {row['hours_from_start']:.1f}h<br>" + \
                                                   f"Day: {int(row['day'])}<br>" + \
                                                   f"Direction: {row['direction']}<br>" + \
                                                   f"{param_px}: {row[param_px_col]:.3f}"
                                        hover_text.append(text)
                                    
                                    fig_ind.add_trace(go.Scatter(
                                        x=device_px_data['hours_from_start'],
                                        y=device_px_data['plot_value'],
                                        mode='lines+markers',
                                        name=f'Device {device_num}',
                                        customdata=hover_text,
                                        hovertemplate='%{customdata}<extra></extra>',
                                    ))
                            
                            # Update layout
                            param_label_px = {
                                "jsc": "Jsc (mA/cm²)",
                                "voc": "Voc (V)",
                                "ff": "FF (%)",
                                "pce": "PCE (%)",
                            }[param_px_col]
                            
                            if plot_mode_px == "Normalized":
                                yaxis_title_px_ind = f"{param_label_px} (Relative to First Value)"
                                plot_title_px_ind = f"Pixel {pixel_selector} - Stability Across Devices ({param_px}) - Normalized"
                            else:
                                yaxis_title_px_ind = param_label_px
                                plot_title_px_ind = f"Pixel {pixel_selector} - Stability Across Devices ({param_px})"
                            
                            fig_ind.update_layout(
                                title=plot_title_px_ind,
                                xaxis_title="Hours from Start",
                                yaxis_title=yaxis_title_px_ind,
                                hovermode='x unified',
                                height=400,
                                template='plotly_white',
                            )
                            
                            st.plotly_chart(fig_ind, use_container_width=True)
                            
                            # Show statistics for this pixel
                            st.markdown(f"##### Statistics for Pixel {pixel_selector}")
                            stat_cols_px = st.columns(4)
                            
                            for col_idx, device_num in enumerate(selected_devices_px):
                                device_px = pixel_individual_data[pixel_individual_data['device_number'] == device_num]
                                if not device_px.empty:
                                    param_vals = device_px[param_px_col].dropna()
                                    if len(param_vals) > 0:
                                        with stat_cols_px[col_idx % 4]:
                                            st.metric(
                                                f"Device {device_num}",
                                                f"{param_vals.mean():.2f}",
                                                f"σ={param_vals.std():.2f}"
                                            )


# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 11px;'>
    <p>PV Stability Analysis Tool v3.0 | Device-Grouped Data Structure | Timestamp-based Analysis</p>
</div>
""", unsafe_allow_html=True)
