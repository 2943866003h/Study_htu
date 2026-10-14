#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : maps.py
# @Path       : signal-insight/src/signal_insight/viz/maps.py
# @Project    : signal-insight
# @Author     : Matri
# @Date       : 2026-10-14 08:36:03
# @Version    : v2.5.1
# @Description: 地图：长宽比、比例尺、指北针，区域专题图 Regions（几何只算一次，画图逐层叠到一个 ax 上）
# @ChangeLog:
#   2026-10-14 08:36:03 | Matri | v1.0.0 | 初始化创建
#   2026-10-14 14:00:00 | Matri | v2.0.0 | 拆成 Regions（只管几何）+ 逐层画到调用方给的 ax；标注改为绘制时按像素排版；
#                                          尺寸单位从"度"改成磅/比例，任何尺度、纬度都能用；颜色改从 C 取；
#                                          支持内环（洞）；外缘不再依赖公共边顶点对齐；DistrictMap 保留为旧接口的薄包装
#   2026-10-14 16:00:00 | Matri | v2.1.0 | 引线回到等距两列样式；新增参数包 LabelLayout（起点/拐点/终点可逐条改，
#                                          存 JSON 复用），Callouts.freeze() 把自动结果定下来，debug 标出坐标；
#                                          引线标注拆到 callouts.py
#   2026-10-14 20:00:00 | Matri | v2.2.0 | 区界拆成三层各自可设计：borders 内边界（公共边只画一次）、outline 外边界、
#                                          edges 指定区域整圈；fill 只管填色。label 默认 span + 中线分侧 + 纬度排序，
#                                          数据可直接给数值（名字、数值分开着色），四部分样式可设、可隐藏、可逐条覆盖
#   2026-10-14 22:00:00 | Matri | v2.3.0 | 颜色和 theme.py 脱钩：默认色统一从 viz.maps.colors 取，可整体设、临时设；
#                                          fill 可按区直接给颜色（colors=），points 可按列分组着色（by= + colors=）
#   2026-10-15 10:00:00 | Matri | v2.4.0 | 底图和数据层分开：base() 只画底图（底色 + 区界 + 附件），数据层 fill / points /
#                                          label / text 往上叠、缺哪个区就不画哪个，空数据不报错；新增区内标注 text()，
#                                          label(inside="auto") 放得下写区内、放不下引到外面；plot() = base() + 数据层
#   2026-10-15 14:00:00 | Matri | v2.5.0 | 地图在 ax 里居中：ax 占满给它的位置、多出的宽度两侧留白（frame fill=True），
#                                          存图裁边时不再被标题挤到一边；比例尺、指北针按地图框定位；新增别名 alias
#   2026-10-15 15:00:00 | Matri | v2.5.1 | 同一个 ax 画两遍底图（base 之后又 plot）时警告

"""地图：长宽比校正、比例尺、指北针，以及区域专题图 Regions。

和 theme.py 分开，是因为改动原因不同（AGENTS.md 第 2 条）：改配色的人不该面对一堆地图代码；
地图要按纬度换算距离、算标注位置，主题不需要。
不读数据库：多边形由调用方用 geo.rings_from_points 还原好传进来（AGENTS.md 第 4 条）。

分工：
  · Regions 只管"边界决定的东西"——外框、长宽比、每个区的落点——按边界算一次，不碰 figure / axes；
  · 画图都是"往调用方给的一个 ax 上加一层"，每层返回 matplotlib 自己的对象，可以接着改、接着叠；
  · 版面（几张子图、多大、地图放哪）由调用方用 plt.subplots / GridSpec 决定，地图模块不建 figure::

    geo = viz.maps.Regions(districts)                  # {名字: 环 或 [环, ...]}，环是 N×2 的 (lng, lat)

    # 底图：只由边界决定，不需要任何数据
    ax = geo.base()                                    # 底色 + 内边界 + 外边界 + 比例尺 + 指北针；也可以 geo.base(ax)

    # 数据层：往上叠，每层只画自己有数据的区，缺哪个区就不画哪个
    pc = geo.fill(ax, values, norm="log")              # 按数值填色；PatchCollection，fig.colorbar(pc) 直接出色条
    # 或 geo.fill(ax, colors={"西塔": "#1D6FA5"})        # 按区直接给颜色（类别图）
    geo.points(ax, sites, by="district", colors={"铁西区": "#D64545"})
    geo.text(ax, values)                               # 区内标注：写在每个区的落点上
    geo.label(ax, values, hot=["辽中区"])              # 外部引线：左右两列
    geo.label(ax, values, inside="auto")               # 放得下写区内，放不下引到外面
    viz.finish(ax.figure, title, subtitle, SOURCE, "D3_xx.png")

  常用组合一步到位：ax = geo.plot(values, texts=True, hot=["辽中区"], ax=ax) = base + fill + label，返回 ax 照常往上加。

颜色和 theme.py 无关：没传颜色时用 viz.maps.colors（见 mapcolors.py），可以整体改、临时改::

    viz.maps.colors.set(hot="#D64545", high="#1D6FA5")              # 之后画的地图都用它
    with viz.maps.colors.use(ink="#000000"): ...                    # 临时改

三层区界各管各的，样式参数直接是 matplotlib 的（color / lw / ls / alpha / zorder…），返回的对象还能接着改::

    geo.borders(ax, color="#C4CAD3", lw=0.5, ls=(0, (2, 2)))       # 内边界：虚线（公共边只画一次，虚线不会叠花）
    geo.outline(ax, color="#1F2937", lw=1.4)                        # 外边界
    geo.edges(ax, ["和平区", "沈河区"], color="#D64545", lw=1.2)     # 强调某几个区的整圈边界

引线标注的四个部分（名字、数值、引线、落点）各自给样式，False = 不显示；each 逐条覆盖::

    geo.label(ax, values, fmt="{:,.0f}",
              nameprops=dict(color="#6B7280"), valueprops=dict(weight="bold"),
              lineprops=dict(lw=0.6, ls="--"), dotprops=False,
              each={"辽中区": dict(value=dict(color="#D64545"), line=dict(color="#D64545", lw=1))})

引线位置先自动排、再手动修、最后固化成参数包（LabelLayout，JSON），同一张底图的所有图都用它::

    co = geo.label(ax, values, debug=True)             # 自动排一版；debug 在图上写出起点/拐点/终点的经纬度
    viz.finish(fig, ...)                               # 先画完（版面定了，坐标才是最终的）
    lay = co.freeze()                                  # 定下来，之后按参数包画
    lay.swap("和平区", "辽中区").move("新民市", dy=-0.05).edit("浑南区", end=(123.52, 41.70))
    lay.save(".../viz/layouts/shenyang_districts.json")
    geo.label(ax, values, layout="shenyang_districts") # 以后每张图：位置全按参数包，只换数值和样式

尺寸单位：地理量（视窗留白、裁剪范围）按地图跨度的比例；版面量（引线、间距）按磅。没有按"度"写死的数，
所以街道、城市、省，北纬 22° 还是 45°，同一套参数都能用。
"""
from __future__ import annotations

import warnings
from typing import Callable, Iterable, Mapping

import matplotlib.pyplot as plt
from matplotlib import cbook
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection, PatchCollection
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize
from matplotlib.patches import PathPatch
from matplotlib.path import Path

from .callouts import FURNITURE, PARTS, Callouts, LabelLayout, Leader, RegionTexts, _as_layout, _Auto   # 引线标注；callouts 不 import maps
from .mapcolors import MapColors, colors as MC   # 地图自己的颜色，不读 theme；颜色在调用那一刻取
from .theme import margins_in           # 只用它给旧接口 DistrictMap 算留白；theme 不 import maps

colors = MC          # viz.maps.colors：地图的默认颜色（set / use / reset），见 mapcolors.py

__all__ = ["LAT0", "LAND", "FURNITURE", "PARTS", "colors", "MapColors", "Regions", "Callouts", "RegionTexts", "LabelLayout", "Leader", "set_map_aspect", "scale_bar", "north_arrow", "DistrictMap"]

LAND = "viz.maps.land"   # 底图底色那一层的 gid：ax.collections 里按它找，可以事后改色
LAT0 = 41.8      # 沈阳大约的纬度。只给旧接口 DistrictMap 当默认值；Regions 用边界的中心纬度


# ── 任何经纬度底图都能用的三件 ──────────────────────────────────────────────
def set_map_aspect(ax, lat0: float | None = None, bare: bool = True) -> None:
    """长宽比校正：经度 1 度只有纬度 1 度的 cos(纬度) 倍长，不校正东西方向会被拉宽。
    lat0 不给就取当前视窗的中心纬度。bare=True 去掉刻度、网格和边框：读者用不到经纬度刻度，比例尺才有用。"""
    lat0 = float(np.mean(ax.get_ylim())) if lat0 is None else lat0
    ax.set_aspect(1 / np.cos(np.radians(lat0)), adjustable="box")
    if bare:
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)


def _view(ax) -> tuple[float, float, float, float]:
    """地图框 (x0, x1, y0, y1)：frame() 定下的那块（地图 + 留白）；不是 frame 出来的 ax 就用当前视窗。
    比例尺、指北针按它定位，地图居中、两侧有空白时也贴着地图，不会跑到空白里。"""
    fr = getattr(ax, "_viz_frame", None)
    if fr is not None:
        return fr[:4]
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    return x0, x1, y0, y1


def _fit_view(ax) -> None:
    """视窗扩到填满 ax 的框：地图框完整、居中，长宽比不变，多出来的地方留白（引线标注就排在这里）。
    每次排版（apply_aspect）时按当时 ax 的大小算，图缩放、换版面都对。调用方自己 set_xlim / set_ylim
    改过视窗（放大某一块）时，以改过的为新的地图框。"""
    x0, x1, y0, y1, aspect = ax._viz_frame
    last = ax._viz_last
    cur = (*ax.get_xlim(), *ax.get_ylim())
    if not np.allclose(cur, last, rtol=0, atol=1e-12):                 # 调用方改过视窗
        x0, x1, y0, y1 = cur
        ax._viz_frame = (x0, x1, y0, y1, aspect)
    pos = ax.get_position(original=True)
    w, h = pos.width * ax.figure.get_figwidth(), pos.height * ax.figure.get_figheight()
    if w <= 0 or h <= 0:
        return
    fx, fy, r = x1 - x0, y1 - y0, h / (aspect * w)                    # 显示时 dy/dx 要等于 r
    dx, dy = (fy / r, fy) if fy / fx > r else (fx, fx * r)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ax.set_xlim(cx - dx / 2, cx + dx / 2, emit=False, auto=None)
    ax.set_ylim(cy - dy / 2, cy + dy / 2, emit=False, auto=None)
    ax._viz_last = (*ax.get_xlim(), *ax.get_ylim())


def _install_fit(ax) -> None:
    """让 ax 每次排版时调用 _fit_view（只装一次）。"""
    if getattr(ax, "_viz_fit_installed", False):
        return
    orig = ax.apply_aspect

    def apply_aspect(position=None):
        orig(position)
        _fit_view(ax)
    ax.apply_aspect = apply_aspect
    ax._viz_fit_installed = True


def _nice(x: float) -> float:
    """不超过 x 的 1 / 2 / 5 × 10ⁿ。"""
    e = 10 ** np.floor(np.log10(x))
    return next(m * e for m in (5, 2, 1) if m * e <= x)


def scale_bar(ax, km: float | None = None, lat0: float | None = None, x: float = 0.04, y: float = 0.04) -> None:
    """比例尺，默认左下角。km 不给就取约 1/4 视窗宽的整数（1、2、5、10、20…），不足 1 公里写成米。
    x, y 是比例尺左端在地图框里的比例位置（0~1，地图框 = frame 定下的地图 + 留白）；压到区域上时挪一下，如 x=0.6, y=0.04 放到右下。
    先设好视窗再调用（位置按当前视窗算）。"""
    x0, x1, y0, y1 = _view(ax)
    lat0 = (y0 + y1) / 2 if lat0 is None else lat0
    km_per_deg = 111.32 * np.cos(np.radians(lat0))
    km = _nice(0.25 * (x1 - x0) * km_per_deg) if km is None else km
    deg, ink = km / km_per_deg, MC.ink
    xs, ys = x0 + x * (x1 - x0), y0 + y * (y1 - y0)
    ax.plot([xs, xs + deg], [ys, ys], color=ink, lw=1.2, solid_capstyle="butt", gid=FURNITURE)
    for x in (xs, xs + deg):                                         # 两端短竖线
        ax.plot([x, x], [ys, ys + 0.008 * (y1 - y0)], color=ink, lw=0.8, gid=FURNITURE)
    ax.text(xs + deg / 2, ys + 0.018 * (y1 - y0), f"{km:g} 公里" if km >= 1 else f"{km * 1000:g} 米",
            ha="center", va="bottom", fontsize=9, color=ink, gid=FURNITURE)


def north_arrow(ax, x: float = 0.95, y: float = 0.95) -> None:
    """指北针，默认地图框右上角（x, y 是地图框里的比例位置）。"""
    ink = MC.ink
    x0, x1, y0, y1 = _view(ax)
    px, py = x0 + x * (x1 - x0), y0 + y * (y1 - y0)
    ax.annotate("北", xy=(px, py), xytext=(px, py - 0.08 * (y1 - y0)), xycoords="data",
                ha="center", va="top", fontsize=9, color=ink,
                arrowprops=dict(arrowstyle="-|>", color=ink, lw=0.8, shrinkA=0, shrinkB=0), gid=FURNITURE)

# ── 几何小工具 ────────────────────────────────────────────────────────────
def _as_rings(geom, name) -> list[np.ndarray]:
    """一个环（N×2）或一组环 → [N×2, ...]；去掉首尾重复点和不足 3 个点的环。"""
    try:
        arr = np.asarray(geom, float)
    except (ValueError, TypeError):                                    # 长短不一的一组环
        arr = None
    raw = [arr] if arr is not None and arr.ndim == 2 else [np.asarray(r, float) for r in geom]
    rings = []
    for r in raw:
        if r.ndim != 2 or r.shape[1] != 2:
            raise ValueError(f"{name!r} 的环应是 N×2 的 (lng, lat)，拿到形状 {r.shape}")
        if len(r) > 1 and np.allclose(r[0], r[-1]):
            r = r[:-1]
        r = r[np.any(r != np.roll(r, -1, 0), axis=1)] if len(r) > 1 else r     # 去掉连续重复点（零长度的边）
        if len(r) >= 3:
            rings.append(r)
    if not rings:
        raise ValueError(f"{name!r} 没有有效的环（每个环至少 3 个点）")
    return rings


def _area(r: np.ndarray) -> float:
    """带符号面积，逆时针为正。"""
    x, y = r[:, 0], r[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _orient(rings: list[np.ndarray]) -> list[np.ndarray]:
    """被奇数个环包住的是洞，统一转成顺时针，其余转成逆时针：每条边的左手边都是区内。
    matplotlib 填色按环绕方向，洞才会是空的；分内外边界时也靠它知道"区外在哪一侧"。"""
    out = []
    for i, r in enumerate(rings):
        depth = sum(Path(o).contains_points(r).mean() > 0.5 for j, o in enumerate(rings) if j != i)
        out.append(r[::-1] if (_area(r) > 0) == (depth % 2 == 1) else r)
    return out


def _region_path(rings: list[np.ndarray]) -> Path:
    """一个区域的所有环（已经 _orient 过）拼成一条复合路径。"""
    verts, codes = [], []
    for r in rings:
        verts += [*r, r[0]]
        codes += [Path.MOVETO] + [Path.LINETO] * (len(r) - 1) + [Path.CLOSEPOLY]
    return Path(np.asarray(verts), codes)


def _inside(rings: list[np.ndarray], pts: np.ndarray) -> np.ndarray:
    """点在不在区内：被奇数个环包住才算（洞里的点被外环和洞各包一次，是偶数）。
    不用 Path.contains_points 判断整条复合路径：它对各子路径的结果取"或"，洞里的点也会算在区内。"""
    return np.sum([Path(r).contains_points(pts) for r in rings], axis=0) % 2 == 1


def _topology(rings: dict[str, list[np.ndarray]], k: float) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """所有区的边分成外边界和内边界（公共边），内边界每条只留一份。返回 (外边界折线, 内边界折线)，都是 N×2 (lng, lat)。

    1. 顶点完全相同的边两两配对 = 公共边（同一来源的边界数据，公共边顶点通常一致；快）；
    2. 配不上的边按几何判断：从边的中点往右手边（区外那侧，见 _orient）挪一小步，
       落进别的区 = 公共边，落在所有区外 = 外边界。先挪一小步，落空再挪远一点（跨过相邻区之间的细缝），
       所以相邻区顶点对不齐、有细小缝隙或重叠（逐个多边形简化过的数据常见）也能分对；
    3. 公共边两侧各有一份，只留名字靠前那个区的——虚线不会两份叠在一起花掉；
    4. 同一个环上同类的连续边连成一条折线，虚线的节奏、拐角的连接都是连续的。"""
    names = list(rings)
    flat = [(i, r) for i, n in enumerate(names) for r in rings[n]]
    P = np.vstack([r for _, r in flat])
    Q = np.vstack([np.roll(r, -1, 0) for _, r in flat])
    R = np.concatenate([np.full(len(r), i) for i, r in flat])
    idx = np.arange(len(P))

    key = np.round(np.hstack([P, Q]), 9)                               # 1) 顶点相同：两端点排好序再比
    flip = (key[:, 0] > key[:, 2]) | ((key[:, 0] == key[:, 2]) & (key[:, 1] > key[:, 3]))
    key[flip] = key[flip][:, [2, 3, 0, 1]]
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    inv = inv.ravel()
    first = np.full(len(cnt), len(P))
    np.minimum.at(first, inv, idx)
    shared = cnt[inv] >= 2
    kind = np.zeros(len(P), int)                                       # 0 外边界，1 内边界（画），2 内边界（另一侧画了）
    kind[shared] = np.where(idx[shared] == first[inv[shared]], 1, 2)

    rest = idx[~shared]                                                # 2) 配不上的：往区外挪一小步看落在哪
    if len(rest):
        scale = np.array([k, 1.0])                                     # 经度按纬度折算，挪的距离两个方向一样
        p, q = P[rest] * scale, Q[rest] * scale
        d = q - p
        length = np.hypot(d[:, 0], d[:, 1])
        diag = float(np.hypot(*(P.max(0) - P.min(0)) * scale))
        right = np.column_stack([d[:, 1], -d[:, 0]]) / np.maximum(length, 1e-30)[:, None]
        boxes = [(np.min([r.min(0) for r in rings[n]], 0), np.max([r.max(0) for r in rings[n]], 0)) for n in names]
        hit = np.full(len(rest), -1)
        for step in (1e-4, 3e-3):                                      # 先挪一小步；落空再挪远些，跨过相邻区之间的细缝
            eps = np.minimum(step * diag, 0.25 * length)              # 不超过边长的 1/4：外缘拐角处不会挪进对面的区
            probe = ((p + q) / 2 + eps[:, None] * right) / scale
            for i, n in enumerate(names):
                lo, hi = boxes[i]
                m = (hit < 0) & (R[rest] != i) & np.all((probe >= lo) & (probe <= hi), axis=1)
                if m.any():
                    hit[np.nonzero(m)[0][_inside(rings[n], probe[m])]] = i
        inner = hit >= 0
        kind[rest[inner]] = np.where(R[rest[inner]] < hit[inner], 1, 2)

    outer_lines, inner_lines, start = [], [], 0                        # 4) 连成折线
    for _, r in flat:
        kd, m = kind[start:start + len(r)], len(r)
        start += m
        cuts = np.nonzero(kd != np.roll(kd, 1))[0]
        if len(cuts) == 0:                                             # 整个环同一类：闭合折线
            if kd[0] < 2:
                (outer_lines if kd[0] == 0 else inner_lines).append(np.vstack([r, r[:1]]))
            continue
        for a, b in zip(cuts, np.append(cuts[1:], cuts[0] + m)):
            if kd[a] < 2:
                seg_idx = np.arange(a, b + 1) % m                      # 第 a..b-1 条边 = 顶点 a..b
                (outer_lines if kd[a] == 0 else inner_lines).append(r[seg_idx])
    return outer_lines, inner_lines


def _line_style(defaults: dict, kw: dict) -> dict:
    """默认样式 + 调用方的样式，别名统一成全名（lw 和 linewidth 不会打架）。"""
    return {**cbook.normalize_kwargs(defaults, LineCollection), **cbook.normalize_kwargs(kw, LineCollection)}


def _dist_to_segments(p: np.ndarray, seg: np.ndarray) -> np.ndarray:
    """每个点到一组线段的最短距离。p: (G, 2)，seg: (S, 2, 2)。"""
    a, ab = seg[:, 0], seg[:, 1] - seg[:, 0]
    t = (((p[:, None, :] - a) * ab).sum(-1) / np.maximum((ab ** 2).sum(-1), 1e-30)).clip(0, 1)
    return np.sqrt(((p[:, None, :] - a - t[..., None] * ab) ** 2).sum(-1)).min(1)


def _pole(rings: list[np.ndarray], k: float, n: int = 32) -> np.ndarray:
    """落点：区内离边界（含洞的边）最远的点，经度差按纬度折成同一长度。一定在区里、不贴边、不落进洞，
    引线进区的位置比"中心点"稳。先粗网格找，再在最好的点周围细化两轮。"""
    scale = np.array([k, 1.0])
    seg = np.concatenate([np.stack([r, np.roll(r, -1, 0)], 1) for r in rings])
    seg = seg[:: len(seg) // 800 + 1] * scale                           # 边太多时抽样，精度够用
    big = max(rings, key=lambda r: abs(_area(r)))
    lo, hi, best = big.min(0), big.max(0), None
    for _ in range(3):
        gx, gy = np.meshgrid(np.linspace(lo[0], hi[0], n), np.linspace(lo[1], hi[1], n))
        g = np.column_stack([gx.ravel(), gy.ravel()])
        g = g[_inside(rings, g)]
        if len(g) == 0:
            break
        best = g[_dist_to_segments(g * scale, seg).argmax()]
        step = (hi - lo) / (n - 1)
        lo, hi = best - 2 * step, best + 2 * step
    return best if best is not None else big.mean(0)


def _norm(norm, values: np.ma.MaskedArray) -> Normalize:
    if isinstance(norm, Normalize):
        return norm
    v = values.compressed()
    if len(v) == 0:                                                     # 没有数据：什么都不填，给个占位色阶
        return LogNorm(1, 10) if norm == "log" else Normalize(0, 1)
    if norm == "log":
        v = v[v > 0]
        if len(v) == 0:
            raise ValueError("norm='log' 需要至少一个正数")
        return LogNorm(v.min() * 0.6, v.max())                          # 留一点底色，最小值不会纯白
    if norm == "linear":                                                # 非负数据从 0 起；有负数从最小值起
        lo, hi = (min(0.0, v.min()), v.max()) if len(v) else (0.0, 1.0)
        return Normalize(lo, hi if hi > lo else lo + 1)
    raise ValueError("norm 只能是 'linear'、'log' 或 Normalize 对象")


# ── 区域 ──────────────────────────────────────────────────────────────────
class Regions:
    """一组命名多边形（区县、街道、网格……），坐标是经纬度。只存边界和由边界决定的东西，不碰 figure / axes。

    regions: {名字: 环 或 [环, ...]}，环是 N×2 的 (lng, lat)；包住别的区域的，把被包住的那圈作为内环一起给（洞）。
    lat0:    长宽比和距离按哪个纬度折算，不给就取边界的中心纬度。
    alias:   {名字: 标注里显示的名字}，名字太长时用，如 {"棋盘山风景区": "棋盘山"}。只改标注显示，
             数据、hot、each、参数包里仍用原名。之后也可以 geo.alias["沈阳世博园"] = "世博园"。
    """

    def __init__(self, regions: Mapping[str, Iterable], *, lat0: float | None = None,
                 alias: Mapping[str, str] | None = None):
        self._rings = {str(n): _orient(_as_rings(g, n)) for n, g in regions.items()}
        if not self._rings:
            raise ValueError("regions 是空的")
        pts = np.vstack([r for rings in self._rings.values() for r in rings])
        (x0, y0), (x1, y1) = pts.min(0), pts.max(0)
        self.bounds = (float(x0), float(y0), float(x1), float(y1))
        self.lat0 = (y0 + y1) / 2 if lat0 is None else float(lat0)
        self._k = float(np.cos(np.radians(self.lat0)))                 # 经度 1 度的长度 ÷ 纬度 1 度的长度
        self._paths = {n: _region_path(r) for n, r in self._rings.items()}
        self._size = {n: max(abs(_area(r)) for r in rings) for n, rings in self._rings.items()}
        self._anchors: dict[str, np.ndarray] = {}
        self._topo: tuple[list, list] | None = None
        self.alias: dict[str, str] = {str(k): str(v) for k, v in (alias or {}).items()}
        self._known(self.alias, "alias")

    @classmethod
    def from_geodataframe(cls, gdf, name: str, **kw) -> "Regions":
        """GeoDataFrame（Polygon / MultiPolygon，经纬度坐标）→ Regions，内环自动带上。不装 geopandas 也能 import 本模块。"""
        out: dict[str, list] = {}
        for n, geom in zip(gdf[name], gdf.geometry):
            for poly in getattr(geom, "geoms", [geom]):
                out.setdefault(str(n), []).extend(np.asarray(r.coords)[:, :2] for r in (poly.exterior, *poly.interiors))
        return cls(out, **kw)

    # ---------------------------------------------------------------- 查询
    @property
    def names(self) -> list[str]:
        return list(self._rings)

    def __len__(self) -> int:
        return len(self._rings)

    def __contains__(self, name) -> bool:
        return str(name) in self._rings

    def __repr__(self) -> str:
        x0, y0, x1, y1 = self.bounds
        return f"Regions({len(self)} 个区域, lng {x0:.3f}–{x1:.3f}, lat {y0:.3f}–{y1:.3f})"

    @property
    def aspect(self) -> float:
        """地图画出来的 宽 ÷ 高。配 figsize 用：宽 ≈ 高 × geo.aspect + 两侧标注宽。"""
        x0, y0, x1, y1 = self.bounds
        return (x1 - x0) * self._k / (y1 - y0)

    def anchor(self, name: str) -> np.ndarray:
        """name 的落点（区内离边界最远的点），用到才算，算过就记住。"""
        name = str(name)
        if name not in self._anchors:
            self._anchors[name] = _pole(self._rings[name], self._k)
        return self._anchors[name]

    def clip(self, df: pd.DataFrame, margin: float = 0.1, lng: str = "lng", lat: str = "lat") -> pd.DataFrame:
        """只留边界外框附近的点：外框四边各外扩 margin × 跨度（默认 10%，市外的点画一圈）。"""
        x0, y0, x1, y1 = self.bounds
        mx, my = margin * (x1 - x0), margin * (y1 - y0)
        return df[df[lng].between(x0 - mx, x1 + mx) & df[lat].between(y0 - my, y1 + my)]

    def _known(self, names: Iterable, what: str) -> None:
        missing = sorted(set(map(str, names)) - set(self._rings))
        if missing:
            warnings.warn(f"{what} 里这些名字不在边界数据里，地图上不画：{missing}", stacklevel=3)

    # ---------------------------------------------------------------- 往 ax 上加层
    def frame(self, ax, margin: float = 0.02, bare: bool = True, fill: bool = True):
        """把 ax 变成这张地图：地图框 = 外框四周留 margin（按长边比例），长宽比按纬度校正。返回 ax。

        fill=True（默认）：ax 占满给它的位置，地图完整、居中，多出来的宽度（或高度）两侧留白，
          引线标注就排在留白里；存图裁边（bbox_inches="tight"）时地图也在正中，不会被标题挤到一边。
        fill=False：ax 缩到地图本身大小（旧行为）。
        想放大某一块，frame 之后自己 ax.set_xlim / set_ylim，以改过的为准。"""
        x0, y0, x1, y1 = self.bounds
        pad = margin * max((x1 - x0) * self._k, y1 - y0)
        fx0, fx1, fy0, fy1 = x0 - pad / self._k, x1 + pad / self._k, y0 - pad, y1 + pad
        ax.set_xlim(fx0, fx1)
        ax.set_ylim(fy0, fy1)
        set_map_aspect(ax, self.lat0, bare)
        ax._viz_frame = (fx0, fx1, fy0, fy1, 1 / self._k)
        ax._viz_last = (fx0, fx1, fy0, fy1)          # 之后视窗和它不一样 = 调用方自己放大过
        if fill:
            ax.set_aspect("auto")
            _install_fit(ax)
        return ax

    def base(self, ax=None, *, land=True, borders: Mapping | bool = True, outline: Mapping | bool = True,
             scale: Mapping | bool = True, north: Mapping | bool = True, km: float | None = None,
             margin: float = 0.02, height: float = 6.0, room: bool = True, fill: bool = True):
        """底图：只由边界决定，不需要任何数据。frame → 底色 → 内边界 → 外边界 → 比例尺 → 指北针，返回 ax。
        数据层（fill / points / text / label）之后往上叠，画在底色上面、区界下面（填色）或最上面（标注）。

        ax:      不给就新建一张图（constrained 版面），高 height 英寸，宽按长宽比；room=True 两侧共多留 3.2 英寸放引线标注。
                 给了 ax：地图在 ax 里居中，多出来的宽度两侧留白（见 frame 的 fill），标注加上去时排在留白里。
        land:    底色。True = colors.land（浅灰）；给颜色字符串；给 dict 传 PatchCollection 样式；False 不画。
                 有了底色，白色内边界才看得见；没数据的区也露出底色，和"数值低"的白色区分得开。
        borders / outline: True 默认样式；dict 传样式（color / lw / ls…）；False 不画。
        scale / north:     True 默认位置；dict 改位置，如 scale=dict(x=0.6)（轴内比例）；False 不画。
        margin:  视窗留白（按长边比例）。区域贴着外框四角时调大，给比例尺、指北针腾地方。"""
        if ax is None:
            _, ax = plt.subplots(figsize=(height * self.aspect + (3.2 if room else 0.4), height), layout="constrained")
        elif getattr(ax, "_viz_base", False):
            warnings.warn("这个 ax 已经画过底图，又画了一遍：比例尺、区界会重复，前一次的样式会被盖住。"
                          "geo.base(ax) 之后用 fill / points / text / label 加数据，不要再调 geo.plot(ax=ax)",
                          stacklevel=2)
        ax._viz_base = True
        self.frame(ax, margin=margin, fill=fill)
        if land is not False:
            style = dict(facecolor=MC.land, edgecolor="face", linewidth=0.3, zorder=0.8)
            if isinstance(land, Mapping):
                style.update(cbook.normalize_kwargs(dict(land), PatchCollection))
            elif land is not True:
                style["facecolor"] = land
            pc = PatchCollection([PathPatch(self._paths[n]) for n in self._rings], **style)
            pc.set_gid(LAND)
            ax.add_collection(pc, autolim=False)
        if borders is not False:
            self.borders(ax, **({} if borders is True else borders))
        if outline is not False:
            self.outline(ax, **({} if outline is True else outline))
        if scale is not False:
            scale_bar(ax, km, self.lat0, **({} if scale is True else scale))
        if north is not False:
            north_arrow(ax, **({} if north is True else north))
        return ax

    def fill(self, ax, values: Mapping[str, float] | pd.Series | None = None, *, colors=None,
             cmap=None, norm: str | Normalize = "linear", nan_color=None, edgecolor="face", lw: float = 0.3,
             **kw) -> PatchCollection:
        """填色，两种方式二选一。只管填色：区界用 borders / outline / edges 另画。

        按数值（values）：{名字: 数} 或 Series，按色阶着色（默认 colors.low → colors.high，即白 → 灰）。
          norm: "linear"（非负数据从 0 到最大值）| "log"（数值差一个数量级以上时用）| 自己传 Normalize。
          返回的 PatchCollection 本身就是 ScalarMappable，fig.colorbar(pc) 直接出色条，
          pc.cmap / pc.norm 给右边的图用同一色阶。
        按区给颜色（colors）：{名字: 颜色}，类别图用（商圈各一色、强调某几个区）；也可以给一个颜色，全部填它。
        nan_color: 没有数值 / 没给颜色的区域填什么色，默认 colors.nan（"none" = 不填，露出底色）。
        edgecolor="face" + 细线：相邻两块之间不留抗锯齿的白缝；想让填色自带分界线，给 edgecolor="white", lw=0.9。"""
        if values is not None and colors is not None:
            raise ValueError("values 和 colors 二选一：按数值上色给 values，按区直接给颜色用 colors")
        nan_color = MC.nan if nan_color is None else nan_color
        order = sorted(self._rings, key=lambda n: -self._size[n])     # 大的先画：没带内环的数据，被包住的小区也不会被盖住
        patches = [PathPatch(self._paths[n]) for n in order]
        if colors is not None:
            if isinstance(colors, str) or not isinstance(colors, Mapping) and mcolors.is_color_like(colors):
                colors = dict.fromkeys(self._rings, colors)
            colors = {str(k): v for k, v in dict(colors).items()}
            self._known(colors, "colors")
            if bad := {n: c for n, c in colors.items() if not mcolors.is_color_like(c)}:
                raise ValueError(f"colors 里这些不是颜色：{bad}")
            face = [colors.get(n, nan_color) for n in order]
            pc = PatchCollection(patches, facecolors=face, edgecolor=edgecolor, linewidth=lw, **kw)
            ax.add_collection(pc, autolim=False)
            return pc
        vals = {} if values is None else {str(k): v for k, v in dict(values).items()}
        self._known(vals, "values")
        arr = np.ma.masked_invalid(np.array([vals.get(n, np.nan) for n in order], float))
        cmap = plt.get_cmap(cmap) if isinstance(cmap, str) else cmap
        cmap = (cmap or LinearSegmentedColormap.from_list("regions", [MC.low, MC.high])).with_extremes(bad=nan_color)
        pc = PatchCollection(patches, cmap=cmap, norm=_norm(norm, arr), edgecolor=edgecolor, linewidth=lw, **kw)
        pc.set_array(arr)
        ax.add_collection(pc, autolim=False)
        return pc

    @property
    def _edges(self) -> tuple[list[np.ndarray], list[np.ndarray]]:
        """(外边界折线, 内边界折线)，用到才算，算过就记住。"""
        if self._topo is None:
            self._topo = _topology(self._rings, self._k)
        return self._topo

    def borders(self, ax, color=None, lw: float = 0.9, ls="-", **kw) -> LineCollection:
        """内边界：相邻两区之间的公共边（含飞地和包住它的区之间那一圈），不含全图最外圈。
        每条公共边只画一次，虚线不会两份叠花。默认 colors.border（白线）：在浅色填充上像\"切开\"，不和数据抢。
        样式参数就是 LineCollection 的（color / lw / ls / alpha / zorder…），返回的对象可以接着改。"""
        lc = LineCollection(self._edges[1], **_line_style(
            dict(color=color or MC.border, lw=lw, ls=ls, capstyle="round", joinstyle="round", zorder=1.5), kw))
        ax.add_collection(lc, autolim=False)
        return lc

    def outline(self, ax, color=None, lw: float = 1.0, ls="-", **kw) -> LineCollection:
        """外边界：所有区拼起来的最外圈（有飞地、海岛就是多圈），区与区之间的线不画。默认 colors.ink。
        线压在边界正中（一半在区内）。样式参数同 borders。"""
        lc = LineCollection(self._edges[0], **_line_style(
            dict(color=color or MC.ink, lw=lw, ls=ls, capstyle="round", joinstyle="round", zorder=1.6), kw))
        ax.add_collection(lc, autolim=False)
        return lc

    def edges(self, ax, names: Iterable[str], color=None, lw: float = 1.2, ls="-", **kw) -> PatchCollection:
        """指定区域的整圈边界（带洞的连洞边一起），画在内外边界上面：强调某几个区。默认 colors.hot。"""
        names = [str(n) for n in names]
        self._known(names, "edges")
        style = {**cbook.normalize_kwargs(dict(edgecolor=color or MC.hot, lw=lw, ls=ls, joinstyle="round",
                                               capstyle="round", zorder=1.7), PatchCollection),
                 **cbook.normalize_kwargs(kw, PatchCollection)}
        pc = PatchCollection([PathPatch(self._paths[n]) for n in names if n in self._rings],
                             facecolor="none", **style)
        ax.add_collection(pc, autolim=False)
        return pc

    def points(self, ax, data, *, lng: str = "lng", lat: str = "lat", color=None,
               by: str | None = None, colors: Mapping | None = None, s: float = 1, **kw):
        """叠点：data 是带 lng/lat 列的 DataFrame（列名可改），或 N×2 数组。先画的在下面。返回 PathCollection。
        color: 所有点一个颜色（默认 colors.ink）。
        by + colors: 按 DataFrame 的某一列分组着色，如 by="district", colors={"铁西区": "#D64545"}；
                     colors 里没有的组用 color。"""
        if isinstance(data, pd.DataFrame):
            x, y = data[lng].to_numpy(), data[lat].to_numpy()
        else:
            xy = np.asarray(data, float)
            x, y = xy[:, 0], xy[:, 1]
        base = color or MC.ink
        if by is not None:
            if not isinstance(data, pd.DataFrame):
                raise TypeError("by= 只能配 DataFrame 用（按它的一列分组）")
            colors = {str(k): v for k, v in dict(colors or {}).items()}
            if bad := {k: c for k, c in colors.items() if not mcolors.is_color_like(c)}:
                raise ValueError(f"colors 里这些不是颜色：{bad}")
            groups = data[by].astype(str)
            if missing := sorted(set(colors) - set(groups)):
                warnings.warn(f"colors 里这些组在 {by!r} 列里没有：{missing}", stacklevel=2)
            base = [colors.get(g, base) for g in groups]
        elif colors is not None:
            raise TypeError("colors 要配 by= 一起用：by 指定按哪一列分组")
        return ax.scatter(x, y, s=s, color=base, **{"lw": 0, "zorder": 3, **kw})

    def text(self, ax, texts: Mapping | pd.Series, *, hot: Iterable[str] = (), fmt: str | Callable = "{:,.0f}",
             nameprops=None, valueprops=None, each: Mapping[str, Mapping | bool] | None = None,
             at: Mapping[str, tuple[float, float]] | None = None, fs: float = 9, stack: bool = True,
             sep: float = 1, halo=True, overflow: str = "show", alias: Mapping[str, str] | None = None) -> RegionTexts:
        """区内标注：名字和数值直接写在每个区的落点上（区内离边界最远的点，不贴边、不落进洞）。返回 RegionTexts。

        数据写法、nameprops / valueprops / each / hot / fmt 和 label() 完全一样（line / dot 两部分在这里不用）。
        stack:    True 名字在上、数值在下（默认，窄）；False 写成一行"名字 数值"。
        sep:      上下两行之间（磅）。halo: 文字白边，True / 颜色 / False，压在填色上也看得清。
        overflow: 文字超出所在区时，"show" 照画并警告一次，"hide" 不画；超出的名字在 co.overflow。
                  想让放不下的自动引到外面，用 geo.label(ax, texts, inside="auto")。
        at:       {名字: (lng, lat)} 手动指定位置。
        alias:    {名字: 显示名}，这一次的别名，盖过 geo.alias。"""
        items, each = self._label_data(texts, each, hot, alias)
        return self._text_layer(ax, items, each=each, hot=hot, fmt=fmt, nameprops=nameprops, valueprops=valueprops,
                                at=at, fs=fs, stack=stack, sep=sep, halo=halo, overflow=overflow)

    def _text_layer(self, ax, items, *, each, hot, fmt, nameprops, valueprops, at, fs, stack=True, sep=1,
                    halo=True, overflow="show") -> RegionTexts:
        at = {str(k): np.asarray(v, float) for k, v in (at or {}).items()}
        anchors = {n: at[n] if n in at else self.anchor(n) for n in items}
        rt = RegionTexts(ax, items, anchors, lambda n, pts: _inside(self._rings[n], np.asarray(pts, float)),
                         props=dict(name=nameprops, value=valueprops), each=each, hot=hot, fmt=fmt, fs=fs,
                         stack=stack, sep=sep, halo=halo, overflow=overflow)
        ax.add_artist(rt)
        return rt

    def _label_data(self, texts, each, hot, alias=None) -> tuple[dict, dict]:
        """label / text 共用：数据 → {名字: (显示文字, 数值)}，去掉底图没有的名字和 each 里给了 False 的。名字写错只警告。
        数据给的是数（或 NaN）时，显示文字 = 别名（这一次的 alias > geo.alias > 原名）；给了字符串、(文字, 数) 就照写。"""
        alias = {**self.alias, **{str(k): str(v) for k, v in (alias or {}).items()}}
        self._known(alias, "alias")
        items = _label_items({} if texts is None else texts, alias)
        self._known(items, "texts")
        each = {str(k): v for k, v in (each or {}).items()}
        self._known([*each, *map(str, hot)], "each / hot")             # 名字写错时提醒，不然样式悄悄不生效
        items = {n: v for n, v in items.items() if n in self._rings and each.get(n, True) is not False}
        return items, {n: v for n, v in each.items() if n in items}

    def label(self, ax, texts: Mapping | pd.Series, *, layout=None, hot: Iterable[str] = (),
              fmt: str | Callable = "{:,.0f}", nameprops=None, valueprops=None, lineprops=None, dotprops=None,
              each: Mapping[str, Mapping | bool] | None = None,
              side="auto", split="center", spread: str = "span", angle: float | None = None, uncross: bool = True,
              at: Mapping[str, tuple[float, float]] | None = None, fs: float = 9,
              elbow: float = 14, stub: float = 28, gap: float = 4, pad: float = 3, sep: float = 3,
              inside=False, alias: Mapping[str, str] | None = None, debug: bool = False) -> Callouts:
        """左右两列引线标注：文字 → 起点 —横线— 拐点 → 斜线进区到终点（落点）。返回 Callouts。

        texts:  {名字: 值} 或 Series，值可以是
                  数 → 写\"名字 数值\"，名字和数值是两段文字，可以分开设样式（NaN 只写名字）；
                  字符串 → 整段照写（旧用法）；(文字, 数) → 自己定名字那段的写法，再跟数值。
        fmt:    数值的写法，格式串或函数，默认千分位取整。

        样式（四个部分：名字 / 数值 / 引线 / 落点）：
          nameprops / valueprops: Text 的参数（color、size、weight、family…）
          lineprops:              Line2D 的参数（color、lw、ls、alpha…）
          dotprops:               Line2D 的标记参数（marker、ms、color、mec、mew…）
          给 False = 这部分不画。each={名字: {\"name\"/\"value\"/\"line\"/\"dot\": 参数 或 False}} 逐条覆盖，
          each={名字: False} 整条不画。优先级：默认 < 整体 < hot < each。
          hot: 强调的名字，名字和数值换成 colors.hot 加粗（一种颜色强调一件事）。
          画完还能直接改：co.texts / co.nums / co.lines / co.dots 按名字取。

        位置，两种来源：
          · 自动（layout=None）：每次绘制按当时的像素排一遍，作为起点。满意了用 co.freeze() 定下来，
            得到 LabelLayout（参数包），可以改几条再 save 成 JSON；
          · 套参数包（layout=LabelLayout / JSON 路径 / viz/layouts/ 下的名字）：位置全按参数包画，
            同一张底图的所有图标注位置都一样。texts 只画参数包里有的名字，没有的给警告；
            参数包里的终点不在对应区域里时也警告（多半是拿了别的底图的参数包）。
        以下只对自动排版有效（套参数包时位置、stub、gap 都以参数包为准）：
          split:  分左右的经度线。\"center\"（默认）= 地图外框左右两沿的正中，落点在线西的进左列、线东的进右列；
                  \"balance\" = 全图所有区落点经度的中位数（两列条数接近，城区偏在一边时用）；也可以直接给经度。
                  分侧只看底图，不看这次标了哪几个区：同一个区在每张图里都在同一侧。
          side:   \"auto\"（按 split）| \"left\" | \"right\" | {名字: \"left\"/\"right\"} 单独指定。
          spread: \"span\"（默认：两列都铺满全部落点的上下范围再等距）| \"fit\"（行位贴着落点高度，引线更平）。
          angle:  None（默认：同一列的拐点对齐在一条竖线上）| 度数（0–90，所有斜线都是这个角度、彼此平行，
                  拐点沿横线往里收；太陡走不到时停在列线上）。90 = 先竖后横的直角引线。
          uncross: 同列两条引线交叉时对调两者的上下顺序（默认开）。
          at:     {名字: (lng, lat)} 手动指定终点，覆盖自动算的落点。
          elbow / stub / gap / pad / sep 单位是磅：拐点离地图外缘、起点到拐点（列线外那段横线）、
          文字离起点、上下两行文字的空隙、名字和数值之间。
          debug:  在图上标出每条引线起点、拐点、终点的经纬度，手动改参数包时对照用。

        alias:  {名字: 显示名}，这一次的别名，盖过 geo.alias（名字太长时用）。
        inside: False（默认）全部引到外面；"auto" 放得下的写在区内（同 text()），放不下的才引到外面。
                "auto" 时区内那部分在 co.inside（RegionTexts），改样式用 co.inside.texts / co.inside.nums。
        数据是空的、或名字都不在底图里：什么都不画（名字写错会警告），不报错。"""
        items, each = self._label_data(texts, each, hot, alias)
        skip, rt = None, None
        if inside == "auto":
            rt = self._text_layer(ax, items, each=each, hot=hot, fmt=fmt, nameprops=nameprops,
                                  valueprops=valueprops, at=at, fs=fs, overflow="hide")
            skip = lambda n, renderer: rt.fits(n, renderer)
        elif inside is not False:
            raise ValueError(f"inside 只能是 False 或 'auto'（全部写在区内请用 geo.text），拿到 {inside!r}")
        common = dict(hot=hot, fmt=fmt, each=each, sep=sep, fs=fs, debug=debug, skip=skip,
                      props=dict(name=nameprops, value=valueprops, line=lineprops, dot=dotprops))
        if layout is not None:
            lay = _as_layout(layout)
            if missing := [n for n in items if n not in lay]:
                warnings.warn(f"参数包里没有这些名字，没画标注：{missing}。用 layout.edit(名字, side=..., elbow=..., "
                              f"end=...) 补上，或者自动排一版再 freeze()", stacklevel=2)
            items = {n: v for n, v in items.items() if n in lay}
            if off := [n for n in items if not _inside(self._rings[n], np.asarray([lay[n].end]))[0]]:
                warnings.warn(f"参数包里这些终点不在对应的区域里：{off}。如果是别的底图调的参数包，"
                              f"换了底图就要重新自动排一版再 freeze()", stacklevel=2)
            co = Callouts(ax, items, layout=lay, **common)
        else:
            if spread not in ("fit", "span"):
                raise ValueError(f"spread 只能是 'span' 或 'fit'，拿到 {spread!r}")
            if angle is not None and not 0 < angle <= 90:
                raise ValueError(f"angle 是斜线和水平方向的夹角，要在 (0, 90] 度之间，拿到 {angle!r}")
            at = {str(k): np.asarray(v, float) for k, v in (at or {}).items()}
            point = lambda n: at[n] if n in at else self.anchor(n)
            anchors = {n: point(n) for n in items}
            sides = {n: "left" if anchors[n][0] < self.split_lng(split, at) else "right" for n in items}
            if isinstance(side, str) and side != "auto":
                sides = dict.fromkeys(items, side)
            elif isinstance(side, Mapping):
                sides.update({str(k): v for k, v in side.items() if str(k) in items})
            if bad := {v for v in sides.values() if v not in ("left", "right")}:
                raise ValueError(f"side 只能是 'auto'、'left'、'right' 或 {{名字: 'left'/'right'}}，拿到 {bad}")
            co = Callouts(ax, items, auto=_Auto(anchors, sides, (self.bounds[0], self.bounds[2]), spread,
                                                elbow, pad, angle, uncross), stub=stub, gap=gap, **common)
        co.inside = rt
        ax.add_artist(co)
        return co

    def split_lng(self, split="center", at: Mapping | None = None) -> float:
        """分左右列的那条经度线（见 label 的 split）。只由底图决定，所以同一个区每张图都在同一侧。"""
        if split == "center":
            return (self.bounds[0] + self.bounds[2]) / 2
        if split == "balance":
            at = at or {}
            return float(np.median([at[n][0] if n in at else self.anchor(n)[0] for n in self._rings]))
        if isinstance(split, (int, float)) and not isinstance(split, bool):
            return float(split)
        raise ValueError(f"split 只能是 'center'、'balance' 或经度数值，拿到 {split!r}")

    def plot(self, values=None, texts=None, *, ax=None, colors=None, norm: str | Normalize = "linear", cmap=None,
             dots: Iterable[tuple] = (), land=True, borders: Mapping | bool = True, outline: Mapping | bool = True,
             scale: Mapping | bool = True, north: Mapping | bool = True, km: float | None = None,
             margin: float = 0.02, height: float = 6.0, **label_kw):
        """常用组合一步画完 = base()（底图）+ fill（填色）+ dots（叠点）+ label（标注）。返回 ax，之后照常往上加东西。
        values / colors 都不给就只有底图。缺数据的区不填色，露出底图的底色（colors.land）。
        texts: 给 label 的数据；texts=True 用 values 写"名字 数值"，没有 values 就只写名字（标出全部区，别名照用）。
        colors: 交给 fill，按区直接给颜色（这时 values 只用来写标注，不填色）。
        land / borders / outline / scale / north / margin: 见 base()。dots: [(DataFrame 或 N×2 数组, 颜色), ...]。
        其余关键字（hot、inside、layout、spread、angle、nameprops、each…）原样交给 label()。
        需要色条或同色阶时，自己调 fill 拿返回值。"""
        if texts is True:
            texts = values if values is not None else dict.fromkeys(self._rings, np.nan)   # 只写名字（别名照用）
        has_texts = texts is not None and len(texts) > 0
        ax = self.base(ax, land=land, borders=borders, outline=outline, scale=scale, north=north, km=km,
                       margin=margin, height=height, room=has_texts)
        if colors is not None:
            self.fill(ax, colors=colors)
        elif values is not None:
            self.fill(ax, values, norm=norm, cmap=cmap)
        for data, color in dots:
            self.points(ax, data, color=color)
        if has_texts:
            self.label(ax, texts, **label_kw)
        return ax


def _label_items(texts, alias: Mapping[str, str] | None = None) -> dict[str, tuple[str, float | None]]:
    """label 的数据 → {名字: (名字那段文字, 数值或 None)}。给的是数时名字那段用别名。"""
    alias, out = alias or {}, {}
    for k, v in dict(texts).items():
        n = str(k)
        if isinstance(v, str):
            out[n] = (v, None)
        elif isinstance(v, tuple) and len(v) == 2:
            out[n] = (str(v[0]), _number(v[1], n))
        else:
            out[n] = (alias.get(n, n), _number(v, n))
    return out


def _number(v, name):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.number)):
        raise TypeError(f"{name!r} 的值应是数、字符串或 (文字, 数)，拿到 {type(v).__name__}")
    v = v.item() if isinstance(v, np.number) else v
    return None if v != v else v                                       # NaN：只写名字


# ── 旧接口 ────────────────────────────────────────────────────────────────
class DistrictMap:
    """旧接口，保留给已经写好的 notebook：dm.figure(cols, n_sub) 建图 + dm.draw(ax, ...) 画图，内部全部转给 Regions。
    新代码请直接用 Regions + plt.subplots。elbow / stub / txt_gap 以前单位是"度"，现在标注按磅排版，
    这三个参数仍然接受，但不再起作用。"""

    map_h_in, label_w_in, head_in = 7.0, 1.30, 0.50
    elbow, stub, txt_gap = 0.07, 0.14, 0.02
    _SIZES = ("map_h_in", "label_w_in", "head_in", "elbow", "stub", "txt_gap")

    def __init__(self, districts: Mapping[str, Iterable], lat0: float = LAT0, **sizes: float):
        for k, v in sizes.items():
            if k not in self._SIZES:
                raise TypeError(f"未知参数：{k}")
            setattr(self, k, v)
        self.regions = Regions(districts, lat0=lat0)
        self.lat0 = lat0
        self.polys = self.regions._rings
        self.bx0, self.by0, self.bx1, self.by1 = self.regions.bounds
        self.ylim = (self.by0 - 0.03, self.by1 + 0.03)
        # 地图宽 + 两侧标注（拐点 + 短横线 + 间隙 = 46 磅 ≈ 0.65 英寸，再加文字宽）
        self.left_w_in = self.map_h_in * self.regions.aspect + 2 * (self.label_w_in + 0.7)

    @property
    def anchors(self) -> dict[str, np.ndarray]:
        return {n: self.regions.anchor(n) for n in self.regions.names}

    def figure(self, cols: Iterable[float] = (), n_sub: int = 2):
        """建图：左边是地图，右边按 cols（英寸）留出列。返回 (fig, 地图轴, gs)；gs 是 2 行 × (1+len(cols)) 列。"""
        cols = list(cols)
        head, foot = margins_in(n_sub)                                  # 与 finish() 同一处留白数字
        fig = plt.figure(figsize=(0.3 + self.left_w_in + sum(cols) + 0.2, self.map_h_in + head + foot + 0.25))
        gs = fig.add_gridspec(2, 1 + len(cols), hspace=0, wspace=0,
                              height_ratios=[self.head_in, self.map_h_in - self.head_in],
                              width_ratios=[self.left_w_in, *cols])
        return fig, fig.add_subplot(gs[:, 0]), gs

    def clip(self, df: pd.DataFrame, pad: float = 0.15, lng: str = "lng", lat: str = "lat") -> pd.DataFrame:
        """只留地图视窗内的点：边界外扩 pad 度，上下用地图上下沿（旧语义，单位是度）。"""
        return df[df[lng].between(self.bx0 - pad, self.bx1 + pad) & df[lat].between(*self.ylim)]

    def draw(self, ax, values=None, texts=None, *, hot: Iterable[str] = (), norm="linear", cmap=None,
             dots: Iterable[tuple] = (), km: float = 20, fs: float = 9, layout=None, spread: str = "span",
             debug: bool = False, **label_kw):
        """参数同旧版，另可传 layout（参数包）、spread、debug 以及 label() 的其他关键字（样式、angle…）；
        返回 (cmap, norm)。引线标注对象放在 self.callouts，自动排版满意了用 dm.callouts.freeze() 定成参数包。"""
        geo = self.regions
        geo.frame(ax)
        pc = geo.fill(ax, values, norm=norm, cmap=cmap)
        geo.borders(ax)
        geo.outline(ax)
        for data, color in dots:
            geo.points(ax, data, color=color)
        self.callouts = (geo.label(ax, texts, layout=layout, hot=hot, spread=spread, fs=fs, debug=debug, **label_kw)
                         if texts is not None and len(texts) else None)
        scale_bar(ax, km, self.lat0)
        north_arrow(ax)
        return pc.cmap, pc.norm


if __name__ == '__main__':
    pass
