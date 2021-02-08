all: test

test:
	python -m langserv.docstate
	python -m langserv.pod
	python tests/test_wrap_langserv.py
	@echo "PASS"
