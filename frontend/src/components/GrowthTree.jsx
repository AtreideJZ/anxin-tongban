/* ============================================================
 * GrowthTree — 生命树（本页唯一视觉主角，v2.4）
 *
 * 状态映射：
 * - 探索芽 +1 → 树冠长新叶（sprout 实色小叶）
 * - 好奇星 +1 → 树上结星形果实（star 金色星星）
 * - 故事册 +1 → 树下摆一本书
 * - 心情云/天气 → 树周围氛围（晴=柔光晕、雨=细雨丝、彩虹=远景小彩虹…）
 * - 有已解锁胶囊 → 树旁几点金色微光（时间胶囊到期的余韵）
 *
 * v2.4 升级：
 * - 类型联动：activeType 对应元素 scale(1.15) + 预渲染 glow 层淡入
 *   （纯 transform/opacity 过渡，禁用 filter drop-shadow 动画）
 * - 树元素可点击：点叶/星/书/云 = 点罗盘对应卫星（onSelectType）
 * - 天气循环动画升级为纯 CSS @keyframes，同一时刻只有当前天气一组
 * - 新增记忆时树心放一小簇 8 粒子（罕见事件可以 delight）
 * - prefers-reduced-motion：关 popIn/粒子（useReducedMotion），
 *   CSS 侧停掉全部循环动画
 *
 * 成长阶段：条目总量 0/1-2/3-5/6-9/10+ 共 5 档（空星球=星空下的小树苗）
 *
 * 实现注意：CSS/framer 的 transform 会覆盖 SVG transform 属性，
 * 所以"定位"一律用外层静态 <g transform>，动效（tree-elem 缩放、
 * wx-* 循环、popIn 弹跳）只放内层嵌套元素。
 * ============================================================ */

import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import "./GrowthTree.css";

/* 五档成长阶段：树干高 / 树冠半径 / 树干半宽 */
const STAGES = [
  { trunkH: 0, canopyR: 0, trunkW: 0 }, // 0 条：空星球（小树苗）
  { trunkH: 46, canopyR: 30, trunkW: 5 }, // 1-2 条：树苗
  { trunkH: 72, canopyR: 46, trunkW: 7 }, // 3-5 条：小树
  { trunkH: 96, canopyR: 60, trunkW: 9 }, // 6-9 条：中树
  { trunkH: 116, canopyR: 74, trunkW: 11 }, // 10+ 条：茂树
];

function stageOf(total) {
  if (total <= 0) return 0;
  if (total <= 2) return 1;
  if (total <= 5) return 2;
  if (total <= 9) return 3;
  return 4;
}

/* 叶子在树冠上的预置落点（单位：树冠半径，相对树冠中心） */
const LEAF_POS = [
  [-0.85, -0.1], [0.8, -0.2], [-0.5, -0.7], [0.42, -0.75],
  [0.05, -0.35], [-0.9, 0.35], [0.85, 0.35], [-0.32, 0.15],
  [0.38, 0.18], [-0.62, -0.42], [0.62, -0.48], [0.0, -0.9],
  [-0.18, 0.5], [0.22, 0.55],
];
/* 星形果实落点（挂在树冠内圈） */
const STAR_POS = [
  [-0.42, -0.32], [0.34, -0.42], [0.0, -0.02], [-0.66, 0.08],
  [0.6, 0.05], [-0.14, -0.6], [0.18, 0.32], [-0.38, 0.32],
  [0.5, -0.62], [0.0, -0.78],
];
/* 书本落点（树根两侧，x 相对树干中心，y 相对地面） */
const BOOK_POS = [
  [-46, -9], [46, -9], [-74, -6], [72, -6], [-46, -25], [46, -27],
];

/* 画布几何常量 */
const CX = 210; // 树干中心 x
const GROUND = 330; // 地面 y

/* 五角星路径（以 0,0 为中心，外径 r，尺寸直接烘进路径避免缩放变换） */
function starPath(r) {
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const rr = i % 2 === 0 ? r : r * 0.45;
    const a = (Math.PI / 5) * i - Math.PI / 2;
    pts.push(`${(rr * Math.cos(a)).toFixed(2)},${(rr * Math.sin(a)).toFixed(2)}`);
  }
  return `M${pts.join("L")}Z`;
}
const FRUIT_D = starPath(9); // 星形果实
const GLOW_D = starPath(5); // 金色微光点
const LEAF_D = "M0 0 Q7 -7 14 0 Q7 7 0 0Z"; // 小叶

/* 类型色（glow 层用，与罗盘/卡片同一 token 粉彩） */
const TYPE_COLOR = {
  star: "var(--star)",
  cloud: "var(--cloud)",
  sprout: "var(--sprout)",
  story: "var(--sunset)",
};

/* 入场 spring：新元素弹跳出现；reduced-motion 时退化为直接就位 */
const popStyle = { transformBox: "fill-box", transformOrigin: "50% 50%" };
function usePopIn() {
  const reduced = useReducedMotion();
  return (i = 0) =>
    reduced
      ? { style: popStyle }
      : {
          initial: { scale: 0, opacity: 0 },
          animate: { scale: 1, opacity: 1 },
          transition: { type: "spring", stiffness: 300, damping: 17, delay: i * 0.06 },
          style: popStyle,
        };
}

/* ---- 类型元素分组：联动高亮 + 可点击（v2.4 §3.2） ----
 * 外层负责定位（transform 属性），内层 .tree-elem 负责 CSS 缩放过渡，
 * glow 层预渲染、用 opacity 切换，全程不碰 filter。 */
function TypeGroup({ type, activeType, onSelectType, transform, glow, children }) {
  const isActive = activeType === type;
  return (
    <g transform={transform}>
      <g
        className={`tree-elem ${isActive ? "is-active" : ""} ${
          onSelectType ? "is-clickable" : ""
        }`}
        onClick={onSelectType ? () => onSelectType(type) : undefined}
      >
        <g className="tree-glow" aria-hidden="true" fill={TYPE_COLOR[type]}>
          {glow}
        </g>
        {children}
      </g>
    </g>
  );
}

/* 粉彩小云朵 = 心情云卫星（可点击，含 glow 层，drift 动画不被打断） */
function TypeCloud({ x, y, small, drift, activeType, onSelectType }) {
  return (
    <TypeGroup
      type="cloud"
      activeType={activeType}
      onSelectType={onSelectType}
      transform={`translate(${x} ${y}) scale(${small ? 0.72 : 1})`}
      glow={<ellipse cx="0" cy="2" rx="34" ry="20" />}
    >
      <g className={drift ? `wx-cloud ${drift}` : undefined}>
        <g fill="var(--cloud)" opacity="0.75">
          <ellipse cx="0" cy="6" rx="26" ry="12" />
          <circle cx="-12" cy="0" r="11" />
          <circle cx="4" cy="-6" r="13" />
          <circle cx="16" cy="2" r="9" />
        </g>
      </g>
    </TypeGroup>
  );
}

/* ---- 天气氛围（树周围的小景，跟随 weather 字段；循环动画纯 CSS） ---- */
function WeatherScene({ weather, canopyCY, canopyR, activeType, onSelectType }) {
  const cloudProps = { activeType, onSelectType };
  switch (weather) {
    case "sunny":
      return (
        <g aria-hidden="true">
          {/* 树冠后的柔光晕 + 左上角小太阳（光线缓慢旋转 12s） */}
          <circle cx={CX} cy={canopyCY} r={canopyR + 46} fill="var(--star)" opacity="0.14" />
          <g transform="translate(56 58)">
            <g className="wx-rays">
              <circle r="20" fill="var(--star)" opacity="0.85" />
              {Array.from({ length: 8 }, (_, i) => {
                const a = (Math.PI / 4) * i;
                return (
                  <line
                    key={i}
                    x1={26 * Math.cos(a)} y1={26 * Math.sin(a)}
                    x2={33 * Math.cos(a)} y2={33 * Math.sin(a)}
                    stroke="var(--star)" strokeWidth="3.5" strokeLinecap="round"
                  />
                );
              })}
            </g>
          </g>
        </g>
      );
    case "partly_sunny":
      return (
        <g aria-hidden="true">
          <circle cx={CX} cy={canopyCY} r={canopyR + 40} fill="var(--star)" opacity="0.1" />
          <circle cx="58" cy="56" r="17" fill="var(--star)" opacity="0.85" />
          <TypeCloud x={88} y={46} drift="wx-cloud--a" {...cloudProps} />
        </g>
      );
    case "partly_cloudy":
      return (
        <g aria-hidden="true">
          <TypeCloud x={64} y={52} drift="wx-cloud--a" {...cloudProps} />
          <TypeCloud x={330} y={70} small drift="wx-cloud--b" {...cloudProps} />
        </g>
      );
    case "cloudy":
      return (
        <g aria-hidden="true">
          <TypeCloud x={70} y={54} drift="wx-cloud--a" {...cloudProps} />
          <TypeCloud x={322} y={62} drift="wx-cloud--c" {...cloudProps} />
          <TypeCloud x={200} y={34} small drift="wx-cloud--b" {...cloudProps} />
        </g>
      );
    case "light_rain":
      return (
        <g aria-hidden="true">
          <TypeCloud x={70} y={48} drift="wx-cloud--a" {...cloudProps} />
          <TypeCloud x={322} y={52} drift="wx-cloud--b" {...cloudProps} />
          {/* 细雨丝：CSS 下落循环，错峰 delay */}
          {[
            [46, 92], [68, 104], [90, 92], [112, 106],
            [300, 96], [322, 108], [344, 94], [366, 106],
          ].map(([x, y], i) => (
            <line
              key={i}
              className="wx-rain-drop"
              style={{ animationDelay: `${(i % 4) * 0.45}s` }}
              x1={x} y1={y} x2={x - 5} y2={y + 14}
              stroke="var(--sky)" strokeWidth="2.5" strokeLinecap="round" opacity="0.75"
            />
          ))}
          {/* 地面涟漪：两圈错位扩散 */}
          {[70, 322].map((x, i) => (
            <ellipse
              key={i}
              className="wx-ripple"
              style={{ animationDelay: `${i * 0.9}s` }}
              cx={x} cy={GROUND + 8} rx="10" ry="3.5"
              fill="none" stroke="var(--sky)" strokeWidth="1.5"
            />
          ))}
        </g>
      );
    case "rainbow":
      return (
        <g aria-hidden="true" transform="translate(330 96)">
          {/* 远景小彩虹：三弧粉彩，透明度 0.7→1 呼吸 */}
          <g className="wx-rainbow-g">
            <path d="M-52 0 A52 52 0 0 1 52 0" fill="none" stroke="var(--cloud)" strokeWidth="7" strokeLinecap="round" opacity="0.8" />
            <path d="M-40 0 A40 40 0 0 1 40 0" fill="none" stroke="var(--star)" strokeWidth="7" strokeLinecap="round" opacity="0.8" />
            <path d="M-28 0 A28 28 0 0 1 28 0" fill="none" stroke="var(--sky)" strokeWidth="7" strokeLinecap="round" opacity="0.8" />
          </g>
          <TypeCloud x={-58} y={2} small drift="wx-cloud--b" {...cloudProps} />
          <TypeCloud x={46} y={2} small drift="wx-cloud--c" {...cloudProps} />
        </g>
      );
    default:
      return null;
  }
}

/* 树下的一本书（粉彩色轮换） */
const BOOK_COLORS = ["var(--cloud)", "var(--sky)", "var(--star)", "var(--sunset)"];
function Book({ x, y, color, i, popIn, activeType, onSelectType }) {
  return (
    <TypeGroup
      type="story"
      activeType={activeType}
      onSelectType={onSelectType}
      transform={`translate(${x} ${y})`}
      glow={<circle cx="0" cy="0" r="22" />}
    >
      <motion.g {...popIn(i)}>
        <rect x="-14" y="-8" width="28" height="17" rx="3" fill={color} />
        <rect x="-14" y="-8" width="28" height="17" rx="3" fill="none" stroke="var(--charcoal)" strokeOpacity="0.12" />
        <line x1="0" y1="-8" x2="0" y2="9" stroke="var(--cream)" strokeWidth="2.5" />
      </motion.g>
    </TypeGroup>
  );
}

/* 空星球：星空下的小树苗（星空微闪是设计文档豁免的循环动画） */
function EmptyPlanet({ popIn }) {
  const reduced = useReducedMotion();
  const stars = [
    [60, 60, 2.2], [130, 34, 1.6], [200, 58, 2.6], [286, 30, 1.8],
    [352, 66, 2.2], [96, 108, 1.5], [330, 120, 1.6], [246, 96, 1.4],
  ];
  return (
    <g>
      {stars.map(([x, y, r], i) => (
        <motion.circle
          key={i}
          cx={x} cy={y} r={r}
          fill="var(--night-sky)"
          animate={reduced ? { opacity: 0.6 } : { opacity: [0.25, 0.85, 0.25] }}
          transition={{ duration: 2.8, repeat: reduced ? 0 : Infinity, delay: i * 0.35, ease: "easeInOut" }}
        />
      ))}
      {/* 小树苗：一茎两叶 */}
      <motion.g
        {...popIn(0)}
        style={{ transformBox: "fill-box", transformOrigin: "50% 100%" }}
      >
        <path
          d={`M${CX} ${GROUND} C ${CX - 2} ${GROUND - 18}, ${CX + 2} ${GROUND - 30}, ${CX} ${GROUND - 44}`}
          fill="none" stroke="var(--sprout)" strokeWidth="4" strokeLinecap="round"
        />
        <path
          d={`M${CX} ${GROUND - 34} Q ${CX - 20} ${GROUND - 44} ${CX - 24} ${GROUND - 30} Q ${CX - 12} ${GROUND - 26} ${CX} ${GROUND - 34}Z`}
          fill="var(--sprout)"
        />
        <path
          d={`M${CX} ${GROUND - 42} Q ${CX + 20} ${GROUND - 54} ${CX + 25} ${GROUND - 38} Q ${CX + 12} ${GROUND - 34} ${CX} ${GROUND - 42}Z`}
          fill="var(--sprout)"
        />
      </motion.g>
    </g>
  );
}

/* 新增记忆的树心粒子：8 点粉彩向外弹开，放完即收（罕见事件） */
const BURST_COLORS = ["var(--star)", "var(--cloud)", "var(--sprout)", "var(--sky)"];
function TreeBurst({ cy }) {
  return (
    <g aria-hidden="true">
      {Array.from({ length: 8 }, (_, i) => {
        const a = (Math.PI / 4) * i;
        return (
          <motion.circle
            key={i}
            cx={CX} cy={cy} r="4.5"
            fill={BURST_COLORS[i % BURST_COLORS.length]}
            initial={{ x: 0, y: 0, scale: 1, opacity: 1 }}
            animate={{
              x: Math.cos(a) * 56,
              y: Math.sin(a) * 56,
              scale: 0.2,
              opacity: 0,
            }}
            transition={{ duration: 0.8, ease: "easeOut", delay: i * 0.03 }}
            style={popStyle}
          />
        );
      })}
    </g>
  );
}

export default function GrowthTree({
  entries = [],
  weather = null,
  goldenGlow = false,
  activeType = null,
  onSelectType = null,
}) {
  const popIn = usePopIn();
  const reduced = useReducedMotion();
  const total = entries.length;
  const stage = stageOf(total);
  const { trunkH, canopyR, trunkW } = STAGES[stage];

  const counts = { star: 0, cloud: 0, sprout: 0, story: 0 };
  for (const e of entries) {
    if (counts[e.type] !== undefined) counts[e.type] += 1;
  }
  const leaves = LEAF_POS.slice(0, Math.min(counts.sprout, LEAF_POS.length));
  const fruits = STAR_POS.slice(0, Math.min(counts.star, STAR_POS.length));
  const books = BOOK_POS.slice(0, Math.min(counts.story, BOOK_POS.length));

  const trunkTop = GROUND - trunkH;
  const canopyCY = trunkTop - canopyR * 0.35; // 树冠中心
  const weatherKey = typeof weather === "string" ? weather : weather?.weather;

  /* 条目数增加（非首次加载）→ 树心放一次粒子 */
  const prevCount = useRef(null);
  const [burst, setBurst] = useState(false);
  useEffect(() => {
    if (prevCount.current === null) {
      prevCount.current = total; // 首次加载只记录，不放粒子
      return undefined;
    }
    if (total > prevCount.current && !reduced) {
      setBurst(true);
      const t = setTimeout(() => setBurst(false), 1100);
      prevCount.current = total;
      return () => clearTimeout(t);
    }
    prevCount.current = total;
    return undefined;
  }, [total, reduced]);

  return (
    <div className="growth-tree">
      <svg
        viewBox="0 0 420 360"
        role="img"
        aria-label={`生命树，星球上已有 ${total} 条记录`}
        className="growth-tree-svg"
      >
        {/* 地面：两片交叠的粉彩小丘 */}
        <ellipse cx={CX - 60} cy={GROUND + 12} rx="130" ry="18" fill="var(--sprout)" opacity="0.14" />
        <ellipse cx={CX + 70} cy={GROUND + 14} rx="120" ry="16" fill="var(--sky)" opacity="0.12" />

        {stage === 0 ? (
          <EmptyPlanet popIn={popIn} />
        ) : (
          <>
            {/* 天气氛围（云层在树后，光晕垫底） */}
            <WeatherScene
              weather={weatherKey}
              canopyCY={canopyCY}
              canopyR={canopyR}
              activeType={activeType}
              onSelectType={onSelectType}
            />

            {/* 树本体：阶段变化时轻轻"再长一次"（key=stage 重挂载 spring） */}
            <motion.g
              key={stage}
              style={{ transformBox: "fill-box", transformOrigin: "50% 100%" }}
              initial={reduced ? false : { scale: 0.82, opacity: 0.6 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 260, damping: 20 }}
            >
              {/* 树干（微锥形） */}
              <path
                d={`M${CX - trunkW} ${GROUND}
                    L${CX - trunkW * 0.55} ${trunkTop}
                    Q${CX} ${trunkTop - 6} ${CX + trunkW * 0.55} ${trunkTop}
                    L${CX + trunkW} ${GROUND}
                    Q${CX} ${GROUND + 5} ${CX - trunkW} ${GROUND}Z`}
                fill="var(--sunset)"
                opacity="0.85"
              />
              {/* 树冠：三团圆，深浅叠出层次 */}
              <circle cx={CX - canopyR * 0.55} cy={canopyCY + canopyR * 0.15} r={canopyR * 0.62} fill="var(--sprout)" opacity="0.5" />
              <circle cx={CX + canopyR * 0.55} cy={canopyCY + canopyR * 0.15} r={canopyR * 0.62} fill="var(--sprout)" opacity="0.65" />
              <circle cx={CX} cy={canopyCY - canopyR * 0.12} r={canopyR * 0.78} fill="var(--sprout)" opacity="0.85" />
            </motion.g>

            {/* 探索芽 → 新叶（实色小叶，跳出树冠） */}
            {leaves.map(([dx, dy], i) => (
              <TypeGroup
                key={`leaf-${i}`}
                type="sprout"
                activeType={activeType}
                onSelectType={onSelectType}
                transform={`translate(${CX + dx * canopyR} ${canopyCY + dy * canopyR}) rotate(${(i % 5) * 36 - 72})`}
                glow={<circle cx="7" cy="0" r="14" />}
              >
                <motion.path
                  d={LEAF_D}
                  fill="var(--sprout)"
                  stroke="var(--cream)"
                  strokeWidth="1"
                  {...popIn(i)}
                />
              </TypeGroup>
            ))}

            {/* 好奇星 → 星形果实 */}
            {fruits.map(([dx, dy], i) => (
              <TypeGroup
                key={`fruit-${i}`}
                type="star"
                activeType={activeType}
                onSelectType={onSelectType}
                transform={`translate(${CX + dx * canopyR * 0.9} ${canopyCY + dy * canopyR * 0.9})`}
                glow={<circle cx="0" cy="0" r="15" />}
              >
                <motion.path
                  d={FRUIT_D}
                  fill="var(--star)"
                  stroke="var(--cream)"
                  strokeWidth="0.6"
                  {...popIn(i)}
                />
              </TypeGroup>
            ))}

            {/* 故事册 → 树下摆书 */}
            {books.map(([bx, by], i) => (
              <Book
                key={`book-${i}`}
                x={CX + bx}
                y={GROUND + by}
                color={BOOK_COLORS[i % BOOK_COLORS.length]}
                i={i}
                popIn={popIn}
                activeType={activeType}
                onSelectType={onSelectType}
              />
            ))}

            {/* 已解锁胶囊 → 树旁金色微光（静态微光点，入场弹跳一次） */}
            {goldenGlow &&
              [
                [CX - canopyR - 26, canopyCY + 10],
                [CX + canopyR + 24, canopyCY - 18],
                [CX + canopyR + 6, canopyCY + canopyR * 0.7],
              ].map(([x, y], i) => (
                <g key={`glow-${i}`} transform={`translate(${x} ${y})`}>
                  <motion.path d={GLOW_D} fill="var(--star)" opacity="0.8" {...popIn(i)} />
                </g>
              ))}

            {/* 新增记忆的树心粒子 */}
            {burst && <TreeBurst cy={canopyCY} />}
          </>
        )}
      </svg>

      {stage === 0 && <p className="growth-tree-empty">等待第一个故事发生 🌱</p>}
    </div>
  );
}
