BASE_TEST_DIR=tests/

.PHONY: test clean

install:
	pip3 install -r requirements.txt

test:
	pytest --tb=line ${BASE_TEST_DIR}

clean:
	find . -name '*.pyc' -delete
	find . -name "__pycache__" -delete

