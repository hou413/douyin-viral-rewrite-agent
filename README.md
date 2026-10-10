# 抖音爆款改写Agent

自动化采集抖音爆款视频 → AI分析爆款因子 → 生成原创文案 → 质量评估筛选

## 🏗️ 架构

```
定时触发 / 手动触发
    ↓
[1] 爆款采集模块 → 根据关键词采集热门视频
    ↓
[2] 爆款筛选模块 → 按互动数据筛选 + 去重
    ↓
[3] 文案提取模块 → 提取字幕、标题、评论
    ↓
[4] AI分析模块 → 拆解钩子、痛点、结构、转化逻辑
    ↓
[5] AI创作模块 → 结合目标用户+产品卖点，生成多版文案
    ↓
[6] 质量评估模块 → 吸引力/相关性/原创性评分
    ↓
[7] 结果输出模块 → 飞书文档 / 本地文案库 / 分析报告
```

## 📦 安装

```bash
# 1. 克隆项目
cd douyin-viral-rewrite-agent

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt
```

## ⚙️ 配置

编辑 `config/settings.yaml`：

```yaml
# 采集配置
collector:
  method: "scraper"  # api / scraper / control_screen
  douyin_cookie: "你的Cookie"  # scraper模式需要

# 筛选阈值
filter:
  time_range_days: 7
  min_play_count: 100000
  min_like_count: 10000

# AI配置
ai:
  provider: "dashscope"  # openai / dashscope / local
  model: "qwen-plus"
  api_key: "sk-xxx"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 输出配置
output:
  mode: "both"  # feishu / local / both
  feishu:
    app_id: "cli_xxx"
    app_secret: "xxx"
    bitable_app_token: "xxx"
```

## 🚀 使用

### 单次运行

```bash
python main.py \
  --keywords "机器人,具身智能,AI Agent" \
  --audience "科技爱好者、创业者" \
  --product "XX智能机器人，主打家庭陪伴"
```

### 定时运行

```bash
python main.py \
  --keywords "机器人,具身智能" \
  --audience "科技爱好者" \
  --product "XX机器人" \
  --schedule \
  --schedule-time "10:00"
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--config` | 配置文件路径 | `config/settings.yaml` |
| `--keywords` | 关键词，逗号分隔 | 必填 |
| `--audience` | 目标受众描述 | `科技爱好者` |
| `--product` | 产品信息/卖点 | 空 |
| `--schedule` | 启用定时模式 | False |
| `--schedule-time` | 定时执行时间 | `10:00` |

## 📁 项目结构

```
douyin-viral-rewrite-agent/
├── main.py                    # 主入口
├── config/
│   └── settings.yaml          # 配置文件
├── src/
│   ├── collectors/            # 采集模块
│   │   └── douyin_collector.py
│   ├── filters/               # 筛选模块
│   │   └── viral_filter.py
│   ├── extractors/            # 提取模块
│   │   └── content_extractor.py
│   ├── analyzers/             # 分析模块
│   │   └── viral_analyzer.py
│   ├── creators/              # 创作模块
│   │   └── content_creator.py
│   ├── evaluators/            # 评估模块
│   │   └── quality_evaluator.py
│   ├── outputs/               # 输出模块
│   │   ├── output_manager.py
│   │   └── feishu_client.py
│   └── pipeline.py            # 流程编排
├── prompts/                   # AI提示词模板
│   ├── analysis_prompt.md
│   ├── creation_prompt.md
│   └── evaluation_prompt.md
├── data/                      # 数据输出目录
├── logs/                      # 日志目录
└── requirements.txt
```

## 🔧 模块说明

### 1. 爆款采集模块
- 支持3种采集方式：API、爬虫、控屏
- 根据关键词+时间范围搜索
- 采集视频基础数据和互动数据

### 2. 爆款筛选模块
- 按播放量、点赞、评论、转发阈值筛选
- 基于标题相似度去重
- 输出候选爆款视频库

### 3. 文案提取模块
- ASR语音识别提取字幕
- 提取标题、标签、评论
- 结构化存储视频内容

### 4. AI分析模块
- 拆解开头钩子模式
- 识别用户痛点
- 分析内容结构和转化逻辑
- 提取爆款因子

### 5. AI创作模块
- 结合目标用户画像
- 融入产品卖点
- 生成多版不同风格文案
- 自动添加话题标签

### 6. 质量评估模块
- 吸引力评分（0-100）
- 相关性评分（0-100）
- 原创性评分（0-100）
- 自动筛选 + 优化建议

### 7. 结果输出模块
- 保存到飞书多维表格
- 本地JSON + Markdown报告
- 每日爆款分析总结

## 📊 输出示例

运行后在 `data/output/` 生成：

```
output/
├── 2024-01-15_scripts.json    # 文案数据
├── 2024-01-15_report.md       # 分析报告
└── latest/
    ├── scripts.json
    └── report.md
```

报告包含：
- 执行摘要（采集/筛选/创作数量）
- 爆款因子分析
- 钩子模式总结
- 用户痛点洞察
- 创作文案（按评分排序）
- 优化建议

## ⚠️ 注意事项

1. **抖音Cookie**：scraper模式需要登录后的Cookie，定期更新
2. **频率控制**：避免高频请求，建议每次间隔2秒+
3. **API配额**：dashscope/openai有调用限制，注意成本
4. **内容合规**：AI生成内容需人工审核后再发布
5. **数据隐私**：不要将敏感信息写入日志

## 🛠️ 开发

```bash
# 安装开发依赖
pip install -r requirements.txt
pip install black isort mypy

# 代码格式化
black src/
isort src/

# 类型检查
mypy src/
```

## 📝 License

MIT
