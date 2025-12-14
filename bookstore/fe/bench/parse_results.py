"""
从性能测试日志中解析结果并生成报告
"""
import os
import sys

# 添加项目根目录到 Python 路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import re
from datetime import datetime

def parse_log_file(log_file):
    """解析日志文件，提取性能指标"""
    results = []
    
    if not os.path.exists(log_file):
        print(f"日志文件不存在: {log_file}")
        return None
    
    # 尝试匹配TPS_C格式
    pattern = re.compile(
        r'TPS_C=(\d+),\s*NO=OK:(\d+)\s+Thread_num:(\d+)\s+TOTAL:(\d+)\s+LATENCY:([\d.]+)\s*,\s*P=OK:(\d+)\s+Thread_num:(\d+)\s+TOTAL:(\d+)\s+LATENCY:([\d.]+)'
    )
    
    # 如果没有找到TPS_C，尝试从日志中提取基本信息
    test_info = {
        'total_orders': 0,
        'total_payments': 0,
        'total_time': 0,
        'sessions': 0
    }
    
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            # 尝试匹配TPS_C
            match = pattern.search(line)
            if match:
                result = {
                    'tps': int(match.group(1)),
                    'no_ok': int(match.group(2)),
                    'no_thread_num': int(match.group(3)),
                    'no_total': int(match.group(4)),
                    'no_latency': float(match.group(5)),
                    'p_ok': int(match.group(6)),
                    'p_thread_num': int(match.group(7)),
                    'p_total': int(match.group(8)),
                    'p_latency': float(match.group(9))
                }
                results.append(result)
            
            # 提取测试配置信息
            if '总请求数:' in line:
                match = re.search(r'总请求数:\s*(\d+)', line)
                if match:
                    test_info['total_orders'] = int(match.group(1))
            if '并发会话数:' in line:
                match = re.search(r'并发会话数:\s*(\d+)', line)
                if match:
                    test_info['sessions'] = int(match.group(1))
            if '已处理订单' in line and '100%' in line:
                match = re.search(r'已处理订单\s+(\d+)/(\d+)', line)
                if match:
                    test_info['total_orders'] = max(test_info['total_orders'], int(match.group(2)))
    
    # 如果没有找到TPS_C结果，但找到了测试信息，返回一个基本结果
    if not results and test_info['total_orders'] > 0:
        print("⚠️  警告：日志中没有找到TPS_C性能指标")
        print("   这可能是因为测试配置较小（请求数少于100）或测试逻辑未满足输出条件")
        print(f"   测试信息：总请求数={test_info['total_orders']}, 会话数={test_info['sessions']}")
        print("   建议：增加 Request_Per_Session 到至少1000来获得详细的性能指标")
        return None
    
    return results if results else None


def generate_report(results, output_file):
    """生成性能测试报告"""
    if not results:
        print("没有找到有效的性能测试结果")
        return
    
    # 计算统计信息
    tps_values = [r['tps'] for r in results]
    avg_tps = sum(tps_values) / len(tps_values) if tps_values else 0
    max_tps = max(tps_values) if tps_values else 0
    min_tps = min(tps_values) if tps_values else 0
    
    # 最后一条记录
    final = results[-1]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("性能测试结果报告\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"采样次数: {len(results)}\n")
        f.write(f"\n")
        f.write("-" * 60 + "\n")
        f.write("性能指标汇总\n")
        f.write("-" * 60 + "\n")
        f.write(f"平均吞吐量 (TPS): {avg_tps:.2f}\n")
        f.write(f"最大吞吐量 (TPS): {max_tps:.2f}\n")
        f.write(f"最小吞吐量 (TPS): {min_tps:.2f}\n")
        f.write(f"\n")
        f.write(f"订单创建:\n")
        f.write(f"  - 成功数: {final['no_ok']}\n")
        f.write(f"  - 总数: {final['no_total']}\n")
        success_rate_no = final['no_ok'] / final['no_total'] * 100 if final['no_total'] > 0 else 0
        f.write(f"  - 成功率: {success_rate_no:.2f}%\n")
        f.write(f"  - 平均延迟: {final['no_latency']:.4f} 秒\n")
        f.write(f"\n")
        f.write(f"订单付款:\n")
        f.write(f"  - 成功数: {final['p_ok']}\n")
        f.write(f"  - 总数: {final['p_total']}\n")
        success_rate_p = final['p_ok'] / final['p_total'] * 100 if final['p_total'] > 0 else 0
        f.write(f"  - 成功率: {success_rate_p:.2f}%\n")
        f.write(f"  - 平均延迟: {final['p_latency']:.4f} 秒\n")
        f.write(f"\n")
        f.write("=" * 60 + "\n")
        f.write("详细数据（每次采样）\n")
        f.write("=" * 60 + "\n")
        for i, result in enumerate(results, 1):
            f.write(f"\n采样 #{i}:\n")
            f.write(f"  TPS: {result['tps']}\n")
            f.write(f"  订单创建: {result['no_ok']}/{result['no_total']}, 延迟: {result['no_latency']:.4f}s, 并发: {result['no_thread_num']}\n")
            f.write(f"  订单付款: {result['p_ok']}/{result['p_total']}, 延迟: {result['p_latency']:.4f}s, 并发: {result['p_thread_num']}\n")
    
    print(f"报告已生成: {output_file}")
    print(f"\n汇总信息:")
    print(f"  平均TPS: {avg_tps:.2f}")
    print(f"  最大TPS: {max_tps}")
    print(f"  最小TPS: {min_tps}")
    print(f"  订单创建成功率: {success_rate_no:.2f}%")
    print(f"  订单付款成功率: {success_rate_p:.2f}%")


def main():
    import sys
    import glob
    
    # 查找最新的日志文件
    log_dir = os.path.dirname(os.path.abspath(__file__))
    log_files = glob.glob(os.path.join(log_dir, "benchmark_*.log"))
    
    if not log_files:
        print("未找到性能测试日志文件")
        print("请先运行性能测试: python fe/bench/run.py")
        return
    
    # 使用最新的日志文件
    latest_log = max(log_files, key=os.path.getctime)
    print(f"解析日志文件: {latest_log}")
    
    results = parse_log_file(latest_log)
    
    if results:
        output_file = latest_log.replace('.log', '_parsed_results.txt')
        generate_report(results, output_file)
    else:
        print("未能从日志中解析出性能测试结果")
        print("请确保日志文件包含格式为 'TPS_C=XXX, NO=OK:XXX ...' 的行")


if __name__ == "__main__":
    main()

