"""
Data Parser Module
==================

Handles reading and parsing stability measurement .txt files.
Extracts Jsc, Voc, FF, and PCE values, organized by variation/device name.

File format: 
  XXXX_YYYY-MM-DD_HH.MM.SS_Stability (JV)_<variation>-<device_num>-<pixel>.txt
  
Example:
  0003_2026-02-26_14.11.38_Stability (JV)_PVK1CIGS-4PADCB-39-1-1C.txt
  
Parsed as:
  - Scan: 0003
  - DateTime: 2026-02-26 14:11:38
  - Variation: PVK1CIGS-4PADCB
  - Device: 39
  - Pixel: 1-1C
"""

from __future__ import annotations

import os
import re
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd


@dataclass
class MeasurementPoint:
    """Single measurement point with timestamp"""
    scan_number: int
    timestamp: datetime
    pixel: str
    day: int  # Day extracted from variation name (e.g., D16 -> 16)
    direction: str = "FW"  # RV (Reverse) or FW (Forward)
    jsc: float | None = None
    voc: float | None = None
    ff: float | None = None
    pce: float | None = None


@dataclass
class DayData:
    """All measurements for a single day within a device"""
    day: int
    variation: str
    measurements: List[MeasurementPoint] = field(default_factory=list)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert measurements to DataFrame"""
        rows = []
        for m in self.measurements:
            rows.append({
                'day': self.day,
                'variation': self.variation,
                'direction': m.direction,
                'pixel': m.pixel,
                'scan': m.scan_number,
                'datetime': m.timestamp,
                'date': m.timestamp.date(),
                'time': m.timestamp.time(),
                'jsc': m.jsc,
                'voc': m.voc,
                'ff': m.ff,
                'pce': m.pce,
            })
        return pd.DataFrame(rows)


@dataclass
class DeviceData:
    """All measurements for a single device, organized by day"""
    device_name: str
    device_number: int
    days: Dict[int, DayData] = field(default_factory=dict)  # day_num -> DayData
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert all measurements to DataFrame"""
        rows = []
        for day_num in sorted(self.days.keys()):
            day_data = self.days[day_num]
            for m in day_data.measurements:
                rows.append({
                    'device': self.device_name,
                    'device_number': self.device_number,
                    'day': day_num,
                    'variation': day_data.variation,
                    'direction': m.direction,
                    'pixel': m.pixel,
                    'scan': m.scan_number,
                    'datetime': m.timestamp,
                    'date': m.timestamp.date(),
                    'time': m.timestamp.time(),
                    'jsc': m.jsc,
                    'voc': m.voc,
                    'ff': m.ff,
                    'pce': m.pce,
                })
        return pd.DataFrame(rows)


def extract_day_from_variation(variation: str) -> int:
    """
    Extract day number from variation name.
    
    Examples:
    - "Stability-D16" -> 16
    - "Stability-D1" -> 1
    - "PVK1CIGS-4PADCB-D5" -> 5
    
    If no day found, returns 1 (default).
    """
    # Look for D followed by digits
    match = re.search(r'-D(\d+)(?:-|$)', variation, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 1  # Default to day 1 if no day marker found


# Updated pattern for new filename format
STABILITY_PATTERN = re.compile(
    r"^(?P<scan>\d+)_(?P<datetime>\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}\.\d{2})_Stability\s*\(JV\)_(?P<variation>[\w\-]+?)-(?P<device>\d+)-(?P<pixel>[\w\-\d]+)\.txt$",
    re.IGNORECASE,
)


def parse_stability_filename(path: Path) -> tuple[int, datetime, str, int, str, int] | None:
    """
    Parse filename to extract metadata.
    Returns (scan_num, timestamp, variation, device_number, pixel, day) or None
    """
    m = STABILITY_PATTERN.match(path.name)
    if not m:
        return None
    
    try:
        scan_num = int(m.group("scan"))
        datetime_str = m.group("datetime")
        timestamp = datetime.strptime(datetime_str, "%Y-%m-%d_%H.%M.%S")
        variation = m.group("variation")
        device_num = int(m.group("device"))
        pixel = m.group("pixel")
        day = extract_day_from_variation(variation)
        
        return (scan_num, timestamp, variation, device_num, pixel, day)
    except Exception:
        return None


def discover_stability_files(base_dir: Path) -> List[Path]:
    """Recursively discover all stability files in a directory."""
    files: List[Path] = []
    for root, _, filenames in os.walk(base_dir):
        for fname in filenames:
            if fname.lower().endswith(".txt"):
                full_path = Path(root) / fname
                # Quick validation
                if STABILITY_PATTERN.match(full_path.name):
                    files.append(full_path)
    return sorted(files)


def parse_stability_file(path: Path) -> pd.DataFrame:
    """
    Parse a single stability file and extract measurement data.
    
    Returns DataFrame with columns: jsc, voc, ff, pce, direction (RV or FW)
    Each row's direction is extracted from the Scan column (FW or RV).
    """
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return pd.DataFrame(columns=["jsc", "voc", "ff", "pce", "direction"])

    # Look for the data table header
    header_idx = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.lower().startswith("scan") and "jsc" in s.lower():
            header_idx = i
            break

    if header_idx is not None and header_idx + 2 < len(lines):
        header_tokens = re.split(r"\t+", lines[header_idx].strip())
        data_start = header_idx + 2
        records = []
        
        for row in lines[data_start:]:
            r = row.strip()
            if not r or re.match(r"^[A-Za-z]_", r):
                break
            tokens = re.split(r"\t+", r)
            
            # First token is the scan type (FW or RV)
            scan_type = tokens[0].strip().upper() if tokens else "FW"
            if scan_type not in ["FW", "RV"]:
                scan_type = "FW"
            
            rec: Dict[str, float | str] = {"direction": scan_type}
            
            # Parse remaining columns using headers
            for h, t in zip(header_tokens[1:], tokens[1:]):  # Skip first column (scan type)
                h_low = h.strip().lower()
                try:
                    val = float(t) if t else None
                except Exception:
                    val = None
                    
                if h_low.startswith("voc"):
                    rec["voc"] = val
                elif h_low.startswith("jsc"):
                    rec["jsc"] = val
                elif h_low.startswith("ff"):
                    rec["ff"] = val
                elif h_low.startswith("eff") or h_low.startswith("pce"):
                    rec["pce"] = val
            
            if rec.get("pce") is not None:
                records.append(rec)
        
        if records:
            return pd.DataFrame(records)
    
    # Fallback: regex search for PCE values
    pces: List[float] = []
    for ln in lines:
        m = re.search(r"(pce|efficiency)[^\d]*([\d\.]+)", ln, re.IGNORECASE)
        if m:
            try:
                pces.append(float(m.group(2)))
            except Exception:
                continue
    
    if pces:
        return pd.DataFrame({"pce": pces, "direction": "FW"})
    
    return pd.DataFrame(columns=["jsc", "voc", "ff", "pce", "direction"])


def build_device_data_map(file_paths: List[Path]) -> Dict[int, DeviceData]:
    """
    Build a map of device_number -> DeviceData with all measurements organized by day.
    
    Returns: {device_number: DeviceData}
    """
    device_map: Dict[int, DeviceData] = {}
    
    for file_path in file_paths:
        parsed = parse_stability_filename(file_path)
        if not parsed:
            continue
        
        scan_num, timestamp, variation, device_num, pixel, day = parsed
        
        # Initialize device if first time seeing it
        if device_num not in device_map:
            device_map[device_num] = DeviceData(
                device_name=f"Device {device_num}",
                device_number=device_num,
            )
        
        # Initialize day if first time seeing it for this device
        if day not in device_map[device_num].days:
            device_map[device_num].days[day] = DayData(
                day=day,
                variation=variation,
            )
        
        # Parse measurements from file
        df = parse_stability_file(file_path)
        
        if df.empty:
            continue
        
        # Create measurement points for each row in the file
        for idx, row in df.iterrows():
            direction = row.get('direction', 'FW')
            measurement = MeasurementPoint(
                scan_number=scan_num,
                timestamp=timestamp,
                pixel=pixel,
                day=day,
                direction=direction,
                jsc=row.get('jsc'),
                voc=row.get('voc'),
                ff=row.get('ff'),
                pce=row.get('pce'),
            )
            device_map[device_num].days[day].measurements.append(measurement)
    
    # Sort measurements by timestamp within each day
    for device in device_map.values():
        for day_data in device.days.values():
            day_data.measurements.sort(key=lambda m: m.timestamp)
    
    return device_map


def build_raw_data_table(device_map: Dict[int, DeviceData]) -> pd.DataFrame:
    """
    Build comprehensive raw data table from all devices.
    
    Returns DataFrame with all measurements.
    """
    all_rows = []
    
    for device_num in sorted(device_map.keys()):
        device = device_map[device_num]
        df = device.to_dataframe()
        all_rows.append(df)
    
    if not all_rows:
        return pd.DataFrame()
    
    result = pd.concat(all_rows, ignore_index=True)
    return result.sort_values(['device_number', 'datetime']).reset_index(drop=True)


def process_uploaded_files(uploaded_files: list) -> List[Path]:
    """
    Process uploaded .txt files or .zip archives.
    
    Returns list of Path objects to extracted files.
    """
    file_paths: List[Path] = []
    tmp_dir = tempfile.mkdtemp()
    
    for uf in uploaded_files:
        name = uf.name
        if name.lower().endswith(".zip"):
            try:
                uf.seek(0)
                with zipfile.ZipFile(uf) as zf:
                    for nm in zf.namelist():
                        if nm.lower().endswith(".txt"):
                            file_path = Path(tmp_dir) / Path(nm).name
                            file_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(file_path, "wb") as f:
                                f.write(zf.read(nm))
                            if STABILITY_PATTERN.match(file_path.name):
                                file_paths.append(file_path)
            except Exception as e:
                raise Exception(f"Could not process zip file: {e}")
        elif name.lower().endswith(".txt"):
            file_path = Path(tmp_dir) / name
            with open(file_path, "wb") as f:
                f.write(uf.getvalue())
            if STABILITY_PATTERN.match(file_path.name):
                file_paths.append(file_path)
    
    return sorted(file_paths)
