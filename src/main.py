"""Main script to run the Apple Health Dashboard pipeline."""

import sys
import zipfile
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from src.parser import (
    extract_workouts,
    extract_heart_rate_records,
    match_heart_rate_to_workouts,
    extract_distance_and_calories,
    enrich_workouts_with_distance_calories
)
from src.gpx_parser import enrich_workouts_with_elevation
from src.analyzer import (
    aggregate_by_year,
    aggregate_by_month,
    calculate_hr_zones,
    get_top_workouts,
    calculate_monthly_trends,
    calculate_yearly_trends,
    calculate_overall_stats
)
from src.excel_generator import ExcelGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_export_data():
    """Extract Apple Health export zip file to data directory."""
    logger.info("=" * 60)
    logger.info("Step 1: Extracting Apple Health export")
    logger.info("=" * 60)

    config.ensure_directories()

    export_zip = config.EXPORT_ZIP_PATH

    if not export_zip.exists():
        raise FileNotFoundError(f"Export file not found: {export_zip}")

    logger.info(f"Extracting {export_zip} to {config.DATA_DIR}")

    with zipfile.ZipFile(export_zip, 'r') as zip_ref:
        zip_ref.extractall(config.DATA_DIR)

    logger.info("Extraction complete")


def parse_workouts():
    """Parse cycling workouts from export.xml."""
    logger.info("=" * 60)
    logger.info("Step 2: Parsing cycling workouts")
    logger.info("=" * 60)

    export_xml = config.DATA_DIR / "apple_health_export" / config.EXPORT_XML_NAME

    if not export_xml.exists():
        raise FileNotFoundError(f"Export XML not found: {export_xml}")

    workouts = extract_workouts(export_xml, config.WORKOUT_TYPES)

    # Filter by date range if specified
    if config.START_DATE:
        workouts = [w for w in workouts if w.start_date >= config.START_DATE]
    if config.END_DATE:
        workouts = [w for w in workouts if w.start_date <= config.END_DATE]

    logger.info(f"Parsed {len(workouts)} cycling workouts")

    return workouts


def enrich_with_gpx(workouts):
    """Add elevation data from GPX files."""
    logger.info("=" * 60)
    logger.info("Step 3: Enriching with GPX elevation data")
    logger.info("=" * 60)

    gpx_dir = config.DATA_DIR / "apple_health_export" / config.WORKOUT_ROUTES_DIR

    enrich_workouts_with_elevation(workouts, gpx_dir)

    workouts_with_elevation = len([w for w in workouts if w.elevation_gain_m is not None])
    logger.info(f"Added elevation data to {workouts_with_elevation} workouts")


def enrich_with_distance_calories(workouts):
    """Add distance and calorie data from records."""
    logger.info("=" * 60)
    logger.info("Step 4: Enriching with distance and calorie data")
    logger.info("=" * 60)

    export_xml = config.DATA_DIR / "apple_health_export" / config.EXPORT_XML_NAME

    # Get date range from workouts to reduce memory usage
    if workouts:
        min_date = min(w.start_date for w in workouts)
        max_date = max(w.end_date for w in workouts)
        logger.info(f"Extracting distance/calorie data from {min_date.date()} to {max_date.date()}")

        distance_records, calorie_records = extract_distance_and_calories(
            export_xml, min_date, max_date
        )
        logger.info(f"Extracted {len(distance_records)} distance records and {len(calorie_records)} calorie records")

        enrich_workouts_with_distance_calories(workouts, distance_records, calorie_records)


def enrich_with_heart_rate(workouts):
    """Add heart rate data to workouts."""
    logger.info("=" * 60)
    logger.info("Step 5: Enriching with heart rate data")
    logger.info("=" * 60)

    export_xml = config.DATA_DIR / "apple_health_export" / config.EXPORT_XML_NAME

    # Get date range from workouts to reduce memory usage
    if workouts:
        min_date = min(w.start_date for w in workouts)
        max_date = max(w.end_date for w in workouts)
        logger.info(f"Extracting HR data from {min_date.date()} to {max_date.date()}")

        hr_records = extract_heart_rate_records(export_xml, min_date, max_date)
        logger.info(f"Extracted {len(hr_records)} heart rate records")

        match_heart_rate_to_workouts(workouts, hr_records)

        return hr_records
    else:
        return []


def analyze_data(workouts, hr_records):
    """Analyze workout data and calculate metrics."""
    logger.info("=" * 60)
    logger.info("Step 6: Analyzing data and calculating metrics")
    logger.info("=" * 60)

    # Calculate aggregations
    yearly_summaries = aggregate_by_year(workouts)
    monthly_summaries = aggregate_by_month(workouts)

    # Calculate trends
    yearly_trends = calculate_yearly_trends(yearly_summaries)
    monthly_trends = calculate_monthly_trends(monthly_summaries)

    # Calculate overall stats
    overall_stats = calculate_overall_stats(workouts)

    # Calculate HR zones
    hr_zones = calculate_hr_zones(
        workouts,
        hr_records,
        config.MAX_HEART_RATE,
        config.HR_ZONES
    )

    # Get top workouts
    top_climbs = get_top_workouts(workouts, metric="elevation_gain_m", top_n=10)

    logger.info("Analysis complete")

    return {
        'yearly_trends': yearly_trends,
        'monthly_trends': monthly_trends,
        'overall_stats': overall_stats,
        'hr_zones': hr_zones,
        'top_climbs': top_climbs
    }


def generate_excel_report(workouts, analysis_results):
    """Generate Excel report with charts."""
    logger.info("=" * 60)
    logger.info("Step 7: Generating Excel report")
    logger.info("=" * 60)

    output_file = config.OUTPUT_DIR / config.get_output_filename()

    generator = ExcelGenerator(output_file, config.EXCEL_THEME_COLORS)

    # Create worksheets
    generator.create_summary_sheet(analysis_results['overall_stats'])
    generator.create_yearly_trends_sheet(analysis_results['yearly_trends'])
    generator.create_monthly_activity_sheet(analysis_results['monthly_trends'])
    generator.create_hr_analysis_sheet(analysis_results['hr_zones'], workouts)
    generator.create_elevation_stats_sheet(
        analysis_results['yearly_trends'],
        analysis_results['top_climbs']
    )
    generator.create_raw_data_sheet(workouts)

    # Save workbook
    generator.save()

    logger.info(f"Excel report saved to: {output_file}")

    return output_file


def print_summary(overall_stats, output_file):
    """Print summary statistics to console."""
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    print("\n" + "=" * 60)
    print("Apple Health Cycling Dashboard - Summary")
    print("=" * 60)
    print(f"\nTotal Rides: {overall_stats['total_workouts']}")
    print(f"Total Distance: {overall_stats['total_distance_km']:.1f} km")
    print(f"Total Time: {overall_stats['total_duration_hours']:.1f} hours")
    print(f"Total Elevation Gain: {overall_stats['total_elevation_gain_m']:.0f} m")
    print(f"Total Calories: {overall_stats['total_calories']:.0f} kcal")
    print(f"\nAverage Distance: {overall_stats['avg_distance_km']:.1f} km")
    print(f"Average Duration: {overall_stats['avg_duration_minutes']:.1f} min")
    print(f"Average Speed: {overall_stats['avg_speed_kmh']:.1f} km/h")
    print(f"\nYears Active: {overall_stats['years_active']}")
    print(f"First Ride: {overall_stats['first_ride_date']}")
    print(f"Last Ride: {overall_stats['last_ride_date']}")
    print(f"\nWorkouts with Elevation Data: {overall_stats['workouts_with_elevation']}")
    print(f"Workouts with Heart Rate Data: {overall_stats['workouts_with_hr']}")

    if overall_stats.get('avg_heart_rate'):
        print(f"Average Heart Rate: {overall_stats['avg_heart_rate']:.1f} bpm")

    print("\n" + "=" * 60)
    print(f"Excel report saved to:")
    print(f"{output_file}")
    print("=" * 60 + "\n")


def main():
    """Run the complete pipeline."""
    try:
        logger.info("Starting Apple Health Dashboard pipeline")

        # Step 1: Extract export data
        extract_export_data()

        # Step 2: Parse workouts
        workouts = parse_workouts()

        if not workouts:
            logger.warning("No cycling workouts found!")
            return

        # Step 3: Enrich with GPX data
        enrich_with_gpx(workouts)

        # Step 4: Enrich with distance and calorie data
        enrich_with_distance_calories(workouts)

        # Step 5: Enrich with heart rate data
        hr_records = enrich_with_heart_rate(workouts)

        # Step 6: Analyze data
        analysis_results = analyze_data(workouts, hr_records)

        # Step 7: Generate Excel report
        output_file = generate_excel_report(workouts, analysis_results)

        # Print summary
        print_summary(analysis_results['overall_stats'], output_file)

        logger.info("Pipeline complete!")

    except Exception as e:
        logger.error(f"Error in pipeline: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
