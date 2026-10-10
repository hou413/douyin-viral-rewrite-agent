#!/usr/bin/env python3
"""
抖音爆款改写Agent - 主入口

用法:
    python main.py --keywords "机器人,具身智能" --audience "科技爱好者" --product "XX机器人"
    python main.py --config config/settings.yaml --schedule  # 定时模式
"""
import argparse
import sys
import time
from pathlib import Path
from typing import List

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline import Pipeline, PipelineResult


def parse_keywords(keywords_str: str) -> List[str]:
    """解析关键词字符串"""
    return [k.strip() for k in keywords_str.split(",") if k.strip()]


def print_result(result: PipelineResult):
    """打印执行结果摘要"""
    print("\n" + "=" * 60)
    print("📊 执行结果摘要")
    print("=" * 60)
    print(f"状态: {'✅ 成功' if result.success else '❌ 失败'}")
    print(f"关键词: {', '.join(result.keywords)}")
    print(f"耗时: {result.duration_seconds:.1f}秒")
    print("-" * 40)
    print(f"采集视频: {result.collected_count}")
    print(f"筛选爆款: {result.filtered_count}")
    print(f"提取内容: {result.extracted_count}")
    print(f"创作文案: {result.created_count}")
    print(f"通过评估: {result.passed_count}")
    print("-" * 40)

    if result.output_paths:
        print("输出文件:")
        for key, path in result.output_paths.items():
            print(f"  {key}: {path}")

    if result.error:
        print(f"\n⚠️ 错误: {result.error}")

    print("=" * 60)


def run_once(args):
    """单次运行模式"""
    keywords = parse_keywords(args.keywords)
    if not keywords:
        print("❌ 请提供至少一个关键词")
        sys.exit(1)

    print(f"🚀 启动抖音爆款改写Agent")
    print(f"关键词: {keywords}")
    print(f"目标受众: {args.audience}")
    print(f"产品信息: {args.product}")
    print("-" * 40)

    pipeline = Pipeline(config_path=args.config)
    result = pipeline.run(
        keywords=keywords,
        target_audience=args.audience,
        product_info=args.product,
    )

    print_result(result)
    sys.exit(0 if result.success else 1)


def run_schedule(args):
    """定时运行模式"""
    try:
        import schedule
    except ImportError:
        print("❌ 定时模式需要安装 schedule: pip install schedule")
        sys.exit(1)

    keywords = parse_keywords(args.keywords)
    if not keywords:
        print("❌ 请提供至少一个关键词")
        sys.exit(1)

    pipeline = Pipeline(config_path=args.config)

    def job():
        print(f"\n🕐 [{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始定时执行...")
        result = pipeline.run(
            keywords=keywords,
            target_audience=args.audience,
            product_info=args.product,
        )
        print_result(result)

    # 从配置读取cron或默认每天10:00
    schedule_time = args.schedule_time or "10:00"
    schedule.every().day.at(schedule_time).do(job)

    print(f"⏰ 定时任务已启动 | 每天 {schedule_time} 执行")
    print(f"关键词: {keywords}")
    print("按 Ctrl+C 停止...")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n👋 定时任务已停止")


def main():
    parser = argparse.ArgumentParser(
        description="抖音爆款改写Agent - 自动采集爆款视频并AI改写文案",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --keywords "机器人,具身智能" --audience "科技爱好者" --product "XX机器人"
  python main.py --keywords "AI Agent" --audience "开发者" --product "OpenClaw" --schedule
        """,
    )

    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="配置文件路径 (默认: config/settings.yaml)",
    )
    parser.add_argument(
        "--keywords",
        required=True,
        help="关键词，多个用逗号分隔 (例: '机器人,具身智能,AI')",
    )
    parser.add_argument(
        "--audience",
        default="科技爱好者",
        help="目标受众描述 (默认: 科技爱好者)",
    )
    parser.add_argument(
        "--product",
        default="",
        help="产品信息/卖点描述",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="启用定时模式",
    )
    parser.add_argument(
        "--schedule-time",
        default="10:00",
        help="定时执行时间 (默认: 10:00)",
    )

    args = parser.parse_args()

    if args.schedule:
        run_schedule(args)
    else:
        run_once(args)


if __name__ == "__main__":
    main()
