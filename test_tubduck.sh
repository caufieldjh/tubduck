echo "Testing TUBDUCK."
pyversion="$(python -V 2>&1)"
python3 tubduck/tubduck_core.py --test_load_db
