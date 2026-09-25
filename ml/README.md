# CityPulse crowd-level data pipeline

This isolated module prepares labeled data and trains a local baseline model.
It does not produce live predictions or connect to FastAPI or the frontend.

## Current dataset status

`ml/data/crowd_observations.csv` is a **SYNTHETIC DEVELOPMENT/DEMO DATASET**
generated only to exercise the training command and baseline pipeline. Its
`crowd_level` values are synthetic labels, not measurements, annotations, or
real observations. Training on it is for development/demo smoke checks only;
its metrics must not be treated as evidence of real-world model quality. The
separate `crowd_observations_TEMPLATE_DEV_ONLY.csv` remains an untrainable
format template and is not used by the trainer. The demo CSV has 1,680 hourly
rows across five Jaipur zones over 14 synthetic days; all three target classes
occur in both the chronological training and test partitions.

When verified crowd observations and labels are available, replace the
synthetic `ml/data/crowd_observations.csv` with the real CSV using the same
schema before evaluating or using model results beyond a demo.

## Prediction target

`crowd_level` is a measured or human-labeled categorical target with values
`low`, `moderate`, and `high`. It should describe observed crowd density for a
zone and time window. The current dashboard's displayed prediction is mock UI
content, not a source of training labels. Do not derive labels from traffic or
incident features because that would leak input information into the target.

## Dataset shape

Use one row per **city zone and time window**, for example a 15-minute or
hourly aggregate. The CSV must have these columns:

| Column | Meaning / source |
| --- | --- |
| `timestamp` | ISO-8601 start/end time of the observation window, including offset |
| `zone` | City zone, such as `Malviya Nagar` |
| `temperature_c`, `rainfall_mm`, `humidity_pct`, `wind_speed_kmh`, `air_quality_index`, `weather_condition` | Weather observation/aggregate |
| `congestion_percentage`, `traffic_delay_minutes`, `average_speed_kmh` | Traffic observation/aggregate |
| `incident_count`, `active_incident_count`, `high_critical_incident_count` | Incident counts in the same zone/window |
| `crowd_level` | Observed/labeled target: `low`, `moderate`, or `high` |

The repository has no measured crowd-density observations. The current
training CSV is synthetic as described above; real evaluation requires a
curated CSV assembled with true crowd observations and verified labels.

### Development-only CSV template

[`data/crowd_observations_TEMPLATE_DEV_ONLY.csv`](data/crowd_observations_TEMPLATE_DEV_ONLY.csv)
contains five illustrative rows for checking CSV formatting and pipeline
development only. Every row has `example_only=TRUE`; its crowd levels are
fabricated examples, **not observed labels**, and must never be used for model
training or evaluation. The loader rejects files containing rows marked this
way. For real data, use the same required columns and remove the `example_only`
column after replacing the examples with verified observations and labels.

### Column meanings

| Column | Meaning |
| --- | --- |
| `example_only` | Template safety marker; `TRUE` identifies non-real development rows. Omit from real labeled data. |
| `timestamp` | ISO-8601 observation-window timestamp, including timezone offset. |
| `zone` | City zone observed during that window. |
| `temperature_c` | Air temperature in degrees Celsius. |
| `rainfall_mm` | Rainfall during the window in millimeters. |
| `humidity_pct` | Relative humidity percentage. |
| `wind_speed_kmh` | Wind speed in kilometers per hour. |
| `air_quality_index` | Measured air-quality index. |
| `weather_condition` | Weather condition category/description for that window. |
| `congestion_percentage` | Traffic congestion from 0 to 100 percent. |
| `traffic_delay_minutes` | Observed traffic delay in minutes. |
| `average_speed_kmh` | Average traffic speed in kilometers per hour. |
| `incident_count` | Total civic incidents in the zone and window. |
| `active_incident_count` | Incidents not yet resolved in that zone and window. |
| `high_critical_incident_count` | High- or critical-severity incidents in that zone and window. |
| `crowd_level` | Observed/human-labeled target for that zone and window. |

Allowed `crowd_level` values are exactly `low`, `moderate`, and `high`. Assign
these from verified crowd-density observations using a documented labeling
policy; do not infer labels from the input columns or dashboard mock prediction.

Place the curated real labeled CSV at
`ml/data/crowd_observations.csv`. Keep the development template separate.

## Features and preprocessing

Inputs are zone and weather condition categories; weather, traffic, and
incident metrics; plus hour-of-day and day-of-week sine/cosine features derived
in Jaipur local time. ID, address, free-text incident description, and the
target are excluded from model inputs. Numeric missing values are median
imputed and standardized; categorical missing values use the most frequent
category and are one-hot encoded with unseen categories ignored.

## Split

The default is an 80/20 chronological split by distinct timestamps. All zones
sharing a timestamp remain together. The preprocessor is fitted only on the
training partition, then applied to the later test partition to avoid temporal
and preprocessing leakage. A chronological split is preferred over random
shuffling for future crowd-level prediction.

## Prepare data manually

Install this module's dependencies from `requirements.txt`, then:

```python
from ml.data_pipeline import load_dataset, prepare_dataset

data = load_dataset("ml/data/crowd_observations.csv")
split = prepare_dataset(data)
# split.X_train / split.y_train and split.X_test / split.y_test are ready
# for a later modeling step; no estimator is created or fitted here.
```

## Train and evaluate a baseline

Install the ML dependencies once:

```powershell
py -m pip install -r ml/requirements.txt
```

The command below runs against the current synthetic development dataset. For
real model evaluation, first replace it with verified labeled observations.
Run from the project root:

```powershell
py -m ml.train --dataset ml/data/crowd_observations.csv
```

The trainer validates the CSV, uses the existing 80/20 chronological split and
preprocessing pipeline, trains a class-balanced logistic-regression baseline,
and reports accuracy, balanced accuracy, macro precision/recall/F1, per-class
scores, and a confusion matrix. Model, fitted preprocessor, and metrics are
saved in `ml/artifacts/`. Missing data, development-only rows, malformed data,
and unusable training splits produce an error instead of generating labels.
Never use the development-only template as training data.
