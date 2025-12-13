from generate_fast_reports import SingleMatchGenerator


def test_generator_skip_injuries_flag():
    gen = SingleMatchGenerator(skip_injuries=True)
    assert gen.data_quality_enhancer.skip_injuries is True
