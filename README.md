# Apple Health Cycling Dashboard

A Python application that parses Apple Health export data and generates comprehensive Excel reports with charts to track mountain biking fitness and activity over time.

## Features

- **Parse Apple Health Exports**: Extract cycling workouts and health records from Apple Health XML exports
- **GPS/Elevation Data**: Automatically match workouts to GPX files for elevation gain metrics
- **Heart Rate Analysis**: Track heart rate zones, average HR, and cardiovascular trends
- **Comprehensive Metrics**: Distance, duration, elevation, calories, and performance trends
- **Excel Reports with Charts**: Professional multi-worksheet Excel files with visualizations
- **Historical Analysis**: Track fitness progress across multiple years (2019-2025+)

## Output Example

The generated Excel report includes 6 worksheets:

1. **Summary** - High-level statistics across all years
2. **Yearly Trends** - Year-over-year comparison with charts
3. **Monthly Activity** - Month-by-month breakdown with trends
4. **Heart Rate Analysis** - HR zones and trends
5. **Elevation Stats** - Climbing metrics and top 10 biggest climbs
6. **Raw Data** - Complete workout details for custom analysis

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

Dependencies installed:
- `pandas` - Data analysis and manipulation
- `openpyxl` - Excel file generation with charts
- `gpxpy` - GPX file parsing for elevation data
- `python-dateutil` - Date/time handling

## Usage

### 1. Export Your Apple Health Data

On your iPhone:
1. Open the **Health** app
2. Tap your profile picture (top right)
3. Scroll down and tap **Export All Health Data**
4. Wait for the export to complete (may take a few minutes)
5. Save the exported zip file to a known location

### 2. Configure the Export Path

Edit `config.py` and update the export file path:

```python
EXPORT_ZIP_PATH = Path.home() / "path/to/your/export.zip"
```

### 3. Adjust Settings (Optional)

In `config.py`, you can customize:

- **Heart Rate Zones**: Adjust `MAX_HEART_RATE` based on your actual max HR
- **Date Range**: Filter workouts by date using `START_DATE` and `END_DATE`
- **Units**: Change between km/miles and meters/feet
- **Workout Types**: Add other activity types beyond cycling

### 4. Run the Analysis

```bash
python src/main.py
```

The pipeline will:
1. Extract the Apple Health export zip file
2. Parse cycling workouts from export.xml (handles large 1GB+ files efficiently)
3. Match workouts to GPX files for elevation data
4. Extract heart rate records for workout timeframes
5. Analyze and aggregate all metrics
6. Generate an Excel report with charts

### 5. View Your Report

The Excel report will be saved to:
```
output/apple_health_cycling_report_YYYY-MM-DD.xlsx
```

Open it with Microsoft Excel, LibreOffice Calc, or any spreadsheet application.

## Project Structure

```
apple-health-dashboard/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── config.py                 # Configuration settings
├── .gitignore               # Git ignore rules
├── src/
│   ├── __init__.py
│   ├── main.py              # Main pipeline orchestrator
│   ├── parser.py            # XML parsing (workouts, HR records)
│   ├── gpx_parser.py        # GPX file parsing for elevation
│   ├── analyzer.py          # Metrics calculations and aggregations
│   ├── excel_generator.py  # Excel report generation with charts
│   └── models.py            # Data models (Workout, HeartRateZone, etc.)
├── data/                     # Extracted Apple Health data (git-ignored)
└── output/                   # Generated Excel reports (git-ignored)
```

## Metrics Tracked

### Distance & Duration
- Total and average distance per ride
- Total and average ride duration
- Ride frequency (rides per month/year)
- Average speed trends

### Heart Rate
- Time spent in each heart rate zone (Zone 1-5)
- Average and max heart rate per ride
- Heart rate trends over time
- Cardiovascular fitness indicators

### Elevation & Climbing
- Total elevation gain per year/month
- Average elevation per ride
- Biggest climbs (top 10)
- Climbing rate and vertical feet trends

### Energy & Calories
- Total and average calories burned
- Energy expenditure per kilometer
- Effort level trends

## Performance Notes

- **Large Files**: The parser uses iterative XML parsing to handle large export files (1GB+) efficiently without loading everything into memory
- **Processing Time**: Parsing 299 workouts with 455K heart rate records takes approximately 1-2 minutes
- **Memory Usage**: Optimized for minimal memory consumption during parsing

## Current Limitations

- **Distance/Calories Data**: Some Apple Health exports may store distance and calorie data in separate Record elements rather than Workout attributes. If your report shows 0 km distance, the parser may need to be extended to extract this data from Record elements.
- **GPX Matching**: Only ~11% of workouts may have matching GPX files (34/299 in the test run). Older workouts or indoor cycling sessions won't have GPS data.
- **Heart Rate Coverage**: Most workouts should have HR data if you wore an Apple Watch during the ride.

## Troubleshooting

### "Export file not found" Error
- Check that `EXPORT_ZIP_PATH` in `config.py` points to the correct file
- Use the full absolute path to the zip file

### Distance Shows as 0.0 km
- This occurs when distance data is stored in Record elements rather than Workout attributes
- The workout duration and heart rate data should still be accurate
- Future enhancement: Parse distance from Record elements

### Low GPX Match Rate
- Only workouts with GPS tracking will have GPX files
- Indoor cycling or older workouts without GPS won't have elevation data
- This is expected behavior

### Memory Issues with Large Exports
- The parser is optimized for large files, but very large exports (multi-GB) may still cause issues
- Try filtering by date range in `config.py` to reduce data size

## Future Enhancements

- [ ] Parse distance/calories from Record elements in addition to Workout attributes
- [ ] Add power meter data support (if available)
- [ ] Include cadence and other cycling-specific metrics
- [ ] Generate trend analysis and fitness progression insights
- [ ] Add web-based dashboard option
- [ ] Support for other activity types (running, swimming, etc.)

## License

This project is open source and available for personal use.

## Acknowledgments

Built with:
- Python 3.x
- pandas for data analysis
- openpyxl for Excel generation
- gpxpy for GPX parsing

---

**Note**: This tool is designed for personal fitness tracking and analysis. All data processing happens locally on your machine. No data is uploaded or shared with external services.
