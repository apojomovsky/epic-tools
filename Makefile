.PHONY: test build build-tool image image-windows image-python setup-hooks help

# The host to build for. The C tools cross-compile for Windows with mingw-w64,
# so no Windows machine is needed: make build SYSTEM=windows_amd64.
SYSTEM ?= linux_x86_64

test: ## Run the test suite (the exact command CI runs)
	python3 -m unittest discover -t . -s tests

build: ## Build every tool package for $(SYSTEM) into dist/
	@for pin in tools/*/pin.json; do \
		python3 scripts/build_tool.py --pin "$$pin" --system $(SYSTEM) --out dist || exit 1; \
	done

build-tool: ## Build one package: make build-tool TOOL=tool-minipro SYSTEM=windows_amd64
	@test -n "$(TOOL)" || { echo "usage: make build-tool TOOL=tool-minipro"; exit 2; }
	python3 scripts/build_tool.py --pin tools/$(TOOL)/pin.json --system $(SYSTEM) --out dist

image: ## Build the C build image (also built on demand by build)
	docker build -f docker/build/Dockerfile -t epic-tools-build:local .

image-windows: ## Build the Windows cross image (also built on demand by build)
	docker build -f docker/build/windows.Dockerfile -t epic-tools-build-windows:local .

image-python: ## Build the pure-Python build image (built on demand by build)
	docker build -f docker/build/python.Dockerfile -t epic-tools-build-python:local .

setup-hooks: ## Install git hooks (.githooks/ -> the repo's hooks dir)
	@mkdir -p $$(git rev-parse --git-path hooks) \
		&& cp .githooks/pre-commit .githooks/commit-msg .githooks/pre-push $$(git rev-parse --git-path hooks)/ \
		&& chmod +x $$(git rev-parse --git-path hooks)/pre-commit $$(git rev-parse --git-path hooks)/commit-msg $$(git rev-parse --git-path hooks)/pre-push
	@echo "git hooks installed (pre-commit, commit-msg, pre-push)"

help: ## List targets
	@grep -hE '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | column -t -s '	'
