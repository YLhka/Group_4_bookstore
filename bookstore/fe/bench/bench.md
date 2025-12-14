# 性能测试说明

## 性能测试概述

本项目实现了基于 MongoDB 的网上书店系统，为了验证系统在高并发场景下的性能表现，以及索引优化带来的性能提升，我们实现了性能基准测试（Benchmark）。

## 测试方法

### 1. 测试场景

性能测试主要模拟以下场景：
- **下单操作**：买家在店铺中创建订单
- **付款操作**：买家对已创建的订单进行付款

### 2. 测试配置

测试配置在 `fe/conf.py` 中设置：
- `Seller_Num`: 卖家数量
- `Buyer_Num`: 买家数量
- `Session`: 并发会话数
- `Request_Per_Session`
- `Book_Num_Per_Store`

### 3. 性能指标

测试会输出以下性能指标：

- **TPS_C (Throughput)**: 吞吐量，单位时间内成功完成的订单数量
  - 计算公式：成功创建订单数量 / (提交订单时间/并发数 + 提交付款订单时间/并发数)

- **LATENCY (延迟)**: 平均响应时间
  - 订单延迟：创建订单所用时间 / 订单数量
  - 付款延迟：付款所用时间 / 付款订单数量

- **成功率**: 
  - 订单创建成功率 = 成功创建订单数 / 总订单数
  - 付款成功率 = 成功付款数 / 总付款数

## 运行性能测试

### 方法1：直接运行性能测试脚本（推荐）

```bash
# 确保后端服务器正在运行（在另一个终端运行）
python be/app.py

# 运行性能测试
python fe/bench/run.py

# 解析测试结果（从日志中提取并生成报告）
python fe/bench/parse_results.py
```

测试结果会保存在：
- 日志文件: `fe/bench/benchmark_YYYYMMDD_HHMMSS.log`
- 解析后的报告: `fe/bench/benchmark_YYYYMMDD_HHMMSS_parsed_results.txt`


**注意**：测试结果会输出到日志文件，可以使用 `parse_results.py` 脚本解析并生成可读的报告。

## 索引优化对性能的影响

### 已建立的索引

1. **books 集合**
   - `id` 唯一索引：快速查找指定书籍
   - `title` 索引：优化书名搜索
   - `author` 索引：优化作者搜索
   - 全文索引：优化多字段全文搜索（title, author, book_intro, tags）

2. **store_books 集合**
   - `(store_id, book_id)` 复合唯一索引：下单时 O(1) 查找库存和价格
   - `title` 索引：优化店铺内书籍搜索

3. **orders 集合**
   - `order_id` 唯一索引：快速查找订单
   - `buyer_id` 索引：优化"我的订单"查询
   - `status` 索引：快速筛选订单状态
   - `created_time` 索引：优化超时订单查询

4. **order_items 集合**
   - `order_id` 索引：快速获取订单明细

5. **users 集合**
   - `user_id` 唯一索引：快速查找用户信息

6. **stores 集合**
   - `store_id` 唯一索引：快速查找店铺
   - `user_id` 索引：优化店铺所有者查询

## 性能优化
1. **索引维护**：定期检查索引使用情况，删除未使用的索引
2. **查询优化**：使用 `explain()` 分析慢查询，优化查询语句
3. **连接池**：使用 MongoDB 连接池减少连接开销
4. **分片**：数据量很大时考虑 MongoDB 分片
