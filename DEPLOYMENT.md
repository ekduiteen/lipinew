# Deployment Architecture: Docker & Kubernetes

**Target**: Single-cluster deployment (Phase 1) → Multi-region (Phase 2)  
**Container Orchestration**: Docker Compose (dev), Kubernetes (production)  
**Infrastructure**: 10× L40S GPU cluster + PostgreSQL + MinIO + Redis

---

## Phase 1: Docker Compose (Development & Single Cluster)

### docker-compose.gpu.yml

```yaml
version: '3.9'

services:
  # ========== FRONTEND ==========
  frontend:
    image: lipi-frontend:latest
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3001:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://nginx:80
      NEXT_PUBLIC_WS_URL: ws://nginx:80/chat
    depends_on:
      - backend
    networks:
      - lipi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ========== LOAD BALANCER & REVERSE PROXY ==========
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend-1
      - backend-2
      - backend-3
    networks:
      - lipi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/health"]
      interval: 10s
      timeout: 5s
      retries: 2

  # ========== BACKEND SERVICES ==========
  backend-1:
    image: lipi-backend:latest
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8001:8000"
    environment:
      DATABASE_URL: postgresql://lipi:lipi@postgres:5432/lipi
      REDIS_URL: redis://redis:6379/0
      ML_SERVER_URL: http://ml-server:5001
      VLLM_URL: http://vllm-server:8080
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: lipi_access
      MINIO_SECRET_KEY: lipi_secret
      CORS_ORIGINS: "http://localhost:3001,http://localhost:3000"
      LLM_PROVIDER: ollama
      OLLAMA_BASE_URL: http://ollama:11434
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
      ml-server:
        condition: service_healthy
    networks:
      - lipi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 5s
      retries: 3
    restart: on-failure

  backend-2:
    extends:
      service: backend-1
    ports:
      - "8002:8000"
    environment:
      DATABASE_URL: postgresql://lipi:lipi@postgres:5432/lipi

  backend-3:
    extends:
      service: backend-1
    ports:
      - "8003:8000"
    environment:
      DATABASE_URL: postgresql://lipi:lipi@postgres:5432/lipi

  # ========== ML INFERENCE SERVER (GPU 5-7) ==========
  ml-server:
    image: lipi-ml:latest
    build:
      context: ./backend_ml
      dockerfile: Dockerfile
    ports:
      - "5001:5001"
    environment:
      CUDA_VISIBLE_DEVICES: "5,6,7"  # GPU 5-7
      PYTHONUNBUFFERED: 1
    volumes:
      - /dev/shm:/dev/shm  # Shared memory for large tensors
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["5", "6", "7"]  # GPU 5-7
              capabilities: [gpu]
    networks:
      - lipi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: on-failure

  # ========== vLLM SERVER (GPU 0-4) ==========
  vllm-server:
    image: vllm/vllm-openai:latest
    ports:
      - "8080:8000"
    environment:
      CUDA_VISIBLE_DEVICES: "0,1,2,3,4"  # GPU 0-4
      MODEL_NAME: "${LLM_MODEL:-meta-llama/Llama-3.3-70B-Instruct}"
      TENSOR_PARALLEL_SIZE: 5
      GPU_MEMORY_UTILIZATION: 0.95
      DTYPE: float16
      TRUST_REMOTE_CODE: "true"
    volumes:
      - vllm_cache:/root/.cache
      - /dev/shm:/dev/shm
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["0", "1", "2", "3", "4"]  # GPU 0-4
              capabilities: [gpu]
    networks:
      - lipi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/v1/models"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: on-failure

  # ========== DATABASE ==========
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: lipi
      POSTGRES_PASSWORD: lipi
      POSTGRES_DB: lipi
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - lipi-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lipi"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # ========== CACHE ==========
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --maxmemory 32gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - lipi-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  # ========== OBJECT STORAGE ==========
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"  # MinIO Console
    environment:
      MINIO_ROOT_USER: lipi_access
      MINIO_ROOT_PASSWORD: lipi_secret
      MINIO_DEFAULT_BUCKETS: lipi-audio,lipi-tts,lipi-models,lipi-archives
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    networks:
      - lipi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # ========== OPTIONAL: OLLAMA LOCAL LLM ==========
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    environment:
      CUDA_VISIBLE_DEVICES: "0,1"  # Can share with vLLM or separate
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["0", "1"]
              capabilities: [gpu]
    networks:
      - lipi-network
    restart: unless-stopped

  # ========== MONITORING (OPTIONAL) ==========
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    networks:
      - lipi-network
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - lipi-network
    restart: unless-stopped

networks:
  lipi-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  minio_data:
  ollama_data:
  vllm_cache:
  prometheus_data:
  grafana_data:
```

### Launch Commands

```bash
# Development (with CPU-only fallbacks)
docker-compose -f docker-compose.gpu.yml up -d

# Production (with proper logging and monitoring)
docker-compose -f docker-compose.gpu.yml \
  --log-driver splunk \
  --log-opt splunk-token=xxx \
  up -d

# Scale backend replicas
docker-compose -f docker-compose.gpu.yml up -d --scale backend=5

# View logs
docker-compose -f docker-compose.gpu.yml logs -f backend

# Health check
docker-compose -f docker-compose.gpu.yml ps
```

---

## Phase 2: Kubernetes (Production Scaling)

### Kubernetes Architecture

```yaml
# lipi-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lipi

---
# lipi-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  namespace: lipi
  name: lipi-config
data:
  DATABASE_URL: "postgresql://lipi:lipi@postgres.lipi.svc.cluster.local:5432/lipi"
  REDIS_URL: "redis://redis.lipi.svc.cluster.local:6379/0"
  ML_SERVER_URL: "http://ml-server.lipi.svc.cluster.local:5001"
  VLLM_URL: "http://vllm-server.lipi.svc.cluster.local:8080"
  CORS_ORIGINS: "https://lipi.example.com"
  LLM_PROVIDER: "openai"  # Or claude, ollama
```

### Backend Deployment

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  namespace: lipi
  name: backend
spec:
  replicas: 5  # Scale horizontally
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: lipi-backend:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: lipi-config
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: lipi-config
              key: REDIS_URL
        resources:
          requests:
            cpu: 2000m
            memory: 2Gi
          limits:
            cpu: 4000m
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 20
          periodSeconds: 15
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - backend
              topologyKey: kubernetes.io/hostname

---
# backend-service.yaml
apiVersion: v1
kind: Service
metadata:
  namespace: lipi
  name: backend
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: backend
```

### GPU Resource Allocation

```yaml
# ml-server-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  namespace: lipi
  name: ml-server
spec:
  replicas: 1  # Single instance (not replicated)
  selector:
    matchLabels:
      app: ml-server
  template:
    metadata:
      labels:
        app: ml-server
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: gpu-node
                operator: In
                values:
                - "true"
      containers:
      - name: ml-server
        image: lipi-ml:latest
        ports:
        - containerPort: 5001
        env:
        - name: CUDA_VISIBLE_DEVICES
          value: "5,6,7"
        resources:
          requests:
            nvidia.com/gpu: 3  # Request 3 GPUs (5, 6, 7)
          limits:
            nvidia.com/gpu: 3
        volumeMounts:
        - name: shm
          mountPath: /dev/shm
      volumes:
      - name: shm
        emptyDir:
          medium: Memory
          sizeLimit: 20Gi

---
# vllm-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  namespace: lipi
  name: vllm-server
spec:
  replicas: 1  # Single instance
  selector:
    matchLabels:
      app: vllm-server
  template:
    metadata:
      labels:
        app: vllm-server
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: gpu-node
                operator: In
                values:
                - "true"
      containers:
      - name: vllm-server
        image: vllm/vllm-openai:latest
        ports:
        - containerPort: 8000
        env:
        - name: CUDA_VISIBLE_DEVICES
          value: "0,1,2,3,4"
        - name: TENSOR_PARALLEL_SIZE
          value: "5"
        - name: GPU_MEMORY_UTILIZATION
          value: "0.95"
        resources:
          requests:
            nvidia.com/gpu: 5  # Request 5 GPUs (0-4)
          limits:
            nvidia.com/gpu: 5
```

### Ingress Configuration

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  namespace: lipi
  name: lipi-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/websocket-services: "backend"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - lipi.example.com
    secretName: lipi-tls
  rules:
  - host: lipi.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      - path: /chat
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
```

### Auto-Scaling

```yaml
# hpa.yaml (Horizontal Pod Autoscaler)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  namespace: lipi
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      selectPolicy: Max
```

---

## Monitoring & Observability

### Prometheus Metrics

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['localhost:8000']
  
  - job_name: 'ml-server'
    static_configs:
      - targets: ['localhost:5001']
  
  - job_name: 'vllm'
    static_configs:
      - targets: ['localhost:8080']
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:5432']
```

### Key Dashboards (Grafana)

```
1. System Health
   - GPU utilization (0-9)
   - GPU memory usage
   - CPU utilization
   - Network I/O

2. Application Performance
   - Request latency (p50, p95, p99)
   - Requests per second
   - Error rate (4xx, 5xx)
   - WebSocket connections active

3. ML Services
   - STT latency distribution
   - TTS latency distribution
   - LLM tokens/second
   - Model load times

4. Database
   - Connection pool usage
   - Query latency (slow logs)
   - Cache hit rate (Redis)
   - Replication lag (if multi-region)

5. Learning Pipeline
   - Queue depth (Redis Streams)
   - Extraction rate (messages/sec)
   - Database write latency
   - Confidence score distribution
```

---

## Backup & Disaster Recovery

### Automated Backups

```bash
# PostgreSQL daily backup
0 2 * * * pg_dump -U lipi lipi | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz

# Upload to MinIO (off-site)
0 3 * * * aws s3 sync /backups/ s3://lipi-backups/ --delete

# MinIO periodic snapshots
# Every 6 hours: MinIO admin snapshot
```

### Disaster Recovery

```
RTO (Recovery Time Objective): 30 minutes
RPO (Recovery Point Objective): 1 hour

Failover process:
1. Detect primary database failure (automated health checks)
2. Promote read replica to primary (60 seconds)
3. Re-point backend connections (30 seconds)
4. Verify data consistency (300 seconds)
5. Total: ~6-7 minutes for critical failover
```

---

## Cost Analysis

```
Development (Docker Compose):
├─ 10× L40S: $20,000/month (lease/amortized)
├─ Power: $2,000/month
├─ Network: $500/month
├─ Personnel: $15,000/month
└─ TOTAL: $37,500/month

Production (Kubernetes, multi-region):
├─ 10× L40S primary: $20,000/month
├─ 10× L40S secondary: $20,000/month
├─ Managed Kubernetes: $5,000/month
├─ Load balancer/CDN: $2,000/month
├─ Managed database (RDS): $3,000/month
├─ Backup/disaster recovery: $2,000/month
├─ Personnel (DevOps, ML Eng): $30,000/month
└─ TOTAL: $82,000/month

Compared to API alternative:
├─ OpenAI Whisper: +$3,000/month
├─ ElevenLabs TTS: +$4,000/month
├─ Anthropic Claude: +$5,000/month
├─ Self-hosted saves: $12,000/month
└─ ROI: Pays for itself at ~7,000 DAU
```

---

## Deployment Checklist

- [ ] Docker images built and pushed to registry
- [ ] docker-compose.yml tested locally with GPUs
- [ ] PostgreSQL migrations run successfully
- [ ] MinIO buckets created and tested
- [ ] Redis persistence verified
- [ ] ML Server health checks passing
- [ ] vLLM model loaded and responsive
- [ ] Backend connects to all services
- [ ] Frontend builds and loads
- [ ] End-to-end chat flow works
- [ ] WebSocket connections stable
- [ ] Monitoring dashboards set up
- [ ] Backup process automated
- [ ] Log aggregation configured
- [ ] SSL/TLS certificates valid

