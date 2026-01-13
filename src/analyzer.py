"""Analyze and aggregate workout data."""

from typing import List, Dict
from collections import defaultdict
import logging

from .models import Workout, WorkoutSummary, HeartRateZone, HeartRateRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def aggregate_by_year(workouts: List[Workout]) -> Dict[int, WorkoutSummary]:
    """Aggregate workouts by year."""
    logger.info("Aggregating workouts by year")

    yearly_workouts = defaultdict(list)

    for workout in workouts:
        yearly_workouts[workout.year].append(workout)

    # Create summaries
    summaries = {}
    for year, year_workouts in yearly_workouts.items():
        summary = WorkoutSummary(workouts=year_workouts)
        summary.calculate_stats()
        summaries[year] = summary

    return summaries


def aggregate_by_month(workouts: List[Workout]) -> Dict[tuple, WorkoutSummary]:
    """
    Aggregate workouts by year-month.

    Returns dict keyed by (year, month) tuples.
    """
    logger.info("Aggregating workouts by month")

    monthly_workouts = defaultdict(list)

    for workout in workouts:
        key = (workout.year, workout.month)
        monthly_workouts[key].append(workout)

    # Create summaries
    summaries = {}
    for (year, month), month_workouts in monthly_workouts.items():
        summary = WorkoutSummary(workouts=month_workouts)
        summary.calculate_stats()
        summaries[(year, month)] = summary

    return summaries


def calculate_hr_zones(
    workouts: List[Workout],
    hr_records: List[HeartRateRecord],
    max_heart_rate: int,
    zone_definitions: Dict[str, tuple]
) -> Dict[str, HeartRateZone]:
    """
    Calculate time spent in each heart rate zone across all workouts.

    zone_definitions: Dict mapping zone name to (min_pct, max_pct) tuples
    """
    logger.info("Calculating heart rate zones")

    # Convert percentage ranges to BPM ranges
    bpm_ranges = {}
    for zone_name, (min_pct, max_pct) in zone_definitions.items():
        min_bpm = int(max_heart_rate * min_pct)
        max_bpm = int(max_heart_rate * max_pct) if max_pct < 1.0 else 999
        bpm_ranges[zone_name] = (min_bpm, max_bpm)

    # Initialize zone objects
    hr_zones = {}
    for zone_name, (min_bpm, max_bpm) in bpm_ranges.items():
        hr_zones[zone_name] = HeartRateZone(
            zone_name=zone_name,
            min_bpm=min_bpm,
            max_bpm=max_bpm
        )

    # Calculate time in each zone
    from .parser import calculate_hr_zone_time

    for workout in workouts:
        zone_times = calculate_hr_zone_time(hr_records, workout, bpm_ranges)

        for zone_name, time_minutes in zone_times.items():
            hr_zones[zone_name].time_minutes += time_minutes

    return hr_zones


def get_top_workouts(
    workouts: List[Workout],
    metric: str = "elevation_gain_ft",
    top_n: int = 10
) -> List[Workout]:
    """
    Get top N workouts by a specific metric.

    metric: One of 'distance_miles', 'duration_minutes', 'elevation_gain_ft', 'calories'
    """
    # Filter out workouts without the metric
    if metric == "elevation_gain_ft":
        filtered = [w for w in workouts if w.elevation_gain_ft is not None]
    else:
        filtered = workouts

    # Sort and return top N
    sorted_workouts = sorted(
        filtered,
        key=lambda w: getattr(w, metric, 0),
        reverse=True
    )

    return sorted_workouts[:top_n]


def calculate_monthly_trends(
    monthly_summaries: Dict[tuple, WorkoutSummary]
) -> List[Dict]:
    """
    Convert monthly summaries to a list suitable for charts/tables.

    Returns list of dicts with keys: year, month, total_distance_miles, total_workouts, etc.
    """
    trends = []

    for (year, month), summary in sorted(monthly_summaries.items()):
        trends.append({
            'year': year,
            'month': month,
            'month_name': f"{year}-{month:02d}",
            'total_workouts': summary.total_workouts,
            'total_distance_miles': summary.total_distance_miles,
            'total_duration_hours': summary.total_duration_minutes / 60.0,
            'total_calories': summary.total_calories,
            'total_elevation_gain_ft': summary.total_elevation_gain_ft,
            'avg_distance_miles': summary.avg_distance_miles,
            'avg_duration_minutes': summary.avg_duration_minutes,
            'avg_speed_mph': summary.avg_speed_mph
        })

    return trends


def calculate_yearly_trends(
    yearly_summaries: Dict[int, WorkoutSummary]
) -> List[Dict]:
    """
    Convert yearly summaries to a list suitable for charts/tables.

    Returns list of dicts with keys: year, total_distance_miles, total_workouts, etc.
    """
    trends = []

    for year, summary in sorted(yearly_summaries.items()):
        trends.append({
            'year': year,
            'total_workouts': summary.total_workouts,
            'total_distance_miles': summary.total_distance_miles,
            'total_duration_hours': summary.total_duration_minutes / 60.0,
            'total_calories': summary.total_calories,
            'total_elevation_gain_ft': summary.total_elevation_gain_ft,
            'avg_distance_miles': summary.avg_distance_miles,
            'avg_duration_minutes': summary.avg_duration_minutes,
            'avg_speed_mph': summary.avg_speed_mph,
            'avg_elevation_gain_ft': summary.avg_elevation_gain_ft,
            'max_distance_miles': summary.max_distance_miles,
            'max_elevation_gain_ft': summary.max_elevation_gain_ft
        })

    return trends


def calculate_overall_stats(workouts: List[Workout]) -> Dict:
    """Calculate overall statistics across all workouts."""
    logger.info("Calculating overall statistics")

    if not workouts:
        return {}

    summary = WorkoutSummary(workouts=workouts)
    summary.calculate_stats()

    # Calculate additional stats
    years_active = len(set(w.year for w in workouts))
    first_ride = min(w.start_date for w in workouts)
    last_ride = max(w.start_date for w in workouts)

    workouts_with_hr = [w for w in workouts if w.avg_heart_rate is not None]
    avg_heart_rate = None
    if workouts_with_hr:
        avg_heart_rate = sum(w.avg_heart_rate for w in workouts_with_hr) / len(workouts_with_hr)

    return {
        'total_workouts': summary.total_workouts,
        'total_distance_miles': summary.total_distance_miles,
        'total_duration_hours': summary.total_duration_minutes / 60.0,
        'total_calories': summary.total_calories,
        'total_elevation_gain_ft': summary.total_elevation_gain_ft,
        'avg_distance_miles': summary.avg_distance_miles,
        'avg_duration_minutes': summary.avg_duration_minutes,
        'avg_speed_mph': summary.avg_speed_mph,
        'avg_elevation_gain_ft': summary.avg_elevation_gain_ft,
        'max_distance_miles': summary.max_distance_miles,
        'max_duration_minutes': summary.max_duration_minutes,
        'max_elevation_gain_ft': summary.max_elevation_gain_ft,
        'years_active': years_active,
        'first_ride_date': first_ride.strftime("%Y-%m-%d"),
        'last_ride_date': last_ride.strftime("%Y-%m-%d"),
        'avg_heart_rate': avg_heart_rate,
        'workouts_with_elevation': len([w for w in workouts if w.elevation_gain_ft is not None]),
        'workouts_with_hr': len(workouts_with_hr)
    }
