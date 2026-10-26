"""Opt-in checks against the existing shared compiler: set COMPILER_URL to run."""
import os
from pathlib import Path

import httpx
import pytest
from agent.latex.tikz import standalone_tikz_document
from latex_compiler.client import compile as compile_latex
from latex_compiler.schemas import CompileRequest, Images, Outputs

from evaluation.evaluator import _score_observations
from evaluation.tikz_observations import compile_observe, read_scene

pytestmark = pytest.mark.skipif(not os.environ.get('COMPILER_URL'), reason='Native TeX integration requires COMPILER_URL')

SOURCE=r'''\begin{tikzpicture}
\coordinate[label=below:$A$] (A) at (0,0);
\coordinate[label=below:$B$] (B) at (4,0);
\draw (A)--node[midway,above] {$M$} (B);
\draw[dashed] (A) circle (2);
\node[draw,fill=white] at (2,2) {$x^2$};
\end{tikzpicture}'''


@pytest.fixture
def compiler():
    with httpx.Client(base_url=os.environ['COMPILER_URL'],timeout=200,trust_env=False) as client:
        yield client


def test_native_hooks_leave_render_unchanged_and_resolve_on_path_label(tmp_path,compiler):
    observed=compile_observe(SOURCE,tmp_path/'native',compiler,preview=True)
    assert observed['compile_success'], observed
    assert not observed['metadata'].get('trace_error'), observed
    scene=read_scene(observed)
    unit=72.27/2.54
    assert scene['points']['A']==pytest.approx((0,0),abs=.01)
    assert scene['points']['B']==pytest.approx((4*unit,0),abs=.01)
    assert scene['points']['M']==pytest.approx((2*unit,0),abs=.01)
    assert not scene['unsupported'] and not scene['unresolved']
    request=CompileRequest(source=standalone_tikz_document(SOURCE),outputs=Outputs(pdf=False,images=Images()))
    original=compile_latex(compiler,request)
    assert original.compile.success and original.raster.success
    png=next(artifact.data for artifact in original.artifacts if artifact.name=='page-1.png')
    assert Path(observed['image_path']).read_bytes()==png
    assert not (tmp_path/'native/result.pdf').exists()


def test_native_scores_without_pdf_or_raster_keep_valid_transform(tmp_path,compiler):
    target=compile_observe(SOURCE,tmp_path/'target',compiler)
    output=compile_observe(SOURCE.replace(r'\begin{tikzpicture}',r'\begin{tikzpicture}[rotate=37,scale=1.5,xscale=-1]'),tmp_path/'output',compiler)
    assert not target['metadata'].get('trace_error') and not output['metadata'].get('trace_error')
    for observation in (target,output):
        assert observation['image_path'] is None and observation['raster']['outcome']=='not_requested'
        assert 'result.pdf' not in observation['artifacts']['pgf']
    scores=_score_observations(target,output)
    assert scores['compile']==1
    assert scores['mathematical_correctness']==scores['content_coverage']==100


@pytest.mark.parametrize('placement,fraction',[('midway,above',.5),('pos=.25,sloped,above',.25)])
def test_native_path_timer_and_end_picture_bounds(tmp_path,compiler,placement,fraction):
    source=r'''\begin{tikzpicture}[execute at end picture={\node at (10,0) {$Z$};}]
\draw (0,0)--node[PLACEMENT] {$M$}(4,3);
\end{tikzpicture}'''.replace('PLACEMENT',placement)
    observed=compile_observe(source,tmp_path/'placement',compiler)
    scene=read_scene(observed)
    from evaluation.tikz_readability import inspect_readability
    assert scene['points']['M']==pytest.approx((4*fraction*72.27/2.54,3*fraction*72.27/2.54),abs=.02)
    assert scene['bounds'][2]>scene['points']['Z'][0]
    assert not any(issue['kind']=='clipped' for row in inspect_readability(scene)['labels'] for issue in row['issues'])


@pytest.mark.parametrize('body', [r'\pgftext{A}',r'\shade (0,0) rectangle (1,1);',
                                  r'\fill[pattern=north east lines] (0,0) rectangle (1,1);'])
def test_unrepresented_native_paint_never_gets_empty_text_credit(tmp_path,compiler,body):
    from evaluation.evaluator import EvaluationError
    observed=compile_observe(r'\begin{tikzpicture}'+body+r'\end{tikzpicture}',tmp_path/'unsupported',compiler)
    assert observed['compile_success'] and not observed['metadata'].get('trace_error'), observed
    scene=read_scene(observed)
    assert scene['paint_issues']
    with pytest.raises(EvaluationError) as failure:
        _score_observations(observed,observed)
    assert failure.value.scores['compile']==1 and failure.value.scores['visual_readability'] is None


def test_native_bar_and_vector_ticks_have_the_same_carriers(tmp_path,compiler):
    import json
    controls=json.loads((Path(__file__).parent/'fixtures/mark-calibration.json').read_text())['controls']
    target=compile_observe(controls['reference']['tikz'],tmp_path/'bars',compiler)
    output=compile_observe(controls['equivalent_vector_ticks']['tikz'],tmp_path/'ticks',compiler)
    scene=read_scene(output)
    assert max(label['size'] for label in scene['text'])==pytest.approx(8*1.3,abs=.02)
    scores=_score_observations(target,output)
    assert scores['mathematical_correctness']==scores['content_coverage']==100



CIRCLE=r"""\begin{tikzpicture}
\coordinate (O) at (0,0);
\coordinate (A) at (2,0);
\draw (O) circle (2);
\node[below] at (O) {$O$};
\node[right] at (A) {$A$};
\end{tikzpicture}"""


def test_filled_stroked_boundary_is_geometry_and_background_not_text_collision(tmp_path,compiler):
    from PIL import Image, ImageChops
    plain=compile_observe(CIRCLE,tmp_path/'plain',compiler,preview=True)
    filled=compile_observe(CIRCLE.replace(r'\draw (O)',r'\filldraw[fill=white] (O)'),tmp_path/'filled',compiler,preview=True)
    missing=compile_observe(CIRCLE.replace(r'\draw (O) circle (2);',''),tmp_path/'missing',compiler)
    first,second=(Image.open(o['image_path']).convert('RGB') for o in (plain,filled))
    assert first.size==second.size and ImageChops.difference(first,second).getbbox() is None
    assert _score_observations(plain,filled)==dict(compile=1,mathematical_correctness=100.,content_coverage=100.,visual_readability=100.)
    scores=_score_observations(filled,missing)
    assert scores['mathematical_correctness']==0 and scores['content_coverage']<100
    scene=read_scene(filled)
    assert len(scene['circles'])==1
    assert [p['kind'] for p in scene['paint']]==['fill','stroke']


@pytest.mark.parametrize('options',['','rotate=37,scale=1.5,xscale=-1'])
def test_native_short_arc_saved_replayed_and_unused_paths(tmp_path,compiler,options):
    source=r"""\begin{tikzpicture}[OPTIONS]
\coordinate (O) at (0,0);
\coordinate (A) at (2,0);
\coordinate (B) at (10:2);
\pgfpathmoveto{\pgfpoint{2cm}{0cm}}
\pgfpatharc{0}{10}{2cm}
\pgfgetpath\savedarc
\pgfusepath{discard}
\pgfpathcircle{\pgfpoint{10cm}{10cm}}{3cm}
\pgfusepath{discard}
\pgfsetpath\savedarc\pgfusepath{stroke}
\pgfsetpath\savedarc\pgfusepath{stroke}
\node[left] at (O) {$O$};
\node[below] at (A) {$A$};
\node[above] at (B) {$B$};
\end{tikzpicture}""".replace('OPTIONS',options)
    observed=compile_observe(source,tmp_path/'native-arc',compiler,preview=True)
    scene=read_scene(observed)
    assert not scene['unsupported']
    assert len(scene['arcs'])==1 and not scene['circles']
    assert scene['arcs'][0]['sweep']==pytest.approx(10*3.141592653589793/180,abs=.0001)
    assert sum(len(p['conics']) for p in scene['paths'])==2
    scores=_score_observations(observed,observed)
    assert scores['mathematical_correctness']==scores['content_coverage']==100
    original=compile_latex(compiler,CompileRequest(source=standalone_tikz_document(source),outputs=Outputs(pdf=False,images=Images())))
    assert original.compile.success and original.raster.success
    assert Path(observed['image_path']).read_bytes()==next(a.data for a in original.artifacts if a.name=='page-1.png')


def test_cached_arrow_paint_is_observed_at_each_invocation(tmp_path,compiler):
    source=r"""\begin{tikzpicture}
\foreach \x in {0,2,4} {\draw[-{Stealth}] (\x,0)--(\x,1);}
\draw[{Latex}-{Latex}] (0,2)--(4,2);
\end{tikzpicture}"""
    observed=compile_observe(source,tmp_path/'arrows',compiler,preview=True)
    scene=read_scene(observed)
    assert not scene['unsupported'] and not scene['paint_issues']
    assert len(scene['arrows'])==5 and len(scene['strokes'])==4
    assert all(not arrow['dashed'] and arrow['width']==pytest.approx(.4) for arrow in scene['arrows'])
    unit=72.27/2.54
    for arrow,x in zip(scene['arrows'][:3],(0,2,4)):
        assert arrow['tip']==pytest.approx((x*unit,unit),abs=.02)
        assert arrow['direction']==pytest.approx((0,1),abs=.001)
    assert scene['arrows'][3]['direction']==pytest.approx((-1,0),abs=.001)
    assert scene['arrows'][4]['direction']==pytest.approx((1,0),abs=.001)
    assert len({p['arrow'] for p in scene['paths'] if p['arrow'] is not None})==5
    original=compile_latex(compiler,CompileRequest(source=standalone_tikz_document(source),outputs=Outputs(pdf=False,images=Images())))
    assert original.compile.success and original.raster.success
    assert Path(observed['image_path']).read_bytes()==next(a.data for a in original.artifacts if a.name=='page-1.png')


def test_unused_and_replayed_native_objects_are_not_definition_time_paint(tmp_path,compiler):
    source=r"""\begin{tikzpicture}
\pgfdefobject{segment}{\pgfpoint{-1pt}{-1pt}}{\pgfpoint{11pt}{1pt}}
 {\pgfpathmoveto{\pgfpoint{0pt}{0pt}}\pgfpathlineto{\pgfpoint{10pt}{0pt}}\pgfusepath{stroke}}
\pgfdefobject{unused}{\pgfpoint{-1pt}{-1pt}}{\pgfpoint{31pt}{1pt}}
 {\pgfpathmoveto{\pgfpoint{0pt}{0pt}}\pgfpathlineto{\pgfpoint{30pt}{0pt}}\pgfusepath{stroke}}
\pgfuseobject{segment}
\begin{scope}[shift={(0,1)}]\pgflowlevelsynccm\pgfuseobject{segment}\end{scope}
\path[use as bounding box] (-1,-1) rectangle (1,2);
\end{tikzpicture}"""
    observed=compile_observe(source,tmp_path/'objects',compiler,preview=True)
    scene=read_scene(observed)
    assert not scene['unsupported'] and not scene['paint_issues']
    assert len(scene['strokes'])==2 and len(scene['paint'])==2
    assert [p['geometry'].length for p in scene['strokes']]==pytest.approx([10,10],abs=.001)
    assert [p['geometry'].bounds[1] for p in scene['strokes']]==pytest.approx([0,72.27/2.54],abs=.001)
    original=compile_latex(compiler,CompileRequest(source=standalone_tikz_document(source),outputs=Outputs(pdf=False,images=Images())))
    assert original.compile.success and original.raster.success
    assert Path(observed['image_path']).read_bytes()==next(a.data for a in original.artifacts if a.name=='page-1.png')



@pytest.mark.parametrize('placement,expected',[('',100.),('behind path,',0.)])
def test_deferred_node_boxes_use_shipout_order_for_readability(tmp_path,compiler,placement,expected):
    source=r"""\begin{tikzpicture}
\draw[very thick] (0,0)--node[PLACEMENTfill=white,inner sep=3pt] {$M$}(4,0);
\end{tikzpicture}""".replace('PLACEMENT',placement)
    observed=compile_observe(source,tmp_path/'inline-node',compiler)
    assert _score_observations(observed,observed)['visual_readability']==expected


def test_cached_arrow_context_and_unused_paint_effects_follow_replay(tmp_path,compiler):
    source=r"""\begin{tikzpicture}
\pgfdefobject{unused}{\pgfpoint{0pt}{0pt}}{\pgfpoint{10pt}{10pt}}
 {\pgfsetfillpattern{north east lines}{black}\pgfpathrectangle{\pgfpointorigin}{\pgfpoint{10pt}{10pt}}\pgfusepath{fill}}
\pgfdefobject{arrow}{\pgfpoint{-10pt}{-10pt}}{\pgfpoint{10pt}{10pt}}{\pgfarrowdraw{Stealth}}
\pgfuseobject{arrow}
\begin{scope}[shift={(1,1)}]\pgflowlevelsynccm\pgfuseobject{arrow}\end{scope}
\path[use as bounding box] (-1,-1) rectangle (2,2);
\end{tikzpicture}"""
    observed=compile_observe(source,tmp_path/'nested-cache',compiler)
    scene=read_scene(observed)
    assert not scene['paint_issues'] and not scene['unsupported']
    assert len(scene['arrows'])==2
    assert len({p['arrow'] for p in scene['paths']})==2
    assert all(p['arrow'] is not None for p in scene['paths'])



@pytest.mark.parametrize('body,visible',[
    (r'\draw[opacity=0] (0,0)--node {$A$}(4,0);',False),
    (r'\draw[opacity=0] (0,0)--node[behind path] {$A$}(4,0);',True),
    (r'\draw[opacity=0] (0,0)--node[opacity=1] {$A$}(4,0);',True),
    (r'\clip (0,0) rectangle (1,1) node at (2,.5) {$A$};',False),
])
def test_deferred_nodes_inherit_actual_insertion_graphics_state(tmp_path,compiler,body,visible):
    from PIL import Image
    observed=compile_observe(r'\begin{tikzpicture}'+body+r'\end{tikzpicture}',tmp_path/'insertion',compiler,preview=True)
    scene=read_scene(observed)
    assert bool(scene['points'])==visible
    image=Image.open(observed['image_path']).convert('RGB')
    assert (min(channel[0] for channel in image.getextrema())<240)==visible
