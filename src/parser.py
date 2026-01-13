"""Parse Apple Health export XML files."""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Tuple
from pathlib import Path
import logging

from .models import Workout, HeartRateRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_datetime(date_str: str) -> datetime:
    """Parse Apple Health date string to datetime object."""
    # Apple Health uses format: 2025-01-11 12:27:45 -0800
    try:
        # Try with timezone
        if '+' in date_str or date_str.count('-') > 2:
            # Remove timezone for simplicity (we care about local time)
            date_part = date_str.rsplit(' ', 1)[0]
            return datetime.strptime(date_part, "%Y-%m-%d %H:%M:%S")
        else:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        logger.error(f"Error parsing date '{date_str}': {e}")
        raise


def extract_workouts(xml_file: Path, workout_types: List[str]) -> List[Workout]:
    """
    Extract cycling workouts from export.xml.

    Uses iterative parsing to handle large files efficiently.
    """
    logger.info(f"Parsing workouts from {xml_file}")
    workouts = []

    # Use iterparse for memory efficiency with large files
    context = ET.iterparse(xml_file, events=("start", "end"))
    context = iter(context)

    event, root = next(context)

    workout_count = 0
    cycling_count = 0

    for event, elem in context:
        if event == "end" and elem.tag == "Workout":
            workout_count += 1

            # Check if this is a cycling workout
            workout_type = elem.get("workoutActivityType", "")
            if workout_type in workout_types:
                cycling_count += 1

                try:
                    # Extract workout attributes
                    start_date = parse_datetime(elem.get("startDate"))
                    end_date = parse_datetime(elem.get("endDate"))

                    # Calculate duration in minutes
                    duration = (end_date - start_date).total_seconds() / 60.0
                    if elem.get("duration"):
                        # Use provided duration if available (more accurate)
                        # Duration is already in minutes according to durationUnit="min"
                        duration = float(elem.get("duration"))

                    # Extract distance (in km)
                    distance_km = 0
                    distance_unit = elem.get("distanceUnit", "")
                    if elem.get("totalDistance"):
                        distance_km = float(elem.get("totalDistance"))
                        # Convert miles to km if necessary
                        if distance_unit == "mi":
                            distance_km *= 1.60934

                    # Extract calories
                    calories = 0
                    if elem.get("totalEnergyBurned"):
                        calories = float(elem.get("totalEnergyBurned"))

                    # Extract source
                    source_name = elem.get("sourceName", "Unknown")

                    # Create workout object
                    workout = Workout(
                        start_date=start_date,
                        end_date=end_date,
                        duration_minutes=duration,
                        distance_km=distance_km,
                        calories=calories,
                        source_name=source_name,
                        workout_type=workout_type
                    )

                    workouts.append(workout)

                except Exception as e:
                    logger.error(f"Error parsing workout: {e}")
                    continue

            # Clear element to save memory
            elem.clear()

        # Periodically clear the root to prevent memory buildup
        if event == "end" and workout_count % 1000 == 0:
            root.clear()

    logger.info(f"Found {cycling_count} cycling workouts out of {workout_count} total workouts")
    return workouts


def extract_heart_rate_records(
    xml_file: Path,
    start_date: datetime = None,
    end_date: datetime = None
) -> List[HeartRateRecord]:
    """
    Extract heart rate records from export.xml.

    Optionally filter by date range to reduce memory usage.
    """
    logger.info(f"Parsing heart rate records from {xml_file}")
    records = []

    context = ET.iterparse(xml_file, events=("start", "end"))
    context = iter(context)

    event, root = next(context)

    record_count = 0
    hr_count = 0

    for event, elem in context:
        if event == "end" and elem.tag == "Record":
            record_count += 1

            # Check if this is a heart rate record
            record_type = elem.get("type", "")
            if record_type == "HKQuantityTypeIdentifierHeartRate":
                try:
                    timestamp = parse_datetime(elem.get("startDate"))

                    # Filter by date range if provided
                    if start_date and timestamp < start_date:
                        elem.clear()
                        continue
                    if end_date and timestamp > end_date:
                        elem.clear()
                        continue

                    # Extract BPM value
                    bpm = float(elem.get("value", 0))
                    source_name = elem.get("sourceName", "")

                    record = HeartRateRecord(
                        timestamp=timestamp,
                        bpm=bpm,
                        source_name=source_name
                    )

                    records.append(record)
                    hr_count += 1

                except Exception as e:
                    logger.error(f"Error parsing heart rate record: {e}")
                    continue

            elem.clear()

        # Periodically clear the root
        if event == "end" and record_count % 10000 == 0:
            root.clear()
            if hr_count % 10000 == 0 and hr_count > 0:
                logger.info(f"Processed {record_count} records, found {hr_count} HR records")

    logger.info(f"Found {hr_count} heart rate records out of {record_count} total records")
    return records


def match_heart_rate_to_workouts(
    workouts: List[Workout],
    hr_records: List[HeartRateRecord]
) -> None:
    """
    Match heart rate records to workouts and calculate avg/min/max HR.

    Modifies workouts in place.
    """
    logger.info("Matching heart rate data to workouts")

    # Sort HR records by timestamp for efficient matching
    hr_records_sorted = sorted(hr_records, key=lambda r: r.timestamp)

    for workout in workouts:
        # Find HR records within this workout's time window
        workout_hrs = [
            hr for hr in hr_records_sorted
            if workout.start_date <= hr.timestamp <= workout.end_date
        ]

        if workout_hrs:
            bpms = [hr.bpm for hr in workout_hrs]
            workout.avg_heart_rate = sum(bpms) / len(bpms)
            workout.max_heart_rate = max(bpms)
            workout.min_heart_rate = min(bpms)

    workouts_with_hr = sum(1 for w in workouts if w.avg_heart_rate is not None)
    logger.info(f"Matched heart rate data to {workouts_with_hr}/{len(workouts)} workouts")


def calculate_hr_zone_time(
    hr_records: List[HeartRateRecord],
    workout: Workout,
    zone_ranges: Dict[str, Tuple[int, int]]
) -> Dict[str, float]:
    """
    Calculate time spent in each heart rate zone for a workout.

    Returns dict mapping zone name to minutes spent in that zone.
    """
    # Filter HR records for this workout
    workout_hrs = [
        hr for hr in hr_records
        if workout.start_date <= hr.timestamp <= workout.end_date
    ]

    if not workout_hrs:
        return {zone: 0 for zone in zone_ranges.keys()}

    # Sort by timestamp
    workout_hrs.sort(key=lambda r: r.timestamp)

    zone_times = {zone: 0 for zone in zone_ranges.keys()}

    # Calculate time between consecutive HR measurements
    for i in range(len(workout_hrs) - 1):
        current_hr = workout_hrs[i]
        next_hr = workout_hrs[i + 1]

        # Time interval in minutes
        time_diff = (next_hr.timestamp - current_hr.timestamp).total_seconds() / 60.0

        # Determine which zone this HR falls into
        for zone_name, (min_bpm, max_bpm) in zone_ranges.items():
            if min_bpm <= current_hr.bpm < max_bpm:
                zone_times[zone_name] += time_diff
                break

    return zone_times


def extract_distance_and_calories(
    xml_file: Path,
    start_date: datetime = None,
    end_date: datetime = None
) -> Tuple[Dict[datetime, float], Dict[datetime, float]]:
    """
    Extract distance cycling and active energy records from export.xml.

    Returns two dicts mapping timestamp to value for distance and calories.
    """
    logger.info(f"Parsing distance and calorie records from {xml_file}")

    distance_records = {}
    calorie_records = {}

    context = ET.iterparse(xml_file, events=("start", "end"))
    context = iter(context)

    event, root = next(context)

    record_count = 0
    distance_count = 0
    calorie_count = 0

    for event, elem in context:
        if event == "end" and elem.tag == "Record":
            record_count += 1

            record_type = elem.get("type", "")

            # Check if this is a distance cycling record
            if record_type == "HKQuantityTypeIdentifierDistanceCycling":
                try:
                    timestamp = parse_datetime(elem.get("startDate"))

                    # Filter by date range if provided
                    if start_date and timestamp < start_date:
                        elem.clear()
                        continue
                    if end_date and timestamp > end_date:
                        elem.clear()
                        continue

                    # Extract distance value (in km)
                    value = float(elem.get("value", 0))
                    unit = elem.get("unit", "")

                    # Convert to km if necessary
                    if unit == "mi":
                        value *= 1.60934
                    elif unit == "m":
                        value /= 1000.0

                    distance_records[timestamp] = value
                    distance_count += 1

                except Exception as e:
                    logger.error(f"Error parsing distance record: {e}")

            # Check if this is an active energy burned record
            elif record_type == "HKQuantityTypeIdentifierActiveEnergyBurned":
                try:
                    timestamp = parse_datetime(elem.get("startDate"))

                    # Filter by date range if provided
                    if start_date and timestamp < start_date:
                        elem.clear()
                        continue
                    if end_date and timestamp > end_date:
                        elem.clear()
                        continue

                    # Extract calorie value
                    value = float(elem.get("value", 0))
                    unit = elem.get("unit", "")

                    # Convert to kcal if necessary
                    if unit == "Cal":  # Already in kcal
                        pass
                    elif unit == "cal":  # Convert from cal to kcal
                        value /= 1000.0

                    calorie_records[timestamp] = value
                    calorie_count += 1

                except Exception as e:
                    logger.error(f"Error parsing calorie record: {e}")

            elem.clear()

        # Periodically clear the root
        if event == "end" and record_count % 10000 == 0:
            root.clear()
            if (distance_count + calorie_count) % 10000 == 0 and (distance_count + calorie_count) > 0:
                logger.info(f"Processed {record_count} records, found {distance_count} distance + {calorie_count} calorie records")

    logger.info(f"Found {distance_count} distance records and {calorie_count} calorie records out of {record_count} total records")
    return distance_records, calorie_records


def enrich_workouts_with_distance_calories(
    workouts: List[Workout],
    distance_records: Dict[datetime, float],
    calorie_records: Dict[datetime, float]
) -> None:
    """
    Match distance and calorie records to workouts and sum up values.

    Modifies workouts in place.
    """
    logger.info("Matching distance and calorie data to workouts")

    for workout in workouts:
        # Sum up distance records within this workout's time window
        workout_distance = sum(
            dist for timestamp, dist in distance_records.items()
            if workout.start_date <= timestamp <= workout.end_date
        )

        # Sum up calorie records within this workout's time window
        workout_calories = sum(
            cal for timestamp, cal in calorie_records.items()
            if workout.start_date <= timestamp <= workout.end_date
        )

        # Only update if we found data (don't overwrite existing data with 0)
        if workout_distance > 0:
            workout.distance_km = workout_distance
        if workout_calories > 0:
            workout.calories = workout_calories

    workouts_with_distance = sum(1 for w in workouts if w.distance_km > 0)
    workouts_with_calories = sum(1 for w in workouts if w.calories > 0)

    logger.info(f"Matched distance data to {workouts_with_distance}/{len(workouts)} workouts")
    logger.info(f"Matched calorie data to {workouts_with_calories}/{len(workouts)} workouts")
