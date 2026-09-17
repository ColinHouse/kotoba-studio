# Kotoba Studio — one entry point for humans and agents.
# Every target is safe to run repeatedly. `make check` is what CI runs.

SHELL := /bin/bash
.DEFAULT_GOAL := help

BACKEND  := backend
FRONTEND := frontend

.PHONY: help setup hooks check check-backend check-frontend fix test test-backend \
        test-frontend e2e dev run build migrate clean package-windows

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# Platform extras. Written as conditionals rather than $(shell ... case ...) because
# make ends a $(shell ...) at the first unmatched ")", and "Darwin)" is one.
UNAME_S := $(shell uname -s)
PLATFORM_EXTRA :=
ifeq ($(UNAME_S),Darwin)
PLATFORM_EXTRA := --extra macos
endif
ifneq (,$(findstring MINGW,$(UNAME_S))$(findstring MSYS,$(UNAME_S))$(findstring CYGWIN,$(UNAME_S)))
PLATFORM_EXTRA := --extra windows
endif

setup: ## Install backend + frontend dependencies and enable git hooks
	cd $(BACKEND) && uv sync --extra dev $(PLATFORM_EXTRA)
	cd $(FRONTEND) && npm ci
	$(MAKE) hooks

hooks: ## Point git at the repo's hooks (blocks junk commits, checks commit messages)
	git config core.hooksPath .githooks
	@chmod +x .githooks/* 2>/dev/null || true
	@echo "git hooks enabled (core.hooksPath=.githooks)"

check: check-backend check-frontend ## Run everything CI runs

check-backend: ## Lint, format-check and test the backend
	cd $(BACKEND) && uv run ruff check .
	cd $(BACKEND) && uv run ruff format --check .
	cd $(BACKEND) && uv run pytest -q

check-frontend: ## Lint, format-check, typecheck, test and build the frontend
	cd $(FRONTEND) && npm run lint
	cd $(FRONTEND) && npm run format:check
	cd $(FRONTEND) && npm run typecheck
	cd $(FRONTEND) && npm run test
	cd $(FRONTEND) && npm run build

fix: ## Auto-fix what can be auto-fixed, both halves
	cd $(BACKEND) && uv run ruff check --fix .
	cd $(BACKEND) && uv run ruff format .
	cd $(FRONTEND) && npm run lint:fix
	cd $(FRONTEND) && npm run format

test: test-backend test-frontend ## Tests only, no lint or build

test-backend:
	cd $(BACKEND) && uv run pytest -q

test-frontend:
	cd $(FRONTEND) && npm run test

# Not part of `make check`: it needs a Chromium download and a real build, and
# check stays fast. CI runs it as its own job.
e2e: ## Smoke the main path in a real browser (Playwright + Chromium)
	cd $(FRONTEND) && npm run e2e

dev: ## Backend (8720) and Vite (5174), both with reload
	./scripts/dev.sh

build: ## Build the frontend into frontend/dist
	cd $(FRONTEND) && npm run build

run: build ## Build, then serve API + web app on one port
	cd $(BACKEND) && uv run python -m kotoba serve --open

migrate: ## Create a migration from model changes (edit the result before committing)
	cd $(BACKEND) && uv run alembic revision --autogenerate -m "$(m)"
	@echo "Now replace kotoba.models.UTCDateTime() with sa.DateTime() in the new revision."

package-windows: ## Build the Windows bundle (ARGS="--installer" adds the setup exe)
	cd $(BACKEND) && uv run --extra packaging python ../packaging/build.py $(ARGS)

clean: ## Remove build output and caches (never touches your data directory)
	rm -rf $(FRONTEND)/dist $(FRONTEND)/dev-dist $(FRONTEND)/node_modules/.tmp
	find $(BACKEND) -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache

version: ## Print the version declared in each manifest (they must agree)
	@printf 'backend  %s\n' "$$(grep -m1 '^version' $(BACKEND)/pyproject.toml | cut -d'"' -f2)"
	@printf 'frontend %s\n' "$$(node -p "require('./$(FRONTEND)/package.json').version")"
	@test "$$(grep -m1 '^version' $(BACKEND)/pyproject.toml | cut -d'"' -f2)" = \
	      "$$(node -p "require('./$(FRONTEND)/package.json').version")" \
	  && echo 'in sync' || { echo 'OUT OF SYNC'; exit 1; }
