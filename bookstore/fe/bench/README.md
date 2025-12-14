# 性能测试使用说明

## 快速开始

### 1. 启动后端服务器

在第一个终端窗口：
```bash
python be/app.py
```

### 2. 运行性能测试

在第二个终端窗口：
```bash
# 方法1：直接运行（推荐）
python fe/bench/run.py

# 方法2：使用模块方式运行
python -m fe.bench.run
```

### 3. 查看和解析结果

测试完成后，运行：
```bash
python fe/bench/parse_results.py
```

这会自动查找最新的日志文件并生成报告。

## 输出文件

- **日志文件**: `benchmark_YYYYMMDD_HHMMSS.log` - 包含所有测试输出
- **结果报告**: `benchmark_YYYYMMDD_HHMMSS_parsed_results.txt` - 解析后的性能指标报告

## 配置测试参数

编辑 `fe/conf.py` 来调整测试参数：
- `Session`: 并发会话数（默认 1）
- `Request_Per_Session`: 每会话请求数（默认 1000）
- `Seller_Num`: 卖家数量（默认 2）
- `Buyer_Num`: 买家数量（默认 10）

## 性能指标说明

- **TPS_C**: 吞吐量（每秒完成的订单数）
- **NO=OK / NO_TOTAL**: 订单创建成功数 / 总数
- **P=OK / P_TOTAL**: 订单付款成功数 / 总数
- **LATENCY**: 平均延迟（秒）

## 注意事项

1. **确保后端服务器正在运行**（最重要！）
   ```bash
   # 检查服务器是否运行
   python fe/bench/check_server.py
   
   # 如果未运行，启动服务器
   python be/app.py
   ```

2. 确保 MongoDB 正在运行

3. **确保所有索引已创建**（重要！性能测试反映的是索引优化后的性能）
   ```bash
   # 创建索引
   python script/init_indexes.py
   
   # 验证索引是否创建成功
   python script/verify_indexes.py
   ```

4. **测试数据加载可能需要较长时间**：
   - 默认配置：2个卖家 × 2个店铺 × 2000本书 = 8000次HTTP请求
   - 如果觉得太慢，可以临时修改 `fe/conf.py` 中的 `Book_Num_Per_Store` 为较小的值（如 100）

5. 测试会产生大量测试数据，测试后可以清理 MongoDB 数据库

## 查看历史结果

所有测试结果都保存在 `fe/bench/` 目录下，可以查看历史日志文件。

