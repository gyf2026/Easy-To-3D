# Easy-To-3D 开发约定

独立开发目录。禁止改写或运行依赖同级 EasyTo3D 历史项目。设计边界见 docs/decisions.md；完整开发计划保存在维护者本地工作区。

发布产物与脚本、需求快照不可变；新修改创建工作区和子版本。评审按版本隔离，原文和事件保留。坐标显式 mm/Z-up、右手系、矩阵 row-major，禁止根据数值猜单位。程序不解读自然语言修改语义。

完整功能测试和原始验证证据单独维护，不随公开源码分发；以下命令仅适用于有完整测试文件的本地开发工作区。核心逻辑测试：PYTHONPATH=core python3 -m unittest discover -s tests -v。真实浏览器：PYTHONPATH=core python3 tools/run_browser_tests.py。真实后端测试与合成夹具分开，不以代码字符串检查替代行为。用户确认、检查通过、执行成功分别记录。

不得将未知本机或客户端兼容性写成已支持。缺少实际证据的指标保持 unknown。本地实施过程记录于被忽略的 docs/status.md；对外支持范围更新 docs/compatibility.md。代码采用Apache-2.0许可证。
