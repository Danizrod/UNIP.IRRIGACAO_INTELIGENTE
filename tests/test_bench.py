import unittest
from datetime import datetime, timedelta, timezone

from app import bench

T0 = datetime(2026, 11, 6, 18, 0, tzinfo=timezone.utc)


def plan(loads, seconds=120):
    steps = []
    for i, load in enumerate(loads):
        start = T0 + timedelta(seconds=i * seconds)
        steps.append(dict(index=i, load=load, label=load, started_at=start.isoformat(),
                          ended_at=(start + timedelta(seconds=seconds)).isoformat()))
    return steps


def samples(steps, counts_for, drift_per_s=0.0, every=10):
    out, t = [], T0
    end = datetime.fromisoformat(steps[-1]['ended_at'])
    while t <= end:
        step = next(s for s in steps if datetime.fromisoformat(s['started_at']) <= t <= datetime.fromisoformat(s['ended_at']))
        out.append(dict(at=t, counts=counts_for(step) + drift_per_s * (t - T0).total_seconds(), mass=None, temp=25.0))
        t += timedelta(seconds=every)
    return out


class BenchAnalysisTests(unittest.TestCase):
    def test_calibration_cancels_linear_drift(self):
        steps = plan(['empty', 'loaded', 'empty', 'loaded', 'empty', 'loaded', 'empty'])
        # 20 counts/g, 600 g load, plus a strong linear drift (~1 g/min).
        data = samples(steps, lambda s: 8_000_000 + (12_000 if s['load'] == 'loaded' else 0), drift_per_s=20 / 60)
        result = bench.calibration(bench.summarize(steps, data), 600)
        self.assertTrue(result['ok'])
        self.assertAlmostEqual(result['factor'], 20, places=2)
        self.assertEqual(result['repeats'], 3)
        self.assertLess(result['repeatability_g'], 0.5)

    def test_calibration_needs_empty_on_both_sides(self):
        steps = plan(['empty', 'loaded'])
        data = samples(steps, lambda s: 1000 if s['load'] == 'loaded' else 0)
        self.assertFalse(bench.calibration(bench.summarize(steps, data), 600)['ok'])

    def test_calibration_rejects_load_not_applied(self):
        steps = plan(['empty', 'loaded', 'empty'])
        data = samples(steps, lambda s: 8_000_000 + (3 if s['load'] == 'loaded' else 0))
        result = bench.calibration(bench.summarize(steps, data), 600)
        self.assertFalse(result['ok'])
        self.assertIn('implausível', result['reason'])

    def test_withdrawal_counts_reps_within_two_grams(self):
        steps = plan(['empty'] + ['loaded', 'empty'] * 10, seconds=40)
        bad = {3}  # one repetition off by 5 g

        def counts(step):
            if step['load'] != 'loaded':
                return 0
            rep = (step['index'] - 1) // 2
            return 20 * (55 if rep in bad else 50)
        result = bench.withdrawal(bench.summarize(steps, samples(steps, counts)), 50, 20)
        self.assertEqual(result['total'], 10)
        self.assertEqual(result['within_2g'], 9)
        self.assertTrue(result['approved'])

    def test_press_reports_return_difference(self):
        steps = plan(['empty', 'press', 'empty', 'press', 'empty'], seconds=40)
        offsets = {0: 0, 2: 40, 4: 0}
        data = samples(steps, lambda s: offsets.get(s['index'], 5000))
        result = bench.press(bench.summarize(steps, data), 20)
        self.assertEqual([round(r['diff_g'], 1) for r in result['returns']], [2.0, 0.0])
        self.assertEqual(result['max_abs_g'], 2.0)

    def test_settling_readings_are_discarded(self):
        steps = plan(['empty'], seconds=40)
        data = [dict(at=T0 + timedelta(seconds=5), counts=999, mass=None, temp=None),
                dict(at=T0 + timedelta(seconds=30), counts=10, mass=None, temp=None)]
        self.assertEqual(bench.summarize(steps, data)[0]['median'], 10)


if __name__ == '__main__':
    unittest.main()
