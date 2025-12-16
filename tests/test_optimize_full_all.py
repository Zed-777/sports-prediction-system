from scripts.optimize_accuracy import AccuracyOptimizer


def test_full_optimization_all_leagues(monkeypatch, tmp_path):
    # Prevent loading the real tools
    def fake_load(self):
        class StubBacktester:
            def run_backtest(self, *args, **kwargs):
                return {'metrics': {'accuracy': 0.60, 'accuracy_pct': '60.0%'}, 'metrics_history': []}
        self.backtester = StubBacktester()
        self.ab_tester = None
        self.tracker = None

    monkeypatch.setattr(AccuracyOptimizer, '_load_tools', fake_load)

    # Make run_parameter_sweep predictable
    def fake_sweep(self, param_name, league):
        return {'optimal_value': 0.18, 'optimal_accuracy': 0.605}

    monkeypatch.setattr(AccuracyOptimizer, 'run_parameter_sweep', fake_sweep)

    opt = AccuracyOptimizer()
    results = opt.full_optimization(league='all')

    # Expect results for all supported leagues
    for expected in ['la-liga', 'premier-league', 'bundesliga', 'serie-a', 'ligue-1']:
        assert expected in results
        assert 'baseline_accuracy' in results[expected]
        assert 'optimized_accuracy' in results[expected]
