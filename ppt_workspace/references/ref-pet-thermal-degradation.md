# PET热降解化学机理

## 摘要
PET在加工温度（~280℃）下发生热降解和热氧化降解，主要产物包括环状三聚体（cyclic trimer，占全部环状低聚物的60-80%）和交联凝胶粒子。降解通过离子型分子内交换反应（200-300℃）和自由基反应（更高温度）两条路径进行。环状三聚体在薄膜表面结晶析出是膜点缺陷的直接成因，交联反应则形成凝胶粒子。

## 关键数据点

| # | 数据/论断 | 来源 | 可信度 |
|---|----------|------|--------|
| 1 | PET中总环状低聚物含量约1-2 wt%，其中环状三聚体占60-80% | Polymerization Byproducts研究 (J. Appl. Polym. Sci.) | 高 |
| 2 | 在200-300℃温度区间，PET主要通过离子型分子内交换反应降解，产物为环状三聚体 | Montaudo et al. (1993), Polym. Degrad. Stab. | 高 |
| 3 | 热氧化降解主要产物为环状和线性二酸低聚物，二甘醇（DEG）共聚单体是降解的"活性位点" | Romão et al. (2009), Polym. Degrad. Stab. | 高 |
| 4 | 环状三聚体在受热时从PET基体迁移至表面结晶，形成白色晶体（"whitening"缺陷） | J-STAGE "Removal of Oligomers from PET" | 高 |
| 5 | 在280℃挤出过程中，同时发生两种竞争反应：链断裂（富氧区）和交联/支化（贫氧区），后者形成凝胶粒子 | SAM-ENSAM "PET extrusion degradation" (2011) | 高 |
| 6 | 挤出机几何结构影响显著：短螺杆/大喂料口→链断裂主导；长螺杆/小料口→交联主导→凝胶增多 | SAM-ENSAM kinetic modeling study | 中 |
| 7 | PET干燥要求水分<10 ppm，15小时120℃干燥，否则水分加速水解降解（分子量急剧下降） | SAM-ENSAM extrusion study | 高 |
| 8 | 回收PET热降解速率比原生PET快约3小时（在280℃氧化条件下） | SAM-ENSAM kinetic modeling | 中 |
| 9 | 70%的PET热降解通过β-H氢转移（六元环过渡态）进行，生成带烯烃和羧酸端基的开链低聚物 | Montaudo et al. 综述 | 高 |
| 10 | PET的活化能Ea约150-200 kJ/mol（热降解），TGA积分法（Coats-Redfern, Horowitz-Metzger）常用 | 热分析文献综述 | 高 |

## 详细内容

### 降解机理分类

#### 1. 离子型分子内交换反应（200-300℃）
- 主要降解路径，在加工温度范围内占主导
- 通过酯交换反应形成**环状低聚物**
- 环状三聚体（cyclic trimer）是最主要产物，因其环结构最稳定
- 反应不需要氧气参与，纯热降解

#### 2. β-H氢转移反应（>300℃）
- 通过六元环过渡态的分子内重排
- 产物：含烯烃端基和羧酸端基的开链低聚物
- 约占PET热降解的70%

#### 3. 热氧化降解
- 在富氧条件下（如挤出机喂料口和模头处）发生
- 产物：环状和线性二酸低聚物
- 二甘醇（DEG）是降解的引发位点，释放羟基自由基
- DEG降解导致薄膜变色（喹啉型结构）

#### 4. 交联/凝胶形成
- 在**贫氧区**（挤出机中段）发生
- 导致分子量增加，形成不溶凝胶粒子
- 与挤出机几何结构和氧气分布密切相关

### 降解产物对薄膜质量的影响

| 降解产物 | 对应缺陷类型 | 影响机制 |
|---------|:-----------:|---------|
| 环状三聚体 | 膜点（film_points）、低聚物（oligomer） | 迁移至表面结晶析出，形成白点 |
| 交联凝胶粒子 | 膜点、熔斑（melt_spots） | 不熔凝胶粒子在薄膜表面形成凸点 |
| 链断裂产物 | 力学性能下降 | 分子量降低，强度/韧性下降 |
| DEG降解色素 | 薄膜变色/黄化 | 形成发色团 |

### 与诊断报告的关系

报告H1假设的核心论据：
1. film_points和oligomer在全数据集高度相关（r=0.9133），在主导等级PG31DS内仍保持中度相关（r=0.8378）
2. **两种缺陷均为PET热降解产物**——膜点对应交联凝胶粒子，低聚物对应环状三聚体
3. Arrhenius检验确认：MD段75-83℃不可能引起化学降解（速率下降10^9-10^10倍）
4. 排除MD段后，降解只能发生在挤出段（~280℃）
5. 关键缺口：无挤出段熔体温度数据直接验证

## 来源列表
- Montaudo, G., Puglisi, C., & Samperi, F. (1993). "Primary thermal degradation mechanisms of PET and PBT." *Polymer Degradation and Stability*, 42(1), 13-28.
- Romão, W., Franco, M.F., Corilo, Y.E., et al. (2009). "Poly(ethylene terephthalate) thermo-mechanical and thermo-oxidative degradation mechanisms." *Polymer Degradation and Stability*, 94(10), 1849-1859.
- SAM-ENSAM (2011). "Kinetic analysis and modelling of PET macromolecular changes during its mechanical recycling by extrusion." (https://sam.ensam.eu/handle/10985/17919)
- J-STAGE. "Removal of Oligomers from Polyethylene Terephthalate Resins by Supercritical Carbon Dioxide Extraction for Improving Properties of PET Films." (https://www.jstage.jst.go.jp/article/seikeikakou/25/11/25_547/_article)
- Lecomte, H.A. & Liggat, J.J. (2006). "Degradation mechanism of diethylene glycol units in a terephthalate polymer." *Polymer Degradation and Stability*, 91(4), 681-689.
- Hujuri, U., Ghoshal, A.K., & Gumma, S. (2013). "Temperature-dependent pyrolytic product evolution profile for PET." *J. Appl. Polym. Sci.*, 130(6), 3993-4000.
- 工业诊断报告 Section 1, 12, 13 (用户材料) — Arrhenius检验和H1论证
