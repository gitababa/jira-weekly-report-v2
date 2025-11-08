# Makefile

ROOT_DIR := $(realpath .)

# Install
install:
	pip install -r requirements.txt

format:
	black --config pyproject.toml ./

lint:
	# black
	echo -e "--------------------- Black ----------------------\n"
	black --config ${ROOT_DIR}/pyproject.toml --diff --quiet ./
	black --config ${ROOT_DIR}/pyproject.toml --check ./

	# flake
	echo -e "\n\n--------------------- Flake ----------------------\n"
	pflake8 --config ${ROOT_DIR}/pyproject.toml ./

	# mypy
	echo -e "\n\n--------------------- MyPy ----------------------\n"
	mypy --config-file ${ROOT_DIR}/pyproject.toml ./ \
		--disable-error-code attr-defined \
		--disable-error-code assignment \
		--disable-error-code override \
		--disable-error-code var-annotated \
		--disable-error-code arg-type \
		--disable-error-code index
