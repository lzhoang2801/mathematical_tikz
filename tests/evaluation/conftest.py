"""Small emitted-PGF fixtures, without a TeX/PDF dependency."""
import hashlib
import math

import pytest

from evaluation.tikz_observations import SCHEMA_VERSION, TRACER_SHA256


def label_records(identity, name, point, *, text=None, box_point=None, visible=True):
    x, y = point
    bx, by = box_point or (x - 2, y - 12)
    records = [f'NODE_CONTEXT|{identity}', f'NODE|{identity}|node{identity}||rectangle',
               f'ATTACH|{identity}|node-position|{x}pt|{y}pt',
               f'TEXT|{identity}|${name if text is None else text}$']
    records += [f'TEXTFONT|{identity}|8', f'TEXTSIZE|{identity}|0pt|0pt|0pt|1pt']
    if visible:
        records.append(f'TEXTBOX|{identity}|{bx}pt|{by+6}pt|{bx+4}pt|{by+6}pt|{bx}pt|{by}pt|{bx+4}pt|{by}pt')
    return records


def circular_records(center, radius, *, ellipse=False, dashed=True):
    x, y = center
    rx, ry = radius, radius * (.5 if ellipse else 1)
    k = 4 * (math.sqrt(2) - 1) / 3
    points = [(x+rx,y), (x+rx,y+k*ry), (x+k*rx,y+ry), (x,y+ry),
              (x-k*rx,y+ry), (x-rx,y+k*ry), (x-rx,y), (x-rx,y-k*ry),
              (x-k*rx,y-ry), (x,y-ry), (x+k*rx,y-ry), (x+rx,y-k*ry), (x+rx,y)]
    rows = [f'setdash|{"4pt,3pt" if dashed else ""}|0pt', f'moveto|{points[0][0]}pt|{points[0][1]}pt']
    for index in range(1, 13, 3):
        rows.append('curveto|' + '|'.join(f'{value}pt' for point in points[index:index+3] for value in point))
    return rows + ['stroke', 'setdash||0pt']


@pytest.fixture
def pgf_records(tmp_path):
    count = 0
    def write(rows, *, bounds=(-10000,-10000,10000,10000)):
        nonlocal count
        count += 1
        path = tmp_path / f'{count}.log'
        records = ['BEGIN|fixture', *rows, 'BOUNDS|'+'|'.join(f'{v}pt' for v in bounds), 'DONE']
        raw = '\n'.join(f'PGFEVAL|{row}|ENDPGFEVAL' for row in records).encode()
        path.write_bytes(raw)
        return {'compile_success': True, 'compile': {'outcome':'ok'}, 'log_path':str(path),
                'metadata': {'schema_version':SCHEMA_VERSION, 'tracer_sha256':TRACER_SHA256},
                'artifacts': {'pgf': {'result.log': {'path':str(path),'complete':True,'sha256':hashlib.sha256(raw).hexdigest()}}}}
    return write


@pytest.fixture
def pgf_diagram(pgf_records):
    def diagram(*, coordinates=None, scale=1., reflection=False, rotation=False, missing_edge=False,
                missing_point=False, missing_box=False, collide=False, wrong_text=False, circle=None):
        points = coordinates or [(30,100),(130,100),(60,30)]
        a,b,c,d = (-scale if reflection else scale),0.,0.,scale
        if rotation:
            a,b,c,d = -b,a,-d,c
        rows = ['beginscope',f'transformcm|{a}|{b}|{c}|{d}|0pt|0pt']
        for i, (name, p) in enumerate(zip('ABC',points), 1):
            if not (missing_point and name == 'C'):
                offset={'A':(-10,4),'B':(8,0),'C':(-10,-12)}[name]
                placement=(points[0][0]-10,points[0][1]+4) if collide and name=='B' else (p[0]+offset[0],p[1]+offset[1])
                rows += label_records(i,name,p,box_point=placement,
                                      visible=not(missing_box and name=='C'))
        rows += label_records(4,'size',(30,160),text='8cm' if wrong_text else '6cm')
        for i, (first,last) in enumerate(zip(points,points[1:]+points[:1])):
            if not missing_edge or i != 1:
                rows += [f'moveto|{first[0]}pt|{first[1]}pt',f'lineto|{last[0]}pt|{last[1]}pt','stroke']
        if circle:
            center = points[0]
            radius = math.dist(points[0],points[2])
            if circle == 'radius': radius *= 1.25
            if circle == 'center': center = (center[0]+10,center[1])
            for _ in range(2 if circle == 'duplicate' else 1):
                rows += circular_records(center,radius,ellipse=circle=='ellipse',dashed=circle!='style')
        rows += ['endscope']
        return pgf_records(rows)
    return diagram
