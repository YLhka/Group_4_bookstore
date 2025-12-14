# script/cancel_timeout.py
"""
自动取消超时未支付的订单
"""

from be.model.order import Order

# 超时时间，秒
TIMEOUT_SECONDS = 15 * 60  # 15分钟

def main():
    om = Order()
    n = om.cancel_timeout_orders(timeout_seconds=TIMEOUT_SECONDS)
    print(f"canceled {n} timeout orders.")

if __name__ == "__main__":
    main()
