REQUIREMENTS_FILE = ./requirements.txt
VENV_DIR      = myenv

.PHONY: all clean create_venv html Ex00 Ex01 install_req install_dep check_lint

all: cat clean

create_venv:
	@python3 -m venv $(VENV_DIR)
	@bash -c "source $(VENV_DIR)/bin/activate && \
	pip install -r $(REQUIREMENTS_FILE)"

start_bot:
	@bash -c "source $(VENV_DIR)/bin/activate && \
	python main.py"

