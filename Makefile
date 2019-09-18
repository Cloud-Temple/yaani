BASE_TEST_DIR=tests/

# TEST_DIRS=$(addprefix ${BASE_TEST_DIR}, \
# 				test_interface_context_parser \
# 			)


.PHONY: test

install:
	pip install -r requirements.txt

test:
	pytest ${BASE_TEST_DIR} -s

# test:
# 	pytest ${TEST_DIRS} -s

