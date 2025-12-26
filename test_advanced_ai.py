#!/usr/bin/env python3
"""
Test Suite for Advanced AI Components
Validates all advanced AI/ML components are working correctly
"""

import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.WARNING)


def test_neural_predictor():
    """Test the advanced neural predictor"""
    print("\n1️⃣ Testing Neural Predictor...")

    from app.models.neural_predictor import (
        AdvancedNeuralPredictor,
        AttentionMechanism,
        LSTMLayer,
        ResidualBlock,
        MonteCarloDropout,
        ConformalPredictor,
    )
    import numpy as np

    # Test attention mechanism
    attention = AttentionMechanism(feature_dim=32, num_heads=4)
    x = np.random.randn(1, 8, 32)
    output, weights = attention.forward(x)
    assert output.shape[-1] == 32, "Attention output dimension mismatch"
    print("   ✓ Multi-head Attention mechanism working")

    # Test LSTM layer
    lstm = LSTMLayer(input_dim=16, hidden_dim=64)
    sequence = np.random.randn(10, 16)
    hidden, all_hidden = lstm.forward(sequence)
    assert hidden.shape[0] == 64, "LSTM hidden dimension mismatch"
    assert all_hidden.shape == (10, 64), "LSTM sequence output mismatch"
    print("   ✓ LSTM layer working")

    # Test residual block
    block = ResidualBlock(dim=64, dropout_rate=0.1)
    x = np.random.randn(64)
    output = block.forward(x, training=True)
    assert output.shape == (64,), "Residual block output shape mismatch"
    print("   ✓ Residual block with layer normalization working")

    # Test Monte Carlo dropout
    mc = MonteCarloDropout(dropout_rate=0.2, num_samples=10)

    def dummy_model(x, training=False):
        return np.array([0.3, 0.2, 0.5]) + np.random.randn(3) * 0.1 * training

    mean, epistemic, aleatoric = mc.predict_with_uncertainty(dummy_model, np.zeros(10))
    assert len(mean) == 3, "MC Dropout prediction shape mismatch"
    print("   ✓ Monte Carlo Dropout uncertainty quantification working")

    # Test conformal predictor
    conformal = ConformalPredictor(alpha=0.1)
    predictions = np.random.rand(100, 3)
    predictions = predictions / predictions.sum(axis=1, keepdims=True)
    labels = np.random.randint(0, 3, 100)
    conformal.calibrate(predictions, labels)
    pred_set, confidence = conformal.get_prediction_set(np.array([0.6, 0.3, 0.1]))
    assert len(pred_set) >= 1, "Conformal prediction set empty"
    assert 0 <= confidence <= 1, "Confidence should be between 0 and 1"
    # Conformal gives 1-alpha coverage guarantee (90% for alpha=0.1)
    print(f"   ✓ Conformal prediction: set size={len(pred_set)}, conf={confidence:.2f}")

    # Test full neural predictor
    predictor = AdvancedNeuralPredictor()
    result = predictor.predict(
        {
            "home_elo": 2000,
            "away_elo": 1800,
            "home_attack": 0.8,
            "away_defense": 0.6,
        }
    )
    assert 0 <= result.home_win_prob <= 1, "Invalid probability"
    assert 0 <= result.confidence <= 1, "Invalid confidence"
    assert result.uncertainty >= 0, "Invalid uncertainty"
    print("   ✓ Full neural predictor working")

    print("   ✅ Neural Predictor: All tests passed!")
    return True


def test_feature_engineer():
    """Test the advanced feature engineer"""
    print("\n2️⃣ Testing Feature Engineer...")

    from app.models.feature_engineer import (
        AdvancedFeatureEngineer,
        TeamEmbedding,
        FourierFeatures,
        TargetEncoder,
        MomentumIndicator,
        PolynomialInteractions,
        TimeDecayAggregator,
    )
    import numpy as np

    # Test team embeddings
    embeddings = TeamEmbedding(embedding_dim=16)
    emb = embeddings.get_embedding("Real Madrid CF")
    assert emb.shape == (16,), "Embedding dimension mismatch"
    embeddings.update_from_match("Real Madrid CF", "FC Barcelona", 2, 1)
    similarity = embeddings.team_similarity("Real Madrid CF", "FC Barcelona")
    assert -1 <= similarity <= 1, "Invalid similarity score"
    print("   ✓ Team embeddings with matrix factorization working")

    # Test Fourier features
    fourier = FourierFeatures(num_frequencies=3)
    encoded = fourier.encode_datetime(datetime.now())
    assert "day_of_week" in encoded, "Missing day_of_week"
    assert len(encoded["day_of_week"]) == 6, "Wrong Fourier feature count"
    print("   ✓ Fourier features for temporal patterns working")

    # Test target encoder
    encoder = TargetEncoder(min_samples_leaf=3, smoothing=3.0)
    encoder.fit(["A", "A", "B", "B", "B", "A"], [1, 1, 0, 0, 1, 0], "test")
    encoded_a = encoder.transform("A", "test")
    encoded_b = encoder.transform("B", "test")
    assert 0 <= encoded_a <= 1, "Invalid target encoding"
    print("   ✓ Bayesian target encoding working")

    # Test momentum indicators
    momentum = MomentumIndicator()
    rsi = momentum.calculate_rsi([0.5, 0.6, 0.7, 0.8, 0.9, 0.8])
    assert 0 <= rsi <= 100, "Invalid RSI value"
    macd, signal = momentum.calculate_macd([0.5, 0.6, 0.7, 0.8, 0.9, 0.8])
    r2, direction = momentum.calculate_trend_strength([0.5, 0.6, 0.7, 0.8, 0.9])
    assert direction in ["up", "down", "neutral"], "Invalid trend direction"
    print("   ✓ Technical momentum indicators (RSI, MACD, trend) working")

    # Test polynomial interactions
    poly = PolynomialInteractions(degree=2, max_features=30)
    features, names = poly.generate({"a": 0.5, "b": 0.7, "c": 0.3})
    assert len(features) > 3, "Should have interaction features"
    assert "a*b" in names, "Missing interaction feature name"
    print("   ✓ Polynomial feature interactions working")

    # Test time decay aggregator
    decay = TimeDecayAggregator(half_life_days=30)
    result = decay.aggregate([1.0, 0.5, 0.8], [0, 15, 30])
    assert 0 <= result <= 1, "Invalid decay aggregation"
    mean, var = decay.aggregate_with_variance([1.0, 0.5, 0.8], [0, 15, 30])
    assert var >= 0, "Variance should be non-negative"
    print("   ✓ Time-decay weighted aggregation working")

    # Test full feature engineer
    engineer = AdvancedFeatureEngineer()
    feature_set = engineer.engineer_features(
        {
            "home_team": "Real Madrid CF",
            "away_team": "FC Barcelona",
            "home_elo": 2050,
            "away_elo": 2020,
        },
        datetime.now(),
    )
    assert len(feature_set.to_flat_array()) > 50, "Should have many features"
    print(f"   ✓ Full feature engineer: {len(feature_set.to_flat_array())} features")

    print("   ✅ Feature Engineer: All tests passed!")
    return True


def test_advanced_calibration():
    """Test the advanced calibration system"""
    print("\n3️⃣ Testing Advanced Calibration...")

    from app.models.advanced_calibration import (
        AdvancedCalibrationManager,
        PlattScaling,
        TemperatureScaling,
        BetaCalibration,
        HistogramBinning,
        VennABERS,
        ConformalCalibrator,
    )
    import numpy as np

    # Test Platt scaling
    platt = PlattScaling()
    logits = np.array([0.5, 1.0, -0.5, 2.0, -1.0])
    labels = np.array([1, 1, 0, 1, 0])
    platt.fit(logits, labels)
    calibrated = platt.calibrate(logits)
    assert all(0 <= p <= 1 for p in calibrated), "Invalid Platt probabilities"
    print("   ✓ Platt Scaling (sigmoid calibration) working")

    # Test temperature scaling
    temp = TemperatureScaling()
    logits_multi = np.random.randn(100, 3)
    labels_multi = np.random.randint(0, 3, 100)
    temp.fit(logits_multi, labels_multi)
    assert temp.temperature > 0, "Temperature should be positive"
    calibrated = temp.calibrate(logits_multi)
    assert np.allclose(calibrated.sum(axis=1), 1.0), "Should sum to 1"
    print(f"   ✓ Temperature Scaling (T={temp.temperature:.3f}) working")

    # Test beta calibration
    beta = BetaCalibration()
    probs = np.random.rand(100)
    labels = (np.random.rand(100) < probs).astype(int)
    beta.fit(probs, labels)
    calibrated = beta.calibrate(probs)
    assert all(0 <= p <= 1 for p in calibrated), "Invalid beta probabilities"
    print("   ✓ Beta Calibration (3-parameter) working")

    # Test histogram binning
    hist = HistogramBinning(n_bins=10)
    hist.fit(probs, labels)
    calibrated = hist.calibrate(probs)
    assert all(0 <= p <= 1 for p in calibrated), "Invalid histogram probabilities"
    print("   ✓ Histogram Binning (non-parametric) working")

    # Test Venn-ABERS
    venn = VennABERS()
    venn.fit(probs, labels)
    lower, upper = venn.calibrate(0.7)
    assert lower <= upper, "Venn-ABERS bounds reversed"
    print("   ✓ Venn-ABERS probability intervals working")

    # Test conformal calibrator
    conformal = ConformalCalibrator(alpha=0.1)
    probs_multi = np.random.rand(100, 3)
    probs_multi = probs_multi / probs_multi.sum(axis=1, keepdims=True)
    conformal.fit(probs_multi, labels_multi)
    pred_set, coverage = conformal.get_prediction_set(np.array([0.6, 0.3, 0.1]))
    assert coverage == 0.9, "Coverage should be 90%"
    print("   ✓ Conformal prediction sets working")

    # Test full calibration manager
    manager = AdvancedCalibrationManager()
    for i in range(100):
        probs = np.random.rand(3)
        probs = probs / probs.sum()
        manager.add_sample(probs, np.random.randint(0, 3))
    manager.fit_all(min_samples=50)

    result = manager.calibrate(np.array([0.6, 0.3, 0.1]), method="ensemble")
    assert 0 <= result.confidence <= 1, "Invalid confidence"
    assert len(result.prediction_set) >= 1, "Empty prediction set"
    print("   ✓ Full calibration manager with ensemble working")

    # Test calibration metrics
    metrics = manager.get_calibration_metrics()
    assert 0 <= metrics.expected_calibration_error <= 1, "Invalid ECE"
    print(f"   ✓ Calibration metrics: ECE={metrics.expected_calibration_error:.4f}")

    print("   ✅ Advanced Calibration: All tests passed!")
    return True


def test_ai_integration():
    """Test the full AI integration"""
    print("\n4️⃣ Testing AI Integration...")

    from app.models.ai_integration import AdvancedAIIntegration

    ai = AdvancedAIIntegration()

    # Check system status
    status = ai.get_system_status()
    assert status["version"] == "2.0.0", "Wrong version"
    components = status["components"]
    working = sum(1 for v in components.values() if v)
    print(f"   ✓ System initialized: {working}/{len(components)} components")

    # Test prediction
    prediction = ai.predict(
        {
            "home_team": "Real Madrid CF",
            "away_team": "FC Barcelona",
            "home_elo": 2050,
            "away_elo": 2020,
            "home_attack": 0.92,
            "away_defense": 0.82,
            "is_derby": True,
        }
    )

    # Validate prediction structure
    assert 0 <= prediction.home_win_prob <= 1, "Invalid home win prob"
    assert 0 <= prediction.draw_prob <= 1, "Invalid draw prob"
    assert 0 <= prediction.away_win_prob <= 1, "Invalid away win prob"

    total = prediction.home_win_prob + prediction.draw_prob + prediction.away_win_prob
    assert 0.99 <= total <= 1.01, f"Probabilities should sum to 1, got {total}"

    assert 0 <= prediction.confidence <= 1, "Invalid confidence"
    assert prediction.uncertainty >= 0, "Invalid uncertainty"
    assert len(prediction.models_used) > 0, "No models used"
    assert prediction.feature_count > 0, "No features"

    print(f"   ✓ Prediction generated: {prediction.get_predicted_outcome()}")
    print(f"   ✓ Confidence: {prediction.confidence:.1%}")
    print(f"   ✓ Models used: {', '.join(prediction.models_used)}")
    print(f"   ✓ Features: {prediction.feature_count}")
    print(f"   ✓ Processing: {prediction.processing_ms:.1f}ms")

    print("   ✅ AI Integration: All tests passed!")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 ADVANCED AI COMPONENT TEST SUITE")
    print("=" * 60)

    results = {}

    # Run tests
    try:
        results["Neural Predictor"] = test_neural_predictor()
    except Exception as e:
        print(f"   ❌ Neural Predictor FAILED: {e}")
        results["Neural Predictor"] = False

    try:
        results["Feature Engineer"] = test_feature_engineer()
    except Exception as e:
        print(f"   ❌ Feature Engineer FAILED: {e}")
        results["Feature Engineer"] = False

    try:
        results["Advanced Calibration"] = test_advanced_calibration()
    except Exception as e:
        print(f"   ❌ Advanced Calibration FAILED: {e}")
        results["Advanced Calibration"] = False

    try:
        results["AI Integration"] = test_ai_integration()
    except Exception as e:
        print(f"   ❌ AI Integration FAILED: {e}")
        results["AI Integration"] = False

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for name, result in results.items():
        icon = "✅" if result else "❌"
        print(f"   {icon} {name}")

    print(f"\n   Total: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("🎉 All advanced AI components working correctly!")
        return 0
    else:
        print("⚠️ Some tests failed - check output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
