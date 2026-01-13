"""Parse GPX files for elevation and route data."""

import gpxpy
import gpxpy.gpx
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import logging

from .models import Workout

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_gpx_file(gpx_file: Path) -> Tuple[float, float, float]:
    """
    Parse a GPX file and extract elevation metrics.

    Returns:
        Tuple of (elevation_gain_m, elevation_loss_m, max_elevation_m)
    """
    try:
        with open(gpx_file, 'r') as f:
            gpx = gpxpy.parse(f)

        elevation_gain = 0
        elevation_loss = 0
        max_elevation = float('-inf')
        prev_elevation = None

        # Iterate through all track points
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if point.elevation is not None:
                        elevation = point.elevation

                        # Track max elevation
                        if elevation > max_elevation:
                            max_elevation = elevation

                        # Calculate gain/loss
                        if prev_elevation is not None:
                            diff = elevation - prev_elevation
                            if diff > 0:
                                elevation_gain += diff
                            else:
                                elevation_loss += abs(diff)

                        prev_elevation = elevation

        # If no elevation data found
        if max_elevation == float('-inf'):
            max_elevation = 0

        return elevation_gain, elevation_loss, max_elevation

    except Exception as e:
        logger.error(f"Error parsing GPX file {gpx_file}: {e}")
        return 0, 0, 0


def extract_gpx_timestamp(gpx_file: Path) -> Optional[datetime]:
    """
    Extract the timestamp from a GPX filename.

    Apple Health GPX files are named like: route_2025-01-11_9.30am.gpx
    """
    try:
        filename = gpx_file.stem  # Remove .gpx extension

        # Parse format: route_YYYY-MM-DD_H.MMam/pm
        parts = filename.split('_')
        if len(parts) >= 3:
            date_str = parts[1]  # YYYY-MM-DD
            time_str = parts[2]  # H.MMam or H.MMpm

            # Parse date
            year, month, day = map(int, date_str.split('-'))

            # Parse time
            time_str = time_str.lower()
            is_pm = 'pm' in time_str
            time_str = time_str.replace('am', '').replace('pm', '')

            if '.' in time_str:
                hour_str, minute_str = time_str.split('.')
                hour = int(hour_str)
                minute = int(minute_str)

                # Convert to 24-hour format
                if is_pm and hour != 12:
                    hour += 12
                elif not is_pm and hour == 12:
                    hour = 0

                return datetime(year, month, day, hour, minute)

    except Exception as e:
        logger.error(f"Error extracting timestamp from {gpx_file}: {e}")

    return None


def match_workout_to_gpx(
    workout: Workout,
    gpx_dir: Path,
    time_tolerance_minutes: int = 30
) -> Optional[Path]:
    """
    Find the GPX file that matches a workout based on timestamp.

    Returns the path to the matching GPX file, or None if no match found.
    """
    if not gpx_dir.exists():
        return None

    # Get all GPX files
    gpx_files = list(gpx_dir.glob("*.gpx"))

    best_match = None
    best_time_diff = timedelta(minutes=time_tolerance_minutes)

    for gpx_file in gpx_files:
        gpx_timestamp = extract_gpx_timestamp(gpx_file)

        if gpx_timestamp:
            # Calculate time difference
            time_diff = abs(workout.start_date - gpx_timestamp)

            # Check if this is a better match
            if time_diff < best_time_diff:
                best_match = gpx_file
                best_time_diff = time_diff

    return best_match


def enrich_workouts_with_elevation(
    workouts: List[Workout],
    gpx_dir: Path
) -> None:
    """
    Match workouts to GPX files and add elevation data.

    Modifies workouts in place.
    """
    logger.info(f"Matching workouts to GPX files in {gpx_dir}")

    if not gpx_dir.exists():
        logger.warning(f"GPX directory does not exist: {gpx_dir}")
        return

    matched_count = 0

    for workout in workouts:
        # Find matching GPX file
        gpx_file = match_workout_to_gpx(workout, gpx_dir)

        if gpx_file:
            # Parse elevation data
            elevation_gain, elevation_loss, max_elevation = parse_gpx_file(gpx_file)

            # Update workout
            workout.gpx_file = gpx_file.name
            workout.elevation_gain_m = elevation_gain
            workout.elevation_loss_m = elevation_loss
            workout.max_elevation_m = max_elevation

            matched_count += 1

    logger.info(f"Matched {matched_count}/{len(workouts)} workouts to GPX files")
