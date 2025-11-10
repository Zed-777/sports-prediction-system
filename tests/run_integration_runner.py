import sys

import pytest


def main():
    """Run the integration tests via pytest for environments that don't run pytest directly."""
    # Run the specific integration test file and return exit code
    ret = pytest.main(['-q', 'tests/test_integration_flashscore.py'])
    if ret == 0:
        print('TEST_RUN_OK')
    else:
        print(f'TESTS_FAILED (exit {ret})')
    return ret


if __name__ == '__main__':
    code = main()
    sys.exit(code)

    # The previous test runner code has been replaced with the pytest-based runner.
    # The following lines are no longer needed.
    # test_flashscore_ingest_and_image_generation()
    # print('TEST_RUN_OK')
    # except AssertionError as e:
    # print('ASSERTION_FAILED:', e)
    # except Exception as e:
    # import traceback
    # traceback.print_exc()
    # print('ERROR:', e)
