"""Feature definitions for the driver-statistics feature store."""

import os
from datetime import timedelta

from feast import Entity, FeatureService, FeatureView, Field, FileSource, ValueType
from feast.types import Float32, Int64

# In production the parquet files live in S3; locally they live in ./data.
DATA_ROOT = os.environ.get("FEAST_DATA_ROOT", "data")

driver = Entity(
    name="driver",
    join_keys=["driver_id"],
    value_type=ValueType.INT64,
    description="A ride-hailing driver",
)

driver_hourly_source = FileSource(
    name="driver_hourly_stats_source",
    path=f"{DATA_ROOT}/driver_hourly_stats.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

driver_hourly_stats = FeatureView(
    name="driver_hourly_stats",
    entities=[driver],
    ttl=timedelta(days=2),
    schema=[
        Field(name="conv_rate", dtype=Float32, description="Share of ride offers accepted"),
        Field(name="acc_rate", dtype=Float32, description="Share of accepted rides completed"),
        Field(name="avg_daily_trips", dtype=Int64, description="Trips per day, trailing 7 days"),
    ],
    online=True,
    source=driver_hourly_source,
    tags={"owner": "ml-platform", "team": "pricing"},
)

driver_activity_v1 = FeatureService(
    name="driver_activity_v1",
    features=[driver_hourly_stats],
    description="Features used by the ride-acceptance model",
)
