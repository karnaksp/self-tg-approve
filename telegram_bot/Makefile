REQUIREMENTS_FILE = ./requirements.txt
VENV_DIR = myenv

.PHONY: all create_venv start_bot

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