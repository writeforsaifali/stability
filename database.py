"""
Database Module
===============

Handles data storage, filtering, and statistics for stability measurements.
Optimized for device-grouped data with timestamp tracking.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd


class StabilityDatabase:
    """Database for storing and filtering stability measurement data."""
    
    def __init__(self, raw_data: pd.DataFrame):
        """
        Initialize the database with raw data.
        
        Args:
            raw_data: DataFrame with columns [device_number, device, variation, pixel, 
                                             datetime, jsc, voc, ff, pce, ...]
        """
        self.raw_data = raw_data.copy() if not raw_data.empty else raw_data
        self.filtered_data = raw_data.copy() if not raw_data.empty else raw_data
        self.filters: Dict[str, Tuple[float, float]] = {}
    
    def set_filter(self, parameter: str, min_val: float, max_val: float) -> None:
        """
        Set a filter for a parameter.
        
        Args:
            parameter: Parameter name (jsc, voc, ff, pce)
            min_val: Minimum acceptable value
            max_val: Maximum acceptable value
        """
        if parameter in ["jsc", "voc", "ff", "pce"]:
            self.filters[parameter] = (min_val, max_val)
    
    def clear_filter(self, parameter: str) -> None:
        """Remove filter for a parameter."""
        if parameter in self.filters:
            del self.filters[parameter]
    
    def clear_all_filters(self) -> None:
        """Remove all filters."""
        self.filters.clear()
    
    def apply_filters(self) -> None:
        """Apply all active filters to the data."""
        filtered = self.raw_data.copy()
        
        for param, (min_val, max_val) in self.filters.items():
            if param in filtered.columns:
                # Filter out NaN values first
                mask = filtered[param].notna() & (filtered[param] >= min_val) & (filtered[param] <= max_val)
                filtered = filtered[mask]
        
        self.filtered_data = filtered.reset_index(drop=True)
    
    def get_raw_data(self) -> pd.DataFrame:
        """Return the original raw data."""
        return self.raw_data.copy()
    
    def get_filtered_data(self) -> pd.DataFrame:
        """Return the filtered data."""
        return self.filtered_data.copy()
    
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        Get overall statistics for each parameter from filtered data.
        
        Returns dictionary with statistics for each parameter.
        """
        stats = {}
        for param in ["jsc", "voc", "ff", "pce"]:
            if param in self.filtered_data.columns:
                col_data = self.filtered_data[param].dropna()
                if len(col_data) > 0:
                    stats[param] = {
                        "min": float(col_data.min()),
                        "max": float(col_data.max()),
                        "mean": float(col_data.mean()),
                        "median": float(col_data.median()),
                        "std": float(col_data.std()),
                        "count": len(col_data),
                    }
        return stats
    
    def get_filter_recommendations(self) -> Dict[str, Tuple[float, float]]:
        """
        Get recommended filter ranges based on raw data statistics.
        
        Uses mean ± 2*std as recommended range.
        """
        recommendations = {}
        for param in ["jsc", "voc", "ff", "pce"]:
            if param in self.raw_data.columns:
                col_data = self.raw_data[param].dropna()
                if len(col_data) > 1:
                    mean = col_data.mean()
                    std = col_data.std()
                    min_val = max(0, mean - 2 * std)
                    max_val = mean + 2 * std
                    recommendations[param] = (float(min_val), float(max_val))
        return recommendations
    
    def export_to_csv(self, use_filtered: bool = True) -> bytes:
        """
        Export data to CSV format.
        
        Args:
            use_filtered: If True, export filtered data; otherwise export raw data
        
        Returns:
            CSV data as bytes
        """
        data = self.filtered_data if use_filtered else self.raw_data
        # Convert datetime to string for CSV
        if 'datetime' in data.columns:
            data = data.copy()
            data['datetime'] = data['datetime'].astype(str)
        return data.to_csv(index=False).encode("utf-8")
    
    def get_devices(self) -> List[int]:
        """Get list of unique device numbers in the data, sorted."""
        if self.filtered_data.empty or 'device_number' not in self.filtered_data.columns:
            return []
        return sorted(self.filtered_data["device_number"].unique().tolist())
    
    def get_data_for_device(self, device_num: int) -> pd.DataFrame:
        """
        Get all filtered data for a specific device.
        
        Args:
            device_num: Device number
        
        Returns:
            Filtered DataFrame for the device
        """
        if self.filtered_data.empty or 'device_number' not in self.filtered_data.columns:
            return pd.DataFrame()
        return self.filtered_data[self.filtered_data["device_number"] == device_num].copy()
    
    def get_data_quality_report(self) -> Dict[str, any]:
        """
        Generate a data quality report.
        
        Returns dictionary with data quality metrics.
        """
        report = {
            "total_records": len(self.raw_data),
            "records_after_filtering": len(self.filtered_data),
            "records_removed": len(self.raw_data) - len(self.filtered_data),
            "removal_percentage": (len(self.raw_data) - len(self.filtered_data)) / len(self.raw_data) * 100 if len(self.raw_data) > 0 else 0,
            "unique_devices": len(self.get_devices()),
        }
        
        # Missing values report
        for param in ["jsc", "voc", "ff", "pce"]:
            if param in self.filtered_data.columns:
                missing = self.filtered_data[param].isna().sum()
                report[f"{param}_missing"] = missing
        
        return report
    
    def get_timeseries_data(self, device_num: int, parameter: str) -> pd.DataFrame:
        """
        Get time-series data for a device and parameter.
        
        Args:
            device_num: Device number
            parameter: Parameter name (jsc, voc, ff, pce)
        
        Returns:
            DataFrame with datetime and parameter values
        """
        device_data = self.get_data_for_device(device_num)
        if device_data.empty or parameter not in device_data.columns or 'datetime' not in device_data.columns:
            return pd.DataFrame()
        
        # Remove NaN values
        ts_data = device_data[['datetime', parameter]].dropna()
        ts_data = ts_data.sort_values('datetime')
        return ts_data
