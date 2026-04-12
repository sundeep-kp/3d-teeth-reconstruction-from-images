#!/usr/bin/env python3
"""Minimal local command runner for command-runner.html.

Endpoint:
  POST /run
Request JSON:
  {"command": "...", "cwd": "/abs/or/relative/path"}
Response JSON:
  {"stdout": "...", "stderr": "...", "code": 0}
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

HOST = "127.0.0.1"
PORT = 8787
MAX_COMMAND_CHARS = 12000
PROCESS_TIMEOUT_SECONDS = 60 * 60

# Restrict execution to this repository tree.
WORKSPACE_ROOT = Path(__file__).resolve().parent
DENTAL_PROJECT_ROOT = WORKSPACE_ROOT / "dental-disease-aiml"
DENTAL_DATASET_PATH = DENTAL_PROJECT_ROOT / "dental_dataset_15_diseases.csv"

_MODEL_CACHE: dict[str, Any] = {}
_MODEL_LOCK = threading.Lock()

# Higher values indicate clinically more concerning conditions.
DISEASE_SEVERITY = {
    "Oral Cancer": 5,
    "Abscess": 5,
    "Periodontitis": 4,
    "Impacted Tooth": 4,
    "Dry Socket": 4,
    "Tooth Fracture": 4,
    "TMJ Disorder": 3,
    "Gingivitis": 3,
    "Enamel Erosion": 3,
    "Tartar": 2,
    "Plaque": 2,
    "Bruxism": 2,
    "Dental Caries": 2,
    "Tooth Sensitivity": 1,
    "Halitosis": 1,
}


def _load_predictor_bundle() -> dict[str, Any]:
    with _MODEL_LOCK:
        if _MODEL_CACHE:
            return _MODEL_CACHE

        try:
            import pandas as pd
            from sklearn.model_selection import train_test_split
            from sklearn.neighbors import KNeighborsClassifier
            from sklearn.naive_bayes import GaussianNB
            from sklearn.preprocessing import LabelEncoder
            from sklearn.tree import DecisionTreeClassifier
        except ImportError as exc:
            raise RuntimeError(f"Missing ML dependency: {exc}") from exc

        if not DENTAL_DATASET_PATH.exists():
            raise RuntimeError(f"Dataset not found: {DENTAL_DATASET_PATH}")

        df = pd.read_csv(DENTAL_DATASET_PATH)
        if "disease" not in df.columns:
            raise RuntimeError("Dataset missing required 'disease' column")

        x = df.drop("disease", axis=1)
        y_raw = df["disease"]

        encoder = LabelEncoder()
        y = encoder.fit_transform(y_raw)

        x_train, _x_test, y_train, _y_test = train_test_split(
            x, y, test_size=0.2, random_state=42, stratify=y
        )

        models = {
            "dt": DecisionTreeClassifier(random_state=42),
            "nb": GaussianNB(),
            "knn": KNeighborsClassifier(n_neighbors=5),
        }
        for model in models.values():
            model.fit(x_train, y_train)

        _MODEL_CACHE.update(
            {
                "models": models,
                "encoder": encoder,
                "symptoms": list(x.columns),
                "diseases": list(encoder.classes_),
            }
        )
        return _MODEL_CACHE


def _rank_danger(disease: str, confidence: float) -> dict[str, Any]:
    severity = float(DISEASE_SEVERITY.get(disease, 2))
    confidence_component = 1.0 + (4.0 * max(0.0, min(1.0, confidence)))
    weighted = (0.7 * severity) + (0.3 * confidence_component)

    if weighted < 2.0:
        label = "Low"
    elif weighted < 3.0:
        label = "Moderate"
    elif weighted < 4.0:
        label = "High"
    else:
        label = "Critical"

    return {
        "label": label,
        "score": round(weighted, 3),
        "severity": int(round(severity)),
        "confidence_component": round(confidence_component, 3),
    }


def _predict_disease(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    symptoms = payload.get("symptoms")
    model_key = (payload.get("model") or "dt").strip().lower()

    if not isinstance(symptoms, list) or not symptoms:
        return 400, {"error": "'symptoms' must be a non-empty array"}
    if not all(isinstance(item, str) for item in symptoms):
        return 400, {"error": "All symptoms must be strings"}

    try:
        bundle = _load_predictor_bundle()
    except RuntimeError as exc:
        return 500, {"error": str(exc)}

    models = bundle["models"]
    encoder = bundle["encoder"]
    all_symptoms = bundle["symptoms"]

    if model_key not in models:
        return 400, {"error": "'model' must be one of: dt, nb, knn"}

    unknown = sorted(set(symptoms) - set(all_symptoms))
    if unknown:
        return 400, {"error": f"Unknown symptoms: {', '.join(unknown)}"}

    feature_vector = [1 if symptom in symptoms else 0 for symptom in all_symptoms]
    model = models[model_key]
    probabilities = model.predict_proba([feature_vector])[0]

    ranked: list[dict[str, Any]] = []
    for class_index, prob in enumerate(probabilities):
        disease = encoder.inverse_transform([class_index])[0]
        ranked.append(
            {
                "disease": disease,
                "confidence": round(float(prob), 6),
                "severity": DISEASE_SEVERITY.get(disease, 2),
            }
        )
    ranked.sort(key=lambda item: item["confidence"], reverse=True)

    top = ranked[0]
    danger = _rank_danger(top["disease"], top["confidence"])

    return 200, {
        "model": model_key,
        "selected_symptoms": sorted(set(symptoms)),
        "top_disease": top["disease"],
        "confidence": top["confidence"],
        "danger": danger,
        "alternatives": ranked[1:6],
        "all_symptoms": all_symptoms,
    }


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    handler.end_headers()
    handler.wfile.write(body)


def _resolve_safe_cwd(raw_cwd: str | None) -> Path:
    if not raw_cwd:
        return WORKSPACE_ROOT

    candidate = Path(raw_cwd)
    if not candidate.is_absolute():
        candidate = (WORKSPACE_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()

    # Prevent path traversal outside workspace.
    if WORKSPACE_ROOT not in candidate.parents and candidate != WORKSPACE_ROOT:
        raise ValueError(f"cwd must stay under workspace root: {WORKSPACE_ROOT}")

    if not candidate.exists() or not candidate.is_dir():
        raise ValueError(f"cwd does not exist or is not a directory: {candidate}")

    return candidate


class RunnerHandler(BaseHTTPRequestHandler):
    server_version = "TeethRunner/1.0"

    def do_OPTIONS(self) -> None:  # noqa: N802
        _json_response(self, 200, {"ok": True})

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/run", "/predict-disease"}:
            _json_response(self, 404, {"error": "Not Found"})
            return

        content_length = self.headers.get("Content-Length", "0")
        try:
            body_size = int(content_length)
        except ValueError:
            _json_response(self, 400, {"error": "Invalid Content-Length"})
            return

        if body_size <= 0:
            _json_response(self, 400, {"error": "Empty request body"})
            return

        raw = self.rfile.read(body_size)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _json_response(self, 400, {"error": "Body must be valid JSON"})
            return

        if self.path == "/predict-disease":
            status, response = _predict_disease(payload)
            _json_response(self, status, response)
            return

        command = payload.get("command")
        raw_cwd = payload.get("cwd")

        if not isinstance(command, str) or not command.strip():
            _json_response(self, 400, {"error": "'command' must be a non-empty string"})
            return

        if len(command) > MAX_COMMAND_CHARS:
            _json_response(self, 400, {"error": "Command too long"})
            return

        try:
            cwd = _resolve_safe_cwd(raw_cwd if isinstance(raw_cwd, str) else None)
        except ValueError as exc:
            _json_response(self, 400, {"error": str(exc)})
            return

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=PROCESS_TIMEOUT_SECONDS,
                env=os.environ.copy(),
            )
            _json_response(
                self,
                200,
                {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "code": result.returncode,
                    "cwd": str(cwd),
                },
            )
        except subprocess.TimeoutExpired as exc:
            _json_response(
                self,
                408,
                {
                    "stdout": exc.stdout or "",
                    "stderr": (exc.stderr or "") + "\nProcess timed out.",
                    "code": -1,
                    "cwd": str(cwd),
                },
            )

    def log_message(self, format: str, *args: Any) -> None:
        # Keep server output readable and short.
        print(f"[runner] {self.address_string()} - {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), RunnerHandler)
    print(f"[runner] listening on http://{HOST}:{PORT}")
    print(f"[runner] workspace root: {WORKSPACE_ROOT}")
    print("[runner] endpoint: POST /run")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("[runner] stopped")


if __name__ == "__main__":
    main()
