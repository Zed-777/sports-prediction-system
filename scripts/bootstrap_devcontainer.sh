#!/bin/bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements_phase2.txt
python -m pip install -r requirements_phase2_fixed.txt
python -m pip install -r requirements_phase2_no_tf.txt
python -m pip check || true

# Install common typed stubs to improve mypy analysis in the dev container
python -m pip install --no-input types-requests types-PyYAML types-urllib3 || true
