import os
import time
import socket
import datetime
from flask import Flask, jsonify

app = Flask(__name__)

APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
APP_NAME    = os.environ.get("APP_NAME", "sample-app")
POD_NAME    = socket.gethostname()


@app.route("/")
def index():
    return jsonify({
        "app":         APP_NAME,
        "version":     APP_VERSION,
        "environment": ENVIRONMENT,
        "pod":         POD_NAME,
        "timestamp":   datetime.datetime.utcnow().isoformat() + "Z",
        "message":     f"Running in {ENVIRONMENT}"
    })


@app.route("/health")
def health():
    """Kubernetes liveness probe — returns 200 as long as app is alive."""
    return jsonify({"status": "healthy", "pod": POD_NAME}), 200


@app.route("/ready")
def ready():
    """Kubernetes readiness probe — returns 200 when app is ready for traffic."""
    return jsonify({"status": "ready", "pod": POD_NAME}), 200


@app.route("/version")
def version():
    """
    Shows the currently deployed image tag.
    When ArgoCD syncs a new image, this value changes.
    This PROVES GitOps is working — call this after each deploy.
    """
    return jsonify({
        "version":     APP_VERSION,
        "environment": ENVIRONMENT,
        "git_commit":  os.environ.get("GIT_COMMIT", "unknown"),
        "deployed_at": os.environ.get("DEPLOYED_AT", "unknown"),
        "pod":         POD_NAME
    })


@app.route("/simulate/load")
def simulate_load():
    """
    Burns CPU for 0.5 seconds.
    Use this to trigger the Horizontal Pod Autoscaler (HPA).

    Demo command:
      watch -n 0.3 'curl -s http://localhost:5000/simulate/load'
    Then watch pods scale up:
      kubectl get hpa -w
    """
    start = time.time()
    while time.time() - start < 0.5:
        _ = sum(i * i for i in range(10000))
    return jsonify({"status": "load simulated", "duration_ms": 500})


@app.route("/simulate/error")
def simulate_error():
    """Returns 500. Used to test alerting in Project 2 (Observability)."""
    return jsonify({"error": "Simulated 500 error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
