venv:
	python -m venv .venv
	. .venv/bin/activate && python -m pip install -r dev-requirements.txt

test: venv
	. .venv/bin/activate && pytest

release: venv
	rm -rf dist/
	. .venv/bin/activate && python -m build
	. .venv/bin/activate && twine upload dist/*

.PHONY: venv test release
