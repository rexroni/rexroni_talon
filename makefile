all: test

test:
	python -m langserv.docstate
	python -m langserv.pod
