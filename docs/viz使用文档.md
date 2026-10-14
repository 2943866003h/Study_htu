# viz 使用文档

版本：maps v2.5.1 · callouts v1.3.0 · mapcolors v1.1.0 · theme 保持你现有的 v1.3.0 不动
日期：2026-10-15

---

## 1. 交付内容与安装

地图分两层画：先画**底图**（`geo.base()`，只由边界决定，不需要任何数据），再往上叠**数据层**（填色、散点、区内标注、外部引线），每层只画自己有数据的区，缺哪个区就不画哪个。地图颜色和 `theme.py` 无关，由 `mapcolors.py` 管。你项目里现有的 `theme.py`、`__init__.py`、`styles/` 一个字节都没改。

### 压缩包里有什么

| 路径 | 放到项目哪里 | 说明 |
| --- | --- | --- |
| `viz/` | `src/signal_insight/viz/` 整个替换 | theme.py、__init__.py、styles/ 是你原来的；maps.py、callouts.py 更新；mapcolors.py 新增 |
| `tests/test_viz_maps.py` | `tests/` | 地图测试，44 项 |
| `tests/fake_geo.py` | `tests/` | 模拟边界：区县版 `make()`、商圈版 `make_areas()` |
| `tests/demo_base_data.py` | 随便放 | 底图与数据层示例，生成第 2 节第一张图 |
| `tests/demo_center_alias.py` | 随便放 | 居中与别名示例，生成第 2 节第二张图 |
| `tests/demo_style_recipe.py` | 随便放 | 配色配方示例，生成第 4.4 节的图 |
| `tests/demo_areas.py` | 随便放 | 商圈示例，生成第 2 节第二张图 |
| `docs/` | 随便放 | 本文档和配图 |

### viz 包的结构

| 文件 | 管什么 | 常用入口 |
| --- | --- | --- |
| `theme.py`（未改） | 主题切换、通用图表的语义色常量、标题区和来源行 | `apply_theme`、`use_theme`、`finish`、`MAIN` 等常量 |
| `mapcolors.py`（新） | 地图自己的默认颜色 | `viz.maps.colors` |
| `maps.py` | 地图几何与分层绘制 | `Regions`、`scale_bar`、`north_arrow` |
| `callouts.py` | 外部引线标注、区内标注、参数包 | `Callouts`、`RegionTexts`、`LabelLayout` |
| `styles/*.mplstyle`（未改） | 主题外观文件 | `default`、`business`、`lively`、`academic` |
| `layouts/*.json` | 存好的引线参数包（第一次保存时自动建） | `geo.label(..., layout="名字")` |

依赖关系：`maps → callouts → mapcolors`；`maps` 只从 `theme` 取 `margins_in` 一个函数（给旧接口 `DistrictMap` 算留白），不取任何颜色。

### 运行前提

- Python 3.9+，matplotlib 3.6+，numpy、pandas；geopandas 可选，只有 `Regions.from_geodataframe` 用到。
- `viz` 依赖 `signal_insight/config.py` 的 `THEME`（默认主题名）和 `IMAGE_DIR`（`finish` 存图根目录），和以前一样。
- 字体沿用 `base.mplstyle`：TeX Gyre Termes、Noto Serif CJK SC。没装中文字体时汉字是方框。
- `styles/`、`layouts/` 是数据文件，打包时要声明为 package data。

---

## 2. 快速上手：先底图，再数据

底图只由边界决定，任何数据都不需要；数据层往上叠，有几个区的数据就画几个区。

```python
import matplotlib.pyplot as plt
from signal_insight import viz

viz.apply_theme("default")                       # 主题只管外观
geo = viz.maps.Regions(districts)                # {'和平区': [array([[123.429, 41.817], ...])], ...}

# 1) 底图：浅灰底色 + 白色内边界 + 深色外边界 + 比例尺 + 指北针
fig, ax = plt.subplots(figsize=(9, 6.4), layout="constrained")
geo.base(ax)

# 2) 数据层：缺和平区也没关系，和平区不填色、露出底色
visits = {"沈河区": 5489, "皇姑区": 765, "大东区": 1599}
geo.fill(ax, visits)                             # 填色
geo.label(ax, visits, inside="auto", hot=["沈河区"])   # 放得下写区内，放不下引到外面

viz.finish(fig, "各区到访人数", "2026 年 9 月", "来源：信令数据", "D3_到访.png")
```

![A 只有底图；B 底图 + 部分数据；C 自定义底图配色 + 只写区内](img/示例_底图与数据层.png)

A：不给任何数据，只写区名。B：只有 8 个区有数据，其余露出灰色底色，和"数值低"的白色分得开。C：底色、内边界、外边界都换了颜色，标注只写在区内，放不下的小区不写。完整代码见 `tests/demo_base_data.py`。

一步画完也可以：`geo.plot(values, texts=True, ...)` 就是 `base` + `fill` + `label`。`geo.plot(texts=True)` 不给数据时，只写全部区名。

### 地图默认居中；名字太长用别名

自己建的图比地图宽时（比如 `plt.subplots(figsize=(9, 6.4))`），地图完整、居中，两侧留白；之后加标注就排在留白里，地图不用挪。notebook 显示和 `finish` 存图都会裁白边，地图仍在正中。

```python
geo = viz.maps.Regions(districts, alias={"棋盘山风景区": "棋盘山", "沈阳世博园": "世博园"})
fig, ax = plt.subplots(figsize=(9, 6.4))
geo.plot(ax=ax)                                          # A 只有底图：居中
geo.plot(visits, texts=True, ax=ax, hot=["和平区"])       # B 加标注：排在两侧留白里
```

![A 只有底图；B 加标注；C 别名；D 窄图 + inside="auto"](img/示例_居中与别名.png)

别名只改标注里显示的名字；数据、`hot`、`each`、参数包仍用原名（图 C 里 `hot=["沈北新区"]` 照样生效）。详见第 3 节。

### 商圈这类零散区域

商圈彼此不相邻，常贴着外框四角，比例尺和指北针容易压上去：调大留白、挪开比例尺。

```python
ax = geo.base(ax, margin=0.08, scale=dict(x=0.55))
geo.fill(ax, colors=viz.AREA_COLOR, alpha=0.85)          # 每个商圈一个固定颜色
geo.points(ax, geo.clip(sites), by="district", colors={"铁西区": "#D64545"}, color="#C4CAD3", s=4, zorder=0.5)
geo.label(ax, visits, fmt="{:,.0f} 人")
```

![左：按数值填色；右：商圈固定颜色、站点按区着色](img/示例_商圈地图.png)

---

## 3. 数据格式

### 边界

| 写法 | 说明 |
| --- | --- |
| `{名字: 数组}` | 一个区一个环 |
| `{名字: [数组, 数组, ...]}` | 一个区多个环：多块飞地，或外环 + 洞 |
| `Regions.from_geodataframe(gdf, name="列名")` | GeoDataFrame，Polygon / MultiPolygon，内环自动带上 |

- 环首尾点相同或不同都可以，连续重复点自动去掉，少于 3 个点的环丢掉。
- 洞不用标：被奇数个环包住的环自动当作洞。被包住的飞地（如铁西区在于洪区里）要作为外面那个区的内环一起给，这样外面的区才会挖空。
- 商圈这类彼此不相邻的区域没问题：每个商圈整圈都算外边界，`borders`（内边界）什么也不画。
- 坐标是经纬度。长宽比按边界中心纬度自动校正，街道、城市、省都能用。

### 别名：名字太长时

```python
geo = viz.maps.Regions(districts, alias={"棋盘山风景区": "棋盘山"})   # 底图级：所有图都用
geo.alias["沈阳世博园"] = "世博园"                                  # 事后加、改
geo.label(ax, values, alias={"铁西区": "铁西(飞地)"})               # 只这一次，盖过 geo.alias
geo.text(ax, values, alias={...})                                   # 区内标注同样可以
```

- 只在数据给的是数（或 NaN、或 `plot(texts=True)` 只写名字）时生效。数据里自己写了字符串或 `(文字, 数)`，按你写的显示。
- 数据、`hot`、`each`、参数包、`at`、`side` 里一律用原名；别名写了底图没有的名字会警告。

### 站点（散点）

`geo.points(ax, df)` 默认读 `lng`、`lat` 两列，列名不同用 `lng=`、`lat=` 指定，也可以直接给 N×2 数组。

```python
geo.points(ax, sites)                                       # 一个颜色，默认 colors.ink
geo.points(ax, sites, color="#9CA3AF", s=3)                 # 自己定颜色、大小
geo.points(ax, sites, by="district",                        # 按某一列分组着色
           colors={"铁西区": "#D64545", "沈河区": "#1D6FA5"},
           color="#C4CAD3")                                 # colors 里没有的组用 color
geo.points(ax, sites, s=sites["nn_m"] / 40)                 # 点大小也可以给一列
geo.clip(sites, margin=0.1)                                 # 只留外框四周外扩 10% 内的点
```

`colors` 里写了、数据里没有的组会警告，方便发现区名写错。其余关键字（`alpha`、`zorder`、`marker`…）原样交给 `ax.scatter`。

---

## 4. 颜色

### 4.1 地图颜色：独立于主题

地图的每个默认颜色都只是"没传参数时用什么"。任何一次调用传了 `color=`、`lineprops=` 之类，以调用为准。

| 名字 | 用在哪 | 默认 |
| --- | --- | --- |
| `ink` | 标注名字和数值、外边界、落点、散点、比例尺、指北针 | `#1F2937` |
| `line` | 引线 | `#6B7280` |
| `hot` | `hot=` 强调的名字和数值、`edges` 整圈边界 | `#1D6FA5` |
| `land` | 底图底色；没数据的区就是这个颜色 | `#EEF0F3` |
| `low` | 填色色阶浅端（最小值） | `#FFFFFF` |
| `high` | 填色色阶深端（最大值） | `#8E99A6` |
| `border` | 内边界（区与区之间） | `#FFFFFF` |
| `nan` | 数据层里没数值、没给颜色的区 | `none`（不填，露出底图的 land） |
| `debug` | `debug=True` 时写的坐标 | `#B7791F` |

```python
viz.maps.colors                                    # 查看当前设置；notebook 里显示色块
viz.maps.colors.set(hot="#D64545", high="#1D6FA5") # 整体改，之后画的地图都用它
with viz.maps.colors.use(ink="#000000"):           # 临时改，出了 with 恢复
    geo.plot(values, texts=True)
viz.maps.colors.reset()                            # 全部恢复默认
```

- 颜色在画的那一刻取定：先 `set`，再画。
- 名字写错报 `TypeError` 并列出可用名字；值不是颜色报 `ValueError`。
- `viz.maps.colors.ink = ...` 这种直接赋值会报错，统一用 `set`。
- 想和某个主题保持一致，自己填进来即可：`viz.maps.colors.set(hot=viz.MAIN, ink=viz.INK)`。

### 4.2 主题：只管通用图表外观（未改动）

```python
viz.apply_theme("business")            # 全局切换，返回生效字体列表；不给参数用 config.THEME
viz.available_themes()                 # ['academic', 'business', 'default', 'lively']
with viz.use_theme("academic"):        # 临时切换
    ...
```

`theme.py` 里的 `MAIN`、`GRAY`、`RED`、`INK`、`AREA_COLOR`、`SEG_COLOR` 等是固定常量，不随主题变，可以 `from signal_insight.viz import MAIN, RED` 直接用，也可以拿来给地图上色（如 `colors=viz.AREA_COLOR`）。换主题不会改变地图颜色，换地图颜色也不会影响其他图表。

### 4.3 finish：标题区、来源行、存图

```python
viz.finish(fig, title, subtitle, source, path=None, *, accent=True)
```

左上角写标题和副标题（副标题可多行，用 `\n`），左下角写来源。给了 `path` 就以 300 dpi 存图，相对路径存进 `config.IMAGE_DIR`，返回完整路径。`accent=False` 去掉标题上方的主色短条。

### 4.4 配色配方：D3_02 / D3_03 的样子

三条规则：**灰阶打底，一种颜色强调一件事，点比区小。** 区县填色只用白到灰，强调色（蓝）只留给要读者注意的那一类；散点要比区界和填色"轻"，不然盖住底图。

![左：常见的坑；右：D3_02 的配方](img/示例_配色配方.png)

左图的三个坑都来自同一段常见写法：

| 坑 | 原因 | 改法 |
| --- | --- | --- |
| 比例尺两个、自定的红色内边界被盖住 | `geo.base(ax, ...)` 之后又 `geo.plot(..., ax=ax)`，plot 里又画了一遍底图 | 二选一：`base` + 数据层，或者只用 `plot`。现在重复画会警告 |
| 整张图一片深灰 | 填色的值全是 1，色阶两端相同，全部落在最深 | 填真实数值；不需要填色就别给 values |
| 城区一团蓝、看不清区界 | 点 `s=3` 太大，市内点用了强调色、`zorder` 压在区界上 | 市内点用墨色、`s≈0.3`；强调色给要强调的那类（市外） |

**D3_02（站点与区县）的配方：**

```python
from signal_insight.viz import MAIN, INK

inside  = sites[sites["district"] != "市外"]          # 按你表里"市外"的写法改
outside = sites[sites["district"] == "市外"]
counts  = inside.groupby("district").size()

fig, ax = plt.subplots(figsize=(9, 6.4), layout="constrained")
geo.base(ax)                                          # 默认就是：浅灰底、白内边界、深色外边界
geo.fill(ax, counts)                                  # 白 → 灰，越多越深（数值差很多倍时加 norm="log"）
geo.points(ax, geo.clip(outside), color=MAIN, s=0.5)  # 市外：强调色，小点
geo.points(ax, inside, color=INK, s=0.3)              # 市内：墨色，更小
geo.label(ax, counts)                                 # 名字 + 数值，同一种墨色
```

**D3_03（站点间距）的配方：**

```python
med = inside.groupby("district")["nn_m"].median()
far = med[med >= 900].index.tolist()                  # 要强调的那几个

fig, ax = plt.subplots(figsize=(9, 6.4), layout="constrained")
geo.base(ax)
geo.fill(ax, med, norm="log")                         # 间距差 16 倍：对数色阶
geo.label(ax, med, fmt="{:,.0f} 米", hot=far)         # hot：名字和数值换成强调色加粗
```

想整体换色调，改地图默认色即可，配方本身不用动：`viz.maps.colors.set(high="#1D6FA5", hot="#D64545")`。

---

## 5. 底图与数据层

地图从下到上分层，顺序由 zorder 固定，和调用先后无关：先画底图、后加数据，填色也会自动落在区界下面。

| 层 | 调用 | 属于 | zorder |
| --- | --- | --- | --- |
| 底色 | `base(land=...)` | 底图 | 0.8 |
| 填色 | `fill(...)` | 数据层 | 1.0 |
| 内边界 / 外边界 / 强调边界 | `borders` / `outline` / `edges` | 底图（edges 常用于强调） | 1.5 / 1.6 / 1.7 |
| 散点 | `points(...)` | 数据层 | 3 |
| 外部引线标注 | `label(...)` | 数据层 | 5 |
| 区内标注 | `text(...)` | 数据层 | 6（白边压住穿过的引线） |

### base：底图

```python
ax = geo.base(ax=None, *, land=True, borders=True, outline=True,
              scale=True, north=True, km=None, margin=0.02, height=6.0, room=True)
```

不需要任何数据，返回 ax。`ax` 不给就新建一张图，宽度按地图长宽比算（`room=True` 时两侧多留引线标注的位置）。给了 ax，地图在 ax 里居中（见下面 `frame` 的 `fill`）。每一层都可以 `True`（默认样式）、`dict`（自定样式）、`False`（不画）。

**区界配色怎么调**，三种方式，按需要选：

```python
# 1) 画底图时直接给：只影响这一张
geo.base(ax, land="#FBF6EE",
         borders=dict(color="#C9B79C", lw=0.6, ls=(0, (3, 2))),   # 内边界
         outline=dict(color="#7A5C3E", lw=1.6))                  # 外边界

# 2) 改地图默认色：之后所有地图都用它
viz.maps.colors.set(land="#F5F5F5", border="#FFFFFF", ink="#333333")   # ink 也是外边界色

# 3) 画完再改：返回值和 ax.collections 都是 matplotlib 对象
lc = geo.borders(ax); lc.set_color("#999999")
```

**为什么以前没数据时看不到内边界**：内边界默认是白线，以前底下没有底色，白线画在白底上等于没画；有数据时填了灰色，白线才显出来。现在底图自带浅灰底色，白线一直看得见。不想要底色，用 `base(land=False, borders=dict(color="#C4CAD3"))` 换成灰线即可。

### frame：把 ax 变成地图

```python
geo.frame(ax, margin=0.02, bare=True, fill=True)
```

地图框 = 外框四周留 `margin`（按长边比例），长宽比按纬度校正，`bare=True` 去刻度和边框。

- `fill=True`（默认）：ax 占满给它的位置，地图完整、居中，多出的宽度（或高度）两侧留白，引线标注排在留白里。每次排版按当时 ax 的大小重算，缩放、换版面都对。裁白边存图时地图也在正中。
- `fill=False`：ax 缩到地图本身大小（旧行为）。裁白边时，左边有标题、右边没有东西，地图会被挤到右边。
- 想放大某一块：`frame` 之后自己 `ax.set_xlim / set_ylim`，以你设的为新的地图框。

### fill（数据层）：按数值，或按区给颜色

```python
pc = geo.fill(ax, values, norm="log")                       # 按数值，走色阶
pc = geo.fill(ax, colors={"西塔": "#1D6FA5", "中街商圈": "#3B8C66"})   # 按区给颜色
pc = geo.fill(ax, colors="#EEEEEE")                         # 全部一个颜色
```

| 参数 | 作用 | 默认 |
| --- | --- | --- |
| `values` | `{名字: 数}` 或 Series；名字不在边界里会警告 | 无 |
| `colors` | `{名字: 颜色}` 或单个颜色；和 `values` 二选一 | 无 |
| `cmap` | 色阶（仅 values） | `colors.low → colors.high` |
| `norm` | `"linear"`、`"log"` 或 Normalize（仅 values） | `"linear"` |
| `nan_color` | 没数值 / 没给颜色的区 | `colors.nan`（露出底色） |
| `edgecolor`、`lw` | 填色块自带的边；默认与填色同色，防白缝 | `"face"`、0.3 |
| 其余 | 交给 PatchCollection，如 `alpha=0.85` | — |

数据为空也不报错，什么都不填。按数值填色时返回的 PatchCollection 本身就能出色条：`fig.colorbar(pc)`；`pc.cmap`、`pc.norm` 可以给旁边的图共用。

### borders / outline / edges（底图里已经画了，单独调用用于自定义或强调）

```python
geo.borders(ax)                                         # 内边界，默认 colors.border（白线）、0.9 磅
geo.borders(ax, color="#C4CAD3", lw=0.5, ls=(0, (2, 2)))  # 灰色虚线
geo.outline(ax, color="#1F2937", lw=1.4)                # 外边界，默认 colors.ink、1.0 磅
geo.edges(ax, ["和平区", "沈河区"], color="#D64545", lw=1.2)   # 强调几个区，默认 colors.hot
```

- `borders`：相邻两区的公共边（含飞地和包住它的区之间那圈），每条只画一次，虚线不会叠花。
- `outline`：所有区拼起来的最外圈；商圈这类零散区域就是每个商圈各一圈。
- `edges`：指定区的整圈边界（连洞边一起），压在内外边界上面。

### 比例尺和指北针

```python
viz.maps.scale_bar(ax, km=None, x=0.04, y=0.04)   # 左下角；km 不给自动取约 1/4 视窗宽的整数
viz.maps.north_arrow(ax, x=0.95, y=0.95)          # 右上角
```

`x`、`y` 是在**地图框**里的比例位置（0~1），不是整个 ax：地图居中、两侧留白时，比例尺和指北针仍贴着地图。区域贴着地图框四角时（商圈常见），挪到空的地方，如 `scale_bar(ax, x=0.55)`。引线标注会自动避开这两个附件；你自己加的图例想让标注避开，`artist.set_gid(viz.maps.FURNITURE)`。

### plot：一步画完

```python
ax = geo.plot(values=None, texts=None, *, ax=None, colors=None, norm="linear", cmap=None,
              dots=(), land=True, borders=True, outline=True, scale=True, north=True, km=None,
              margin=0.02, height=6.0, **label_kw)
```

等于 `base()` + `fill` + `points` + `label`。`values`、`colors` 都不给就只有底图；`texts=True` 用 values 写"名字 数值"，没有 values 就只写全部区名。其余关键字（`hot`、`inside`、`layout`、`angle`、`nameprops`、`each`…）交给 `label`。

---

## 6. 标注位置：label 怎么排

`geo.label(ax, values)` 在地图左右两侧各排一列文字。每条引线从文字出发，横走到拐点，再斜线扎进区内落点（区内离边界最远的点，`geo.anchor(名字)`）。

### 数据怎么给

```python
geo.label(ax, {"西塔": 3120})                   # 数 → "名字 数值"，两段可分开设样式
geo.label(ax, {"西塔": "西塔 3,120 人"})        # 字符串 → 整段照写
geo.label(ax, {"西塔": ("西塔商圈", 3120)})      # (文字, 数) → 自定名字那段，再跟数值
geo.label(ax, values, fmt="{:.1%}")            # 数值格式：格式串或函数，默认千分位取整
```

NaN 只写名字；名字不在边界里会警告，不画；数据为空就什么都不画，不报错。

### inside：放得下写区内，放不下引到外面

```python
co = geo.label(ax, values, inside="auto")
```

每次绘制时量一下文字能不能整块放进自己的区：放得下的写在区内（同第 7 节的 `text`），放不下的才排进左右两列。郊县这类大区写在区内，城区小区引到外面，两列短很多。区内那部分在 `co.inside`，改样式用 `co.inside.texts[名字]`；`co.freeze()` 的参数包里只有引到外面的那些。默认 `inside=False`，全部引到外面。

### 自动排版的六步

1. 分侧：按 `split` 定一条经度线，落点在线西进左列、线东进右列。只看底图，不看这次标了哪几个区，同一个区每张图都在同一侧。
2. 排序：每列按落点纬度从北到南。
3. 行位：`spread="span"`（默认）两列都铺满落点的上下范围再等距；`"fit"` 行位贴着落点高度，引线更平。
4. 拐点：`angle=None`（默认）同一列拐点对齐在一条竖线上；给度数则所有斜线同一角度、互相平行。
5. 去交叉：`uncross=True`（默认）出现交叉就对调这两条。
6. 避让：让开指北针、比例尺等地图附件。

每次绘制都按当时像素重排，缩放、`finish` 调整版面、存 300 dpi 都不会错位。

### split：分左右的那条线

| 取值 | 分界线 | 适用 |
| --- | --- | --- |
| `"center"`（默认） | 外框左右两沿的正中 | 区分布比较均匀 |
| `"balance"` | 所有区落点经度的中位数 | 区域偏在一边，想两列条数接近 |
| 数值，如 `123.3` | 直接给经度 | 精确控制 |

```python
geo.split_lng("center")                         # 查看分界线经度
geo.label(ax, values, side={"沈阳北站": "right"}) # 个别区单独指定；side="left" 全放左列
```

![左 split="center"、右 split="balance"（城区偏东的模拟底图）](img/分侧_center_vs_balance.png)

按模拟的商圈位置：城区四个商圈在西侧，世博园和棋盘山在东侧，`center` 分成左 4 右 2（见第 2 节的图）。真实沈阳区县很可能是左 2 右 11，这时 `balance` 更均衡。建议用真实边界各出一张再定。

### angle：拐点样式

| 取值 | 效果 |
| --- | --- |
| `None`（默认） | 同一列拐点对齐在竖线上，再斜线进区；最干净 |
| (0, 90) 内的度数，如 `60` | 所有斜线同一角度、互相平行，拐点沿横线往地图内收；更规整，横线会伸进地图 |
| `90` | 先竖后横的直角引线 |

![A 默认、B angle=60、C angle=90](img/引线角度对比.png)

### 其他位置参数

| 参数 | 含义 | 默认 |
| --- | --- | --- |
| `at` | `{名字: (lng, lat)}` 手动指定终点 | 无 |
| `elbow` | 拐点离地图外缘（磅） | 14 |
| `stub` | 起点到拐点的横线（磅） | 28 |
| `gap` | 文字离起点（磅） | 4 |
| `pad` | 上下两行文字的空隙（磅） | 3 |
| `sep` | 名字和数值之间（磅） | 3 |
| `fs` | 字号 | 9 |
| `debug` | 图上写出拐点、终点经纬度 | False |

---

## 7. 区内标注：text

名字和数值直接写在每个区的落点上（区内离边界最远的点，不贴边、不落进洞）。数据写法和样式参数与 `label` 完全一样。

```python
rt = geo.text(ax, values, hot=["沈河区"], fmt="{:,.0f}",
              nameprops=dict(size=8), valueprops=dict(weight="bold"),
              each={"康平县": dict(value=False)},
              stack=True,          # True 名字在上、数值在下；False 一行"名字 数值"
              halo=True,           # 文字白边，压在深色填色上也看得清；也可以给颜色或 False
              overflow="show")     # 放不下时："show" 照画并警告一次；"hide" 不画
rt.overflow                        # 最近一次绘制时放不下的区名
rt.texts["沈河区"], rt.nums["沈河区"]   # matplotlib Text，可以接着改
```

| 参数 | 含义 | 默认 |
| --- | --- | --- |
| `stack` | 名字、数值上下两行；False 写成一行 | True |
| `sep` | 上下两行的间距（磅） | 1 |
| `halo` | 文字白边：True / 颜色 / False | True |
| `overflow` | 放不下时 `"show"` 照画并警告、`"hide"` 不画 | `"show"` |
| `at` | `{名字: (lng, lat)}` 手动指定位置 | 无 |

"放得下"按当前版面判断，图变小了原本放得下的可能放不下。想自动处理，用 `geo.label(ax, values, inside="auto")`。

---

## 8. 标注样式：四个部分逐个设置

每条标注有四个部分：名字 `name`、数值 `value`、引线 `line`、落点 `dot`。每部分可整体设样式、用 `False` 隐藏、用 `each` 对单个区覆盖。优先级：默认 < 整体 props < `hot` < `each`。

![左：默认；右：名字与数值分色、虚线引线、去掉落点、两区红色强调、内外边界分开设计](img/样式对比.png)

| 部分 | 参数 | 接受的样式 | 默认 |
| --- | --- | --- | --- |
| 名字 | `nameprops` | Text：`color`、`size`、`weight`、`family`、`alpha`… | 9 号，`colors.ink` |
| 数值 | `valueprops` | 同上 | 9 号，`colors.ink` |
| 引线 | `lineprops` | Line2D：`color`、`lw`、`ls`、`alpha`… | `colors.line`，0.45 磅实线 |
| 落点 | `dotprops` | Line2D 标记：`marker`、`ms`、`color`、`mec`、`mew` | 圆点 2.2，`colors.ink`，白边 |

```python
geo.label(ax, values, fmt="{:,.0f}",
    nameprops=dict(color="#6B7280", size=8.5),
    valueprops=dict(weight="bold"),
    lineprops=dict(lw=0.6, ls=(0, (3, 2))),
    dotprops=False,                                 # False = 这部分全部不画
    hot=["中街商圈"],                                # 名字和数值换成 colors.hot 加粗
    each={
        "太原街商圈": dict(value=dict(color="#D64545"), line=dict(color="#D64545", lw=1)),
        "沈阳北站": dict(value=False),               # 只写名字
        "西塔": dict(line=False, dot=False),         # 只留文字
        "棋盘山风景区": False,                       # 整条不画
    })
```

- 部分名写错直接报错并指出哪个区；区名写错会警告。
- 画完还能改：`co = geo.label(...)`，然后 `co.texts[名字]`、`co.nums[名字]`、`co.lines[名字]`、`co.dots[名字]` 都是 matplotlib 对象。位置相关属性由排版控制，改了会被覆盖。
- 一个区整体突出，通常三处一起改：`geo.edges(ax, [名字], color=...)`、`each` 里的 name/value/line、必要时 `fill(colors=...)`。

样式不存进参数包：位置是底图的属性，样式是这张图的属性。

---

## 9. 参数包与手动微调

自动排版满意后，用 `co.freeze()` 把位置定成参数包（`LabelLayout`），手动改几条，存成 JSON；以后同一张底图的所有图都套这个包，只换数值和样式。

### 流程

1. 自动排一版并打开 debug：`co = geo.label(ax, values, debug=True)`。
2. 先把图画完：`viz.finish(...)` 存图，或在 notebook 里显示一次。版面定了坐标才是最终的。
3. 定下来：`lay = co.freeze()`。
4. 微调：`swap` / `move` / `edit`，可以连着写。
5. 保存：`lay.save("src/signal_insight/viz/layouts/shenyang_areas.json")`。
6. 以后每张图：`geo.label(ax, values, layout="shenyang_areas")`。

```python
co = geo.label(ax, visits, debug=True)
viz.finish(fig, title, sub, src, "draft.png")
lay = co.freeze()
print(lay)                                    # 每条一行：侧、拐点、终点
lay.swap("西塔", "中街商圈").move("沈阳北站", dy=-0.005).edit("棋盘山风景区", stub=40)
lay.save("src/signal_insight/viz/layouts/shenyang_areas.json")
```

### 修改方法

| 方法 | 作用 | 单位 |
| --- | --- | --- |
| `swap(a, b)` | 两条对调位置（侧、拐点、起点、横线长），终点不变 | — |
| `move(name, dx=0, dy=0)` | 拐点（及单给的起点）平移，文字跟着走 | 度 |
| `edit(name, **字段)` | 改 `side`、`elbow`、`end`、`start`、`stub`；名字不在包里时新加一条（side、elbow、end 必填） | 坐标 (lng, lat)，stub 磅 |

`edit(name, start=None)` 让起点回到"从拐点水平向外 stub 磅"。商圈这类小范围底图，`move` 的 `dy` 要按实际纬度跨度给，比如 0.005 度约 550 米。

### JSON 格式

一个名字一行，方便手改和看 diff（坐标是示意）：

```json
{
  "stub": 28.0,
  "gap": 4.0,
  "labels": {
    "西塔": {"side": "left", "elbow": [123.36512, 41.80123], "end": [123.41201, 41.80598]},
    "棋盘山风景区": {"side": "right", "elbow": [123.71234, 41.93012], "end": [123.66, 41.93], "stub": 40}
  }
}
```

### 套参数包时的规则

- `layout` 可以是 `LabelLayout`、JSON 路径，或 `viz/layouts/` 下的文件名（不带 `.json`）。
- 位置、`stub`、`gap` 全按参数包；`split`、`spread`、`angle`、`at` 不起作用。
- 数据里有、包里没有的区会警告并跳过；终点不在对应区内也会警告（多半拿错了底图的包）。
- 自检：文字重叠、文字压到附件、同列引线交叉时各警告一次。

---

## 10. API 速查

### viz.maps.Regions

| 调用 | 返回 | 说明 |
| --- | --- | --- |
| `Regions(regions, *, lat0=None, alias=None)` | Regions | `{名字: 环或[环...]}`；alias 别名 |
| `Regions.from_geodataframe(gdf, name)` | Regions | 从 GeoDataFrame 建 |
| `.names` / `.bounds` / `.aspect` / `.lat0` / `.alias` | — | 区名、外框、宽高比、折算纬度、别名 |
| `.anchor(name)` | (lng, lat) | 区内落点 |
| `.split_lng(split="center")` | 经度 | 分左右列的线 |
| `.clip(df, margin=0.1)` | DataFrame | 只留外框附近的点 |
| `.base(ax=None, *, land, borders, outline, scale, north, km, margin)` | ax | 底图，不需要数据 |
| `.frame(ax, margin=0.02, bare=True, fill=True)` | ax | 地图框、长宽比；fill 居中留白 |
| `.fill(ax, values=None, *, colors=None, cmap, norm, nan_color, ...)` | PatchCollection | 填色 |
| `.borders(ax, color=None, lw=0.9, ls="-")` | LineCollection | 内边界 |
| `.outline(ax, color=None, lw=1.0, ls="-")` | LineCollection | 外边界 |
| `.edges(ax, names, color=None, lw=1.2)` | PatchCollection | 指定区整圈边界 |
| `.points(ax, data, *, color=None, by=None, colors=None, s=1)` | PathCollection | 叠点 |
| `.text(ax, texts, ..., alias=None)` | RegionTexts | 区内标注 |
| `.label(ax, texts, ..., inside=False, alias=None)` | Callouts | 外部引线；`inside="auto"` 放得下写区内 |
| `.plot(values, texts, *, ax, colors, land, ..., margin, **label_kw)` | ax | base + 数据层，一步出图 |

### 其他

| 调用 | 说明 |
| --- | --- |
| `viz.maps.colors.set(**kw)` / `.use(**kw)` / `.reset()` | 地图默认颜色 |
| `viz.maps.scale_bar(ax, km=None, lat0=None, x=0.04, y=0.04)` | 比例尺 |
| `viz.maps.north_arrow(ax, x=0.95, y=0.95)` | 指北针 |
| `viz.maps.set_map_aspect(ax, lat0=None, bare=True)` | 只做长宽比校正 |
| `viz.maps.FURNITURE` | 让标注避开的 gid |
| `viz.maps.LAND` | 底色层的 gid，`ax.collections` 里按它找 |
| `Callouts.texts / nums / lines / dots` | 按区名取四个部分 |
| `Callouts.freeze()` / `.layout` | 定成参数包 / 当前参数包 |
| `LabelLayout.load(path)` / `.save(path)` / `.swap` / `.move` / `.edit` | 参数包读写与微调 |
| `viz.apply_theme` / `use_theme` / `available_themes` / `finish` | 主题与出图（theme.py，未改） |

---

## 11. 常见问题、升级说明、测试

### 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `ImportError: cannot import name 'C'` | 用了上一轮那个 `viz.zip`（maps 依赖新版 theme） | 换成本次交付的 `viz/` |
| 比例尺出现两个、自定的区界样式没生效 | `base()` 之后又 `plot(ax=ax)`，底图画了两遍 | 二选一，见 4.4 节；现在会警告 |
| 地图一片深灰 | 填色的值全一样 | 填真实数值，或不给 values |
| 地图偏在图的一边（左边一大块空白） | 旧版 ax 缩到地图大小，裁白边时左边被标题撑住、右边没有 | 现在默认居中；仍偏的话检查是不是 `frame(fill=False)` |
| 名字太长，标注挤 | — | 用别名：`Regions(..., alias={...})` 或 `label(..., alias={...})` |
| 没数据时内边界看不见 | 内边界默认白线，旧版底下没有底色 | 现在 `base()` 自带浅灰底色；或 `borders=dict(color="#C4CAD3")` |
| `geo.plot(texts=True)` 没出标注 | 旧版 texts=True 只从 values 取 | 现在没有 values 会写全部区名 |
| 比例尺或指北针压在区域上 | 区域贴着外框四角（商圈常见） | `plot(..., margin=0.08, scale=dict(x=0.55))`，或 `scale_bar(ax, x=...)` |
| 换主题后地图颜色没变 | 地图颜色已经和主题独立 | 用 `viz.maps.colors.set(...)` |
| 地图颜色改了没生效 | 图在 `set` 之前就画了 | 先 `set` 再画 |
| 汉字显示成方框 | 没装 Noto Serif CJK SC | 装字体，或主题文件里改 `font.family` |
| 单独调 `fill` 后区与区之间没有分界线 | `fill` 只填色 | 补 `geo.borders(ax)` |
| `freeze()` 坐标和最终图不一致 | 版面还没定 | 先 `finish` 或显示一次再 `freeze` |
| 警告"终点不在对应的区域里" | 套了别的底图的参数包 | 重新自动排一版再 `freeze` |
| 区名相关警告 | 名字和边界数据不一致（如少了"商圈"两字） | 按警告里的名字改 |
| 内边界上零星黑点 | 相邻区顶点错位约 165 米以上 | 用拓扑一致的边界数据 |

### 和上一轮交付相比的变化

- 同一个 ax 画两遍底图（`base` 之后又 `plot`）会警告；文档新增 4.4 配色配方。
- 地图默认在 ax 里居中，多出的宽度两侧留白，标注排在留白里；裁白边存图也在正中。比例尺、指北针按地图框定位。
- 新增别名：`Regions(..., alias=)`、`geo.alias`、`label/text(..., alias=)`，只改显示名。
- 底图和数据层分开：新增 `geo.base()`，自带浅灰底色（`colors.land`），没数据时内边界也看得见；`plot()` 改为 `base()` + 数据层。
- 新增区内标注 `geo.text()`；`label(inside="auto")` 放得下写区内、放不下引到外面。
- 空数据不再报错：`fill(None, norm="log")`、`label(ax, {})`、名字全写错，都只是不画（写错会警告）。
- `plot(texts=True)` 没有 values 时写全部区名。
- 视觉变化：`plot()` 出的图多了一层浅灰底色，缺数据的区从"透明"变成"灰色"。不要底色传 `land=False`。
- 更早一轮：地图颜色和 `theme.py` 脱钩；`fill(colors=)`、`points(by=, colors=)`、比例尺位置 `x/y`。

### 从更早的旧版升级

- `fill` 默认不再画白色分区线，单独调 `fill` 的地方补 `geo.borders(ax)`；`plot()` 和 `DistrictMap` 已自动加上。
- 自动排版默认 `span` + 中线分侧；要旧效果传 `spread="fit"`。
- `co.dots` 是按区名取的字典。
- 旧接口 `DistrictMap(districts).figure(cols)` + `.draw(ax, values, texts, hot=...)` 仍能用，内部转给 `Regions`。

### 测试

`test_viz_maps.py` 和 `fake_geo.py` 放进 `tests/`，`pytest tests/test_viz_maps.py` 运行，共 44 项，覆盖标注不重叠、引线不交叉、多尺度、参数包、分侧排序、样式优先级、内外边界。本轮新增四项：无数据底图（底色在、内边界可见）、数据层缺区与空数据不报错、区内标注与放不下的判断、`inside="auto"` 每个区只出现一次。最新一轮再加三项：宽 ax 里地图居中（裁白边后也居中）、放大后视窗不被拉回、别名只改显示。沙箱里没有 pytest，我用一个最小替身跑的，44 项全部通过。

### 第一次用真实数据的建议

1. `geo = viz.maps.Regions(areas)`，`print(geo)` 确认区域数和经纬度范围。
2. 先 `geo.base()` 只画底图，确认边界、底色、比例尺位置；再叠 `fill` 和 `label(..., inside="auto", debug=True)` 看标注。
3. 换 `split="balance"` 再出一张对比。
4. 满意后 `freeze()`，按需微调，存进 `viz/layouts/`；之后一律 `layout="包名"`。
