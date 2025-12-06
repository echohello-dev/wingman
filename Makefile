.PHONY: help up down logs build clean test-backend test-frontend test

help: ## Show this help message
	@echo "Wingman - Slack Support Assistant"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## View logs from all services
	docker-compose logs -f

logs-backend: ## View backend logs
	docker-compose logs -f backend

logs-bot: ## View bot logs
	docker-compose logs -f bot

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

build: ## Build all Docker images
	docker-compose build

clean: ## Remove all containers and volumes
	docker-compose down -v

restart: ## Restart all services
	docker-compose restart

ps: ## Show running services
	docker-compose ps

test-backend: ## Run backend tests
	cd backend && pytest

test-frontend: ## Run frontend tests
	cd frontend && npm test

test: test-backend ## Run all tests

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/sh

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U wingman -d wingman

init: ## Initialize project (copy .env.example to .env)
	cp .env.example .env
	@echo "✅ Created .env file. Please edit it with your credentials."

install-backend: ## Install backend dependencies locally
	cd backend && pip install -r requirements.txt

install-frontend: ## Install frontend dependencies locally
	cd frontend && npm install

install: install-backend install-frontend ## Install all dependencies locally

dev-backend: ## Run backend in development mode
	cd backend && uvicorn app.main:app --reload

dev-frontend: ## Run frontend in development mode
	cd frontend && npm run dev

dev-bot: ## Run bot in development mode
	cd backend && python run_bot.py
