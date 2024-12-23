REQUIREMENTS_FILE = ./requirements.txt
VENV_DIR = myenv

.PHONY: all create_venv start_bot pep8 pylint sort check_lint

all: create_venv start_bot

create_venv:
	@python -m venv $(VENV_DIR)
	@bash -c "source $(VENV_DIR)/bin/activate && \
	pip install -r $(REQUIREMENTS_FILE)"

start_bot:
	@bash -c "source $(VENV_DIR)/bin/activate && \
	python main.py"

clean:
	@bash -c "rm -rf *.tgz myenv __pycache__"

pep8:
	autopep8 --in-place --recursive --aggressive *.py

pylint:
	pylint --disable=c-extension-no-member --fail-under=9.0 --output-format=colorized *.py

sort:
	isort .

check_lint: pep8 sort pylint

