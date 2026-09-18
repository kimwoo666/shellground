"""Bounded JSON snapshots of actual scientific Python objects, not repr grading."""
import math

MAX_ITEMS = 20000


def scalar(value):
    if value is None or isinstance(value, (str, bool, int)): return value
    if isinstance(value, float):
        if math.isnan(value): return {'special': 'nan'}
        if math.isinf(value): return {'special': 'inf' if value > 0 else '-inf'}
        return value
    if hasattr(value, 'item'):
        try: return scalar(value.item())
        except (ValueError, TypeError): pass
    return str(value)


def snapshot(value, depth=0):
    import numpy as np
    import pandas as pd
    from matplotlib.figure import Figure
    if depth > 6: raise ValueError('표시할 객체의 중첩이 너무 깊습니다.')
    if isinstance(value, np.ndarray):
        if value.size > MAX_ITEMS: raise ValueError('배열 표시 상한은 20,000개입니다.')
        return {'kind': 'array', 'shape': list(value.shape), 'dtype': str(value.dtype),
                'data': snapshot(value.tolist(), depth + 1)}
    if isinstance(value, pd.DataFrame):
        if value.size > MAX_ITEMS: raise ValueError('표 표시 상한은 20,000칸입니다.')
        return {'kind': 'frame', 'shape': list(value.shape),
                'index': snapshot(list(value.index)), 'columns': snapshot(list(value.columns)),
                'index_names':snapshot(list(value.index.names)), 'column_names':snapshot(list(value.columns.names)),
                'data': [[scalar(v) for v in row] for row in value.itertuples(index=False, name=None)],
                'dtypes': [str(v) for v in value.dtypes]}
    if isinstance(value, pd.Series):
        if value.size > MAX_ITEMS: raise ValueError('시리즈 표시 상한은 20,000개입니다.')
        return {'kind': 'series', 'index': snapshot(list(value.index)),
                'name': scalar(value.name), 'dtype': str(value.dtype), 'data': [scalar(v) for v in value]}
    if isinstance(value, Figure): return figure_snapshot(value)
    if isinstance(value, (tuple, list)):
        if len(value) > MAX_ITEMS: raise ValueError('목록이 너무 큽니다.')
        return [snapshot(v, depth + 1) for v in value]
    if isinstance(value, dict):
        if len(value) > 1000: raise ValueError('사전이 너무 큽니다.')
        # A learner dictionary must never masquerade as an ndarray/Figure tag.
        return {'__python_type__':'dict', 'items':{str(k): snapshot(v, depth + 1) for k, v in value.items()}}
    return scalar(value)


def figure_snapshot(fig):
    import numpy as np
    from matplotlib.patches import Rectangle, Wedge, PathPatch
    from matplotlib.colors import to_hex
    axes = []
    if len(fig.axes) > 12: raise ValueError('그림당 Axes 상한은 12개입니다.')
    # Resolve per-point mapped colors before inspecting visible artist state.
    fig.canvas.draw()
    colorbar_axes = {artist.colorbar.ax for ax in fig.axes for artist in [*ax.collections, *ax.images]
                     if getattr(artist, 'colorbar', None) is not None and artist.colorbar.ax in fig.axes}
    for ax in fig.axes:
        lines = [{'x': snapshot(line.get_xdata()), 'y': snapshot(line.get_ydata()),
                  'label': line.get_label(), 'color': to_hex(line.get_color(), keep_alpha=False),
                  'linestyle': line.get_linestyle(), 'marker': line.get_marker()} for line in ax.lines]
        collections = []
        for c in ax.collections:
            item = {'offsets': snapshot(c.get_offsets())}
            if hasattr(c, 'get_sizes'):
                sizes=c.get_sizes()
                if len(sizes)>1 and np.all(sizes==sizes[0]): sizes=sizes[:1]
                item['sizes'] = snapshot(sizes)
            if c.get_array() is not None: item['array'] = snapshot(c.get_array())
            item['alpha'] = scalar(c.get_alpha())
            item['colorbar'] = getattr(c,'colorbar',None) is not None and c.colorbar.ax in fig.axes
            collections.append(item)
        patches = []
        for p in ax.patches:
            if isinstance(p, Rectangle):
                patches.append({'kind': 'rectangle', 'x': scalar(p.get_x()), 'y': scalar(p.get_y()),
                                'width': scalar(p.get_width()), 'height': scalar(p.get_height())})
            elif isinstance(p, Wedge):
                patches.append({'kind': 'wedge', 'theta1': scalar(p.theta1), 'theta2': scalar(p.theta2),
                                'angle':scalar(p.theta2-p.theta1),
                                'center': [scalar(v) for v in p.center], 'radius': scalar(p.r)})
            elif isinstance(p, PathPatch): patches.append({'kind': 'path', 'vertices': snapshot(p.get_path().vertices)})
        legend = ax.get_legend()
        spec=ax.get_subplotspec()
        subplot=None if spec is None else [*spec.get_gridspec().get_geometry(),
            spec.rowspan.start,spec.rowspan.stop,spec.colspan.start,spec.colspan.stop]
        axes.append({'title': ax.get_title(), 'xlabel': ax.get_xlabel(), 'ylabel': ax.get_ylabel(),
                     'scatter': scatter_snapshot(ax, fig),
                     'subplot':subplot, 'boxes':boxplot_snapshot(ax),
                     'line_count': len(lines), 'patch_count': len(patches), 'collection_count':len(collections),
                     'xlim': [scalar(v) for v in ax.get_xlim()], 'ylim': [scalar(v) for v in ax.get_ylim()],
                     'xscale': ax.get_xscale(), 'yscale': ax.get_yscale(),
                     'lines': lines, 'collections': collections, 'patches': patches,
                     'images': [snapshot(im.get_array()) for im in ax.images],
                     'image_colorbars': [im.colorbar is not None and im.colorbar.ax in fig.axes for im in ax.images],
                     'legend': [t.get_text() for t in legend.get_texts()] if legend else [],
                     'grid_x': any(g.get_visible() for g in ax.get_xgridlines()),
                     'grid_y': any(g.get_visible() for g in ax.get_ygridlines()),
                     'texts': [t.get_text() for t in ax.texts],
                     'xticklabels': [t.get_text() for t in ax.get_xticklabels()],
                     'named_xticklabels': [t.get_text() for t in ax.get_xticklabels() if t.get_text()],
                     'position': [scalar(v) for v in ax.get_position().bounds]})
    def visual_order(index):
        ax = fig.axes[index]
        spec = ax.get_subplotspec()
        if spec is not None:
            # Colorbars can wrap a subplot in a nested GridSpec. Preserve the
            # original row/column, including equal-aspect image plots.
            spec = spec.get_topmost_subplotspec()
            rows, columns = spec.get_gridspec().get_geometry()
            row, column = spec.rowspan.start / rows, spec.colspan.start / columns
        else:
            bounds = ax.get_position()
            row, column = -round(bounds.y1, 6), round(bounds.x0, 6)
        return (ax in colorbar_axes, row, column)
    empty = not (fig.texts or fig.artists or fig.lines or fig.images or fig.patches or fig.legends)
    empty = empty and all(not (ax.lines or ax.collections or ax.patches or ax.images or ax.texts
        or ax.artists or ax.get_legend() or ax.get_title() or ax.get_xlabel() or ax.get_ylabel()) for ax in fig.axes)
    return {'kind': 'figure', 'size': [scalar(v) for v in fig.get_size_inches()],
            'axis_count':len(axes), 'axes': axes, 'empty':bool(empty),
            'axes_by_position':[axes[i] for i in sorted(range(len(axes)), key=visual_order)]}


def scatter_snapshot(ax, fig):
    """Canonical visible point tuples; preserve coordinate/size/color pairing.

    Collection boundaries and input row order are not learning objectives.
    A colorbar must belong to a plotted mappable (or the same actual scale),
    rather than merely occupy an extra Axes beside an unrelated plot.
    """
    import numpy as np
    from matplotlib.collections import PathCollection
    points, mapped = [], []
    collections = [c for c in ax.collections if isinstance(c, PathCollection)]
    linked = [c for c in collections if getattr(c, 'colorbar', None) is not None
              and c.colorbar.ax in fig.axes and c.colorbar.mappable is c]
    def same_scale(c, link):
        if c is link: return True
        if c.cmap != link.cmap or type(c.norm) is not type(link.norm): return False
        if c.norm is link.norm: return True
        # Separate Normalize instances are equivalent when they describe the
        # same visible scale. Identity alone rejects harmless split calls.
        if (c.norm.vmin, c.norm.vmax, c.norm.clip) != (link.norm.vmin, link.norm.vmax, link.norm.clip): return False
        if c.norm.vmin is None or c.norm.vmax is None: return False
        samples = np.linspace(c.norm.vmin, c.norm.vmax, 17)
        return bool(np.allclose(c.norm(samples), link.norm(samples), equal_nan=True))
    connected = True
    for c in collections:
        if not c.get_visible() or not ax.get_visible(): continue
        offsets = np.ma.asarray(c.get_offsets())
        sizes = c.get_sizes()
        values = c.get_array()
        faces, edges = c.get_facecolors(), c.get_edgecolors()
        widths = c.get_linewidths()
        for i, xy in enumerate(offsets):
            if len(points) >= MAX_ITEMS: raise ValueError('산점도 표시 상한은 20,000개입니다.')
            if np.ma.is_masked(xy) or not np.all(np.isfinite(xy)) or not len(sizes): continue
            size = float(sizes[i % len(sizes)])
            if not math.isfinite(size) or size <= 0: continue
            alpha = 0.
            if len(faces): alpha = float(faces[i % len(faces)][3])
            if len(edges) and len(widths) and widths[i % len(widths)] > 0:
                alpha = max(alpha, float(edges[i % len(edges)][3]))
            if alpha <= 0: continue
            point = [float(xy[0]), float(xy[1]), size, alpha]
            points.append(point)
            if values is not None and len(values) and not np.ma.is_masked(values[i % len(values)]):
                value = float(values[i % len(values)])
                if math.isfinite(value):
                    mapped.append(point + [value])
                    connected = connected and any(same_scale(c, link) for link in linked)
    return {'points':sorted(points), 'mapped_points':sorted(mapped),
            'colorbar_connected':bool(mapped) and len(mapped) == len(points) and connected}


def equivalent(actual, expected, *, atol=1e-8, rtol=1e-6):
    # Explicitly distinguish bool from 0/1 and shape/labels from displayed strings.
    if isinstance(expected, bool): return isinstance(actual, bool) and actual == expected
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isclose(actual, expected, abs_tol=atol, rel_tol=rtol)
    if isinstance(expected, dict):
        if isinstance(actual,dict) and actual.get('__python_type__')=='dict': actual=actual['items']
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(equivalent(actual[k], v, atol=atol, rtol=rtol) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(equivalent(a, e, atol=atol, rtol=rtol) for a, e in zip(actual, expected))
    return type(actual) is type(expected) and actual == expected


def boxplot_snapshot(ax):
    """Read box geometry for both line boxes and patch_artist=True boxes."""
    import numpy as np
    from matplotlib.patches import PathPatch
    outlines=[]
    for line in ax.lines:
        x,y=np.asarray(line.get_xdata()),np.asarray(line.get_ydata())
        if len(x)==5 and x[0]==x[-1] and y[0]==y[-1]: outlines.append((x,y))
    for patch in ax.patches:
        if isinstance(patch,PathPatch):
            vertices=patch.get_path().vertices
            if len(vertices) in (5,6): outlines.append((vertices[:,0],vertices[:,1]))
    boxes=[]
    for x,y in outlines:
        low,high=float(x.min()),float(x.max())
        q1,q3=float(y.min()),float(y.max())
        center=(low+high)/2
        median=None; fliers=[]
        for line in ax.lines:
            lx,ly=np.asarray(line.get_xdata()),np.asarray(line.get_ydata())
            if len(lx)==2 and np.allclose(lx,[low,high]) and ly[0]==ly[1] and q1<=ly[0]<=q3:
                median=float(ly[0])
            if line.get_linestyle()=='None' and len(lx) and np.allclose(lx,center):
                fliers=[float(v) for v in ly]
        if median is not None: boxes.append({'center':center,'q1':q1,'q3':q3,'median':median,'fliers':fliers})
    return sorted(boxes,key=lambda box:box['center'])


def grade_snapshot(values, checks):
    """Selectors are authored paths in serialized values, never executable code."""
    results = []
    for check in checks:
        try:
            actual = values[check['target']]
            for key in check.get('path', []): actual = actual[key]
            if check.get('rule')=='positive_measurements':
                passed=isinstance(actual,list) and len(actual)==check['expected'] and all(
                    isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>0 for v in actual)
            else:
                passed = equivalent(actual, check['expected'], atol=check.get('atol', 1e-8), rtol=check.get('rtol', 1e-6))
            reason = '조건을 만족합니다.' if passed else check.get('feedback', '값·형태·라벨과 목표 조건을 다시 비교하세요.')
        except (KeyError, IndexError, TypeError):
            passed, reason = False, '필요한 결과 객체 또는 속성이 없습니다: ' + check['target']
        results.append({'label': check['label'], 'passed': passed, 'detail': reason})
    return {'passed': bool(results) and all(r['passed'] for r in results), 'checks': results}
