# PotatoTool 资源自动更新系统

自动化更新 PotatoTool 的 JAR 文件和资源文件，并推送到 GitHub。

## 📁 目录结构

```
ResourceUpload/
├── README.md           # 项目说明
├── manifest.json       # 资源清单配置文件
├── .gitignore         
│
├── scripts/            # 脚本文件目录
│   ├── auto_update.py              # 主自动化更新脚本 ⭐
│   ├── upload_to_release.py        # 上传到Release脚本
│   │
│   ├── run_auto_update.sh          # macOS/Linux 运行脚本
│   ├── setup_cron.sh               # macOS/Linux 定时任务设置
│   │
│   ├── run_auto_update.bat         # Windows 批处理脚本
│   ├── run_auto_update.ps1         # Windows PowerShell 脚本
│   └── setup_task_scheduler.ps1    # Windows 任务计划程序设置
│
└── data/               # 数据文件目录
    ├── winKbInfo20250214.csv
    └── winKbInfo.zip
```

## 🔧 脚本说明

### 核心脚本

- **`auto_update.py`** - 主程序，执行完整的自动化更新流程
  - 从 PotatoTool/outJar 读取最新 JAR 文件信息（不复制文件）
  - 自动检测资源变化，无变化时跳过更新
  - 计算文件校验和（SHA256 + MD5）
  - 更新 Windows KB 补丁信息（保存到 data/）
  - 生成 manifest.json（仅当资源有变化时）
  - 提交 manifest.json 和 data/ 到 GitHub（不包含 JAR 文件）

- **`test_auto_update.py`** - 测试脚本，验证各模块功能

- **`upload_to_release.py`** - 上传文件到 GitHub Release

### macOS/Linux 脚本

- **`run_auto_update.sh`** - Shell 包装脚本，用于定时任务
- **`setup_cron.sh`** - 交互式设置 crontab 定时任务

### Windows 脚本

- **`run_auto_update.bat`** - 批处理包装脚本，用于定时任务
- **`run_auto_update.ps1`** - PowerShell 包装脚本（推荐）
- **`setup_task_scheduler.ps1`** - 交互式设置 Windows 任务计划程序

## 🚀 快速开始

### macOS / Linux

```bash
# 1. 测试
python3 scripts/test_auto_update.py

# 2. 手动运行
python3 scripts/auto_update.py

# 3. 设置定时任务
./scripts/setup_cron.sh
```

### Windows

```powershell
# 1. 测试
python scripts/test_auto_update.py

# 2. 手动运行
python scripts/auto_update.py

# 3. 设置定时任务（以管理员身份运行 PowerShell）
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\setup_task_scheduler.ps1
```

## ⚙️ 配置

编辑 `scripts/auto_update.py` 修改配置：

```python
CONFIG = {
    'jar_source_dir': '/Users/a/Desktop/项目开发/PotatoTool/outJar',  # JAR 源目录
    'work_dir': os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # 工作目录（自动）
    'github_release_base': 'https://github.com/HotBoy-java/PotatoTool/releases/download',
    'mirror_base': 'http://potato.gold:16668/releases',
    'resource_mirror_base': 'http://potato.gold:16668/resources',
}
```

## 📊 工作流程

1. 查找最新 JAR 文件（jdk8 和 jdk11+ 版本） - 只读取信息，不复制
2. 更新 Windows KB 补丁信息 → 保存到 `data/winKbInfo.csv`
3. 检测 MD5 数据库（如果存在） - 从 `data/` 目录
4. **检查资源变化** - 对比旧 manifest.json
   - ✅ 有变化 → 继续更新
   - ⏭️ 无变化 → 跳过更新，避免无意义的提交
5. 生成 manifest.json（仅当有变化时）
6. 提交到 Git（`manifest.json` + `data/`）
7. 记录日志

## 📁 文件组织

- **JAR 文件**: 保留在 `PotatoTool/outJar`，不复制、不提交
- **数据文件**: 统一存储在 `data/` 目录，随 Git 提交
- **配置文件**: `manifest.json` 在项目根目录，包含所有资源信息

## 📝 日志查看

**macOS/Linux:**
```bash
tail -f auto_update.log
```

**Windows:**
```powershell
Get-Content auto_update.log -Tail 50
```