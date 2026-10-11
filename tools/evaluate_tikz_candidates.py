"""Independently evaluate eight frozen candidates and a one-call generation baseline."""
from __future__ import annotations
import argparse
import ast
import json
import math
import re
from pathlib import Path
from typing import Literal
import prepare_tikz_candidates as prep
from prepare_tikz_candidates import (
    ROOT, RUN, CANDIDATES, Candidate, Check, SETTINGS,
    configure, rows, dump, sha, model_call, validate_tikz,
    BaseModel,
)

from agent.latex.compiler import compile_tex
from agent.latex.tikz import standalone_tikz_document
from agent.utils.media import image_content_block
from IR_model import TikzIR
from evaluator import Evaluator
from verify_diagram_ir import evaluate_ir

# Experiment tolerances, fixed before drawing. Not a general dataset standard.
REL_TOL = 0.005
ANGLE_TOL = math.sin(math.radians(1))
AUDIT = r"""Audit this prepared Vietnamese diagram dataset candidate against its original
problem and sample TikZ. Return a corrected complete Candidate. Do not generate a model-test
output; this is offline dataset preparation before freezing. Fix these failure modes:
- Every instruction condition needs a rubric item/check, including strict inequalities,
  incidence, segment/ray order, second/distinct intersections, tangencies and given ratios.
- Do NOT demand any relation mark or dash/style absent an explicit instruction request.
  Visual readability checks readability, not an invented requirement for all right-angle marks.
- Include explicit visible labels and required lines/circles; internal coordinates alone
  do not prove coverage. Add a content-scope item that rejects meaningful extraneous objects.
- Checks belong only in mathematical_correctness, never compile/coverage/readability.
- Do not invent a point label just to fit a check. Hidden circle centers in sample code are
  not required labels: evaluate the actual drawn circle via code/render inspection if needed.
- Keep each requirement verifiable, include allowed scale/rotation/layout differences when
  they preserve meaning, preserve numeric givens as visible labels without forcing canvas units.
- Source says 'line AH' in bai-06: F may be beyond H; draw the line through F.
- Drawing proof configurations does not mean printing proof conclusions.
Keep existing valid target construction; make only necessary compatibility/math/scope repairs.
If the target changes, list the concrete change. Do not assert compile success without running.
Include concrete pass conditions for ALL four dimensions, with checks per supported syntax.
Avoid a single generic coverage check that loses requested segments/rays/labels.
"""
class GeneratedTikz(BaseModel):
    tikz: str

class Grade(BaseModel):
    id: str
    status: Literal["pass", "fail", "unknown"]
    evidence: str
class Review(BaseModel):
    grades: list[Grade]
    overall_findings: list[str]

JUDGE = r"""Evaluate the produced diagram against the supplied frozen instruction and rubric.
Use the target as one valid reference, not a pixel/code template. The supplied images are
TARGET then OUTPUT. Follow only the fixed rubric; do not invent marks, labels, constraints,
or numerical values. Each criterion must receive pass/fail/unknown with concrete evidence.
Do not infer a line is drawn merely because a coordinate/path is defined. Distinguish visible
segments from infinite construction lines. Inspect tangency, incidence, missing content,
wrong numerical labels, labels on wrong points, clipping and unreadability.
Compilation is supplied evidence; do not rejudge it visually. Mathematical claims from this
model are diagnostic; deterministic checks are evaluated separately. If uncertain, unknown.
Return every rubric id exactly once. Preserve acceptable equivalent layouts/code/styles.
"""

def audit_case(record):
    dest=RUN/record["id"]
    source=next(r for r in rows(prep.SOURCES) if r["id"]==record["id"])
    path=dest/"audit"/"parsed.json"
    if path.exists():
        candidate=Candidate.model_validate_json(path.read_text(encoding="utf-8"))
    else:
        candidate=model_call(Candidate,[("system",prep.PREPARE+"\n"+AUDIT),
            ("human",json.dumps({"source":source,"prepared_candidate":record},ensure_ascii=False))],
            dest/"audit","audit-candidate",record["id"],
            settings={**SETTINGS,"model":"gemini-3.1-flash-lite","thinking_level":"low"})
    prep.validate_candidate(candidate)
    report=prep.compile_target(candidate.target_tikz,dest/"target-audited")
    dump(dest/"target-audited"/"verification.json",report)
    if not report["success"]: raise RuntimeError(f"Audited target failed: {record['id']}: {report.get('diagnostic')}")
    audited={**record,**candidate.model_dump(mode="json"),
             "target_artifact_dir":str(dest/"target-audited"),"agent_review_status":"audited_before_generation"}
    dump(dest/"candidate-audited.json",audited)
    return audited

def freeze(records):
    expected={r["id"] for r in rows(prep.SOURCES)}
    assert len(records)==len(expected)==8 and {r["id"] for r in records}==expected, "Freeze the eight unique authorized cases"
    for r in records:
        assert r.get("agent_review_status")=="audited_before_generation"
        source=next(x for x in rows(prep.SOURCES) if x["id"]==r["id"])
        assert r["source_sha256"]==sha(json.dumps(source,ensure_ascii=False,sort_keys=True)), "Source changed"
        calibration=json.loads((RUN/r["id"]/"calibration/calibration.json").read_text(encoding="utf-8"))
        assert calibration["target_sha256"]==sha(r["target_tikz"]) and not calibration["failures"] and not calibration["unknown"], "Target calibration missing/stale/failed"
        assert calibration["checks"], "Empty mathematical calibration"
        control=json.loads((RUN/r["id"]/"controls/summary.json").read_text(encoding="utf-8"))
        assert all(x["compile_success"] for x in control["results"])
        assert all(x["status"]=="pass" for x in control["results"][0]["checks"])
        assert any(x["status"]=="fail" for x in control["results"][1]["checks"])
        assert calibration["rubric_sha256"]==sha(json.dumps(r["evaluation_rubric"],sort_keys=True)), "Rubric changed after calibration"
        prep.validate_candidate(Candidate.model_validate({k:r[k] for k in Candidate.model_fields}))
    payload="".join(json.dumps(r,ensure_ascii=False)+"\n" for r in records)
    contract={"candidate_sha256":sha(payload),"relative_tolerance":REL_TOL,
              "angle_tolerance_degrees":1,"generation_calls_per_case":1,
              "online_review_calls":0,"provider_retries":0,
              "decision":"per-dimension diagnostics; unknown is never pass; no unvalidated aggregate gold score",
              "scope":"8 development Generate candidates, not independent held-out benchmark",
              "code_sha256":sha(Path(__file__).read_text(encoding="utf-8"))}
    path=RUN/"frozen.json"
    if path.exists():
        assert json.loads(path.read_text(encoding="utf-8"))["candidate_sha256"]==contract["candidate_sha256"],"Frozen candidate changed"
    else:
        CANDIDATES.write_text(payload,encoding="utf-8")
        dump(path,contract)
    return contract

def draw(record):
    """One model call, instruction only; compilation and evaluation are independent."""
    folder=RUN/record["id"]/"draw"
    if (folder/"result.json").exists():
        return json.loads((folder/"result.json").read_text(encoding="utf-8"))
    prompt=r"""Draw the requested mathematical diagram as one self-contained
\begin{tikzpicture}...\end{tikzpicture}. Return only the structured tikz field.
No preamble. Libraries available: calc,angles,quotes,intersections,through,positioning,
arrows.meta,patterns; tkz-euclide is loaded. Use public TikZ syntax, no overlay, clipping,
raw TeX definitions/conditionals or undefined custom pics. Preserve mathematical conditions,
draw all requested objects and place labels legibly. Arbitrary canvas scale is allowed.
The user instruction is the entire drawing task; do not add proof text or invented givens.
"""
    try:
        generated=model_call(GeneratedTikz,[("system",prompt),("human",record["instruction"])],
                             folder/"generation","direct-tikz-baseline",record["id"],allow_retry=False)
        compiled=prep.compile_target(generated.tikz,folder/"render")
        dump(folder/"render/verification.json",compiled)
        data={"tikz":generated.tikz,"compile_success":compiled["success"],
              "rendered_png_path":str(folder/"render/target-1.png") if compiled["success"] else None,
              "generation_design":"single call; instruction only; no online review or repair",
              "diagnostic":compiled.get("diagnostic")}
        dump(folder/"result.json",data)
        return data
    except Exception as error:
        dump(folder/"error.json",{"error":f"{type(error).__name__}: {error}"})
        raise


def measure_points(tikz, names, folder):
    """Read actual PGF named-coordinate positions; no model-inferred coordinates."""
    path=folder/"points.json"
    if path.exists():
        cached=json.loads(path.read_text(encoding="utf-8"))
        if cached["tikz_sha256"] != sha(tikz):
            raise ValueError("Stale coordinate evidence: use a new artifact directory")
        return cached
    assert all(re.fullmatch(r"[A-Za-z]{1,3}",n) for n in names)
    probes=[]
    for n in sorted(names):
        probes.append(r"\ifcsname pgf@sh@ns@"+n+r"\endcsname"+
                      r"\path ("+n+r");\pgfgetlastxy{\cfx}{\cfy}"+
                      r"\typeout{CFPOINT|"+n+r"|\cfx|\cfy}\fi")
    source=validate_tikz(tikz).replace(r"\end{tikzpicture}","\n".join(probes)+"\n"+r"\end{tikzpicture}")
    compiled=compile_tex(standalone_tikz_document(source),tex_path=folder/"measurement.tex",
                         log_path=folder/"measurement.log",timeout_seconds=45,infrastructure_retries=0)
    text=(folder/"measurement.log").read_text(encoding="utf-8",errors="replace") if (folder/"measurement.log").exists() else ""
    matches=re.findall(r"CFPOINT\|([A-Za-z]+)\|([-0-9.]+)pt\|([-0-9.]+)pt",text)
    points={n:[float(x),float(y)] for n,x,y in matches}
    result={"success":compiled.success,"points":points,"missing":sorted(set(names)-set(points)),
            "units":"TeX points in the actual TikZ coordinate system",
            "diagnostic":compiled.diagnostic,"tikz_sha256":sha(tikz)}
    dump(path,result)
    return result

def check(q, points):
    """Return normalized residuals, not a model's geometric verdict."""
    if any(n not in points for n in q.points):
        return {"status":"unknown","reason":"Named-coordinate binding missing; inspect labels/code"}
    p=[points[n] for n in q.points]
    def sub(a,b): return (a[0]-b[0],a[1]-b[1])
    def dot(a,b): return a[0]*b[0]+a[1]*b[1]
    def cross(a,b): return a[0]*b[1]-a[1]*b[0]
    def norm(a): return math.hypot(*a)
    def dist(a,b): return norm(sub(a,b))
    scale=max((dist(a,b) for a in p for b in p),default=0)
    if scale<=1e-9: return {"status":"fail","reason":"Degenerate configuration"}
    try:
        op=q.op
        threshold=REL_TOL
        if op in ("perpendicular","parallel","equal_length","length_ratio","shorter"):
            a,b=sub(p[1],p[0]),sub(p[3],p[2])
            da,db=norm(a),norm(b)
            if min(da,db)<scale*1e-6: raise ValueError("Zero-length segment")
            if op in ("perpendicular","parallel"):
                residual=abs((dot if op=="perpendicular" else cross)(a,b))/(da*db)
                threshold=ANGLE_TOL
                passed=residual<=threshold
            elif op=="shorter":
                residual=da/db
                passed=residual < 1-1e-5
            else:
                residual=abs(da/db-(q.value if op=="length_ratio" else 1))
                threshold=REL_TOL*abs(q.value if op=="length_ratio" else 1)
                passed=residual<=threshold
        elif op=="midpoint":
            residual=dist(p[0],[(p[1][0]+p[2][0])/2,(p[1][1]+p[2][1])/2])/scale
            passed=residual<=threshold
        elif op in ("on_circle","outside_circle"):
            radius=dist(p[1],p[2])
            if radius<scale*1e-6: raise ValueError("Zero radius")
            ratio=dist(p[0],p[1])/radius
            residual=abs(ratio-1) if op=="on_circle" else ratio
            passed=residual<=threshold if op=="on_circle" else ratio>1+1e-5
        elif op in ("collinear","between","same_ray"):
            a,b=(sub(p[0],p[1]),sub(p[2],p[1])) if op!="collinear" else (sub(p[1],p[0]),sub(p[2],p[0]))
            if min(norm(a),norm(b))<scale*1e-6: raise ValueError("Undefined line")
            residual=abs(cross(a,b))/(norm(b)*scale)
            parameter=dot(a,b)/dot(b,b)
            passed=residual<=threshold and (op=="collinear" or (1e-5<parameter<1-1e-5 if op=="between" else parameter>1e-5))
        elif op=="minor_arc":
            k,o,b,c=p
            radius=dist(o,b)
            if radius<scale*1e-6: raise ValueError("Zero radius")
            angles=[math.atan2(x[1]-o[1],x[0]-o[0]) for x in (k,b,c)]
            wrap=lambda x:(x+math.pi)%(2*math.pi)-math.pi
            whole=wrap(angles[2]-angles[1])
            if abs(abs(whole)-math.pi)<1e-5 or abs(whole)<1e-5:
                raise ValueError("Minor arc undefined for coincident or antipodal endpoints")
            part=wrap(angles[0]-angles[1])
            residual=max(abs(dist(k,o)/radius-1),abs(dist(c,o)/radius-1))
            passed=residual<=threshold and part*whole>0 and abs(part)<abs(whole)-1e-5
        elif op in ("tangent","tangent_circumcircle"):
            if op=="tangent":
                center,witness,a,b=p
                radius=dist(center,witness)
            else:
                a,b,c,d,e=p
                dx,dy=sub(d,c); ex,ey=sub(e,c)
                det=2*(dx*ey-dy*ex)
                if abs(det)<scale*scale*1e-6: raise ValueError("Collinear circumcircle witnesses")
                ux=((dx*dx+dy*dy)*ey-(ex*ex+ey*ey)*dy)/det
                uy=(dx*(ex*ex+ey*ey)-ex*(dx*dx+dy*dy))/det
                center=[c[0]+ux,c[1]+uy]
                radius=dist(center,c)
            direction=sub(b,a)
            if min(radius,norm(direction))<scale*1e-6: raise ValueError("Undefined tangent line/circle")
            residual=abs(abs(cross(direction,sub(center,a)))/(norm(direction)*radius)-1)
            passed=residual<=threshold
        elif op=="concyclic":
            a,b,c,d=p
            bx,by=sub(b,a); cx,cy=sub(c,a)
            det=2*(bx*cy-by*cx)
            if abs(det)<scale*scale*1e-6: raise ValueError("Collinear circle witnesses")
            ux=((bx*bx+by*by)*cy-(cx*cx+cy*cy)*by)/det
            uy=(bx*(cx*cx+cy*cy)-cx*(bx*bx+by*by))/det
            center=[a[0]+ux,a[1]+uy]
            residual=abs(dist(center,d)/dist(center,a)-1)
            passed=residual<=threshold and min(dist(x,y) for i,x in enumerate(p) for y in p[i+1:])>scale*1e-5
        else: raise ValueError("Unsupported check")
        return {"status":"pass" if passed else "fail","residual":residual,"tolerance":threshold}
    except (ZeroDivisionError,ValueError) as error:
        return {"status":"unknown","reason":str(error)}

def extract_ir(tikz, folder, case_id):
    tree=ast.parse((ROOT/"DiagramIR/backtranslation.py").read_text(encoding="utf-8"))
    prompt=next(ast.literal_eval(n.value).strip() for n in tree.body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id=="BACKTRANSLATION_PROMPT_SMALL" for t in n.targets))
    input_path=folder/"observed.tikz"
    if input_path.exists():
        assert input_path.read_text(encoding="utf-8")==tikz, "Stale IR extraction input"
    else:
        input_path.write_text(tikz,encoding="utf-8")
    path=folder/"extract"/"parsed.json"
    if not path.exists():
        model_call(TikzIR,[("human",prompt.replace("{tikz_code}",tikz))],
                   folder/"extract","extract-observed-diagramir",case_id)
    # Save canonical aliases; bind observations to the exact produced code.
    metadata={"path":str(path.relative_to(ROOT).as_posix()),"sha256":sha(path.read_text(encoding="utf-8")),
              "tikz_sha256":sha(tikz),"extraction_method":"Gemini + upstream BACKTRANSLATION_PROMPT_SMALL",
              "unsupported_features":["LLM extraction not independently certified; no instruction fidelity in global checks"]}
    result=evaluate_ir(tikz,metadata,TikzIR,Evaluator(),root=ROOT)
    dump(folder/"diagramir-evidence.json",result)
    return result

def evaluate(record, artifact):
    folder=RUN/record["id"]/f"evaluate-{artifact}"
    result_path=folder/"evaluation.json"
    folder.mkdir(parents=True,exist_ok=True)
    if artifact=="target":
        tikz=record["target_tikz"]
        image=Path(record["target_artifact_dir"])/"target-1.png"
        compiled=image.exists()
    else:
        draw_path=RUN/record["id"]/"draw/result.json"
        if not draw_path.exists():
            error_path=RUN/record["id"]/"draw/error.json"
            if not error_path.exists(): raise RuntimeError("Drawing stage has not finished")
            report={"case_id":record["id"],"artifact":artifact,"status":"provider_or_harness_failed",
                    "compile_success":False,"dimension_scores":{"compile":0},"evaluation_coverage":0,
                    "error":json.loads(error_path.read_text(encoding="utf-8"))}
            dump(result_path,report)
            return report
        draw_data=json.loads(draw_path.read_text(encoding="utf-8"))
        tikz=draw_data["tikz"]
        image=Path(draw_data["rendered_png_path"]) if draw_data.get("rendered_png_path") else None
        compiled=bool(image and image.exists())
    report={"case_id":record["id"],"artifact":artifact,"compile_success":compiled,
            "candidate_sha256":sha(json.dumps(record,ensure_ascii=False,sort_keys=True)),
            "tikz_sha256":sha(tikz),"rubric_sha256":sha(json.dumps(record["evaluation_rubric"],ensure_ascii=False,sort_keys=True)),
            "evaluator_sha256":sha(Path(__file__).read_text(encoding="utf-8")),
            "judge_prompt_sha256":sha(JUDGE),"model_settings":SETTINGS}
    if result_path.exists():
        cached=json.loads(result_path.read_text(encoding="utf-8"))
        assert all(cached.get(k)==v for k,v in report.items()), "Stale evaluation result; use a new run directory"
        return cached
    if not compiled:
        report.update(status="compile_failed",dimension_scores={"compile":0},evaluation_coverage=0)
        dump(result_path,report)
        return report
    names={n for c in record["evaluation_rubric"] for q in c["checks"] for n in q["points"]}
    measured=measure_points(tikz,names,folder)
    report["coordinate_evidence"]=measured
    report["mathematical_checks"]=[
        {"criterion_id":c["id"],"check":q,**check(Check.model_validate(q),measured["points"])}
        for c in record["evaluation_rubric"] for q in c["checks"]]
    dump(folder/"geometry-evidence.json",{"coordinate_evidence":measured,"checks":report["mathematical_checks"]})
    try:
        report["diagramir"]=extract_ir(tikz,folder,record["id"])
    except Exception as error:
        report["diagramir"]={"status":"extraction_failed","error":f"{type(error).__name__}: {error}"}
    review_path=folder/"rubric-review"/"parsed.json"
    if review_path.exists():
        review=Review.model_validate_json(review_path.read_text(encoding="utf-8"))
    else:
        target_image=Path(record["target_artifact_dir"])/"target-1.png"
        messages=[{"role":"system","content":JUDGE},{"role":"user","content":[
            {"type":"text","text":json.dumps({"instruction":record["instruction"],"rubric":record["evaluation_rubric"],
              "target_tikz":record["target_tikz"],"output_tikz":tikz,"compile_success":compiled},ensure_ascii=False)},
            image_content_block(target_image),image_content_block(image)]}]
        try:
            review=model_call(Review,messages,folder/"rubric-review","offline-rubric-review",record["id"],
                              settings={**SETTINGS,"model":"gemini-3.1-flash-lite","thinking_level":"low"})
        except Exception as error:
            review=Review(grades=[Grade(id=c["id"],status="unknown",evidence="Model review failed") for c in record["evaluation_rubric"]],overall_findings=[f"{type(error).__name__}: {error}"])
    expected={c["id"] for c in record["evaluation_rubric"]}
    if {g.id for g in review.grades}!=expected or len(review.grades)!=len(expected):
        dump(folder/"rubric-review"/"validation-error.json", {"expected_ids":sorted(expected),"returned_ids":[g.id for g in review.grades]})
        # Missing grades remain unknown, never silently disappear from the denominator.
        by_id={g.id:g for g in review.grades if g.id in expected}
        duplicate_ids={g.id for g in review.grades if sum(x.id==g.id for x in review.grades)>1}
        review=Review(grades=[by_id[i] if i in by_id and i not in duplicate_ids else
            Grade(id=i,status="unknown",evidence="Evaluator returned missing or duplicate criterion ID") for i in sorted(expected)],
            overall_findings=review.overall_findings+["Incomplete evaluator response retained as unknown criteria"])

    report["model_rubric_review"]=review.model_dump(mode="json")
    report["judge_design"]="reference-assisted fixed-rubric diagnostic, not blind gold judgment"
    report["status"]="diagnostic_only"
    report["dimension_scores"]={}
    report["criterion_results"]=[]
    report["dimension_counts"]={}
    for dimension in ("compile","mathematical_correctness","content_coverage","visual_readability"):
        ids={c["id"] for c in record["evaluation_rubric"] if c["dimension"]==dimension}
        statuses=[]
        for g in review.grades:
            if g.id not in ids: continue
            checks=[q["status"] for q in report["mathematical_checks"] if q["criterion_id"]==g.id]
            status="fail" if "fail" in checks else "unknown" if "unknown" in checks else g.status
            if dimension=="compile": status="pass"
            statuses.append(status)
            report["criterion_results"].append({"id":g.id,"dimension":dimension,"status":status,"model_evidence":g.evidence,"coordinate_statuses":checks})
        report["dimension_counts"][dimension]={s:statuses.count(s) for s in ("pass","fail","unknown")}
        report["dimension_scores"][dimension]=1.0 if dimension=="compile" else sum(s=="pass" for s in statuses)/len(statuses)
    statuses=[r["status"] for r in report["mathematical_checks"]]
    report["deterministic_check_counts"]={s:statuses.count(s) for s in ("pass","fail","unknown")}
    report["geometric_check_coverage"]=sum(s!="unknown" for s in statuses)/len(statuses) if statuses else 0
    report["rubric_grade_coverage"]=sum(g["status"]!="unknown" for g in report["criterion_results"])/len(report["criterion_results"])
    report["limitation"]="Dimension scores are model diagnostics. PGF checks establish selected coordinate relations, not visible content; DiagramIR is extraction-dependent. No gold approval."
    dump(result_path,report)
    return report

def calibrate(record):
    folder=RUN/record["id"]/"calibration"
    folder.mkdir(parents=True,exist_ok=True)
    names={n for c in record["evaluation_rubric"] for q in c["checks"] for n in q["points"]}
    measurement=folder/sha(record["target_tikz"]+json.dumps(sorted(names)))[:12]
    measurement.mkdir(exist_ok=True)
    evidence=measure_points(record["target_tikz"],names,measurement)
    results=[{"criterion_id":c["id"],"check":q,**check(Check.model_validate(q),evidence["points"])}
             for c in record["evaluation_rubric"] for q in c["checks"]]
    report={"case_id":record["id"],"target_sha256":sha(record["target_tikz"]),"rubric_sha256":sha(json.dumps(record["evaluation_rubric"],sort_keys=True)),"evidence":evidence,"checks":results,
            "failures":[q for q in results if q["status"]=="fail"],"unknown":[q for q in results if q["status"]=="unknown"]}
    dump(folder/"calibration.json",report)
    if report["failures"]: raise ValueError(f"Target fails its own mathematical rubric: {record['id']}")
    return report

def controls(record):
    """Calibrate against original, rigidly translated, and corrupted geometry."""
    base=record["target_tikz"]
    criteria=record["evaluation_rubric"]
    checks=[(c["id"],q) for c in criteria for q in c["checks"]]
    if not checks: raise ValueError("No executable mathematical checks")
    point=checks[0][1]["points"][0]
    names={n for _,q in checks for n in q["points"]}
    drawing=re.search(r"\\(?:draw|filldraw|fill)\b",base)
    if not drawing: raise ValueError("No visible draw command to mutate safely")
    prefix=base[:drawing.start()]
    if not re.search(r"\\coordinate\s*\("+re.escape(point)+r"\)",prefix):
        raise ValueError("Mutation point not defined before painting; curate this control explicitly")
    mutant=base[:drawing.start()]+"\n\\coordinate ("+point+") at ($("+point+")+(0.37,0.53)$);\n"+base[drawing.start():]
    alternative=base.replace(r"\begin{tikzpicture}[",r"\begin{tikzpicture}[xshift=8mm,yshift=-5mm,",1)
    if alternative==base:
        alternative=base.replace(r"\begin{tikzpicture}",r"\begin{tikzpicture}[xshift=8mm,yshift=-5mm]",1)
    reports=[]
    for label,tikz in (("valid-alternative",alternative),("wrong-geometry",mutant)):
        folder=RUN/record["id"]/"controls"/label/sha(tikz+json.dumps(sorted(names)))[:12]
        compiled=prep.compile_target(tikz,folder)
        dump(folder/"compile.json",compiled)
        measured=measure_points(tikz,names,folder)
        results=[{"criterion_id":cid,"check":q,**check(Check.model_validate(q),measured["points"])} for cid,q in checks]
        report={"control":label,"mutation":f"move {point} by (0.37,0.53) before painting" if label=="wrong-geometry" else "whole-picture translation",
                "compile_success":compiled["success"],"checks":results,"tikz_sha256":sha(tikz)}
        dump(folder/"result.json",report)
        reports.append(report)
    assert reports[0]["compile_success"] and all(q["status"]=="pass" for q in reports[0]["checks"]),"Valid geometric alternative rejected/unresolved"
    assert reports[1]["compile_success"] and any(q["status"]=="fail" for q in reports[1]["checks"]),"Corrupted geometry not detected"
    dump(RUN/record["id"]/"controls"/"summary.json",{"case_id":record["id"],"results":reports,
        "scope":"geometry-check calibration only; does not establish visual or content-coverage evaluator accuracy"})
    return reports

def visible_content(record):
    from verify_painted_segments import probe
    contract=json.loads((ROOT/"docs/dataset-selection/candidate-flow-8.stroke-checks.json").read_text(encoding="utf-8"))
    entry=next(x for x in contract["cases"] if x["id"]==record["id"])
    assert entry["candidate_sha256"]==sha(json.dumps(record,ensure_ascii=False,sort_keys=True)), "Stale content contract"
    variants={"target":record["target_tikz"]}
    for label,relative in (("output","draw/result.json"),("repaired","harness-repair/result.json")):
        path=RUN/record["id"]/relative
        if path.exists():
            data=json.loads(path.read_text(encoding="utf-8"))
            compiled=data.get("compile_success",data.get("compile",{}).get("success",False))
            if compiled: variants[label]=data["tikz"]
    reports=[]
    for label,tikz in variants.items():
        folder=RUN/record["id"]/"visible-content"/label
        report=probe(tikz,entry["required_segments"],folder)
        report.update(artifact=label,criterion_id=entry["criterion_id"],
                      candidate_sha256=entry["candidate_sha256"],
                      contract_sha256=sha(json.dumps(entry,sort_keys=True)),
                      checker_sha256=sha((ROOT/"tools/verify_painted_segments.py").read_text(encoding="utf-8")),
                      limitation=entry["basis"])
        dump(folder/"evidence.json",report)
        reports.append(report)
    dump(RUN/record["id"]/"visible-content/summary.json",reports)
    return reports


def self_check():
    p={"A":[0,0],"B":[2,0],"C":[0,2],"H":[1,0],"K":[math.sqrt(2),math.sqrt(2)]}
    assert check(Check(op="perpendicular",points=["A","B","A","C"]),p)["status"]=="pass"
    assert check(Check(op="midpoint",points=["H","A","B"]),p)["status"]=="pass"
    assert check(Check(op="minor_arc",points=["K","A","B","C"]),p)["status"]=="pass"
    assert check(Check(op="on_circle",points=["H","A","B"]),p)["status"]=="fail"
    assert check(Check(op="collinear",points=["A","B","C"]),p)["status"]=="fail"
    assert check(Check(op="between",points=["B","A","H"]),p)["status"]=="fail"
    assert check(Check(op="parallel",points=["A","B","A","Q"]),p)["status"]=="unknown"
    assert check(Check(op="perpendicular",points=["A","B","A","A"]),p)["status"]!="pass"
    assert check(Check(op="collinear",points=["A","A","B"]),p)["status"]!="pass"
    assert check(Check(op="minor_arc",points=["K","A","B","C"]),{**p,"C":[-2,0]})["status"]=="unknown"
    assert check(Check(op="length_ratio",points=["A","H","A","B"],value=0.5),p)["status"]=="pass"
    assert check(Check(op="shorter",points=["A","B","A","H"]),p)["status"]=="fail"
    assert check(Check(op="same_ray",points=["B","A","H"]),p)["status"]=="pass"
    assert check(Check(op="equal_length",points=["A","B","A","C"]),p)["status"]=="pass"
    assert check(Check(op="outside_circle",points=["B","A","H"]),p)["status"]=="pass"
    assert check(Check(op="concyclic",points=["A","B","C","H"]),p)["status"]=="fail"
    assert check(Check(op="concyclic",points=["A","B","C","H"]),{**p,"H":[2,2]})["status"]=="pass"
    assert check(Check(op="tangent",points=["A","C","B","H"]),{**p,"H":[2,2]})["status"]=="pass"
    assert check(Check(op="tangent",points=["A","C","A","H"]),p)["status"]=="fail"
    q={"A":[0,1],"B":[1,0],"C":[-1,0],"T":[1,1]}
    assert check(Check(op="tangent_circumcircle",points=["A","T","A","B","C"]),q)["status"]=="pass"
    print("Self-check passed: all geometric operator families, invalid relations, missing bindings and degeneracy.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage",choices=["audit","calibrate","controls","freeze","draw","target","output","visible","check"])
    p.add_argument("--id",action="append")
    args=p.parse_args()
    if args.stage=="check": self_check();return
    model_stage=args.stage in {"audit","draw","target","output"}
    if model_stage:
        configure()
    else:
        prep.load_dotenv(prep.MATHPAPER/".env")
    if args.stage=="audit":
        records=[]
        for source in rows(prep.SOURCES):
            folder=RUN/source["id"]
            latest=sorted(folder.glob("prepare-*/parsed.json"))
            prepared=json.loads((folder/"candidate.json").read_text(encoding="utf-8")) if (folder/"candidate.json").exists() else {
                "id":source["id"], "task":"Generate", "status":"candidate", "source_group":source["provenance"]["source_group"],
                "provenance":source["provenance"], "source_sha256":sha(json.dumps(source,ensure_ascii=False,sort_keys=True)),
                "human_review_status":"pending", "experiment_role":"development_only",
                **(json.loads(latest[-1].read_text(encoding="utf-8")) if latest else {"preparation_failure":"No usable response; prepare directly from source."})}
            records.append(prepared)
        selected=[r for r in records if not args.id or r["id"] in args.id]
        prep.run_batch("audit",audit_case,selected)
    elif args.stage in ("calibrate","controls"):
        records=[json.loads(p.read_text(encoding="utf-8")) for p in sorted(RUN.glob("*/candidate-audited.json"))]
        selected=[r for r in records if not args.id or r["id"] in args.id]
        prep.run_batch(args.stage,calibrate if args.stage=="calibrate" else controls,selected)
    elif args.stage=="freeze":
        records=[json.loads(p.read_text(encoding="utf-8")) for p in sorted(RUN.glob("*/candidate-audited.json"))]
        freeze(records)
    else:
        records=rows(CANDIDATES)
        assert sha(CANDIDATES.read_text(encoding="utf-8"))==json.loads((RUN/"frozen.json").read_text())["candidate_sha256"]
        selected=[r for r in records if not args.id or r["id"] in args.id]
        results=prep.run_batch(args.stage,draw if args.stage=="draw" else visible_content if args.stage=="visible" else lambda r:evaluate(r,args.stage),selected)
        if args.stage in ("target","output"): dump(RUN/f"{args.stage}-results.json",results)
    if model_stage: prep.verify_traces()

if __name__=="__main__": main()
