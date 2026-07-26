# 国产芯片 vs 英伟达：演化博弈分析

用**非对称演化博弈 + 复制者动力学**，形式化 WSJ 脉络下的出口管制两难：卖则喂养中国 Token 市场，不卖则把华为「逼到墙角」并加速国产替代。

## 快速开始

```bash
pip install -r requirements.txt
python -m src.simulate
```

输出：

- `output/trajectories.csv` — 全情景时间序列
- `output/summary.json` — 参数、2021/2025/2030 快照、校准误差
- `figures/*.png` — 轨迹 / 相平面 / 两难对比 / EUV / 校准图

研究报告：[`report/analysis.md`](report/analysis.md)

## 模型一眼看懂

| 符号 | 含义 |
|------|------|
| \(x\) | 中国 AI 厂商选择国产栈的份额 |
| \(y\) | 国产芯片侧高强度研发投入份额 |
| \(\sigma(t)\) | 美方出口管制强度（情景外生） |
| \(\kappa(t)\) | DUV/EUV 约束下的有效产能·先进性天花板 |

基准情景 `wsj_dilemma` 校准到公开中枢：**10%（2021）→ ~41%（2025）→ ~75%（2030）**。

## 情景

- `no_control` — 无管制（CUDA 锁定）
- `sell_soft` — 卖：持续特供
- `wsj_dilemma` — WSJ 两难基准路径
- `hard_ban` — 不卖：高强度围堵
- `ascend_shock` — 昇腾 950 / 平头哥性能冲击
- `euv_breakthrough` — 反事实 EUV 突破

## 项目结构

```
src/model.py       # 支付函数与复制者动力学
src/scenarios.py   # 政策情景
src/visualize.py   # 绘图
src/simulate.py    # 入口
report/analysis.md # 中文研究报告
tests/             # 单元测试
```

## 测试

```bash
python -m pytest tests/ -q
```
