import os
import sys

# 添加项目根目录到 Python 路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fe.bench.workload import Workload
from fe.bench.session import Session


def run_bench():
    import logging
    
    wl = Workload()
    
    wl.gen_database()

    logging.info("=" * 60)
    logging.info("开始性能测试")
    logging.info(f"并发会话数: {wl.session}")
    logging.info(f"每会话请求数: {wl.procedure_per_session}")
    logging.info(f"总请求数: {wl.session * wl.procedure_per_session}")
    logging.info("=" * 60)

    sessions = []
    for i in range(0, wl.session):
        logging.info(f"创建会话 {i+1}/{wl.session}...")
        logging.info("注意：生成订单请求需要多次登录，可能需要一些时间...")
        ss = Session(wl)
        sessions.append(ss)
        logging.info(f"会话 {i+1} 创建完成！")

    logging.info("启动所有会话...")
    for i, ss in enumerate(sessions):
        logging.info(f"启动会话 {i+1}/{len(sessions)}")
        ss.start()

    logging.info("等待所有会话完成...")
    for i, ss in enumerate(sessions):
        ss.join()
        logging.info(f"会话 {i+1}/{len(sessions)} 已完成")
    
    logging.info("=" * 60)
    logging.info("性能测试完成！")
    logging.info("=" * 60)


if __name__ == "__main__":
    import logging
    from datetime import datetime
    
    # 配置日志：同时输出到控制台和文件
    log_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(log_dir, f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # 创建日志格式
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # 配置日志：同时输出到文件和控制台
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info(f"日志文件: {log_file}")
    run_bench()
    logging.info(f"测试完成，日志已保存到: {log_file}")
