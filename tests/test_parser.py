"""Tests for parser module."""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from src.parser import (
    parse_datetime,
    extract_workouts,
    extract_heart_rate_records,
    match_heart_rate_to_workouts,
    calculate_hr_zone_time,
    extract_distance_and_calories,
    enrich_workouts_with_distance_calories
)
from src.models import Workout, HeartRateRecord


class TestParseDatetime:
    """Tests for parse_datetime function."""

    def test_parse_basic_format(self):
        """Test parsing basic datetime format."""
        result = parse_datetime("2025-01-11 12:30:45")
        assert result == datetime(2025, 1, 11, 12, 30, 45)

    def test_parse_with_timezone(self):
        """Test parsing datetime with timezone (timezone is stripped)."""
        result = parse_datetime("2025-01-11 12:30:45 -0800")
        assert result == datetime(2025, 1, 11, 12, 30, 45)

    def test_parse_with_positive_timezone(self):
        """Test parsing datetime with positive timezone."""
        result = parse_datetime("2025-01-11 12:30:45 +0500")
        assert result == datetime(2025, 1, 11, 12, 30, 45)

    def test_parse_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            parse_datetime("invalid-date")


class TestExtractWorkouts:
    """Tests for extract_workouts function."""

    @pytest.fixture
    def sample_xml_file(self):
        """Create a temporary XML file with sample workout data."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeCycling"
             duration="15.5"
             durationUnit="min"
             totalDistance="5.2"
             distanceUnit="mi"
             totalEnergyBurned="250"
             sourceName="Apple Watch"
             startDate="2025-01-11 10:00:00 -0800"
             endDate="2025-01-11 10:15:30 -0800">
    </Workout>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning"
             duration="30.0"
             durationUnit="min"
             totalDistance="5.0"
             distanceUnit="mi"
             sourceName="Apple Watch"
             startDate="2025-01-11 11:00:00 -0800"
             endDate="2025-01-11 11:30:00 -0800">
    </Workout>
    <Workout workoutActivityType="HKWorkoutActivityTypeCycling"
             duration="45.2"
             durationUnit="min"
             totalDistance="20.0"
             distanceUnit="km"
             totalEnergyBurned="500"
             sourceName="iPhone"
             startDate="2025-01-12 14:00:00 -0800"
             endDate="2025-01-12 14:45:12 -0800">
    </Workout>
</HealthData>
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        temp_path.unlink()

    def test_extract_cycling_workouts(self, sample_xml_file):
        """Test extracting cycling workouts."""
        workout_types = ["HKWorkoutActivityTypeCycling"]
        workouts = extract_workouts(sample_xml_file, workout_types)

        assert len(workouts) == 2
        assert all(w.workout_type == "HKWorkoutActivityTypeCycling" for w in workouts)

    def test_workout_data_accuracy(self, sample_xml_file):
        """Test that workout data is parsed correctly."""
        workout_types = ["HKWorkoutActivityTypeCycling"]
        workouts = extract_workouts(sample_xml_file, workout_types)

        # Check first workout
        w1 = workouts[0]
        assert w1.duration_minutes == 15.5
        assert w1.distance_miles == 5.2
        assert w1.calories == 250
        assert w1.source_name == "Apple Watch"
        assert w1.start_date == datetime(2025, 1, 11, 10, 0, 0)

    def test_km_to_miles_conversion(self, sample_xml_file):
        """Test that kilometers are converted to miles."""
        workout_types = ["HKWorkoutActivityTypeCycling"]
        workouts = extract_workouts(sample_xml_file, workout_types)

        # Second workout has distance in km, should be converted to miles
        w2 = workouts[1]
        expected_miles = 20.0 / 1.60934
        assert abs(w2.distance_miles - expected_miles) < 0.01

    def test_exclude_non_cycling_workouts(self, sample_xml_file):
        """Test that non-cycling workouts are excluded."""
        workout_types = ["HKWorkoutActivityTypeCycling"]
        workouts = extract_workouts(sample_xml_file, workout_types)

        # Should not include running workout
        assert all(w.workout_type != "HKWorkoutActivityTypeRunning" for w in workouts)

    def test_duration_calculated_from_dates_if_missing(self):
        """Test duration is calculated from start/end dates when not provided."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeCycling"
             sourceName="Apple Watch"
             startDate="2025-01-11 10:00:00 -0800"
             endDate="2025-01-11 10:30:00 -0800">
    </Workout>
</HealthData>
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        try:
            workout_types = ["HKWorkoutActivityTypeCycling"]
            workouts = extract_workouts(temp_path, workout_types)

            assert len(workouts) == 1
            assert workouts[0].duration_minutes == 30.0
        finally:
            temp_path.unlink()


class TestExtractHeartRateRecords:
    """Tests for extract_heart_rate_records function."""

    @pytest.fixture
    def sample_hr_xml_file(self):
        """Create a temporary XML file with heart rate records."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Record type="HKQuantityTypeIdentifierHeartRate"
            value="120"
            unit="count/min"
            sourceName="Apple Watch"
            startDate="2025-01-11 10:05:00 -0800"
            endDate="2025-01-11 10:05:00 -0800">
    </Record>
    <Record type="HKQuantityTypeIdentifierHeartRate"
            value="135"
            unit="count/min"
            sourceName="Apple Watch"
            startDate="2025-01-11 10:10:00 -0800"
            endDate="2025-01-11 10:10:00 -0800">
    </Record>
    <Record type="HKQuantityTypeIdentifierDistanceCycling"
            value="1.5"
            unit="km"
            startDate="2025-01-11 10:05:00 -0800"
            endDate="2025-01-11 10:05:00 -0800">
    </Record>
    <Record type="HKQuantityTypeIdentifierHeartRate"
            value="142"
            unit="count/min"
            sourceName="Apple Watch"
            startDate="2025-01-11 10:15:00 -0800"
            endDate="2025-01-11 10:15:00 -0800">
    </Record>
</HealthData>
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink()

    def test_extract_hr_records(self, sample_hr_xml_file):
        """Test extracting heart rate records."""
        records = extract_heart_rate_records(sample_hr_xml_file)

        assert len(records) == 3
        assert all(isinstance(r, HeartRateRecord) for r in records)

    def test_hr_record_values(self, sample_hr_xml_file):
        """Test that HR values are correct."""
        records = extract_heart_rate_records(sample_hr_xml_file)

        assert records[0].bpm == 120
        assert records[1].bpm == 135
        assert records[2].bpm == 142

    def test_hr_date_filtering(self, sample_hr_xml_file):
        """Test filtering HR records by date range."""
        start_date = datetime(2025, 1, 11, 10, 8, 0)
        end_date = datetime(2025, 1, 11, 10, 12, 0)

        records = extract_heart_rate_records(sample_hr_xml_file, start_date, end_date)

        # Should only include the 10:10:00 record
        assert len(records) == 1
        assert records[0].bpm == 135


class TestMatchHeartRateToWorkouts:
    """Tests for match_heart_rate_to_workouts function."""

    def test_match_hr_to_workouts(self):
        """Test matching heart rate records to workouts."""
        workout = Workout(
            start_date=datetime(2025, 1, 11, 10, 0, 0),
            end_date=datetime(2025, 1, 11, 10, 30, 0),
            duration_minutes=30,
            distance_miles=5.0,
            calories=250,
            source_name="Apple Watch"
        )

        hr_records = [
            HeartRateRecord(datetime(2025, 1, 11, 10, 5, 0), 120),
            HeartRateRecord(datetime(2025, 1, 11, 10, 15, 0), 135),
            HeartRateRecord(datetime(2025, 1, 11, 10, 25, 0), 140),
            HeartRateRecord(datetime(2025, 1, 11, 10, 35, 0), 110),  # Outside workout
        ]

        match_heart_rate_to_workouts([workout], hr_records)

        assert abs(workout.avg_heart_rate - 131.67) < 0.01  # (120 + 135 + 140) / 3
        assert workout.max_heart_rate == 140
        assert workout.min_heart_rate == 120

    def test_no_hr_match(self):
        """Test workout with no matching HR records."""
        workout = Workout(
            start_date=datetime(2025, 1, 11, 10, 0, 0),
            end_date=datetime(2025, 1, 11, 10, 30, 0),
            duration_minutes=30,
            distance_miles=5.0,
            calories=250,
            source_name="Apple Watch"
        )

        hr_records = [
            HeartRateRecord(datetime(2025, 1, 11, 11, 0, 0), 120),  # After workout
        ]

        match_heart_rate_to_workouts([workout], hr_records)

        assert workout.avg_heart_rate is None
        assert workout.max_heart_rate is None
        assert workout.min_heart_rate is None


class TestCalculateHrZoneTime:
    """Tests for calculate_hr_zone_time function."""

    def test_hr_zone_calculation(self):
        """Test calculating time in heart rate zones."""
        workout = Workout(
            start_date=datetime(2025, 1, 11, 10, 0, 0),
            end_date=datetime(2025, 1, 11, 10, 30, 0),
            duration_minutes=30,
            distance_miles=5.0,
            calories=250,
            source_name="Apple Watch"
        )

        hr_records = [
            HeartRateRecord(datetime(2025, 1, 11, 10, 0, 0), 100),  # Zone 2
            HeartRateRecord(datetime(2025, 1, 11, 10, 10, 0), 130),  # Zone 3
            HeartRateRecord(datetime(2025, 1, 11, 10, 20, 0), 160),  # Zone 4
            HeartRateRecord(datetime(2025, 1, 11, 10, 30, 0), 140),  # End
        ]

        zone_ranges = {
            "Zone 2": (90, 120),
            "Zone 3": (120, 150),
            "Zone 4": (150, 180),
        }

        zone_times = calculate_hr_zone_time(hr_records, workout, zone_ranges)

        assert zone_times["Zone 2"] == 10.0  # 10 minutes
        assert zone_times["Zone 3"] == 10.0  # 10 minutes
        assert zone_times["Zone 4"] == 10.0  # 10 minutes

    def test_empty_hr_records(self):
        """Test with no HR records."""
        workout = Workout(
            start_date=datetime(2025, 1, 11, 10, 0, 0),
            end_date=datetime(2025, 1, 11, 10, 30, 0),
            duration_minutes=30,
            distance_miles=5.0,
            calories=250,
            source_name="Apple Watch"
        )

        zone_ranges = {
            "Zone 2": (90, 120),
            "Zone 3": (120, 150),
        }

        zone_times = calculate_hr_zone_time([], workout, zone_ranges)

        assert zone_times["Zone 2"] == 0
        assert zone_times["Zone 3"] == 0


class TestExtractDistanceAndCalories:
    """Tests for extract_distance_and_calories function."""

    @pytest.fixture
    def sample_distance_calories_xml(self):
        """Create a temporary XML file with distance and calorie records."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Record type="HKQuantityTypeIdentifierDistanceCycling"
            value="1.5"
            unit="mi"
            startDate="2025-01-11 10:05:00 -0800"
            endDate="2025-01-11 10:05:00 -0800">
    </Record>
    <Record type="HKQuantityTypeIdentifierDistanceCycling"
            value="2.3"
            unit="mi"
            startDate="2025-01-11 10:10:00 -0800"
            endDate="2025-01-11 10:10:00 -0800">
    </Record>
    <Record type="HKQuantityTypeIdentifierDistanceCycling"
            value="3.0"
            unit="km"
            startDate="2025-01-11 10:15:00 -0800"
            endDate="2025-01-11 10:15:00 -0800">
    </Record>
    <Record type="HKQuantityTypeIdentifierActiveEnergyBurned"
            value="50"
            unit="Cal"
            startDate="2025-01-11 10:05:00 -0800"
            endDate="2025-01-11 10:05:00 -0800">
    </Record>
    <Record type="HKQuantityTypeIdentifierActiveEnergyBurned"
            value="75"
            unit="Cal"
            startDate="2025-01-11 10:10:00 -0800"
            endDate="2025-01-11 10:10:00 -0800">
    </Record>
    <Record type="HKQuantityTypeIdentifierHeartRate"
            value="120"
            unit="count/min"
            startDate="2025-01-11 10:05:00 -0800"
            endDate="2025-01-11 10:05:00 -0800">
    </Record>
</HealthData>
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink()

    def test_extract_distance_records(self, sample_distance_calories_xml):
        """Test extracting distance records."""
        distance_records, calorie_records = extract_distance_and_calories(
            sample_distance_calories_xml
        )

        assert len(distance_records) == 3
        assert len(calorie_records) == 2

    def test_distance_unit_conversion(self, sample_distance_calories_xml):
        """Test that km are converted to miles."""
        distance_records, _ = extract_distance_and_calories(
            sample_distance_calories_xml
        )

        # Find the record that was in km
        km_record = None
        for timestamp, distance in distance_records.items():
            if timestamp == datetime(2025, 1, 11, 10, 15, 0):
                km_record = distance
                break

        expected_miles = 3.0 / 1.60934
        assert abs(km_record - expected_miles) < 0.01

    def test_calorie_values(self, sample_distance_calories_xml):
        """Test calorie values are extracted correctly."""
        _, calorie_records = extract_distance_and_calories(
            sample_distance_calories_xml
        )

        total_calories = sum(calorie_records.values())
        assert total_calories == 125  # 50 + 75


class TestEnrichWorkoutsWithDistanceCalories:
    """Tests for enrich_workouts_with_distance_calories function."""

    def test_enrich_with_distance_calories(self):
        """Test enriching workouts with distance and calorie data."""
        workout = Workout(
            start_date=datetime(2025, 1, 11, 10, 0, 0),
            end_date=datetime(2025, 1, 11, 10, 30, 0),
            duration_minutes=30,
            distance_miles=0,
            calories=0,
            source_name="Apple Watch"
        )

        distance_records = {
            datetime(2025, 1, 11, 10, 5, 0): 1.5,
            datetime(2025, 1, 11, 10, 15, 0): 2.3,
            datetime(2025, 1, 11, 10, 25, 0): 1.2,
            datetime(2025, 1, 11, 10, 35, 0): 1.0,  # Outside workout
        }

        calorie_records = {
            datetime(2025, 1, 11, 10, 5, 0): 50,
            datetime(2025, 1, 11, 10, 15, 0): 75,
            datetime(2025, 1, 11, 10, 25, 0): 60,
            datetime(2025, 1, 11, 10, 35, 0): 40,  # Outside workout
        }

        enrich_workouts_with_distance_calories(
            [workout], distance_records, calorie_records
        )

        assert workout.distance_miles == 5.0  # 1.5 + 2.3 + 1.2
        assert workout.calories == 185  # 50 + 75 + 60

    def test_no_matching_records(self):
        """Test workout with no matching distance/calorie records."""
        workout = Workout(
            start_date=datetime(2025, 1, 11, 10, 0, 0),
            end_date=datetime(2025, 1, 11, 10, 30, 0),
            duration_minutes=30,
            distance_miles=0,
            calories=0,
            source_name="Apple Watch"
        )

        distance_records = {
            datetime(2025, 1, 11, 11, 0, 0): 5.0,  # After workout
        }

        calorie_records = {
            datetime(2025, 1, 11, 11, 0, 0): 100,  # After workout
        }

        enrich_workouts_with_distance_calories(
            [workout], distance_records, calorie_records
        )

        # Should remain 0 since no records match
        assert workout.distance_miles == 0
        assert workout.calories == 0
