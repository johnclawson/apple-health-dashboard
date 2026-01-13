"""Data models for Apple Health Dashboard."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class Workout:
    """Represents a cycling workout from Apple Health."""

    start_date: datetime
    end_date: datetime
    duration_minutes: float
    distance_km: float
    calories: float
    source_name: str
    workout_type: str = "Cycling"

    # Optional fields populated later
    gpx_file: Optional[str] = None
    elevation_gain_m: Optional[float] = None
    elevation_loss_m: Optional[float] = None
    max_elevation_m: Optional[float] = None

    # Heart rate data
    avg_heart_rate: Optional[float] = None
    max_heart_rate: Optional[float] = None
    min_heart_rate: Optional[float] = None

    def __post_init__(self):
        """Validate and calculate derived fields."""
        if self.distance_km < 0:
            self.distance_km = 0
        if self.duration_minutes < 0:
            self.duration_minutes = 0

    @property
    def duration_hours(self) -> float:
        """Return duration in hours."""
        return self.duration_minutes / 60.0

    @property
    def avg_speed_kmh(self) -> float:
        """Calculate average speed in km/h."""
        if self.duration_hours > 0:
            return self.distance_km / self.duration_hours
        return 0

    @property
    def calories_per_km(self) -> float:
        """Calculate calories burned per kilometer."""
        if self.distance_km > 0:
            return self.calories / self.distance_km
        return 0

    @property
    def year(self) -> int:
        """Return the year of the workout."""
        return self.start_date.year

    @property
    def month(self) -> int:
        """Return the month of the workout."""
        return self.start_date.month

    @property
    def date_str(self) -> str:
        """Return formatted date string."""
        return self.start_date.strftime("%Y-%m-%d")


@dataclass
class HeartRateZone:
    """Represents time spent in a heart rate zone."""

    zone_name: str
    min_bpm: int
    max_bpm: int
    time_minutes: float = 0

    @property
    def time_hours(self) -> float:
        """Return time in hours."""
        return self.time_minutes / 60.0

    @property
    def percentage(self) -> float:
        """Return percentage of total time (set externally)."""
        return 0  # Calculated by analyzer


@dataclass
class HeartRateRecord:
    """Individual heart rate measurement."""

    timestamp: datetime
    bpm: float
    source_name: str = ""


@dataclass
class WorkoutSummary:
    """Summary statistics for a group of workouts."""

    total_workouts: int = 0
    total_distance_km: float = 0
    total_duration_minutes: float = 0
    total_calories: float = 0
    total_elevation_gain_m: float = 0

    avg_distance_km: float = 0
    avg_duration_minutes: float = 0
    avg_speed_kmh: float = 0
    avg_calories: float = 0
    avg_elevation_gain_m: float = 0

    max_distance_km: float = 0
    max_duration_minutes: float = 0
    max_elevation_gain_m: float = 0

    workouts: List[Workout] = field(default_factory=list)

    def calculate_stats(self):
        """Calculate summary statistics from workouts list."""
        if not self.workouts:
            return

        self.total_workouts = len(self.workouts)
        self.total_distance_km = sum(w.distance_km for w in self.workouts)
        self.total_duration_minutes = sum(w.duration_minutes for w in self.workouts)
        self.total_calories = sum(w.calories for w in self.workouts)
        self.total_elevation_gain_m = sum(
            w.elevation_gain_m for w in self.workouts if w.elevation_gain_m is not None
        )

        if self.total_workouts > 0:
            self.avg_distance_km = self.total_distance_km / self.total_workouts
            self.avg_duration_minutes = self.total_duration_minutes / self.total_workouts
            self.avg_calories = self.total_calories / self.total_workouts

            workouts_with_elevation = [
                w for w in self.workouts if w.elevation_gain_m is not None
            ]
            if workouts_with_elevation:
                self.avg_elevation_gain_m = sum(
                    w.elevation_gain_m for w in workouts_with_elevation
                ) / len(workouts_with_elevation)

        total_hours = self.total_duration_minutes / 60.0
        if total_hours > 0:
            self.avg_speed_kmh = self.total_distance_km / total_hours

        if self.workouts:
            self.max_distance_km = max(w.distance_km for w in self.workouts)
            self.max_duration_minutes = max(w.duration_minutes for w in self.workouts)
            elevation_gains = [
                w.elevation_gain_m for w in self.workouts if w.elevation_gain_m is not None
            ]
            if elevation_gains:
                self.max_elevation_gain_m = max(elevation_gains)
