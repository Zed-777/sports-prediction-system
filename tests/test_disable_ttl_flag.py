from generate_fast_reports import SingleMatchGenerator


def test_disable_ttl_override_propagates():
    ttl_override = 123
    gen = SingleMatchGenerator(skip_injuries=False, injuries_disable_ttl_override=ttl_override)
    assert gen.data_quality_enhancer.injuries_disable_ttl_override == ttl_override
