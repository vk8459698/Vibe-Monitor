# main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator
import logging
import time
import random
import uvicorn
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
import json
from datetime import datetime

# Configure logging
import os

# Remove app.log if it's a directory
if os.path.isdir('app.log'):
    os.rmdir('app.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(funcName)s:%(lineno)d',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Configure OpenTelemetry tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=14268,
    collector_endpoint="http://localhost:14268/api/traces",
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Create FastAPI app
app = FastAPI(title="Demo Service", description="A simple service with observability")

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

# Configure Prometheus metrics
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Custom metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    # Log incoming request
    logger.info(f"Incoming request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Update metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=str(request.url.path),
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.observe(process_time)
    
    # Log response
    logger.info(f"Request completed: {request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Duration: {process_time:.4f}s")
    
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/")
async def root():
    """Root endpoint"""
    with tracer.start_as_current_span("root_handler") as span:
        span.set_attribute("endpoint", "/")
        logger.info("Root endpoint accessed")
        return {"message": "Hello World!", "timestamp": datetime.now().isoformat()}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    with tracer.start_as_current_span("health_check") as span:
        span.set_attribute("endpoint", "/health")
        logger.info("Health check requested")
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/slow")
async def slow_endpoint():
    """Simulate a slow endpoint"""
    with tracer.start_as_current_span("slow_endpoint") as span:
        # Random delay between 1-3 seconds
        delay = random.uniform(1, 3)
        span.set_attribute("delay_seconds", delay)
        span.set_attribute("endpoint", "/slow")
        
        logger.info(f"Slow endpoint called, simulating {delay:.2f}s delay")
        time.sleep(delay)
        logger.info("Slow endpoint completed")
        
        return {
            "message": "This was slow!",
            "delay": delay,
            "timestamp": datetime.now().isoformat()
        }

@app.get("/error")
async def error_endpoint():
    """Simulate an error"""
    with tracer.start_as_current_span("error_endpoint") as span:
        span.set_attribute("endpoint", "/error")
        logger.error("Error endpoint accessed - simulating server error")
        span.record_exception(Exception("Simulated error"))
        return JSONResponse(
            status_code=500,
            content={"error": "Simulated server error", "timestamp": datetime.now().isoformat()}
        )

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID"""
    with tracer.start_as_current_span("get_user") as span:
        span.set_attribute("user_id", user_id)
        span.set_attribute("endpoint", "/users/{user_id}")
        
        logger.info(f"Fetching user {user_id}")
        
        # Simulate user data
        user_data = {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"User {user_id} data retrieved successfully")
        return user_data

if __name__ == "__main__":
    logger.info("Starting FastAPI application")
    uvicorn.run(app, host="0.0.0.0", port=8000)
