"""PGF paint/text-box clearance, intentionally distinct from glyph-ink overlap."""
import pytest

from evaluation.tikz_observations import read_scene
from evaluation.tikz_readability import inspect_readability
from conftest import label_records


def status(observation):
    return [row['status'] for row in inspect_readability(read_scene(observation))['labels']]


@pytest.mark.parametrize('dash,expected',[('', 'fail'),('3pt,3pt','pass')])
def test_dash_gaps_affect_readability_not_continuous_carriers(pgf_records,dash,expected):
    rows=label_records(1,'A',(0,0),box_point=(3.2,-3))
    # Narrow label wholly inside the [3,6] gap, with a six-pt height.
    rows[-1]='TEXTBOX|1|3.2pt|3pt|5.8pt|3pt|3.2pt|-3pt|5.8pt|-3pt'
    rows += [f'setdash|{dash}|0pt','moveto|0pt|0pt','lineto|20pt|0pt','stroke']
    obs=pgf_records(rows)
    assert status(obs)==[expected]
    assert read_scene(obs)['strokes'][0]['geometry'].length==20


@pytest.mark.parametrize('operation', ['stroke','fill'])
def test_transparent_paint_does_not_collide(pgf_records,operation):
    rows=label_records(1,'A',(0,0),box_point=(0,0))
    rows += ['stroke@opacity|0','fill@opacity|0','rect|0pt|0pt|10pt|10pt',operation]
    assert status(pgf_records(rows))==['pass']


def test_label_ownership_excludes_own_background_but_not_other_paint(pgf_records):
    rows=label_records(1,'A',(0,0),box_point=(0,0))
    path=['rect|0pt|0pt|10pt|10pt','fill']
    assert status(pgf_records(rows+['NODE_BEGIN|box|1',*path,'NODE_END']))==['pass']
    assert status(pgf_records(rows+path))==['fail']


def test_clip_limits_paint_and_partially_clipped_text_fails(pgf_records):
    clip=['rect|0pt|0pt|2pt|10pt','clipnext','discardpath']
    label=label_records(1,'A',(0,0),box_point=(4,0))
    assert status(pgf_records(label+clip+['rect|0pt|0pt|10pt|10pt','fill']))==['pass']
    partial=label_records(1,'A',(0,0),box_point=(0,0))
    assert status(pgf_records(clip+partial))==['fail']


def test_overlapping_text_and_unknown_boxes(pgf_records):
    first=label_records(1,'A',(0,0))
    assert status(pgf_records(first+label_records(2,'B',(0,0))))==['fail','fail']
    assert status(pgf_records(label_records(1,'A',(0,0),visible=False)))==['unknown']


def test_round_zero_length_dashes_have_visible_support(pgf_records):
    rows=label_records(1,'A',(0,0),box_point=(-.2,-.2))
    rows += ['setlinewidth|2pt','roundcap','setdash|0pt,3pt|0pt','moveto|0pt|0pt','lineto|20pt|0pt','stroke']
    assert status(pgf_records(rows))==['fail']


def test_short_thin_strokes_and_hairlines_are_not_silently_dropped(pgf_records):
    label=label_records(1,'A',(0,0),box_point=(0,0))
    line=['moveto|0pt|3pt','lineto|4pt|3pt','stroke']
    assert status(pgf_records(label+['setlinewidth|.01pt']+line))==['fail']
    assert status(pgf_records(label+['setlinewidth|0pt']+line))==['unknown']


def test_even_odd_hole_and_canvas_scaling(pgf_records):
    label=label_records(1,'A',(0,0),box_point=(4,4))
    fill=['FILL_RULE|even_odd','rect|0pt|0pt|20pt|20pt','rect|2pt|2pt|10pt|10pt','fill']
    assert status(pgf_records(label+fill))==['pass']
    assert status(pgf_records(['beginscope','transformcm|2|0|0|3|0pt|0pt',*label,*fill,'endscope']))==['pass']


@pytest.mark.parametrize('order,opacity,expected', [('before',1,'pass'),('after',1,'fail'),('after',0,'pass'),('after',.5,'fail')])
def test_fill_order_and_opacity_determine_text_overpaint(pgf_records,order,opacity,expected):
    label=label_records(1,'A',(0,0),box_point=(0,0))
    fill=[f'fill@opacity|{opacity}','rect|-1pt|-1pt|10pt|10pt','fill']
    rows=fill+label if order=='before' else label+fill
    assert status(pgf_records(rows))==[expected]


@pytest.mark.parametrize('opacity,expected', [(1,'pass'),(.5,'fail')])
def test_background_mask_hides_earlier_strokes_before_text(pgf_records,opacity,expected):
    stroke=['moveto|0pt|3pt','lineto|4pt|3pt','stroke']
    mask=[f'fill@opacity|{opacity}','rect|-1pt|-1pt|10pt|10pt','fill','fill@opacity|1']
    label=label_records(1,'A',(0,0),box_point=(0,0))
    assert status(pgf_records(stroke+mask+label))==[expected]
