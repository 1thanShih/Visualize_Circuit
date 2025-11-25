
ENV_NAME = circuit_cad
PYTHON_VER = 3.11

all: setup run

setup:
	@echo "Checking/Creating Conda environment: $(ENV_NAME)..."
	conda create -n $(ENV_NAME) python=$(PYTHON_VER) tk -y || echo "Environment might already exist."


run:
	@echo "Starting Circuit CAD..."
	conda run -n $(ENV_NAME) python main.py

# Remove the conda environment
# clean:
# 	conda env remove -n $(ENV_NAME) -y