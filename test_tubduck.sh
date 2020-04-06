echo "Testing TUBDUCK."
pyversion="$(python3 -V 2>&1)"
(cd tubduck/ && python3 tubduck_core.py --test_load_db)
