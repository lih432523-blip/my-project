# 2026-10-14 测评中断诊断

本次停止是 Python 进程在 PyTorch 原生库中崩溃。没有 25 题的运行上限，也没有本次 CUDA 显存不足的证据。

Windows Application 日志：

- 时间：2026-10-14 16:48:37（北京时间）。
- 事件：Application Error，Event ID 1000；随后 Windows Error Reporting 1001。
- 应用：D:\Anaconda\envs\NLP\python.exe。
- 模块：D:\Anaconda\envs\NLP\lib\site-packages\torch\lib\c10.dll。
- 异常码：0xc0000005；偏移 0x000000000008b645。
- 报告 ID：4b6b7d96-7a73-477d-a753-a058e805ace9。

结果目录：evaluation/runs/agent55_20261014_162205_a10fcc。共 23 条完整且唯一的结果，顺序为 F01–F20、C01–C03；最后写入时间为 16:47:23。下一题为 C04（第 24/55 题）。没有结束状态和最终汇总文件，当前也没有评测 Python 进程。

23 条中 21 条 execution success=true，2 条 false；它们都是执行状态，不代表答案正确性。原先已记录的两条失败在续跑中保留。Ollama 日志最后的 chat 请求返回 HTTP 200；单凭这些证据不能确定导致 c10.dll 崩溃的是查询向量计算、重排还是其他底层调用，也不能把 C04 认定为必然触发崩溃的输入。

处理：run55.py 新增 --resume，未完成的历史结果经严格一致性校验后，在新目录保留来源并只补跑缺失题。当前保留 23 条，余下 32 条。原始元数据、题目快照和结果文件保留。每题结果同步到磁盘；metadata 记录开始与完成题号；终端输出同时保存日志，并启用 Python faulthandler。该机制用于恢复和诊断，没有宣称底层 PyTorch 故障已经修复。

验证：真实 55 题题集检查通过；使用原 23 条检查配置、内容和来源；用模拟后端验证只调用 C04 起的 32 题、最终唯一题数 55、保留两条失败及已有人工评分、初始化再次失败仍保全旧结果、拒绝配置/模型 digest 变化，以及包装脚本捕获 0xC0000005 退出码。测试没有加载模型或生成新的正式评测答案；原三个数据文件 SHA256 均未改变。

[Python 3.10 faulthandler 官方说明](https://docs.python.org/3.10/library/faulthandler.html)支持启动参数 -X faulthandler，以及 Windows 异常处理器。现有历史运行没有这样的 Python 调用栈，无法仅凭模块名称推断具体触发原因。

后续 17:42 运行在 F06 完成、F07 开始前出现 PermissionError / WinError 5，发生于 metadata.json.tmp 替换 metadata.json。该目录实际保存 F01–F06 共 6 条；abort 元数据随后成功写入，目标文件 ACL 有正常修改权限。证据符合短暂文件占用，尚未确认占用进程。此错误来自进度文件更新，与前面的 c10.dll 事件分开。

修复将 JSON 临时文件改为唯一名称，为 Windows 替换错误 5/32/33 增加 7 次尝试（退避共最多 3.15 秒）。替换持续失败时，write_metadata 保留已完整写入并 fsync 的快照，按递增 metadata_revision 恢复；所有读取入口统一读取同 run_id 的最新有效版本。真正的文件创建、写入和 fsync 错误继续报告；记录 abort 状态失败不会掩盖原始错误。旧 metadata.json.tmp 不用于该新恢复协议。

测试在独立临时目录进行：真实 Windows 句柄禁止替换后延时解锁，验证自动重试；持续锁验证读取恢复快照和之后回到主文件；模拟磁盘满验证仍抛出原始错误；模拟整个续跑阶段持续锁验证仅调用 C04 起 32 题、最终 55 条、旧两条失败保留且生成汇总。没有加载模型；旧 23 题与新 6 题的 metadata.json/results.jsonl 哈希均未改变。这修复了元数据锁导致的中断，没有宣称修复此前 PyTorch 底层崩溃。
