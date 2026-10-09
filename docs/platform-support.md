# macOS 与 Windows 核心适配

当前目标：macOS 与 Windows 10/11，Python 3.10 及以上。macOS 有本机运行证据；Windows 10 AMD64 / Python3.12.10 实机已完成97项核心测试与浏览器检查，Blender4.5.10原生工作流通过。FreeCAD1.1.4中文脚本路径失败，修正后的完整工作流须在该机复测；Windows11、其他架构与Python版本未推定兼容。

- 协议、文件清单、绘图索引与 HTTP 资源路径统一使用 `/` 相对路径；本机文件访问由 pathlib 转换。项目可以搬迁，保存原有 ID 与哈希。
- 原子 JSON、发布、整项目备份和交付目录不依赖 POSIX 命令。文件锁分别用 fcntl 与 Windows msvcrt，跨进程冲突有真实行为测试。
- macOS 使用进程组清理及启动时间/所属用户校验。Windows 使用 ctypes 封装原生 Job Objects，启动器进入 Job 后才放行建模命令，防止分配前产生子进程；取消、超时、正常退出和控制器崩溃均关闭/结束 Job。恢复绑定 PID、进程创建时间和独立 Job 名称，身份无法验证时拒绝随意清理。
- Windows Job 行为依据 [Microsoft Job Objects 文档](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)，结构布局依据 [JOBOBJECT_EXTENDED_LIMIT_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)。这些 API 不可代替真实 Windows 验收。
- doctor 支持 PATH、用户提供的可执行路径和 Windows ProgramFiles/LOCALAPPDATA 中的常见 FreeCAD/Blender 安装位置。实际探测仍分别记录找到、启动、脚本/导出结果。
- 浏览器依赖可配置；测试默认使用所安装 Playwright 的浏览器，不再内置开发者的 macOS 路径。使用者无需 Node/npm。

`.github/workflows/core-platforms.yml` 对macOS/Windows × Python3.10/3.14进行构建、安装与CLI启动检查。测试源码按维护者要求仅在本地保留，不纳入Git；因此该公开工作流不执行完整功能测试，也不能作为后端兼容性通过证据。尚未有远程运行记录。

Windows FreeCAD1.1.4实测不能直接接收含中文的脚本argv路径，ASCII脚本与中文工作目录的对照正常。产品的受控run针对FreeCADCmd生成每次执行独立的ASCII相对入口，通过嵌入Python读取原脚本；保留中文项目名、工作目录、原脚本、相邻模块导入和参数，并记录原始/实际argv、入口及脚本哈希。不改写历史脚本，也不自动重试已执行的脚本。该修正尚待Windows实机复测；保持中文标定项目，不以改成英文项目规避验收。

路径按argv传递，避免shell拼接；后端对Unicode的实际能力需分别验证。Windows项目可放在短路径以减少外部软件长路径限制。切片器与Cairo的Windows集成尚未实测；可选PDF缺失时保留SVG，补齐依赖遵循经用户同意后Agent安装流程。
