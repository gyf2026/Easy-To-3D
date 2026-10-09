# 实测支持矩阵

日期：2026-10-09。仅下列环境有运行证据，其他环境不推定兼容。

| 组件 | 实测版本/系统 | 已验证 | 限制 |
|---|---|---|---|
| Python 核心 | Python 3.10.21、3.14.7 / macOS 27.0.1 arm64 | macOS修正版100项测试：96通过、4项Windows专用跳过；Windows原版97项全通过；锁、备份恢复、导出、HTTP、Unicode协议；最低版本无网络安装wheel | Windows10 AMD64/Python3.12.10已有实机证据；修正版FreeCAD中文入口、Windows11及Linux待验证 |
| Web 查看器 | Chrome 154.0.8037.97 / 本机 headless SwiftShader | 28项浏览器检查：GLB、拾取、冲突、自动保存、四语切换、编辑保留、历史双画布与Agent交付指引 | Safari/Firefox 未实测；本机已测100352三角形软件渲染，非所有模型容量保证 |
| Three.js | 固定 0.180.0 | 离线模块、OrbitControls、GLTFLoader | 不依赖 CDN；MIT 原文随包 |
| FreeCAD | 1.1.4 Revision 20260928 / 官方 arm64 dmg | FCStd、STEP、GLB、原生几何测量、TechDraw SVG、三项目各两轮局部修订 | 当前从临时只读包运行；不代表 GUI 全功能兼容 |
| Blender | 4.5.3 LTS / 官方 arm64 dmg | blend、GLB、显式单位轴向、发布与哈希 | 原生精确 CAD 和专利隐线输出未验证 |
| PDF | CairoSVG 2.9.1 + 系统 Cairo | 原生 SVG 转矢量 PDF、Poppler 渲染 | 可选依赖；复杂 SVG 仍需视觉检查 |
| build123d | 0.12.0 / Python 3.12.14 / arm64 | 同一非对称支架与两轮孔径修订、实体有效性、STEP往返、FreeCAD体积与包围盒一致、原生投影SVG | 隔离实验；BREP不作为产品正式原生版本类型；58依赖包，不成为用户必装依赖 |
| Codex Skill | 当前开发会话、技能静态验证通过 | 本地命令与文件、浏览器程序测试 | 从干净客户端安装/加载完整流程待测 |
| Worker Buddy / 其他客户端 | 未验证 | 通用安装说明 | 不承诺自动唤醒 |

真实后端包从官方下载，SHA256 校验；不随程序包分发。FreeCAD 首次从 dmg 加载动态库耗时较长，实际脚本须检查成功标记和产物，不能只信返回码 0。

Windows 实施与运行边界见 [跨平台说明](platform-support.md)，Agent 保存和打印操作见 [交付流程](agent-delivery.md)。真实用户项目已完成368文件备份及解压重开、4历史版本哈希核验与STL交付，原始验收记录由维护者本地保留；机器适用性仍为unknown。

Windows10/Python3.12.10/Chrome153.0.8010.53的实际28项浏览器检查、Blender4.5.10 LTS建模/STL/备份恢复已通过。FreeCAD1.1.4仅ASCII脚本argv的对照通过，中文脚本argv在原版失败；修正后需复测，不称Windows全部验收完成。原始 Windows 验收报告由维护者本地保留，不随仓库分发。
