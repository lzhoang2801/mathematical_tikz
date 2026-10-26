"""Notebook transport to the shared compiler worker and current PGF evaluator."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

import httpx

from evaluation.evaluator import _score_observations
from evaluation.tikz_observations import SCHEMA_VERSION, TRACER_SHA256, compile_observe
from latex_compiler.schemas import MAX_ARTIFACT_BYTES, MAX_RESPONSE_BYTES, CompileRequest, CompileResponse, RenderResponse


def worker_response(payload: CompileRequest, raw: bytes, toolchain: str) -> CompileResponse:
    """Validate the existing worker's compile receipt followed by its optional raster receipt."""
    lines = raw.splitlines()
    if not lines or any(len(line) > MAX_RESPONSE_BYTES for line in lines):
        raise ValueError("Missing or oversized compiler receipt")
    response = CompileResponse.model_validate_json(lines[0])
    expected = 2 if response.compile.success and payload.outputs.images is not None else 1
    if len(lines) != expected:
        raise ValueError("Incomplete compiler/raster protocol")
    if response.compile.success and (payload.outputs.pdf or payload.outputs.images is not None) and not any(a.name == "result.pdf" and a.complete for a in response.artifacts):
        raise ValueError("Successful compiler omitted its PDF")
    if expected == 2:
        raster = RenderResponse.model_validate_json(lines[1])
        pdf = next(a for a in response.artifacts if a.name == "result.pdf")
        if raster.pdf_sha256 and raster.pdf_sha256 != hashlib.sha256(pdf.data).hexdigest():
            raise ValueError("Raster receipt does not match the compiled PDF")
        response.raster, response.page_count = raster.raster, raster.page_count
        response.artifacts.extend(raster.artifacts)
    if sum(len(a.data) for a in response.artifacts) > MAX_ARTIFACT_BYTES:
        raise ValueError("Combined compiler artifacts exceed quota")
    if not payload.outputs.pdf and (payload.outputs.images is None or response.raster.success):
        response.artifacts = [artifact for artifact in response.artifacts if artifact.name != 'result.pdf']
    response.toolchain_id = toolchain
    response.source_digest = payload.digest(toolchain)
    return response


def local_compiler() -> httpx.Client:
    """Transport-only bridge to the pinned worker; no changes to TeX wrapping or metric logic."""
    fingerprint = subprocess.check_output(["xelatex", "--version"], timeout=10)
    fingerprint += subprocess.check_output(["latexmk", "--version"], timeout=10)
    fingerprint += subprocess.check_output(["dpkg-query", "-W", "texlive*", "latexmk"], timeout=10)
    import pymupdf
    fingerprint += pymupdf.VersionBind.encode()
    toolchain = "kaggle-xelatex:" + hashlib.sha256(fingerprint).hexdigest()
    root = Path(__file__).resolve().parents[1] / "src"

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method != "POST" or request.url.path != "/compile":
            return httpx.Response(404)
        payload = CompileRequest.model_validate_json(request.content)
        env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH") if key in os.environ}
        env.update(PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", OMP_NUM_THREADS="1")
        with tempfile.TemporaryDirectory(prefix="tikz-worker-") as directory:
            env.update(HOME=directory, TMPDIR=directory, TEXMFVAR=directory, TEXMFCONFIG=directory)
            # Notebook process limits are not equivalent to the production Docker sandbox.
            command = ["prlimit", "--as=2147483648", "--fsize=67108864", "--nproc=128", "--cpu=120",
                       sys.executable, "-B", "-m", "latex_compiler.worker", "compile"]
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, cwd=directory, env=env, start_new_session=True)
            try:
                raw, errors = process.communicate(payload.model_dump_json().encode() + b"\n\n", timeout=125)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                return httpx.Response(503, text="Compiler process-group deadline exceeded")
            if process.returncode:
                return httpx.Response(503, text=errors.decode(errors="replace")[-2000:])
            try:
                response = worker_response(payload, raw, toolchain)
            except ValueError as error:
                return httpx.Response(503, text=str(error))
            return httpx.Response(200, json=response.model_dump())

    return httpx.Client(base_url="http://kaggle-compiler", transport=httpx.MockTransport(handle), timeout=200,
                        headers={"X-TikZ-Toolchain-ID": toolchain})


def observation(code: str, directory: Path, compiler: httpx.Client, *, preview: bool = False) -> dict:
    path = directory / "observations.json"
    if path.exists():
        result = json.loads(path.read_text(encoding="utf-8"))
        if result["metadata"]["input_tikz_sha256"] != hashlib.sha256(code.encode()).hexdigest():
            raise ValueError("Cached diagram source changed")
        if (result['metadata'].get('schema_version') != SCHEMA_VERSION or
                result['metadata'].get('tracer_sha256') != TRACER_SHA256):
            raise ValueError('Cached evaluator schema changed; use a new output directory')
        recorded_toolchain = result["metadata"].get("toolchain_id")
        if recorded_toolchain and recorded_toolchain != compiler.headers["X-TikZ-Toolchain-ID"]:
            raise ValueError("Cached compiler version changed; use a new output directory")
        if (result.get("compile", {}).get("outcome") not in (None, "unknown") and not result['metadata'].get('trace_error')
                and (not preview or result.get('image_path') or not result.get('compile_success'))):
            for artifact in result.get("artifacts", {}).get("pgf", {}).values():
                if hashlib.sha256(Path(artifact["path"]).read_bytes()).hexdigest() != artifact["sha256"]:
                    raise ValueError("Cached diagram artifact changed")
            return result
    result = compile_observe(code, directory, compiler, preview=preview)
    result["tikz"] = code
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def evaluate_pair(target_tikz: str, output_tikz: str, directory: Path, compiler: httpx.Client) -> dict:
    """Use the same observer/scorer as evaluation.evaluator.evaluate, with caller-owned transport."""
    target = observation(target_tikz, directory / hashlib.sha256(target_tikz.encode()).hexdigest(), compiler)
    output = target if output_tikz == target_tikz else observation(
        output_tikz, directory / hashlib.sha256(output_tikz.encode()).hexdigest(), compiler,
    )
    return _score_observations(target, output)
