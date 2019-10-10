BASE_TEST_DIR=yaani/tests/

.PHONY: test clean

install:
	pip3 install -r requirements.txt

test:
	pytest ${BASE_TEST_DIR}

clean:
	find . -name '*.pyc' -delete
	find . -name "__pycache__" -delete

