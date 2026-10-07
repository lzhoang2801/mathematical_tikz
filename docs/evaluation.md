# TikZ evaluation

`evaluate(target_tikz, output_tikz)` returns four deterministic scores for Generate, Edit and Reconstruct. The target defines the observed geometric relations and required content. No LLM judge or per-case rubric enters scoring.

## Method

1. Compile both TikZ inputs with the shared wrapper/compiler.
2. Extract painted PDF paths and glyph outlines; bind visible point labels through a nonpainting PGF probe verified against the original render.
3. Compare geometric relations and content; measure readability on the output.

Separating geometric representation from deterministic checks follows [DiagramIR (Kumar et al., 2025), section 2.3](https://arxiv.org/html/2511.08283v1#S2.SS3). Here the observations come from executed PDF/PGF.

## Metrics

| Metric | Score |
| --- | --- |
| **Compile** | `1` if the output validates and compiles; otherwise `0`. Dataset compile rate is the mean. |
| **Mathematical correctness** | `100 × passed relation units / target relation units`. |
| **Content coverage** | Percentage of target point identities, maximal connections and circles present with the required solid/dashed style. Extra or unsupported objects add failed units. |
| **Visual readability** | Percentage of output text labels with resolved outlines and no detected stroke/text collision or clipping. Count each affected label once; exclude bar-only equality marks. |

Missing evidence fails the corresponding unit. Failed output compilation gives four zeros; an invalid target or unavailable compiler/probe raises an error. No mathematical/content units gives 0; no scored text gives 100.

## Geometric relations

| Target observation | Output requirement |
| --- | --- |
| Named point pair | Preserve distinctness/coincidence; one unit per pair. |
| Collinear triple | Preserve collinearity and midpoint when present; one unit per triple. |
| Noncollinear triples | Preserve nondegeneracy; one combined guard. |
| Point inside a painted segment | Preserve incidence and bounds; one unit per incidence. |
| Parallel painted carriers | Preserve parallelism and equal vectors when present; one unit per pair. |
| Square corner mark | Preserve perpendicularity; one unit per marked angle. |
| Full circle | Preserve detected center, boundary, radius-segment and tangency relations; one unit per circle, matched one-to-one. |

## Mathematical basis

For correctly bound observations $X$ and target predicates $R_T$, define

$$
\mathcal S_T=\{X:\;r(X)=\mathrm{true}\text{ for every }r\in R_T\}.
$$

This solution set can contain multiple nonsimilar drawings. Free points, dependent points and constraints also underpin [GeoLoom (Wei et al., v2), section 4.2](https://arxiv.org/html/2512.08180v2#S4.SS2). Our predicates are extracted from the target; the proofs below establish exact geometric preservation, while the implementation tests numerical approximations.

**1. 2D coordinate freedom.** For $f(P)=sQP+t$, $s>0$ and $Q^\top Q=I$,

$$
\|f(P)-f(C)\|=s\|P-C\|,
\qquad (sQu)\cdot(sQv)=s^2(u\cdot v).
$$

Distance ratios, perpendicularity, circles and tangency are preserved. Thus translation, rotation, reflection and uniform scale preserve the checked relations. General affine transforms preserve affine dependencies, but can turn circles into ellipses and change right angles.

**2. Different 2D constructions, same relations.** Take $A=(0,0)$, $B=(0,h)$, $C=(b,0)$ with $b,h>0$, and $q=b^2+h^2$. Define

$$
M=(b/2,0),\quad N=(b/2,h/2),\quad
H=(bh^2/q,hb^2/q),\quad r=b/2.
$$

Substitution gives

$$
\begin{aligned}
2M&=A+C,\quad 2N=B+C,\quad H=B+\tfrac{h^2}{q}(C-B),\\
(H-A)\cdot(C-B)&=0,\qquad \|C-M\|=r.
\end{aligned}
$$

Changing $b/h$ changes the triangle's shape while preserving these midpoints, the altitude and circle $(C,CM)$. Full credit remains conditional on the other extracted relations and nondegeneracy guards. This proves why a single global similarity is unnecessarily restrictive.

**3. 3D dependencies can be checked in their 2D projection.** Let $P_i\in\mathbb R^3$ and $p_i=\pi(P_i)=LP_i+t$, with $L\in\mathbb R^{2\times3}$ of rank 2. For any affine combination,

$$
\pi\!\left(\sum_i\alpha_iP_i\right)
=\sum_i\alpha_i\pi(P_i),\qquad \sum_i\alpha_i=1.
$$

Proof: distribute $L$ and use $(\sum_i\alpha_i)t=t$. Midpoints, incidence, segment membership and equal-vector/parallel dependencies therefore survive when the relevant objects do not collapse. The linear orthographic special case is documented by [Tomasi and Kanade (1992), section 3.1, equation 9](https://cs.brown.edu/courses/cs143/2011/proj5/Tomasi_Kanade_IJCV_1992.pdf#page=4).

For the prism, take projected $A,B,C,d\in\mathbb R^2$ and set

$$
\begin{aligned}
A'&=A+d,\quad B'=B+d,\quad C'=C+d,\\
M&=B+\tfrac12d,\quad N=C+\tfrac12d,\\
H&=2B-A,\quad K=2C-A.
\end{aligned}
$$

Then $2M=B+B'=A'+H$, $2N=C+C'=A'+K$, $B'-A'=B-A$, and $C'-A'=C-A$. These identities hold for changing free points. Moreover,

$$
\Phi(x,y,z)=A+x(B-A)+y(C-A)+zd
$$

maps the canonical 3D prism with base $(0,e_1,e_2)$ and translation $e_3$ exactly to these projected vertices and dependencies. This supplies a 3D realization of this dependency system without requiring XYZ input to the evaluator.

**Boundary.** Projection is not invertible: for $v\ne0$ in $\ker L$, $\pi(P+v)=\pi(P)$. Consequently, projected checks certify the observed dependencies, not arbitrary spatial lengths, angles or hidden incidence; perspective projections also need different invariants. These derivations and cited methods do not prove extractor accuracy or score calibration. Target-inferred relations can be incidental to the original problem.

Changing $(C,CM)$ to $(C,CN)$ affects mathematics when the radii differ; deleting MN affects coverage; label collisions affect readability. Printed measurement text is not parsed as a mathematical requirement.

## Use and scope

```powershell
python -m evaluation.run --target target.tex --output output.tex --preview preview.html
```

The optional preview contains both renders, scores and TikZ sources. Set `COMPILER_URL` for the shared compiler; default: `http://127.0.0.1:18080`.

Supported observations: labeled points, straight solid/dashed segments, full circles and square corner marks. Gxx labels do not select scoring logic. General arcs/conics, filled regions and unmarked metric givens are outside the implemented checks; unsupported output geometry currently also withholds readability credit. **100% means all extracted checks passed**, not that unstated problem requirements were proved.

Implementation: [evaluator](../evaluation/evaluator.py), [geometry](../evaluation/tikz_geometry.py), [coverage](../evaluation/tikz_coverage.py), [readability](../evaluation/tikz_readability.py). Regression tests cover valid transformations/reconstructions, missing content, broken relations and label collisions under [tests/evaluation](../tests/evaluation/).
