# PPT制作规划文件

## 一、基本信息

| 字段 | 值 |
|------|-----|
| PPT标题 | BOPET划伤问题已定位到MD拉伸段过程失稳，但原发机理仍需在线验证 |
| 副标题 | 面向经营层的结论汇报：结论、推导过程、证据链与下一步行动 |
| 总页数 | 12页（其中6页配图，6页text-only） |
| 制作引擎 | huashu-slides + html2pptx |
| 路径 | Path A（可编辑HTML） |
| 风格 | Study Style #20 — 学术研究双模系统（暖学术 + 锐学术） |
| **比例** | **16:9（960pt×540pt）** |
| 语言 | 中文 |
| 受众 | 商业（企业老板 + 制造管理层） |

## 二、风格参数速查

### 暖学术模式（Warm Academic）
- 页面底色: #FAF9F6
- 主色: #16324F
- 强调色: #C7772B
- 正文色: #1F1F1F
- 辅助色: #6C6A66
- 卡片底色: #F2EEE7
- 分割线色: #DDD3C7
- 标题字体: Microsoft YaHei Bold, 24-28pt
- 正文字体: Microsoft YaHei Regular, 10-13pt

### 锐学术模式（Crisp Academic）
- 页面底色: #FFFFFF
- 主色: #0E2A47
- 强调色: #B42318
- 卡片底色: #EEF4FA
- 重点卡片色: #FFF4F2
- 标题字体: Microsoft YaHei Bold, 24-26pt
- 正文字体: Microsoft YaHei Regular, 10-12pt

## 三、逐页规划

### 第1页：封面
- 标题: BOPET划伤问题已定位到MD拉伸段过程失稳
- 布局: 中央断言标题 + 下方四条管理层摘要 + 右侧结论卡
- 图片决策: text-only

### 第2页：经营层要先记住什么
- 标题: 先讲结论：不是温度设定值偏移，而是拉伸段过程稳定性失控
- 布局: 左侧三条核心结论，右侧风险边界与管理动作
- 图片决策: text-only

### 第3页：问题定义
- 标题: 我们分析的不是“某个坏批次”，而是55批次持续出现的划伤波动
- 布局: 左侧背景与样本说明，右侧大数字矩阵
- 图片决策: text-only

### 第4页：第一层证据
- 标题: 方差分解先回答了一个关键问题：问题主要发生在产品内，而不是产品之间
- 布局: 左图右文，图为方差分解
- 图片决策: 1张
- 配图:
  - 文件: garden-gpt-image-2/image/fig_variance_decomposition.png
  - 占位符id: img-variance

### 第5页：第二层证据
- 标题: 分产品时间线说明设备具备低缺陷能力，但部分型号对过程失稳更敏感
- 布局: 左图右文，图为分产品时间线
- 图片决策: 1张
- 配图:
  - 文件: garden-gpt-image-2/image/fig_product_timelines.png
  - 占位符id: img-products

### 第6页：第三层证据
- 标题: 参数排序把关注点收敛到MD拉伸段扭矩STD与速度STD
- 布局: 左文右图，图为相关排序
- 图片决策: 1张
- 配图:
  - 文件: garden-gpt-image-2/image/fig_torque_correlation.png
  - 占位符id: img-corr

### 第7页：第四层证据
- 标题: 时序叠加图把“划伤峰值”和“扭矩/速度波动峰值”串到了一起
- 布局: 上图下文，图为主时序叠加
- 图片决策: 1张
- 配图:
  - 文件: garden-gpt-image-2/image/fig_master_time_aligned_overlay.png
  - 占位符id: img-overlay

### 第8页：第五层证据
- 标题: 温度断面几乎重合，因此温度不是主根因
- 布局: 左图右侧反证链
- 图片决策: 1张
- 配图:
  - 文件: garden-gpt-image-2/image/fig_zone_profile.png
  - 占位符id: img-zone

### 第9页：证据链收束
- 标题: 由“排除法 + 关联证据 + 物理机理”收束到两个竞争假设
- 布局: 双列竞争假设卡片 + 底部证据链
- 图片决策: text-only

### 第10页：为什么现在不能直接定单根因
- 标题: 当前最大风险不是没找到方向，而是把批次级相关误当成确定因果
- 布局: 左侧统计稳健性问题，右侧对结论的影响
- 图片决策: text-only

### 第11页：企业下一步怎么做
- 标题: 下一步不是继续争论，而是设计能区分H1/H2的验证动作
- 布局: 三阶段行动路线图
- 图片决策: text-only

### 第12页：汇报收口
- 标题: 管理层决策建议：先稳住过程，再用在线数据定责
- 布局: 左侧一句话收口，右侧三条决策请求
- 图片决策: text-only

## 四、配图生成清单

| 序号 | 文件名 | 对应页码 | 来源 |
|------|--------|---------|------|
| 1 | fig_variance_decomposition.png | 4 | 诊断run原始图 |
| 2 | fig_product_timelines.png | 5 | 诊断run原始图 |
| 3 | fig_torque_correlation.png | 6 | 诊断run原始图 |
| 4 | fig_master_time_aligned_overlay.png | 7 | 诊断run原始图 |
| 5 | fig_zone_profile.png | 8 | 诊断run原始图 |

## 五、技术规范

- slide尺寸: 960pt×540pt
- 顶部签名线: 6pt 深蓝
- 底部信息栏: 22pt，页码右下
- 图片: placeholder div + compile.cjs addImage
- 编码: UTF-8
