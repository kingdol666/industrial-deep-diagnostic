# CCD在线检测技术

## 摘要
工业薄膜表面缺陷的CCD在线检测采用高速线阵相机（line-scan camera），配合透射/反射照明和FPGA实时图像处理，实现>10亿像素/秒的在线检测。可检测膜点、凝胶、气泡、划伤、条纹、针孔等缺陷，最小检测精度达0.05mm，最高速度>1000m/min。缺陷分类依赖灰度阈值算法和机器学习分类器。

## 关键数据点

| # | 数据/论断 | 来源 | 可信度 |
|---|----------|------|--------|
| 1 | 主流CCD线阵相机分辨率达8192像素，线扫描速率78kHz，支持>10亿像素/秒实时处理 | Dr. Schenk WebFeat技术白皮书 | 高 |
| 2 | 在线检测系统最小可检测缺陷尺寸可达0.05mm（双元科技），高端系统分辨率可达1μm区域（Fraunhofer FEP） | CHINAPLAS / Fraunhofer FEP | 高 |
| 3 | 检测速度范围：<500 m/min（Sunplus）至>1000 m/min（双元科技、捷将科技） | 供应商规格表 | 高 |
| 4 | 检测模式分透射式（transmission）和反射式（reflection），亮场（bright-field）和暗场（dark-field）照明，需根据缺陷类型选择 | Dr. Schenk Whitepaper | 高 |
| 5 | 可检测缺陷类型：凝胶（gel）、鱼眼（fish eye）、黑点/白点、气泡（bubble）、划伤（scratch）、针孔（pinhole）、条纹（streak）、模线（die-line）、异物（contaminant）、褶皱（wrinkle）、表面污渍 | Fraunhofer FEP / 多家供应商 | 高 |
| 6 | 现代系统采用FPGA+DSP架构实现实时处理，暗场模式对低对比度缺陷（如划伤、条纹）更敏感 | Dr. Schenk / 学术论文 | 中 |
| 7 | 哈工大博士学位论文（2009）系统研究了基于CCD的聚合物薄膜缺陷检测关键技术，包括FPGA实时图像采集、FIR滤波、动态缺陷提取 | CNKI博士论文2009233916 | 中 |
| 8 | 光学分辨率与检测宽度的平衡：2048像素相机在1米幅宽下像素分辨率约0.5mm，在0.5米幅宽下约0.25mm | R.K.B. Opto Model 3040规格 | 高 |

## 详细内容

### 系统架构

典型的CCD在线缺陷检测系统包括：
1. **照明系统** — 透射式（检测透明度变化）或反射式（检测表面反射率变化），亮场或暗场配置
2. **线阵相机** — 工业级CCD/CMOS线阵相机，像素数1024-8192
3. **图像采集卡** — FPGA硬件实时处理
4. **缺陷检测软件** — 灰度阈值算法、形态学分析、机器学习分类器
5. **缺陷标记与报警系统** — 实时缺陷映射、报警、分类统计

### 检测模式选择

| 模式 | 适用缺陷类型 | 原理 |
|:----:|------------|------|
| 透射亮场 | 凝胶、气泡、异物（对比度高） | 缺陷吸收/散射光线，呈现暗点 |
| 透射暗场 | 划伤、条纹（低对比度） | 缺陷衍射光线至暗场相机 |
| 反射亮场 | 表面膜点、低聚物结晶 | 表面凸起反射变化 |
| 反射暗场 | 极浅划伤、表面污染 | 表面微小结构散射光 |

### 缺陷分类体系（基于行业实践）

| 缺陷类别 | 物理成因 | 典型尺寸 | CCD检测难度 |
|---------|---------|:--------:|:----------:|
| 凝胶（gel）/鱼眼 | 未完全塑化或交联颗粒 | 0.1-2mm | 低 |
| 膜点（film_points） | 降解凝胶粒子、异物 | 0.05-1mm | 低-中 |
| 低聚物（oligomer） | 环状三聚体表面结晶 | 0.1-0.5mm | 中 |
| 气泡（bubbles） | 水分/挥发物释出 | 0.05-0.5mm | 低 |
| 熔斑（melt_spots） | 降解残留/污染 | 0.1-3mm | 中 |
| 划伤（scratch） | 机械接触损伤 | 长度>1mm | 中-高（需暗场） |
| 尘埃（dust） | 环境污染物 | 可变 | 低-中 |
| 条纹（streak） | 模唇积碳/磨损 | 连续性 | 高 |

### 与诊断报告的关系

报告的CCD检测数据为批次级汇总计数，具有以下局限性：
1. **无单缺陷图像/特征数据** — 无法区分缺陷的类型细分类
2. **批次级聚合丢失空间分布信息** — 无法判断缺陷是否在MD方向重复出现
3. **CCD自身存在漏检/误检率** — 具体数值未知，属于随机不确定性
4. **检测阈值影响计数** — CCD灵敏度设置变化可能导致计数波动

### CC检测行业发展

- 欧洲：Dr. Schenk（德国）、Fraunhofer FEP（德国）在高端光学设计方面领先
- 亚洲：双元科技、太阳科技（中国）、捷将科技、奈米趋势（台湾）在性价比方案方面占优
- 发展趋势：深度学习取代传统阈值法、更高像素（16K）、更高速（>2000m/min）

## 来源列表
- Dr. Schenk GmbH. "WebFeat Article — Web Inspection of Plastic Films." (http://www.drschenk.com/fileadmin/downloads/04_Web_inspection/WebFeat%20Article_Plastic%20Film_e.pdf)
- Fraunhofer FEP. "Roll-to-roll inspection system." (https://www.fep.fraunhofer.de/content/dam/fep/en/documents/Anlagenflyer/M07_Roll-to-roll_inspection_system_EN_net.pdf)
- 双元科技. "表面缺陷在线检测系统(CCD)." CHINAPLAS 展会资料. (https://www.chinaplasonline.com/eMarketplace/productinfo/simp?compid=1021152&SeqId=9871)
- 捷将科技. "Film Surface Inspection System." (https://www.jyejiang.com/en/product-intro/thin-film/)
- 太阳科技. "Web Film Defect In-line Detection and Analyze System." (http://en.sunplustech.com/ProductsStd_224.html)
- Nano-Trend Technology. "表面缺陷瑕疵檢查." (https://www.nano-trend.com/zh_TW/category/%E7%B3%BB%E7%B5%B1%E9%83%A8%E9%96%80/%E5%BD%B1%E5%83%8F%E7%BC%BA%E9%99%B7%E6%AA%A2%E6%9F%A5/%E8%A1%A8%E9%9D%A2%E7%BC%BA%E9%99%B7%E7%91%95%E7%96%B5%E6%AA%A2%E6%9F%A5/220503)
- R.K.B. Opto-Electronics. "Model 3040 OPTIMIZER." (http://rkbopto.com/rkbmedia/rkbpdf/a4/3040_a4.pdf)
- 哈工大博士论文. "基于CCD扫描的聚合物薄膜缺陷检测关键技术研究." (2009)
- 诊断报告 Section 8-9 (用户材料) — 缺陷数据描述和分类
