# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Python application that parses Apple Health export data (XML + GPX files) and generates Excel reports with charts for cycling fitness tracking. It handles large XML files (1GB+) efficiently using iterative parsing and enriches workout data from multiple sources.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full pipeline (processes Apple Health export → Excel report)
python src/main.py

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test class
pytest tests/test_parser.py::TestExtractWorkouts -v

# Run specific test
pytest tests/test_parser.py::TestExtractWorkouts::test_extract_cycling_workouts -v
```

The pipeline will:
1. Extract the zip file specified in `config.py` to `data/`
2. Parse `export.xml` for cycling workouts
3. Match workouts to GPX files for elevation data
4. Extract distance/calorie records and match to workouts
5. Extract heart rate records and match to workouts
6. Aggregate metrics and generate Excel report in `output/`

## Configuration

**Before running**, update `config.py`:
- `EXPORT_ZIP_PATH`: Path to Apple Health export zip file
- `MAX_HEART_RATE`: User's actual max heart rate for HR zone calculations
- `WORKOUT_TYPES`: Activity types to extract (default: cycling)
- `START_DATE`/`END_DATE`: Optional date filtering

## Architecture

### Data Flow Pipeline

The application follows a sequential enrichment pattern where workout data is progressively enhanced:

```
export.zip → extract → export.xml
                          ↓
                    extract_workouts() → List[Workout] (basic data: start/end time)
                          ↓
                    enrich_with_gpx() → adds elevation_gain_m, gpx_file
                          ↓
                    enrich_with_distance_calories() → adds distance_km, calories
                          ↓
                    enrich_with_heart_rate() → adds avg_heart_rate, hr zones
                          ↓
                    analyze_data() → aggregations, trends
                          ↓
                    generate_excel_report() → 6 worksheets with charts
```

Each enrichment step **modifies workouts in place** rather than creating new objects.

### Critical Parsing Details

**Apple Health XML Structure:**
- `<Workout>` elements contain metadata (start/end dates, source) but often lack distance/calories
- `<Record>` elements contain granular data (`HKQuantityTypeIdentifierDistanceCycling`, `HKQuantityTypeIdentifierActiveEnergyBurned`, `HKQuantityTypeIdentifierHeartRate`)
- Records must be matched to workouts by timestamp ranges

**Why separate extraction functions:**
- `extract_workouts()`: Fast initial pass for workout boundaries
- `extract_distance_and_calories()`: Second pass extracting only relevant record types within workout date ranges
- `extract_heart_rate_records()`: Third pass for HR data (can be 455K+ records)

This approach minimizes memory usage by filtering records by date range and type before loading into memory.

**Duration parsing gotcha:**
- The `duration` attribute in XML is already in minutes (per `durationUnit="min"`)
- Do NOT divide by 60 again or you'll get incorrect values
- Fallback: Calculate from `(end_date - start_date)` if `duration` attribute missing

**Unit conversions handled:**
- Distance: `mi` → `km` (*1.60934), `m` → `km` (/1000)
- Elevation: Stored as meters
- Calories: `Cal` = kcal (no conversion), `cal` → `kcal` (/1000)

### Memory Efficiency

Uses `ET.iterparse()` with `events=("start", "end")` for streaming XML parsing:
- Process elements one at a time
- Call `elem.clear()` after processing to release memory
- Call `root.clear()` periodically (every 1000-10000 elements)
- Critical for handling 1.9GB export files without OOM

### Data Models

**Workout** (central data structure):
- Core fields populated from `<Workout>` elements
- Optional fields enriched later: `gpx_file`, `elevation_gain_m`, `avg_heart_rate`
- Computed properties: `duration_hours`, `avg_speed_kmh`, `calories_per_km`

**Enrichment pattern:**
Functions modify `List[Workout]` in place rather than returning new data. This is intentional for memory efficiency with large datasets.

### GPX Matching

Workouts are matched to GPX files by extracting timestamp from filename format:
```
route_2025-01-11_9.30am.gpx → datetime(2025, 1, 11, 9, 30)
```

Matching tolerance: 30 minutes (workouts within ±30 min of GPX timestamp are candidates).

### Excel Generation

The `ExcelGenerator` class creates 6 worksheets:
1. **Summary**: Overall statistics (total distance, rides, etc.)
2. **Yearly Trends**: Year-over-year with line/bar charts
3. **Monthly Activity**: Month-by-month breakdown
4. **Heart Rate Analysis**: HR zones, yearly avg HR
5. **Elevation Stats**: Yearly elevation totals, top 10 climbs
6. **Raw Data**: All workouts with full details

Charts are created using `openpyxl.chart` (LineChart, BarChart) with `Reference` objects pointing to worksheet data ranges.

## Key Implementation Notes

### When modifying parsers:

1. **Always use iterative parsing** with `iterparse()` for XML files
2. **Filter by date range** when extracting records to reduce memory
3. **Match records to workouts by timestamp** using `start_date <= timestamp <= end_date`
4. **Aggregate records per workout** (e.g., sum all distance records during workout timeframe)

### When adding new metrics:

1. Add optional field to `Workout` dataclass in `models.py`
2. Create extraction function in `parser.py` (follow pattern of `extract_distance_and_calories()`)
3. Create enrichment function that modifies workouts in place
4. Add enrichment step to pipeline in `main.py`
5. Update analyzer functions in `analyzer.py` for aggregations
6. Add to Excel report in `excel_generator.py`

### Common data issues:

- **Distance = 0**: Distance stored in `<Record>` elements, not `<Workout>` attributes
- **Calories = 0**: Same as distance, extract from records
- **No GPX match**: Indoor workouts or pre-GPS era rides won't have route files
- **Missing HR**: User didn't wear Apple Watch during workout

## File Organization

```
src/
├── main.py              # Pipeline orchestration (7 steps)
├── parser.py            # XML parsing with iterparse (workouts, records)
├── gpx_parser.py        # GPX elevation extraction, timestamp matching
├── analyzer.py          # Aggregations (yearly/monthly), HR zones, trends
├── excel_generator.py   # ExcelGenerator class, 6 worksheets + charts
└── models.py            # Dataclasses: Workout, HeartRateRecord, WorkoutSummary

config.py                # All settings (paths, HR zones, units, colors)
```

## Apple Health Export Structure

```
apple_health_export/
├── export.xml                    # Main data file (1-2GB)
└── workout-routes/              # GPS tracks
    ├── route_2025-01-11_9.30am.gpx
    └── ...
```

The export.xml contains:
- `<Workout>` elements: High-level workout metadata
- `<Record>` elements: Granular time-series data
- Record types used: `HKQuantityTypeIdentifierDistanceCycling`, `HKQuantityTypeIdentifierActiveEnergyBurned`, `HKQuantityTypeIdentifierHeartRate`

## Testing

The test suite covers all parser functions with 21 tests:

**Test organization:**
- `tests/test_parser.py`: Tests for all parsing functions
- Uses pytest fixtures for sample XML data
- Tests create temporary XML files to simulate Apple Health exports

**Test coverage:**
- `parse_datetime()`: Basic format, timezone handling, error cases
- `extract_workouts()`: Workout extraction, unit conversion, type filtering
- `extract_heart_rate_records()`: HR extraction, date filtering
- `match_heart_rate_to_workouts()`: Matching logic, aggregation
- `calculate_hr_zone_time()`: Zone calculation, edge cases
- `extract_distance_and_calories()`: Record extraction, unit conversion
- `enrich_workouts_with_distance_calories()`: Enrichment logic, timestamp matching

**When adding new parser functions:**
1. Create sample XML data as a pytest fixture
2. Test the happy path with valid data
3. Test edge cases (missing data, empty results, boundary conditions)
4. Test unit conversions if applicable
5. Use approximate comparisons for floating point values (`abs(actual - expected) < 0.01`)
