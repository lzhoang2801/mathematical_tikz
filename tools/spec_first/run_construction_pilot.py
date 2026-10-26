"""Paired, bounded native-vs-construction pilot on frozen real dataset rows."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from functools import partial
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import statistics
import sys
from threading import Lock
from time import perf_counter
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import httpx
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import RunnableLambda
from langchain_core.tracers.langchain import wait_for_all_tracers
from langsmith import Client, tracing_context

import agent.workflows.tikz as harness
import spec_first.construction_agent as construction_harness
import latex_compiler.client as compiler_client
from spec_first.prompts.construction import CONSTRUCTION_PROMPT_VERSION, construction_messages
from agent.prompts.problem_tikz import PROBLEM_TIKZ_PROMPT_VERSION, problem_tikz_messages
from agent.prompts.tikz import TIKZ_PROMPT_VERSION
from evaluation.evaluator import EvaluationError, EvaluationInfrastructureError, _score_observations
from evaluation.tikz_observations import SCHEMA_VERSION, TRACER_SHA256, compile_observe, read_scene
from tools.spec_first import construction_pilot_cases, spatial_pilot_cases, spec_first_pilot_cases
from spec_first.prompts.spec_first import SPEC_FIRST_PROMPT_VERSION
from spec_first.workflow import draw_spec_first
from spec_first.prompts.spatial_construction import SPATIAL_PROMPT_VERSION, spatial_construction_messages, spatial_task_messages
from tools.cpa import build_model

DEFAULT_OUTPUT = ROOT / "runs/construction-pilot-20261019"
MAX_MODEL_CALLS = 4
MAX_COMPILES = 4
REPETITIONS = 2


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def frozen_data_hashes(output: Path) -> dict:
    files = [output / "inputs.json", *sorted((output / "references").rglob("*.json"))]
    if (output / "manifest.json").exists():
        files += [output / "manifest.json", output / "worker-freeze.json", *sorted((output / "checks").glob("*.py"))]
        files += [path for path in (output / "calibration.json", output / "prepare_study.py") if path.is_file()]
        files += sorted((output / "calibration").glob("*/target/observations.json"))
    return {str(path.relative_to(output)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def model_settings(model) -> dict:
    return {"endpoint_sha256": hashlib.sha256(str(model.openai_api_base).encode()).hexdigest(),
            "temperature": model.temperature, "top_p": model.top_p, "seed": model.seed,
            "max_tokens": model.max_tokens, "max_retries": model.max_retries}


def code_hashes() -> dict:
    files = list((ROOT / "src").rglob("*.py")) + list((ROOT / "evaluation").glob("*.py"))
    files += [ROOT / "evaluation/pgf_trace.tex", Path(__file__), ROOT / "tools/spec_first/construction_pilot_cases.py", ROOT / "tools/spec_first/spatial_pilot_cases.py", ROOT / "tools/spec_first/spec_first_pilot_cases.py", ROOT / "tools/cpa.py"]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}


class MeasuredCompiler(httpx.Client):
    """Measure complete HTTP response consumption, including failed attempts."""
    def __init__(self, directory: Path, *, limit: int | None = None, **kwargs):
        super().__init__(**kwargs)
        self.directory, self.limit = directory, limit
        self.records: list[dict] = read(directory / "requests.json") if (directory / "requests.json").exists() else []
        self.lock = Lock()

    @contextmanager
    def stream(self, method, url, *args, **kwargs):
        if method.upper() != "POST" or not str(url).endswith("/compile"):
            with super().stream(method, url, *args, **kwargs) as response:
                yield response
            return
        with self.lock:
            if self.limit is not None and len(self.records) >= self.limit:
                raise RuntimeError("Pilot compiler request budget exhausted")
            record = {"index": len(self.records) + 1, "seconds": None, "status": None, "error": None}
            self.records.append(record)
            save(self.directory / str(record["index"]) / "request.json", kwargs.get("json"))
        started = perf_counter()
        try:
            with super().stream(method, url, *args, **kwargs) as response:
                record["status"] = response.status_code
                yield response
        except Exception as error:
            record["error"] = type(error).__name__ + ": " + str(error)
            raise
        finally:
            record["seconds"] = perf_counter() - started
            with self.lock:
                save(self.directory / "requests.json", self.records)


class Recorder(BaseCallbackHandler):
    """Retain model/tool events even if the graph raises before final persistence."""
    def __init__(self, directory: Path):
        self.directory, self.lock = directory, Lock()
        self.calls, self.starts = [], {}
        self.tool_events = []
        self.tool_names = {}

    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        self.starts[str(run_id)] = perf_counter()
        self.calls.append({"run_id": str(run_id), "seconds": None, "usage": {}, "error": None})
        save(self.directory / "model_calls.json", self.calls)

    def on_llm_end(self, response, *, run_id, **kwargs):
        row = next(row for row in self.calls if row["run_id"] == str(run_id))
        message = response.generations[0][0].message
        row.update(seconds=perf_counter() - self.starts[str(run_id)], usage=message.usage_metadata or {},
                   response_model=message.response_metadata.get("model_name"))
        save(self.directory / "responses" / (str(run_id) + ".json"), message.model_dump(mode="json"))
        save(self.directory / "model_calls.json", self.calls)

    def on_llm_error(self, error, *, run_id, **kwargs):
        row = next(row for row in self.calls if row["run_id"] == str(run_id))
        row.update(seconds=perf_counter() - self.starts[str(run_id)], error=type(error).__name__ + ": " + str(error))
        save(self.directory / "model_calls.json", self.calls)

    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        self.tool_names[str(run_id)] = serialized.get("name")

    def on_tool_error(self, error, *, run_id, **kwargs):
        with self.lock:
            event = {"status": "error", "name": self.tool_names.get(str(run_id)),
                     "error": type(error).__name__ + ": " + str(error), "run_id": str(run_id)}
            self.tool_events.append(event)
            save(self.directory / "tools" / (str(run_id) + ".json"), event)

    def on_tool_end(self, output, *, run_id, **kwargs):
        with self.lock:
            event = output.model_dump(mode="json") if hasattr(output, "model_dump") else {"output": str(output)}
            self.tool_events.append(event)
            save(self.directory / "tools" / (str(run_id) + ".json"), event)


def compiler(directory: Path, url: str, *, limit=None) -> MeasuredCompiler:
    return MeasuredCompiler(directory, limit=limit, base_url=url, timeout=200, trust_env=False)


def prepare(output: Path, url: str, suite: str = "planar", method: str = "construction") -> None:
    if suite == "mixed":
        raise ValueError("Mixed studies require an explicitly prepared frozen manifest")
    if method not in {"construction", "spec_first"}:
        raise ValueError("Unknown method")
    cases = spatial_pilot_cases if suite == "spatial" else construction_pilot_cases
    if (output / "protocol.json").exists():
        raise FileExistsError("Protocol is already frozen")
    for module in (harness, compiler_client):
        if not Path(module.__file__).resolve().is_relative_to(ROOT / "src"):
            raise RuntimeError("Pilot imported external source: " + module.__file__)
    source = ROOT / "dataset/synthetic_new/generate.jsonl"
    rows = {row["id"]: row for row in map(json.loads, source.read_text(encoding="utf-8").splitlines())}
    model = build_model(timeout=180, max_tokens=8192)
    with httpx.Client(base_url=url, timeout=5, trust_env=False) as http:
        ready = http.get("/readyz")
        ready.raise_for_status()
        readiness = ready.json()
    inputs = []
    for name, identity in cases.CASES.items():
        row = rows[identity]
        if row["task"] != "Generate" or not row.get("target_tikz"):
            raise ValueError("Selected case no longer matches the audited task")
        save(output / "references" / name / "original-record.json", row)
        save(output / "references" / name / "requirements.json", cases.requirements(name).model_dump(mode="json"))
        inputs.append({"case": name, "id": identity, "instruction": row["instruction"]})
    save(output / "inputs.json", inputs)
    order = []
    for repetition in range(REPETITIONS):
        for index, case in enumerate(cases.CASES):
            arms = ["native", method] if (repetition + index) % 2 == 0 else [method, "native"]
            order.extend({"case": case, "arm": arm, "repetition": repetition + 1,
                          "key": f"{case}-{repetition + 1}-{arm}"} for arm in arms)
    protocol = {"suite": suite, "method": method, "created_at": datetime.now(timezone.utc).isoformat(), "model": model.model_name,
                "max_tokens": 8192, "model_timeout_seconds": 180, "provider_retries": 0,
                "max_model_calls_per_drawing": MAX_MODEL_CALLS, "max_compiles_per_drawing": MAX_COMPILES,
                "maximum_model_calls": sum(1 if job["arm"] == "spec_first" else MAX_MODEL_CALLS for job in order), "order": order,
                "arm_budgets": {"native": {"model_calls": MAX_MODEL_CALLS, "compiles": MAX_COMPILES}, method: {"model_calls": 1 if method == "spec_first" else MAX_MODEL_CALLS, "compiles": 1 if method == "spec_first" else MAX_COMPILES}},
                "post_agent_label_repair": "Not run; primary geometry/content checks exclude label placement, reported separately.",
                "compiler_url": url, "compiler_readiness": readiness,
                "source_file_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "code_sha256": code_hashes(), "data_sha256": frozen_data_hashes(output), "model_settings": model_settings(model), "upstream": read(ROOT / "src/upstream.json"),
                "prompts": [TIKZ_PROMPT_VERSION, PROBLEM_TIKZ_PROMPT_VERSION, SPEC_FIRST_PROMPT_VERSION if method == "spec_first" else SPATIAL_PROMPT_VERSION if suite == "spatial" else CONSTRUCTION_PROMPT_VERSION],
                "packages": {name: importlib.metadata.version(name) for name in
                             ("langchain", "langchain-core", "langgraph", "langchain-openai", "langsmith", "pydantic", "httpx", "numpy", "shapely", "pymupdf")},
                "acceptance": "Independent source checks on executed PGF plus separate blinded visual review; model completion is reported separately.",
                "timing": "Drawing includes model, tool, compiler HTTP and local orchestration. Preparation, calibration, offline evaluation and human/assistant review are separate.",
                "scope": spatial_pilot_cases.SCOPE if suite == "spatial" else "Three curated grade-7 Generate cases; two repetitions; no Edit, Reconstruct, 3D, training, post-hoc repairs or dataset promotion.",
                "selection": spatial_pilot_cases.SELECTION if suite == "spatial" else "Assistant-selected cases cover midpoint/rotation, projection/tangency, and reflection/intersection. Not a random or held-out generalization benchmark."}
    save(output / "protocol.json", protocol)
    for relative in protocol["code_sha256"]:
        path = output / "source_snapshot" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    print(json.dumps({"phase": "prepared", "drawings": len(order), "model_call_cap": protocol["maximum_model_calls"], "model": model.model_name}), flush=True)


def calibrate(output: Path, url: str, suite: str = "planar") -> None:
    if suite == "mixed":
        raise ValueError("Manifest studies use their frozen source-obligation calibration")
    cases = spatial_pilot_cases if suite == "spatial" else construction_pilot_cases
    report = {}
    with compiler(output / "calibration-http", url) as http:
        for case in cases.CASES:
            row = read(output / "references" / case / "original-record.json")
            for name, (tikz, expected) in cases.calibration_variants(case, row["target_tikz"]).items():
                directory = output / "calibration" / case / name
                started = perf_counter()
                if (directory / "observations.json").exists():
                    observation = read(directory / "observations.json")
                    if (observation['metadata'].get('schema_version') != SCHEMA_VERSION or
                            observation['metadata'].get('tracer_sha256') != TRACER_SHA256):
                        raise RuntimeError('Calibration schema changed; use a new revision')
                    expected_hash = hashlib.sha256(tikz.encode()).hexdigest()
                    if observation["metadata"]["input_tikz_sha256"] != expected_hash:
                        raise RuntimeError("Calibration source changed; retain evidence in a new revision")
                else:
                    observation = compile_observe(tikz, directory, http, preview=True)
                    save(directory / "observations.json", observation)
                checked = cases.check_output(case, read_scene(observation))
                passed = (set(expected) == set(checked["failed_checks"]) if name in {"target", "valid_similarity"} else set(expected) <= set(checked["failed_checks"])) if expected else checked["status"] == "pass"
                result = {"pass": passed, "expected_failures": expected, "checks": checked,
                          "seconds": perf_counter() - started, "image_path": observation["image_path"]}
                save(directory / "result.json", result)
                report[case + ":" + name] = result
                print(json.dumps({"calibration": case + ":" + name, "pass": result["pass"], "failed_checks": result["checks"]["failed_checks"]}), flush=True)
    save(output / "calibration.json", report)
    if not all(result["pass"] for result in report.values()):
        raise RuntimeError("Calibration failed; no model drawing is authorized by this runner until it passes")


def _invoke_spec_first(instruction, *, model, directory, http):
    return draw_spec_first(instruction=instruction, model=model, artifact_dir=directory, compiler_http=http)


def draw(output: Path, url: str, suite: str = "planar") -> None:
    cases = spatial_pilot_cases if suite == "spatial" else construction_pilot_cases
    protocol = read(output / "protocol.json")
    if protocol["code_sha256"] != code_hashes() or protocol["data_sha256"] != frozen_data_hashes(output):
        raise RuntimeError("Code changed after protocol freeze; use a new explicit run revision")
    if protocol.get("case_manifest"):
        jobs = protocol["order"]
        identities = [(job["case"], job["repetition"], job["arm"]) for job in jobs]
        pairs = {(case, repetition) for case, repetition, _ in identities}
        if (not jobs or len({job["key"] for job in jobs}) != len(jobs)
                or len(set(identities)) != len(jobs)
                or set(identities) != {(case, repetition, arm) for case, repetition in pairs for arm in ("native", "spec_first")}):
            raise ValueError("Manifest requires unique paired job keys and identities")
        frozen_worker = read(output / "worker-freeze.json")["files"]
        if any(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest for relative, digest in frozen_worker.items()):
            raise RuntimeError("Held-out worker changed after initial freeze")
    calibration = read(output / "calibration.json")
    expected = (set(protocol["calibration_keys"]) if protocol.get("case_manifest") else
                {case + ":" + name for case in cases.CASES for name in cases.calibration_variants(case, read(output / "references" / case / "original-record.json")["target_tikz"])})
    if not expected or set(calibration) != expected or not all(row["pass"] for row in calibration.values()):
        raise RuntimeError("Complete calibration has not passed")
    if (output / "provider-stop.json").exists():
        raise RuntimeError("Provider-stopped run cannot resume")
    if (output / "infrastructure-stop.json").exists():
        raise RuntimeError("Infrastructure-stopped run requires a fresh explicit revision")
    model = build_model(timeout=180, max_tokens=8192)
    if model.model_name != protocol["model"] or model_settings(model) != protocol["model_settings"] or url != protocol["compiler_url"]:
        raise RuntimeError("Pinned model/compiler configuration changed")
    with httpx.Client(base_url=url, timeout=5, trust_env=False) as http:
        ready = http.get("/readyz")
        ready.raise_for_status()
        if ready.json() != protocol["compiler_readiness"]:
            raise RuntimeError("Pinned compiler toolchain changed")
    if not os.environ.get("LANGSMITH_API_KEY") or not os.environ.get("LANGSMITH_PROJECT"):
        raise RuntimeError("Tracing credentials/project are required")
    input_rows = read(output / "inputs.json")
    input_records = {row["case"]: row for row in input_rows}
    if protocol.get("case_manifest") and (
            protocol.get("method") != "spec_first" or len(input_records) != len(input_rows)
            or set(input_records) != {job["case"] for job in protocol["order"]}
            or any(row.get("dimension") not in (2, 3) for row in input_rows)):
        raise ValueError("Invalid frozen study input coverage or dimensions")
    inputs = {case: row["instruction"] for case, row in input_records.items()}
    method = protocol.get("method", "construction")
    agents = {"native": harness.build_tikz_agent(model, max_model_calls=MAX_MODEL_CALLS)}
    if method == "construction":
        agents["construction"] = construction_harness.build_construction_agent(
            model, max_model_calls=MAX_MODEL_CALLS, spatial=suite == "spatial")
    client = Client()
    try:
        for job in protocol["order"]:
            directory = output / "drawings" / job["key"]
            if (directory / "attempt.json").exists():
                continue  # Never silently rerun an attempted invocation.
            ledger = {output, *(Path(p).resolve() for p in protocol.get("budget_ledger", []))}
            if any(not p.is_relative_to(ROOT / "runs") for p in ledger):
                raise ValueError("Budget ledger must reference local run folders")
            used_calls = sum(len(read(p)) for folder in ledger for p in (folder / "drawings").glob("*/model_calls.json"))
            used_compiles = sum(len(read(p)) for folder in ledger for p in (folder / "drawings").glob("*/http/requests.json"))
            next_calls = 1 if job["arm"] == "spec_first" else MAX_MODEL_CALLS
            next_compiles = 1 if job["arm"] == "spec_first" else MAX_COMPILES
            if (used_calls + next_calls > protocol.get("aggregate_model_call_cap", protocol["maximum_model_calls"])
                    or used_compiles + next_compiles > protocol.get("aggregate_compile_cap", len(protocol["order"]) * MAX_COMPILES)):
                save(output / "budget-stop.json", {"next_job": job, "used_calls": used_calls, "used_compiles": used_compiles})
                break
            # Recheck before spending the next job's model budget: a pinned image
            # can disappear after the initial readiness check. Never auto-resume.
            try:
                with httpx.Client(base_url=url, timeout=5, trust_env=False) as health:
                    ready = health.get("/readyz")
                    ready.raise_for_status()
                    if ready.json() != protocol["compiler_readiness"]:
                        raise ValueError("Pinned compiler toolchain changed")
            except (httpx.HTTPError, ValueError) as error:
                save(output / "infrastructure-stop.json", {"next_job": job, "error": type(error).__name__ + ": " + str(error)})
                break
            recorder = Recorder(directory)
            trace_id = uuid4()
            record = {**job, "trace_id": str(trace_id), "started_at": datetime.now(timezone.utc).isoformat(), "error": None}
            save(directory / "attempt.json", record)
            spatial_job = input_records[job["case"]].get("dimension", 3 if suite == "spatial" else 2) == 3
            method_messages = spatial_construction_messages if spatial_job else construction_messages
            closed_solid = input_records[job["case"]].get("closed_solid", spatial_job)
            native_messages = spatial_task_messages if spatial_job and closed_solid else problem_tikz_messages
            messages = (method_messages if job["arm"] == "construction" else native_messages)(inputs[job["case"]])
            started = perf_counter()
            with compiler(directory / "http", url, limit=1 if job["arm"] == "spec_first" else MAX_COMPILES) as http:
                try:
                    with tracing_context(enabled=True, client=client, project_name=os.environ["LANGSMITH_PROJECT"], parent=False):
                        config = {"run_id":trace_id, "callbacks":[recorder], "tags":["construction-pilot", method, job["arm"]],
                                      "metadata":{"case":job["case"], "repetition":job["repetition"], "suite":suite,
                                                  "method_version":SPEC_FIRST_PROMPT_VERSION if method == "spec_first" else SPATIAL_PROMPT_VERSION if suite == "spatial" else CONSTRUCTION_PROMPT_VERSION}}
                        if job["arm"] == "spec_first":
                            workflow = RunnableLambda(partial(_invoke_spec_first, model=model, directory=directory, http=http), name="spec_first")
                            result = workflow.invoke(inputs[job["case"]], config=config)
                        else:
                            configured = agents[job["arm"]].with_config(**config)
                            draw = construction_harness.draw_construction if job["arm"] == "construction" else harness.draw_tikz
                            result = draw(messages=messages, artifact_dir=directory, agent=configured, compiler_http=http)
                    record["result"] = result.model_dump(mode="json")
                except Exception as error:  # noqa: BLE001 -- checkpoint one failed bounded invocation, never retry it
                    record["error"] = type(error).__name__ + ": " + str(error)
                record.update(seconds=perf_counter() - started, model_calls=len(recorder.calls),
                              model_seconds=sum(call["seconds"] or 0 for call in recorder.calls),
                              compile_calls=len(http.records), compile_seconds=sum(row["seconds"] or 0 for row in http.records),
                              tool_errors=sum(row.get("status") == "error" for row in recorder.tool_events),
                              usage={key: sum(call["usage"].get(key, 0) or 0 for call in recorder.calls) for key in ("input_tokens", "output_tokens", "total_tokens")})
                if (directory / "stages.json").exists():
                    record["stages"] = read(directory / "stages.json")
                save(directory / "attempt.json", record)
            print(json.dumps({key: record.get(key) for key in ("key", "seconds", "model_calls", "compile_calls", "tool_errors", "error")}), flush=True)
            if any(call["error"] for call in recorder.calls):
                save(output / "provider-stop.json", record)
                break
        wait_for_all_tracers()
        client.flush()
        trace_checks = []
        for path in (output / "drawings").glob("*/attempt.json"):
            record = read(path)
            try:
                run = client.read_run(record["trace_id"])
                trace_checks.append({"key": record["key"], "readable": True, "error": run.error, "url": client.get_run_url(run=run)})
            except Exception as error:  # noqa: BLE001 -- retain trace-verification failure without changing drawing results
                trace_checks.append({"key": record["key"], "readable": False, "error": type(error).__name__ + ": " + str(error)})
        save(output / "traces.json", trace_checks)
    finally:
        client.close()


def evaluate_outputs(output: Path, url: str, suite: str = "planar") -> None:
    cases = spatial_pilot_cases if suite == "spatial" else construction_pilot_cases
    for path in (output / "drawings").glob("*/attempt.json"):
        record, directory = read(path), path.parent
        if (directory / "evaluation.json").exists():
            continue
        tikz = record.get("result", {}).get("tikz")
        if not tikz:
            save(directory / "evaluation.json", {"status": "unavailable", "reason": "No delivered TikZ", "mathematics_pass": None, "geometry_content_pass": None})
            continue
        started = perf_counter()
        with compiler(directory / "evaluation-http", url) as http:
            observation = compile_observe(tikz, directory / "evaluation", http, preview=True)
            save(directory / "evaluation/observations.json", observation)
            reference = read(output / "calibration" / record["case"] / "target/observations.json")
            error = None
            try:
                metrics = _score_observations(reference, observation)
            except (EvaluationError, EvaluationInfrastructureError) as failure:
                metrics, error = failure.scores, str(failure)
            try:
                if not observation["compile_success"] and observation.get("compile", {}).get("outcome") in (None, "unknown"):
                    checked = {"status": "unavailable", "mathematics_pass": None, "geometry_content_pass": None,
                               "reason": "Compiler evidence unavailable"}
                elif not observation["compile_success"]:
                    checked = {"status": "held", "mathematics_pass": False, "geometry_content_pass": False, "failed_checks": ["compile"]}
                elif read(output / "protocol.json").get("case_manifest"):
                    checked = {"status": "unreviewed", "mathematics_pass": None, "geometry_content_pass": None,
                               "reason": "Manifest source obligations are evaluated separately; shared scores are not instruction fidelity."}
                elif read(output / "protocol.json").get("method") == "spec_first":
                    checked = spec_first_pilot_cases.check_output(record["case"], read_scene(observation), suite=suite)
                else:
                    checked = cases.check_output(record["case"], read_scene(observation))
            except (ValueError, ArithmeticError) as failure:
                checked = {"status": "unavailable", "mathematics_pass": None, "geometry_content_pass": None, "failed_checks": ["observations"], "observation_error": str(failure)}
            result = {**checked, "metrics": metrics, "metric_error": error, "seconds": perf_counter() - started,
                      "compile_calls": len(http.records), "image_path": observation["image_path"]}
            save(directory / "evaluation.json", result)
            print(json.dumps({"evaluation": record["key"], "status": result["status"], "mathematics_pass": result["mathematics_pass"], "failed": result.get("failed_checks"), "metrics": metrics}), flush=True)


def summarize(output: Path, suite: str = "planar") -> None:
    rows = []
    for job in read(output / "protocol.json")["order"]:
        directory = output / "drawings" / job["key"]
        if (directory / "attempt.json").exists():
            record = read(directory / "attempt.json")
            record["evaluation"] = read(directory / "evaluation.json") if (directory / "evaluation.json").exists() else None
            rows.append(record)
    groups = {}
    method = read(output / "protocol.json").get("method", "construction")
    for arm in ("native", method):
        selected = [row for row in rows if row["arm"] == arm and row.get("seconds") is not None]
        if not selected:
            continue
        accepted = sum((row.get("evaluation") or {}).get("status") == "pass" for row in selected)
        groups[arm] = {"n": len(selected), "model_calls": sum(row["model_calls"] for row in selected),
                       "compile_calls": sum(row["compile_calls"] for row in selected),
                       "mean_seconds": statistics.mean(row["seconds"] for row in selected),
                       "median_seconds": statistics.median(row["seconds"] for row in selected),
                       "mean_model_seconds": statistics.mean(row["model_seconds"] for row in selected),
                       "mean_compile_seconds": statistics.mean(row["compile_seconds"] for row in selected),
                       "mathematics_pass": sum(bool((row.get("evaluation") or {}).get("mathematics_pass")) for row in selected),
                       "mathematics_unavailable": sum((row.get("evaluation") or {}).get("mathematics_pass") is None for row in selected),
                       "executable_acceptance": accepted,
                       "geometry_content_pass": sum(bool((row.get("evaluation") or {}).get("geometry_content_pass")) for row in selected),
                       "mean_realization_seconds": statistics.mean((row.get("stages") or {}).get("realization_seconds", 0) for row in selected),
                       "drawing_seconds_per_executable_pass": sum(row["seconds"] for row in selected) / accepted if accepted else None}
    expected_jobs = read(output / "protocol.json")["order"]
    finished = {row["key"] for row in rows if row.get("seconds") is not None and row.get("evaluation") is not None}
    pairs = sorted({(job["case"], job["repetition"]) for job in expected_jobs})
    complete_pairs = [f"{case}-{repetition}" for case, repetition in pairs
                      if all(any(job["key"] in finished for job in expected_jobs
                                 if job["case"] == case and job["repetition"] == repetition and job["arm"] == arm)
                             for arm in ("native", method))]
    save(output / "summary.json", {"arms": groups, "rows": rows, "complete_pairs": complete_pairs,
        "missing_jobs": [job["key"] for job in expected_jobs if job["key"] not in finished],
        "comparison_complete": len(complete_pairs) == len(pairs), "visual_review": "Separate review required; executable acceptance alone is not final approval."})
    print(json.dumps(groups, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "calibrate", "draw", "evaluate", "report"])
    parser.add_argument("--suite", choices=["planar", "spatial", "mixed"])
    parser.add_argument("--method", choices=["construction", "spec_first"], default="construction")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--compiler-url", default="http://127.0.0.1:18080")
    args = parser.parse_args()
    protocol_path = args.output / "protocol.json"
    suite = args.suite or (read(protocol_path).get("suite", "planar") if protocol_path.exists() else "planar")
    if protocol_path.exists() and suite != read(protocol_path).get("suite", "planar"):
        raise ValueError("Cannot change suite for an existing run")
    if args.phase == "report":
        summarize(args.output.resolve(), suite)
    elif args.phase == "prepare":
        prepare(args.output.resolve(), args.compiler_url, suite, args.method)
    else:
        {"calibrate": calibrate, "draw": draw, "evaluate": evaluate_outputs}[args.phase](args.output.resolve(), args.compiler_url, suite)


if __name__ == "__main__":
    main()
