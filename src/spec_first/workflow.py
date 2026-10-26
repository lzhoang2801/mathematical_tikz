"""One semantic extraction call followed by deterministic construction and rendering."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

from pydantic import ValidationError

from agent.latex.tikz import standalone_tikz_document
from spec_first.prompts.spec_first import spec_first_messages
from agent.schemas.tikz import TikzResult
from spec_first.spec import GeometrySpec, SpecError, instruction_preflight, realize_spec
from agent.workflows.tikz import Context, render_tikz


def _save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n',encoding='utf-8')


def draw_spec_first(*, instruction: str, model, artifact_dir: Path, compiler_http):
    """The only model step is extraction; failures are retained without silent retries."""
    directory = Path(artifact_dir)
    directory.mkdir(parents=True,exist_ok=True)
    stages = {'extraction_calls':0,'extraction_seconds':0.0,'realization_seconds':0.0,'render_seconds':0.0,
              'failure_stage':None,'failure_category':None,'status':'running'}
    stage = 'instruction_preflight'
    started = perf_counter()
    try:
        audit = instruction_preflight(instruction)
        _save(directory/'instruction-preflight.json',audit)
        stage,started = 'extraction',perf_counter()
        structured = model.with_structured_output(GeometrySpec,method='function_calling',include_raw=True)
        stages['extraction_calls'] = 1
        response = structured.invoke(spec_first_messages(instruction))
        stages['extraction_seconds'] = perf_counter()-started
        _save(directory/'specification-response.json',response['raw'].model_dump(mode='json'))
        spec,raw = response['parsed'],response['raw']
        stages['response_format'] = 'tool_call'
        if spec is None and isinstance(raw.content,str) and not raw.tool_calls and not raw.invalid_tool_calls:
            # Same complete-JSON transport fallback as tools/generate_instruction.py.
            # No prose extraction, partial JSON repair, schema relaxation or model retry.
            candidate = raw.content
            for newline in ('\n','\r\n'):
                opening,closing = f'```json{newline}',f'{newline}```'
                if candidate.startswith(opening) and candidate.endswith(closing):
                    candidate = candidate[len(opening):-len(closing)]
                    break
            try:
                spec = GeometrySpec.model_validate_json(candidate)
            except ValidationError as error:
                raise SpecError('invalid_spec',str(error)) from error
            stages['response_format'] = 'json_text_fallback'
        if not isinstance(spec,GeometrySpec):
            raise SpecError('invalid_spec',str(response['parsing_error'] or 'No parsed specification'))
        _save(directory/'specification.json',spec.model_dump(mode='json'))
        stage,started = 'realization',perf_counter()
        source,evidence = realize_spec(spec,instruction)
        stages['realization_seconds'] = perf_counter()-started
        evidence['tikz_sha256'] = hashlib.sha256(source.encode()).hexdigest()
        _save(directory/'realization.json',evidence)
        _save(directory/'admitted-specification.json',evidence['spec'])
        _save(directory/'instruction-admission.json',evidence['instruction_audit'])
        (directory/'precompile.tikz').write_text(source,encoding='utf-8')
        stage,started = 'render',perf_counter()
        _,artifact = render_tikz.func(source,SimpleNamespace(context=Context(directory,compiler_http)))
        stages['render_seconds'] = perf_counter()-started
        # Usable generated output is not independent mathematical acceptance.
        result = TikzResult(success=False,status='usable_with_issues',usable=True,tikz=artifact['tikz'],
                            rendered_png_path=artifact['rendered_png_path'],unresolved_issues=[
                                'Supplied specification validated; instruction completeness requires independent review.'])
        stages['status'] = 'rendered_without_model_review'
        stages['supplied_spec_validated'] = True
        stages['instruction_coverage_verified'] = False
        (directory/'main.tex').write_text(standalone_tikz_document(result.tikz),encoding='utf-8')
        _save(directory/'result.json',result.model_dump(mode='json'))
        return result
    except Exception as error:
        stages[stage+'_seconds'] = perf_counter()-started
        stages.update(status='failed',failure_stage=stage,
                      failure_category=getattr(error,'category',type(error).__name__),error=str(error))
        raise
    finally:
        _save(directory/'stages.json',stages)
