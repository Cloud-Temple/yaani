BASE_TEST_DIR=tests/

# TEST_DIRS=$(addprefix ${BASE_TEST_DIR}, \
# 				test_interface_context_parser \
# 			)


.PHONY: test

install:
	pip3 install -r requirements.txt

test:
	pytest ${BASE_TEST_DIR}

# test:
# 	pytest ${TEST_DIRS} -s

