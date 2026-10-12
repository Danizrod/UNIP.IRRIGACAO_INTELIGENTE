from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import pandas as pd

from app.ml import estimate, export_estimator, features, infer, load_model, splits, version


class MLTests(unittest.TestCase):
    def test_json_export_matches_sklearn(self):
        rng = np.random.default_rng(17)
        X = rng.normal(size=(80, 5))
        y = 50 + X[:, 0] * 2 + X[:, 1]
        models = {'ridge': Pipeline([('scale', StandardScaler()), ('ridge', Ridge())]),
                  'random_forest': RandomForestRegressor(n_estimators=5, max_depth=3, random_state=17),
                  'gradient_boosting': GradientBoostingRegressor(n_estimators=5, random_state=17)}
        for kind, model in models.items():
            with self.subTest(kind=kind):
                model.fit(X[:60], y[:60])
                actual = [estimate(export_estimator(model, kind), row) for row in X[60:]]
                np.testing.assert_allclose(actual, model.predict(X[60:]), atol=1e-10)

    def test_purged_splits_do_not_leak_six_hour_targets(self):
        times = pd.date_range('2026-01-01', periods=160, freq='h', tz='UTC')
        frame = pd.DataFrame({'time': times, 'target_time': times + pd.Timedelta(hours=6)})
        for train, valid in splits(frame):
            self.assertLess(frame.iloc[train].target_time.max(), frame.iloc[valid].time.min())

    def test_missing_sensor_features_fail_closed(self):
        item = dict(collected_at=datetime.now(timezone.utc).isoformat(), sensor_valid=True,
                    soil_index=50, temperature_c=None, humidity_pct=60)
        with self.assertRaises(ValueError):
            features(item)

    def test_origin_and_calibration_cannot_be_mixed(self):
        body = dict(source='simulation', device_id='sim-01', unit_id='pot', calibration_id='sim-cal')
        item = dict(source='physical', device_id='sim-01', unit_id='pot', calibration_id='sim-cal')
        with self.assertRaises(ValueError):
            infer(dict(body=body), item)

    def test_modified_artifact_rejected(self):
        body = dict(schema_version=1, source='simulation', features=[], horizon_s=21600)
        artifact = {'body': body, 'model_version': version(body)}
        body['source'] = 'physical'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model.json'
            path.write_text(json.dumps(artifact))
            with self.assertRaises(ValueError):
                load_model(path)
