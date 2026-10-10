# Easy-To-3D

Agent 驱动的本地结构设计与三维评审工作台。独立于历史 EasyTo3D 工程。当前为开发中的 Alpha；已验证能力和剩余验收见 [支持矩阵](docs/compatibility.md)。

Agent 按需求选择已验证的客户端 3D 能力，或自由编写 FreeCAD / Blender 脚本。程序保存需求、原生模型、GLB 预览、不可变版本和三维批注；不托管模型，不用关键词自动改变几何。用户数据本地保存，运行查看器无需网络。

## 安装

Python 3.10+。核心适配目标为 macOS 与 Windows；本机 macOS 已实测，Windows10 AMD64/Python3.13.14已通过114项核心及34项浏览器检查，FreeCAD中文路径和Blender原生交付流程通过，见 [跨平台说明](docs/platform-support.md)。在仓库运行 `python -m pip install .`，或安装构建的 wheel。无需 Node/npm 即可使用预构建查看器。需要 SVG 转 PDF 时安装 `python -m pip install '.[drawings]'`；CairoSVG 需要本机 Cairo 运行库。

精确机械结构优先 FreeCAD；复杂外形可优先使用已验证的客户端生成能力，网格编辑可使用 Blender；外部软件不随包分发。官方下载：[FreeCAD](https://www.freecad.org/downloads.php)、[Blender](https://www.blender.org/download/)。无需同时安装。

将 `skills/structural-design` 放到所用客户端的技能目录或按客户端方式加载。技能安装不代表取得识图或本地执行能力；首次需要实际会话测试。

## 首次流程

```sh
easy-to-3d --json doctor --cache <local-capability-cache.json>
# Agent 按本次需求选择后端；需要 CAD 时再实际探测
easy-to-3d --json doctor --backend freecad --probe
easy-to-3d project init --parent /absolute/designs --name 传感器外壳 --feature 固定孔
easy-to-3d project inspect --project /absolute/designs/project-folder
easy-to-3d workspace create --project /absolute/designs/project-folder
```

项目目录必须与安装目录分离。返回路径和稳定项目 ID；同名项目仍有独立身份。需求与假设通过 `requirements --project <path> --file <card.json> --revision <n>` 保存，创建工作区时快照。分支从来源版本继承需求，使用 `--variant <variant-id>` 编辑该方案的独立需求；不会覆盖其他方案。

自由建模示例：复制 `backend-examples/freecad/calibration.py` 到工作区 `scripts/`，将 core 包所在路径提供给 FreeCAD Python，执行：

```sh
easy-to-3d run --workspace <absolute-workspace> --timeout 180 -- /path/to/FreeCADCmd <absolute-workspace>/scripts/calibration.py
easy-to-3d check --workspace <absolute-workspace> --profile structure
easy-to-3d version publish --project <project> --workspace <workspace-id> --summary 初始白模
easy-to-3d view --project <project>
```

`view` 打印回环 URL，浏览器打开即可旋转、缩放、标准视角、隐藏部件和双击表面点评。滚轮围绕鼠标位置缩放，右键拖动平移；放大后可移动视图观察模型上部，“适应模型”恢复完整构图。加载成功后底部显示操作提示，加载失败显示实际错误。退出有效编辑后自动保存；提交后按钮显示“已提交”，意见后显示绿色✅，新增未提交意见时恢复“提交修改”。绿色✅只表示已提交，不表示修改完成或用户接受。提交后复制一条继续修改指令发给 Agent。网页不自动唤醒客户端。

Agent 先恢复原版批注视角，从原版创建子工作区，修改后发布新版本并逐条回复。旧文件和原意见保留。点击点评恢复完整相机、宽高比与显示状态。点评直接在左侧编辑，退出输入后自动保存；浏览器保留未完成输入，冲突时自动保留双方内容。选择历史版本后，左侧显示所选模型、右侧显示最新版，两侧共用视角；右侧添加点评。参考系默认关闭，可从右侧工具栏打开。右上角切换中文、英语、日语、法语；默认中文，语言偏好保存在本机浏览器，点评原文不翻译。

用户可在查看器选择白模、设计或交付阶段，填写确认范围并点击“记录我的确认”。Agent 也可在取得真实用户确认后记录原文：

```sh
easy-to-3d project confirm --project <path> --version <id> --kind white_model --note "用户的实际确认原文"
```

## 导入与执行恢复

静态 GLB 和二进制 STL 可直接导入，必须显式指定源单位与上轴：

```sh
easy-to-3d import --project <path> --source <original.glb> --units m --up-axis Y
easy-to-3d cancel --workspace <path> --run-id <run-id>
easy-to-3d recover --workspace <path>
```

导入保留原文件和哈希，生成独立预览转换脚本；可查看与批注，但不恢复参数化设计历史。FreeCAD/Blender 原生文件需要明确的后端导入脚本与检查。取消请求绑定运行 ID；恢复仅清理进程身份仍可核对的孤立进程。新运行拒绝与同一工作区内的在途任务并发。参数提示是可选作者说明，不限制自由脚本。

静态GLB导入保留材质贴图、UV与节点层级。接入WorkBuddy等客户端的外部3D生成服务时，使用[外部模型流程](docs/external-models.md)；Agent可用`review handoff`读取编号点评、视角和原文件坐标，再把修改结果导入为子版本。实际服务的局部编辑能力仍须客户端实测。

## Agent 保存与打印交付

先让 Agent 执行 [保存与打印指引](docs/agent-delivery.md)，无需查看器导出按钮。

```sh
easy-to-3d --json delivery-guide --project <path> --version <id>
easy-to-3d --json backup --project <path> --output <new-project-backup.zip>
easy-to-3d --json backup-verify --file <new-project-backup.zip>
easy-to-3d version verify --project <path> --version <id>
easy-to-3d export --project <path> --version <id> --profile print --output <delivery-directory>
easy-to-3d export --project <path> --version <id> --profile drawings --output <delivery-directory>
```

STL 坐标单位是 mm，清单包含确切版本与哈希。网格导出成功、网格检查结果、打印条件适用性分开报告。壁厚、间隙、材料、支撑方向需进一步确认。需要 G-code 或机器专用文件时，Agent 先确认打印机与配置，再操作外部切片器；核心不内置切片引擎。导出事务失败不留下半成品，也不覆盖历史或已有交付。

附图先在工作区从原生模型生成标准线图，再转换 PDF、检查和发布。剖视、静态爆炸图目前作为实验输出；专利附图不保证申请合规，规则核查与图形人工复核独立记录。

## 开发与构建

```sh
python -m pip install '.[dev]'
python tools/build_release.py
```

本仓库只分发产品源码、正式示例、协议、Skill及使用文档。测试源码、评测、诊断和开发过程文件保留在维护者本地，不纳入Git或源码分发包。公开CI只检查跨平台构建、安装与CLI启动，不代表完整功能验收。

协议、容差和边界见 [决策记录](docs/decisions.md)、[Schema](schemas/)、[支持矩阵](docs/compatibility.md)。当前没有遥测、账号、云存储或自动执行模型附带脚本。代码按 [Apache-2.0](LICENSE) 授权；当前为 Alpha，不代表完整功能或所有平台验收完成。

用户体验与能力自检、建模路径选择见 [Agent 引导流程](docs/user-workflow.md)。`doctor --cache` 支持本地探测缓存，`--session-report` 接收当前客户端实测证据；`workflow-guide` 提供按需求选择的路径和交付指引。
