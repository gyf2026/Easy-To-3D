# Agent 引导的用户流程

用户描述需求、查看模型并点评。能力探测、建模、校验、保存与导出由Agent执行；查看器不承担工具安装或云账号设置。

## 首次使用或环境变化

Agent先发现当前客户端实际提供的工具，再运行轻量自检，不要求首次安装所有软件：

```sh
easy-to-3d --json doctor --cache <local-capability-cache.json>
```

找到可执行程序只代表路径可用。需要本地建模时，对选择的后端运行 `doctor --backend freecad --probe` 或Blender，并可附加 `--executable <path>` 和 `--cache <path>`。缓存最多保留7天，系统、路径、程序大小/修改时间、探测参数变化会重查；失败不缓存，发生实际失败后用 `--refresh`。缓存不应进入Git。启动、脚本执行、导出和设计符合要求分别判断。

客户端能力由Agent在当前会话中实测，不能从客户端名称猜测。向 `doctor --session-report <session.json>` 提供以下结构；未测试的能力保留unknown。客户端、模型或工具上下文变化后重新测试，不能直接沿用旧报告。

```json
{
  "context": {"client": "实际客户端及版本", "model": "实际模型", "tools_fingerprint": "实际工具集及版本"},
  "tested_at": "2026-10-10T00:00:00+00:00",
  "capabilities": {
    "generation": {"status": "unknown"},
    "geometry_edit": {"status": "unknown"},
    "texture_edit": {"status": "unknown"},
    "local_download": {"status": "unknown"},
    "execution": {"status": "unknown"},
    "vision": {"status": "unknown"},
    "slicing": {"status": "unknown"}
  }
}
```

pass必须提供 `evidence` 字符串，说明实际测试及证据位置；过期报告降为unknown。核心只整理Agent提供的证据，不能独立访问宿主客户端的私有工具接口，也不会凭报告发起云调用。

只向用户展示一句可用能力结论和下一步。缺少本次所需工具时：查找常见位置 → 请用户提供已安装程序路径 → 推荐官方版本、架构和位置，经同意后Agent下载、核验、安装并实际探测。已有同一安装授权无需重复询问。

## 按需求选择路径

Agent提取用途、关键尺寸、外形和制造要求，只追问影响结果的缺失信息。程序不解析自然语言；Agent选择明确的task并提供本次doctor输出文件：

```sh
easy-to-3d --json workflow-guide --task precision --report <doctor-report.json>
```

| task | 路径 |
|---|---|
| organic | 已验证的客户端生成及本地下载能力优先；否则Blender，能力未知先探测 |
| precision | CAD优先；精确配合不以外观生成替代 |
| mesh-edit | 已验证局部几何编辑及下载能力优先；否则Blender |
| texture | 已验证纹理编辑及下载能力优先；否则Blender |
| save | 完整项目备份及校验 |
| print | 模型检查、实际支持的导出及按机器配置切片 |

返回ready只表示该路径具备记录的工具能力，不能表示本次模型已满足要求。没有ready路径时给出探测或配置步骤，不自动安装，也不把unknown当作缺失。Agent可以说明有证据的其他路径选择，不将路由表当成唯一可用建模方法。

## 初稿、点评与修订

交付前检查可打开性、单位/方向、关键尺寸、外形及需要保留的结构；使用实际测量和视图比对。发现可修复问题先修复再检查。精确结构先确认白模布局；外形任务可直接用带材质初稿。分别报告已验证、需用户确认和尚未验证；真实装配、受力和打印条件未知时不能声称通过。

用户在查看器提交点评后，按钮显示“已提交”，对应点评显示绿色✅，仅表示已交给Agent，并非已修改或已接受。出现新的未提交点评（包括移动已提交标记形成的新意见）时按钮恢复“提交修改”。已删除草稿不触发新提交，旧批次及意见历史保留。

Agent读取确切版本和批次的 `review handoff`，恢复视角和坐标。能力未知先核对接口；纹理修改不能代替几何修改。无法局部编辑而需全量再生成时，先说明保留结构可能变化。结果导入为点评源版本的子版本，核验变化及保留要求，逐条回复，再打开同视角新旧对比。

## 保存与打印

“保存项目”使用完整项目备份和SHA校验；编集中仅存浏览器的草稿先完成编辑并自动保存。打印交付使用 `delivery-guide`，用户无需到查看器操作导出。

当前核心直接导出打印STL。3MF等格式需实际转换工具验证，不能把规划格式写成已有支持。机器专用文件需打印机、固件、喷嘴、材料、层高及认可的切片配置；只询问尚缺字段。Agent探测切片器实际CLI和配置、执行切片、检查结果并保存日志及哈希。缺少工具按上述经同意安装流程处理，不启动打印，不将STL改名为G-code。

查看导航：模型加载成功后底部结束“正在加载”并显示操作提示。滚轮按鼠标位置缩放，右键拖动平移；正交/透视切换、恢复点评视角和历史双画布均保留这些操作。“适应模型”恢复整个模型的构图，模型坐标原点不因导航改变。


Language and naming: use the language the user uses to communicate with the Agent (zh/en/ja/fr), unless the user requests otherwise. Pass `project init --language <code>` and use that language for `--name`, `--feature`, design summaries and human-facing generated/export filenames. Keep technical keys and fixed artifact-contract paths unchanged. Open `view --language <code>` for the current conversation, including existing projects; never rename published artifacts or existing project paths in place. Unsupported conversation languages fall back to Chinese and offer the four supported choices. The user can change the viewer language manually.

Visible review numbers are consecutive among non-deleted annotations and may change after deletion. Use annotation IDs plus source version/batch IDs as authoritative references, never numbers alone.
