echo "Testing TUBDUCK."
pyversion="$(python -V 2>&1)"
(cd tubduck/ && python3 tubduck_core.py --test_load_db)
