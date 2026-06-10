# 量化交易系统（Quant System）

基于 Python + PyQt6 开发的桌面端量化交易系统，集行情查看、策略回测、模拟交易、AI 对话于一体。

## 技术栈

- Python 3.x
- PyQt6 — 桌面 GUI 界面
- Pandas / NumPy — 数据处理
- MySQL / PyMySQL — 数据存储
- Matplotlib — 图表可视化

## 功能模块

```
quant_system/
├── main.py          # 程序入口，PyQt6 主窗口启动
├── 1.py             # 工具：生成项目目录树
├── 2.py             # 工具：CSV 分时数据批量导入 MySQL
├── api / API说明     # 数据接口 & 接口文档
├── quant_system/
│   ├── ui/          # PyQt6 界面（主窗口、菜单、面板）
│   ├── core/        # 核心引擎（策略调度、信号生成）
│   ├── backtest/    # 回测模块（历史数据回放、收益计算）
│   ├── simtrade/    # 模拟交易（虚拟下单、持仓管理）
│   ├── stock/       # 股票数据（实时行情、K线数据）
│   ├── data/        # 数据管理（本地缓存、数据库读写）
│   ├── charts/      # 图表展示（K线图、分时图、指标图）
│   ├── chat/        # AI 对话模块（智能问答、策略建议）
│   ├── services/    # 后端服务层
│   ├── config/      # 系统配置（数据库连接、参数设置）
│   ├── common/      # 公共工具（日志、工具函数）
│   ├── user/        # 用户管理（登录、权限）
│   └── login.py     # 登录窗口
```

## 快速开始

### 1. 安装依赖

```bash
pip install pyqt6 pandas numpy pymysql matplotlib
```

或使用 uv：

```bash
uv sync
```

### 2. 配置数据库

在 `quant_system/config/` 中配置 MySQL 连接信息。

### 3. 导入数据

```bash
python 2.py    # 将 cache/fenshi/ 下的 CSV 分时数据导入数据库
```

### 4. 启动系统

```bash
python main.py
```

## 项目作者

颜驿（walkeryi）

广东金融学院 · 软件工程（金融科技方向）· 2022-2026
