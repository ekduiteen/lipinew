# LIPI — convenience targets
# Usage: make <target>

COMPOSE         = docker compose -f docker-compose.yml
COMPOSE_DEV     = docker compose -f docker-compose.yml -f docker-compose.dev.yml
COMPOSE_MON     = docker compose -f docker-compose.yml --profile monitoring

.PHONY: help dev prod down logs health build setup deploy

help:
	@echo "LIPI targets:"
	@echo "  make dev              Start local dev stack (no GPU, hot-reload)"
	@echo "  make prod             Start full production stack (GPU required)"
	@echo "  make monitoring       Start prod stack + Prometheus + Grafana"
	@echo "  make down             Stop all containers"
	@echo "  make logs             Follow all logs"
	@echo "  make health           Show container health + backend /health"
	@echo "  make build            Rebuild all images"
	@echo "  make db-shell         Open psql shell"
	@echo "  make valkey-shell     Open valkey-cli shell"
	@echo "  make deploy           Run deploy script (production server only)"
	@echo "  make server-health    Full server health check (production server only)"

## ─── Local development (no GPU) ────────────────────────────────────────────
dev:
	$(COMPOSE_DEV) up -d postgres valkey minio
	$(COMPOSE_DEV) up -d minio-init
	$(COMPOSE_DEV) up -d backend
	@echo ""
	@echo "Dev stack running:"
	@echo "  Backend:  http://localhost:8000"
	@echo "  Postgres: localhost:5432"
	@echo "  Valkey:   localhost:6379"
	@echo "  MinIO:    http://localhost:9000 (console :9001)"
	@echo ""
	@echo "Start frontend separately: cd frontend && npm run dev"

## ─── Production stack (GPU required) ───────────────────────────────────────
prod:
	$(COMPOSE) up -d postgres valkey minio
	$(COMPOSE) up -d minio-init
	$(COMPOSE) up -d backend frontend
	$(COMPOSE) up -d ml vllm
	$(COMPOSE) up -d caddy
	@echo "Production stack started."

monitoring:
	$(COMPOSE_MON) up -d
	@echo "Monitoring available at http://localhost:9090 (Prometheus)"

## ─── Common operations ──────────────────────────────────────────────────────
down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

build:
	$(COMPOSE) build --pull backend frontend ml

health:
	@echo "=== Container status ==="
	@$(COMPOSE) ps
	@echo ""
	@echo "=== Backend health ==="
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "(not reachable)"

db-shell:
	$(COMPOSE) exec postgres psql -U lipi -d lipi

valkey-shell:
	$(COMPOSE) exec valkey valkey-cli

## ─── Production server deploy ───────────────────────────────────────────────
deploy:
	bash scripts/deploy.sh

server-health:
	bash scripts/server-health-check.sh

## ─── Schema reset (DESTROYS ALL DATA) ──────────────────────────────────────
reset-db:
	@echo "WARNING: This will destroy all data. Ctrl+C to cancel, Enter to continue."
	@read _
	$(COMPOSE) down -v
	$(COMPOSE) up -d postgres
