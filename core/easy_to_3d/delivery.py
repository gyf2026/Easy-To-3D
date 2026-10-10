"""Agent-first delivery instructions: model export and printer-specific slicing are separate."""
from pathlib import Path
from .storage import uid

def instructions(project, ident, language="zh"):
    version=project.version(ident)
    output=project.root/'deliveries'/uid('print')
    backup_path=project.root.parent/'backups'/(project.data['id']+'_'+uid('snapshot')+'.zip')
    # argv is authoritative and portable; do not embed user paths into a shell command.
    commands=[['easy-to-3d','--json','project','inspect','--project',str(project.root)],
              ['easy-to-3d','--json','version','verify','--project',str(project.root),'--version',ident],
              ['easy-to-3d','--json','backup','--project',str(project.root),'--output',str(backup_path)],
              ['easy-to-3d','--json','export','--project',str(project.root),'--version',ident,'--profile','print','--output',str(output)]]
    import json
    text=f'''请作为 Agent 保存项目并准备打印文件。项目路径：{project.root}
项目 ID：{project.data['id']}；模型版本：{ident}；版本摘要：{version['summary']}。
先检查待保存点评与未完成工作区，明确要交付的版本。发布版本已经持久保存在项目目录，保留原生 CAD/Blender 文件、脚本、需求、点评和检查证据；备份时复制整个项目，不只复制预览文件。不要覆盖历史版本，不替用户记录确认。
按下面 argv 数组逐条执行（不用 shell 拼接路径）：
{json.dumps(commands,ensure_ascii=False,indent=2)}
验证失败时停止交付并修复原因。导出后重读 manifest.json 与 print-checks.json，核对文件 SHA-256、毫米单位、尺寸、封闭性、非流形边、法向和体积。mesh fail 时不得称为可打印；unknown 不等于通过。告诉用户实际保存路径，交付 STL、打印说明、检查结果和清单。
如果用户需要打印机直接使用的 G-code 或机器专用文件，复用项目中已经确认的配置，只询问缺失的打印机型号、固件、喷嘴直径、材料、层高以及用户认可的切片配置；还需检查摆放、支撑、壁厚、间隙和热床范围。使用该打印机支持的切片器，先探测实际 CLI 与已安装配置。没有切片器时说明官方安装方案，经用户同意后由 Agent 下载、核验、安装并自检。不要猜测或套用另一打印机配置。
配置确认后，Agent 在独立交付目录执行切片，保存切片器版本、配置文件和哈希、输入 STL 哈希、执行日志、输出文件及 SHA-256；检查切片预览、尺寸、温度、挤出/运动范围与预计耗材。机器专用文件未经实际检查时标记待验证，不把 STL 更名为 G-code；不直接发送打印机或开始打印。整个过程优先在 Agent 对话中完成，无需查看器导出按钮。
'''
    translated={
'en':'''Act as the Agent to save and prepare printing files. Inspect unfinished work and reviews, select the exact version, and verify published file integrity. Preserve the whole project, including native CAD/Blender files, scripts, requirements, feedback and evidence. Finish browser-only drafts first; they are excluded from backups. Never overwrite history or record user acceptance without actual consent.
Execute the following argv arrays individually without shell interpolation. The backup is a verified portable ZIP; keep it outside the project. Inspect print-checks.json and manifest.json after STL export: verify SHA-256, millimetre units, dimensions, closed mesh, nonmanifold edges, winding and volume. Export success is separate from print suitability; fail blocks delivery as printable and unknown requires verification. Report the actual output paths.
For G-code or machine-specific files, reuse confirmed project settings and ask only for missing printer model, firmware, nozzle, material, layer height and approved slicing profile. Check bed size, orientation, supports, wall thickness and clearance. Use a compatible installed slicer and its actual CLI/configuration. If missing, propose the official installation and, after user agreement, have the Agent download, verify, install and probe it. Do not guess settings or rename STL to G-code.
Slice into a separate delivery folder; preserve slicer version, profile/input hashes, execution logs, output and SHA-256. Review layers, dimensions, temperatures, motion/extrusion range and estimated material. Mark unverified machine files accordingly. Do not send files to a printer or start printing. Perform the workflow in the Agent conversation; viewer export buttons are optional.''',
'ja':'''Agent としてプロジェクトを保存し、印刷ファイルを準備してください。未完了の作業とコメントを確認し、正確なバージョンを選択して公開ファイルを検証します。CAD/Blender 原本、スクリプト、要件、コメント、検査証拠を含むプロジェクト全体を保持します。ブラウザーで編集中の下書きは先に完了してください。履歴を上書きせず、実際の同意なしにユーザーの承認を記録しないでください。
以下の argv 配列を順番に実行し、パスをシェルに埋め込まないでください。バックアップは検証済み ZIP としてプロジェクト外に保存します。STL 出力後は manifest.json と print-checks.json を読み、SHA-256、mm 単位、寸法、閉じたメッシュ、非多様体エッジ、法線、体積を確認してください。出力成功と印刷適合性は別です。fail は印刷可能と扱わず、unknown は未検証です。保存先をユーザーに伝えてください。
G-code または機種専用ファイルには、確認済みの設定を再利用し、不足しているプリンター機種、ファームウェア、ノズル、材料、積層ピッチ、切片設定だけを質問します。ベッド範囲、向き、支持、壁厚、隙間も確認します。互換性のあるスライサーの実際の CLI と設定を使用します。未導入の場合は公式導入案を説明し、ユーザーの同意後に Agent がダウンロード、検証、導入、動作確認を行います。設定を推測せず、STL を G-code に改名しないでください。
独立した納品フォルダーに切片結果を保存し、スライサーのバージョン、設定と入力のハッシュ、ログ、出力 SHA-256 を保持してください。レイヤー、寸法、温度、動作・押出範囲、材料量を確認し、未検証の結果は明示してください。プリンターへの送信や印刷開始は行わず、Agent の会話で進めてください。''',
'fr':'''Agissez comme Agent pour sauvegarder le projet et préparer les fichiers d’impression. Examinez les travaux et commentaires inachevés, choisissez la version exacte et vérifiez l’intégrité des fichiers publiés. Conservez le projet complet : fichiers CAD/Blender natifs, scripts, exigences, commentaires et preuves. Terminez d’abord les brouillons du navigateur, exclus de la sauvegarde. Ne remplacez pas l’historique et n’enregistrez aucune acceptation sans accord réel.
Exécutez séparément les tableaux argv ci-dessous sans interpolation dans le shell. La sauvegarde ZIP vérifiée reste hors du projet. Après export STL, examinez manifest.json et print-checks.json : SHA-256, unités mm, dimensions, fermeture du maillage, arêtes non-manifold, orientation et volume. La réussite de l’export ne garantit pas l’imprimabilité : fail bloque cette qualification ; unknown reste à vérifier. Communiquez les chemins réels.
Pour le G-code ou un fichier propre à une machine, réutilisez les réglages approuvés et demandez uniquement les informations manquantes : modèle d’imprimante, micrologiciel, buse, matériau, hauteur de couche et profil de tranchage. Vérifiez plateau, orientation, supports, épaisseur et jeux. Utilisez un trancheur compatible et sa véritable CLI/configuration. S’il manque, proposez l’installation officielle ; après accord de l’utilisateur, l’Agent télécharge, vérifie, installe et teste. Ne devinez pas les réglages et ne renommez pas un STL en G-code.
Tranchez dans un dossier de livraison distinct et conservez version du trancheur, empreintes du profil et du STL, journaux, sortie et SHA-256. Examinez couches, dimensions, températures, limites de mouvement/extrusion et quantité de matériau. Signalez les fichiers non vérifiés. N’envoyez rien à l’imprimante et ne démarrez pas l’impression. Privilégiez la conversation avec l’Agent ; les boutons d’export sont facultatifs.'''}
    if language in translated:
        text=f"Project: {project.root}\nProject ID: {project.data['id']}\nVersion: {ident}\n"+translated[language]+'\n'+json.dumps(commands,ensure_ascii=False,indent=2)
    return {'project_id':project.data['id'],'model_version_id':ident,'commands':commands,'instructions':text,'output':str(output),'printer_configuration':'required_before_machine_specific_slicing'}
