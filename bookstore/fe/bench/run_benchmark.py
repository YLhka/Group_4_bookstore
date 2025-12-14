"""
性能测试运行脚本
运行此脚本进行性能测试并保存结果
"""
import os
import sys
import time
import logging
from datetime import datetime
from fe.bench.run import run_bench
from fe import conf

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fe", "bench")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class BenchmarkResult:
    """性能测试结果收集器"""
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
        
    def record(self, tps, no_ok, no_total, no_latency, p_ok, p_total, p_latency, thread_num):
        """记录一次性能指标"""
        self.results.append({
            'tps': tps,
            'no_ok': no_ok,
            'no_total': no_total,
            'no_latency': no_latency,
            'p_ok': p_ok,
            'p_total': p_total,
            'p_latency': p_latency,
            'thread_num': thread_num,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_summary(self):
        """获取汇总统计"""
        if not self.results:
            return None
            
        total_results = len(self.results)
        avg_tps = sum(r['tps'] for r in self.results) / total_results if total_results > 0 else 0
        max_tps = max(r['tps'] for r in self.results) if self.results else 0
        min_tps = min(r['tps'] for r in self.results) if self.results else 0
        
        # 最后一条记录包含最终统计
        final = self.results[-1] if self.results else {}
        
        return {
            'total_samples': total_results,
            'avg_tps': avg_tps,
            'max_tps': max_tps,
            'min_tps': min_tps,
            'final_no_ok': final.get('no_ok', 0),
            'final_no_total': final.get('no_total', 0),
            'final_p_ok': final.get('p_ok', 0),
            'final_p_total': final.get('p_total', 0),
            'final_no_latency': final.get('no_latency', 0),
            'final_p_latency': final.get('p_latency', 0),
            'test_duration': (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0
        }


# 全局结果收集器
benchmark_result = BenchmarkResult()

def save_results_to_file(result_obj, log_file):
    """保存测试结果到文件"""
    summary = result_obj.get_summary()
    if not summary:
        logging.warning("没有收集到性能测试结果")
        return
    
    result_file = log_file.replace('.log', '_results.txt')
    
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("性能测试结果报告\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"测试配置:\n")
        f.write(f"  - 卖家数量: {conf.Seller_Num}\n")
        f.write(f"  - 买家数量: {conf.Buyer_Num}\n")
        f.write(f"  - 并发会话数: {conf.Session}\n")
        f.write(f"  - 每会话请求数: {conf.Request_Per_Session}\n")
        f.write(f"  - 每店铺书籍数: {conf.Book_Num_Per_Store}\n")
        f.write(f"\n")
        f.write(f"测试总时长: {summary['test_duration']:.2f} 秒\n")
        f.write(f"采样次数: {summary['total_samples']}\n")
        f.write(f"\n")
        f.write("-" * 60 + "\n")
        f.write("性能指标汇总\n")
        f.write("-" * 60 + "\n")
        f.write(f"平均吞吐量 (TPS): {summary['avg_tps']:.2f}\n")
        f.write(f"最大吞吐量 (TPS): {summary['max_tps']:.2f}\n")
        f.write(f"最小吞吐量 (TPS): {summary['min_tps']:.2f}\n")
        f.write(f"\n")
        f.write(f"订单创建:\n")
        f.write(f"  - 成功数: {summary['final_no_ok']}\n")
        f.write(f"  - 总数: {summary['final_no_total']}\n")
        f.write(f"  - 成功率: {summary['final_no_ok']/summary['final_no_total']*100:.2f}%\n" if summary['final_no_total'] > 0 else "  - 成功率: N/A\n")
        f.write(f"  - 平均延迟: {summary['final_no_latency']:.4f} 秒\n")
        f.write(f"\n")
        f.write(f"订单付款:\n")
        f.write(f"  - 成功数: {summary['final_p_ok']}\n")
        f.write(f"  - 总数: {summary['final_p_total']}\n")
        f.write(f"  - 成功率: {summary['final_p_ok']/summary['final_p_total']*100:.2f}%\n" if summary['final_p_total'] > 0 else "  - 成功率: N/A\n")
        f.write(f"  - 平均延迟: {summary['final_p_latency']:.4f} 秒\n")
        f.write(f"\n")
        f.write("=" * 60 + "\n")
        f.write("详细数据（每次采样）\n")
        f.write("=" * 60 + "\n")
        for i, result in enumerate(result_obj.results, 1):
            f.write(f"\n采样 #{i}:\n")
            f.write(f"  TPS: {result['tps']}\n")
            f.write(f"  订单创建: {result['no_ok']}/{result['no_total']}, 延迟: {result['no_latency']:.4f}s\n")
            f.write(f"  订单付款: {result['p_ok']}/{result['p_total']}, 延迟: {result['p_latency']:.4f}s\n")
            f.write(f"  并发数: {result['thread_num']}\n")
    
    logging.info(f"测试结果已保存到: {result_file}")
    return result_file


def main():
    """主函数"""
    logging.info("=" * 60)
    logging.info("开始性能测试")
    logging.info("=" * 60)
    logging.info(f"测试配置:")
    logging.info(f"  - 卖家数量: {conf.Seller_Num}")
    logging.info(f"  - 买家数量: {conf.Buyer_Num}")
    logging.info(f"  - 并发会话数: {conf.Session}")
    logging.info(f"  - 每会话请求数: {conf.Request_Per_Session}")
    logging.info(f"  - 每店铺书籍数: {conf.Book_Num_Per_Store}")
    logging.info(f"日志文件: {log_file}")
    logging.info("=" * 60)
    
    benchmark_result.start_time = datetime.now()
    
    try:
        # 运行性能测试
        # 注意：这里需要修改 workload.py 来收集结果
        # 暂时先运行测试，结果会输出到日志
        run_bench()
        
        benchmark_result.end_time = datetime.now()
        
        logging.info("=" * 60)
        logging.info("性能测试完成")
        logging.info("=" * 60)
        
        # 尝试从日志中解析结果（如果实现了结果收集）
        # 目前先保存基本信息
        if benchmark_result.results:
            save_results_to_file(benchmark_result, log_file)
        else:
            logging.info("提示：性能测试结果已输出到日志，请查看日志文件获取详细结果")
            logging.info(f"日志文件: {log_file}")
        
    except Exception as e:
        logging.error(f"性能测试失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

