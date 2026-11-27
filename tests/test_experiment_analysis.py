import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('analysis',ROOT/'tools/experiment_analysis.py')
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)


def event(cid,status,at,unit='pot-01',treatment='T1',**extra):
    return dict(event_id=f'{cid}-{status}',command_id=cid,unit_id=unit,treatment=treatment,source='physical',experiment_id='tcc-2026',status=status,occurred_at=at,**extra)


def cycle(cid,at,unit='pot-01',treatment='T1',terminal='completed',**extra):
    return [event(cid,'accepted',at,unit,treatment),event(cid,'started',at,unit,treatment),event(cid,terminal,at,unit,treatment,**extra)]


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((ROOT/'config/experiment.json').read_text(encoding='utf-8'))
        self.end=analysis.windows(self.plan)['total'][1]

    def test_halves_and_model_period_are_not_replication(self):
        spans=analysis.windows(self.plan)
        self.assertEqual(spans['primeira_metade'][1],spans['segunda_metade'][0])
        self.assertEqual(spans['pos_modelo_t3'][1],self.end)
        report=analysis.describe(self.plan,[],[],self.end)
        self.assertFalse(report['analysis_periods_are_replicates'])
        # No T1 water: saving undefined, never 0 % or 100 %.
        self.assertIsNone(report['periods']['total']['T2']['water_saving_pct_range'])

    def test_reject_inverted_or_replicated_protocol(self):
        bad=dict(self.plan,ends_at=self.plan['starts_at'])
        with self.assertRaises(ValueError): analysis.windows(bad)
        with self.assertRaises(ValueError): analysis.windows(dict(self.plan,analysis_periods_are_replicates=True))

    def test_water_by_calibrated_dose_scale_is_complementary(self):
        # 26/11: pot-03 dose of 2.5 s measured 44 mL by the scale; water counts as the calibrated 50 mL.
        events=cycle('a','2026-11-26T14:34:40-03:00','pot-03','T3',duration_s=2.5,measurements_valid=True,volume_ml=44.0,energy_wh=None)
        result=analysis.describe(self.plan,events+events,[],self.end)['periods']['total']['T3']
        self.assertEqual((result['dosed_water_ml_min'],result['dosed_water_ml_max']),(50,50))
        self.assertEqual(result['scale_water_ml'],44.0)
        self.assertIsNone(result['pump_energy_wh'])

    def test_failed_after_start_is_a_range_not_zero(self):
        # 23/11: reboot during the T1 settle; water applied but not measured.
        events=cycle('r','2026-11-23T04:11:51-03:00',terminal='failed',measurements_valid=False)
        result=analysis.describe(self.plan,events,[],self.end)['periods']['total']['T1']
        self.assertEqual(result['cycles_failed_after_start'],1)
        self.assertEqual((result['dosed_water_ml_min'],result['dosed_water_ml_max']),(0,50))
        rejected=[event('x','rejected','2026-11-23T05:00:00-03:00')]
        self.assertEqual(analysis.describe(self.plan,rejected,[],self.end)['periods']['total']['T1']['dosed_water_ml_max'],0)

    def test_saving_range_uses_uncertain_extremes(self):
        events=cycle('t1a','2026-11-20T10:00:00-03:00',duration_s=2.0)+cycle('t1b','2026-11-21T10:00:00-03:00',terminal='failed')
        events+=cycle('t2','2026-11-22T10:00:00-03:00','pot-02','T2',duration_s=2.0)
        result=analysis.describe(self.plan,events,[],self.end)['periods']['total']['T2']
        self.assertEqual(result['water_saving_pct_range'],[0.0,50.0])
        unfinished=analysis.describe(self.plan,events,[],analysis.timestamp('2026-11-30T00:00:00-03:00'))
        self.assertIsNone(unfinished['periods']['total']['T2']['water_saving_pct_range'])

    def test_coverage_and_range_from_unique_minutes(self):
        readings=[dict(message_id=str(i),unit_id='pot-01',treatment='T1',source='physical',experiment_id='tcc-2026',collected_at='2026-11-16T20:40:10-03:00',sensor_valid=True,soil_index=40+30*(i%2)) for i in range(10)]
        at=analysis.timestamp('2026-11-16T20:42:00-03:00')
        result=analysis.describe(self.plan,[],readings,at)['periods']['total']['T1']
        self.assertEqual(result['valid_readings'],10)
        self.assertEqual(result['valid_reading_coverage'],.5)
        self.assertEqual(result['in_range_pct_of_valid'],50)

    def test_unconfirmed_command_is_not_zero_water(self):
        item=event('1','unconfirmed','2026-11-20T00:00:00-03:00')
        item['event_id']='ledger-1'
        result=analysis.describe(self.plan,[item],[],self.end)['periods']['total']['T1']
        self.assertEqual(result['cycles_unresolved'],1)
        self.assertEqual((result['dosed_water_ml_min'],result['dosed_water_ml_max']),(0,50))
