# First session / 首次体验

## Requirements

Use Python 3.10+, Chrome, and an Agent client with local file/command access and visual inspection tools. Install from the repository as described in the [README](../README.md). Use the same Python environment when the Agent invokes `easy-to-3d`.

For mechanical parts, install [FreeCAD](https://www.freecad.org/downloads.php). For mesh editing, install [Blender](https://www.blender.org/download/). Do not install both unless the task needs both. Optional PDF conversion requires `python -m pip install '.[drawings]'` and a working Cairo runtime.

Load [the Skill](../skills/structural-design/SKILL.md) through your client's skill mechanism; copying a directory alone does not prove it loaded. Ask the Agent to read it, report the project CLI version/help, and perform the required session capability checks. [Generic integration instructions](../integrations/generic/INSTALL.md).

## Try a bracket

Send this to your Agent after loading the Skill:

> Create a mechanical L-bracket in a separate project folder: a 60 × 40 × 4 mm base, a 30 mm tall upright with 4 mm thickness, and two 6 mm diameter mounting holes in the base. Confirm the hole positions, upright orientation and intended manufacturing method with me before modeling. Use FreeCAD, preserve the editable source and scripts, and open a first version in the viewer. Do not treat an exported STL as proof it is ready to print.

1. Confirm the requirements and explicit dimensions. The Agent checks only the backend needed for this task.
2. Inspect the first version: rotate, zoom, pan and double-click the surface to add a comment such as “increase this hole diameter to 8 mm; keep the other hole unchanged”.
3. Submit comments and paste the viewer's continuation instruction into the same Agent conversation.
4. Let the Agent read the source version and review batch, revise in a child workspace, check changed and preserved dimensions, and publish a new version.
5. Compare the old and new versions from the same view. Confirm only after checking the result. Ask for a backup, editable source and STL if needed.

The example is a requirement prompt, not a promise of identical geometry from every model. Agent capability and native backend execution affect the outcome. For executable reference scripts see [calibration.py](../backend-examples/freecad/calibration.py), [enclosure.py](../backend-examples/freecad/enclosure.py) and [hinge.py](../backend-examples/freecad/hinge.py). `calibration.py` creates actual asymmetric bracket geometry for coordinate checks; its objects are not a complete sketch-based feature history. The Skill handles workspace setup and publication; scripts are references, not a restricted modeling API.

## 中文体验步骤

1. 按首页安装软件包，加载 Skill，并告诉 Agent 本次使用的 Python 环境。识图、文件读写和命令执行能力需要本次会话实际检查。
2. 描述一个 L 形支架，例如底板 60×40×4 mm、立板高 30 mm/厚 4 mm、底板两个直径 6 mm 的孔；先确认孔位、朝向和制造用途，再生成第一版。
3. 在查看器旋转观察，双击需要修改的位置并点评，例如“这个孔改为直径 8 mm，另一个孔不变”。
4. 点击提交，把网页提供的继续指令发回 Agent。Agent 读取原版点评并生成子版本，不覆盖历史。
5. 用同视角对比检查改动，再记录你的确认。需要交付时让 Agent 提供可编辑源文件、备份和打印 STL，并单独检查打印条件。

项目数据放在软件仓库以外。首次使用失败时，记录操作步骤、系统、Python、客户端、后端版本和脱敏错误；不要在 Issue 上传私人模型或账号信息。

See [the CLI workflow](cli-workflow.zh-CN.md) for exact commands and [compatibility](compatibility.md) for known limits. The viewer runs on a local loopback address and does not wake the Agent automatically.
