from fe.bench.workload import Workload
from fe.bench.workload import NewOrder
from fe.bench.workload import Payment
import time
import threading
import logging


class Session(threading.Thread):
    def __init__(self, wl: Workload):
        threading.Thread.__init__(self)
        self.workload = wl
        self.new_order_request = []
        self.payment_request = []
        self.payment_i = 0
        self.new_order_i = 0
        self.payment_ok = 0
        self.new_order_ok = 0
        self.time_new_order = 0
        self.time_payment = 0
        self.thread = None
        self.gen_procedure()

    def gen_procedure(self):
        total = self.workload.procedure_per_session
        logging.info(f"正在生成 {total} 个订单请求（每个请求需要登录）...")
        for i in range(0, total):
            new_order = self.workload.get_new_order()
            self.new_order_request.append(new_order)
            # 每生成100个请求显示一次进度
            if (i + 1) % 100 == 0 or (i + 1) == total:
                logging.info(f"已生成 {i + 1}/{total} 个订单请求 ({(i+1)*100//total}%)")
        logging.info(f"订单请求生成完成！共 {len(self.new_order_request)} 个")

    def run(self):
        logging.info(f"会话 {self.name} 开始执行，共 {len(self.new_order_request)} 个订单请求")
        self.run_gut()
        logging.info(f"会话 {self.name} 执行完成")

    def run_gut(self):
        total_requests = len(self.new_order_request)
        for idx, new_order in enumerate(self.new_order_request, 1):
            before = time.time()
            ok, order_id = new_order.run()
            after = time.time()
            self.time_new_order = self.time_new_order + after - before
            self.new_order_i = self.new_order_i + 1
            if ok:
                self.new_order_ok = self.new_order_ok + 1
                payment = Payment(new_order.buyer, order_id)
                self.payment_request.append(payment)
            # 每10个订单显示一次进度（更频繁的进度提示）
            if self.new_order_i % 10 == 0:
                logging.info(f"会话 {self.name}: 已处理订单 {self.new_order_i}/{total_requests} ({self.new_order_i*100//total_requests}%)")
            
            if self.new_order_i % 100 ==0 or self.new_order_i == len(
                self.new_order_request
            ):
                # 先处理付款
                for payment in self.payment_request:
                    before = time.time()
                    ok = payment.run()
                    after = time.time()
                    self.time_payment = self.time_payment + after - before
                    self.payment_i = self.payment_i + 1
                    if ok:
                        self.payment_ok = self.payment_ok + 1
                self.payment_request = []
                
                # 然后更新统计（此时付款已经完成）
                self.workload.update_stat(
                    self.new_order_i,
                    self.payment_i,
                    self.new_order_ok,
                    self.payment_ok,
                    self.time_new_order,
                    self.time_payment,
                )
