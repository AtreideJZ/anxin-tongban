# DESIGN-anxin · 安心童伴融合设计系统（v2.1）

> 2026-07-31 · 融合 `DESIGN-lovable.md`（材质：温暖的纸）+ `DESIGN-shopify.md`（结构：双轨极性），按儿童产品需求加入"活的色彩层"与动效语言。
> 决策记录（已与产品负责人确认）：① 双轨策略（儿童端/家长端同 DNA、分轨道）；② 安全引擎页允许深色例外；③ 标题字用圆润黑体，不用活泼字体。

## 核心思想

- **Lovable 给材质**：奶油 `#f7f4ed` 羊皮纸 + 炭黑 `#1c1c1c` + 透明度灰阶 + `#eceae4` 暖边框——温暖、安全、类纸的"非科技感"。
- **Shopify 给结构**：一套 DNA、两条轨道。儿童端/家长端共享按钮词汇、边框系统、间距基准、语义色层；按角色切换密度、色相与字体人格。
- **我们加的两样东西**（两套参考系统都没有）：
  1. **活的色彩层**——粉彩系装饰色（天空蓝/新芽绿/星星金/云朵粉），低饱和，温暖不刺眼。语义色（risk_0-3）与装饰色同源：新芽绿、暖橙本就在现有色板里。
  2. **动效语言**——"万物生长，无机械滑动"：spring 曲线、300-500ms、宁可少不可猛。儿童产品的"全出血摄影"是生成式 SVG 插画（小星球即吉祥物），不用照片。

## 双轨规则

| | 儿童端（日轨 · 会呼吸的星球） | 家长端（同一产品的大人模式） |
|---|---|---|
| 画布 | 奶油底 + 粉彩装饰 | 奶油底，装饰色转冷（石板青） |
| 密度 | 宽松（80px+ 段落留白） | 收紧（48-64px，数据密度优先） |
| 强调色 | 粉彩（sky/sprout/star/cloud） | 石板青 `--accent` |
| 标题字 | 圆润黑体栈 | 系统中黑 + Inter |
| 数字/拉丁 | Nunito（圆角，与 pill 同构） | Inter |
| **例外** | — | 安全引擎可视化页：深色"夜空"画布（`.dark-safety` 作用域），决策链步骤卡发光；其余家长页面全浅（避免"监控感"） |

## Design Tokens

### base（两端共享）

```css
/* 材质 */
--cream: #f7f4ed;          /* 页面/卡片背景 */
--charcoal: #1c1c1c;       /* 主文字 */
--off-white: #fcfbf8;      /* 深底按钮文字 */
--muted: #5f5f5d;          /* 次要文字 */
--border: #eceae4;         /* 暖边框（容器用边框不用阴影） */
--border-strong: rgba(28,28,28,.4);  /* 交互边框 */
--tint: rgba(28,28,28,.04);          /* 微染（hover/用户气泡） */
--focus-shadow: rgba(0,0,0,.1) 0 4px 12px;

/* 语义色（两端统一含义：聊天气泡徽章/家长告警/安全引擎步骤卡） */
--risk-0: #7BB76E;  /* 安全绿 */
--risk-1: #E8C547;  /* 轻度黄 */
--risk-2: #E89B47;  /* 中度橙 */
--risk-3: #D9534F;  /* 高危红 */
--info-blue: #3b82f6;

/* 形状：pill 是唯一主按钮形状（Shopify 纪律） */
--r-xs: 4px; --r-sm: 6px; --r-md: 8px; --r-lg: 12px; --r-xl: 16px; --r-pill: 9999px;

/* 间距（8px 基准） */
--sp-1: 8px; --sp-2: 16px; --sp-3: 24px; --sp-4: 32px; --sp-6: 48px; --sp-8: 64px; --sp-10: 80px;

/* 主按钮内凹阴影（Lovable 签名细节） */
--btn-inset: rgba(255,255,255,.2) 0 .5px 0 inset, rgba(0,0,0,.2) 0 0 0 .5px inset, rgba(0,0,0,.05) 0 1px 2px;

/* 字体栈 */
--font-body: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui, sans-serif;
--font-num: "Nunito", var(--font-body);
```

### track-child（儿童端叠加）

```css
/* 粉彩装饰色（低饱和，不糖果） */
--sky: #8FCDE0;      /* 天空蓝 */
--sprout: #7BB76E;   /* 新芽绿（与 risk-0 同源） */
--star: #F2C94C;     /* 星星金 */
--cloud: #F4B8C1;    /* 云朵粉 */
--sunset: #E89B47;   /* 暖橙（与 risk-2 同源） */
--night-sky: #2E3A59; /* 夜空（星空点缀/深色小元素） */

/* 标题：圆润黑体栈（不用活泼字体——安心童伴的定位是温暖可信，不是热闹） */
--font-display-child: "阿里妈妈方圆体 VF", "AlimamaFangYuanTi", "Source Han Rounded",
  "思源柔黑", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui, sans-serif;

/* 密度：宽松 */
--section-gap: var(--sp-10);
```

### track-parent（家长端叠加）

```css
--accent: #4A7384;          /* 石板青（替代粉彩） */
--font-display-parent: Inter, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
--section-gap: var(--sp-6);  /* 收紧 */
```

### .dark-safety（安全引擎页深色作用域，仅此页）

```css
.dark-safety {
  --canvas: #14181f;         /* 夜空（不用纯黑，更柔和） */
  --surface: #1d242e;
  --text: #e8e6e0;
  --border: rgba(255,255,255,.08);
  /* risk 语义色不变——步骤卡在深色上自然"发光" */
}
```

## 组件要点

- **按钮**：pill（`--r-pill`）+ `--btn-inset` 内凹阴影；主按钮炭黑暗底/浅字，次按钮透明底/`--border-strong` 描边，active 时 opacity .8。矩形按钮只允许 `--r-sm` 小圆角用于工具类小按钮
- **卡片**：奶油底 + `1px solid var(--border)` + `--r-lg`（标准）/`--r-xl`（特色）；默认无阴影，悬浮可用多层微阴影
- **聊天气泡**：用户气泡 `--tint` 微染；AI 气泡奶油底 + 暖边框；风险/策略徽章用语义色 pill 小标签
- **输入区**：大圆角输入框 + 语音 pill 按钮；暖边框，focus 用 `--focus-shadow`，不用生硬描边

## 动效语言

- 曲线：spring（Framer Motion 默认 spring 即可），时长 300-500ms
- 语义：种树=弹跳萌芽；胶囊=破壳粒子；步骤链=逐节点亮；等待=呼吸盾牌
- 克制：同一屏幕同时进行的动效 ≤2 个；不做循环播放的喧闹动画（星空微闪除外）

## Do / Don't

- Do：奶油底永不换纯白；灰阶从 charcoal 调透明度；边框做容器；pill 做主按钮
- Don't：不用饱和糖果色；不用重投影；不给儿童端用细重（300-）字体；家长端除安全引擎页外不用深画布；不在儿童端堆技术细节（决策链给家长端看，儿童端只显示"已安全检查"）

## 落地

`frontend/src/styles/tokens.css`（base）+ `track-child.css` + `track-parent.css`（含 `.dark-safety`）。组件只引 base + 所在轨。
