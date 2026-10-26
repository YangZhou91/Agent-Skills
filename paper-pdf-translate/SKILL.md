---
name: paper-pdf-translate
description: 下载学术论文并批量翻译成保留原版式、公式和插图的中文 PDF，生成原文、中文及双语版并执行版面检查。用于论文全文翻译，不用于仅摘要或重排成阅读报告。
---

# 论文 PDF 中文翻译

先明确论文清单，优先从作者主页、会议开放仓库、arXiv 下载可公开获取的 PDF。保留英文原件，记录标题、年份、版本、URL、SHA256、页数。不要用同名但不同作者的论文替代。

使用独立虚拟环境运行 PDFMathTranslate / BabelDOC，先查当前官方仓库说明和本机 CLI。原位置替换文本以保留双栏、图像、矢量图、公式及页码；不要将整页截图重新排成中文长文。中文长度变化允许字距和字号调整，不能承诺像素级完全一致。图内嵌文字默认保留，图注翻译。作者姓名、引用键、公式变量保持可核对。

在 Windows 上，已验证的起点是 Python 3.12、`pdf2zh==1.9.11`、`tencentcloud-sdk-python-tmt==3.0.1336`、`bitstring==4.3.1`；后两项固定是为了避免新版本删除接口，后续版本应重新验证。依赖安装使用系统证书，避免无输出地等待 TLS 重试。辅助脚本 `translate.py` 限制请求超时与重试，并将 Bing 长段落分段，防止上游默认的 1000 字符截断；公式占位符变化即报错。

上游默认会误把 CMBX 粗体标题和整段斜体摘要当成公式。`translate.py` 使用更窄的公式字体模式；必须检查标题和摘要确实已翻译。Bing 若省略数学引用，脚本回退为分开翻译公式间的文字，保留全部原公式顺序；这种回退仍需检查语句连贯性。

先执行一篇的 1-2 页验证下载、翻译服务、中文字体和公式保留，再运行全批次。免费 Google/Bing 可作为无凭证起点；若用户指定模型则遵从指定。不得自行读取凭证数据库、更换用户服务配置或引入付费服务。为网络请求设置超时和有限重试。

使用 [scripts/batch.py](scripts/batch.py) 下载与执行，manifest 为 JSON 数组，每项包含 `id`, `title`, `url`。脚本用调用方指定的 Python 执行 `pdf2zh.pdf2zh`，服务可配置；每篇独立日志、状态及校验，已有结果可复用。示例：

```powershell
python scripts/batch.py --manifest papers.json --root ./paper-translations/collection --download-only
python scripts/batch.py --manifest papers.json --root ./paper-translations/collection --service bing
```

输出组织为 `original/`, `translated/`, `logs/`, `qa/`。输出中文单语版与原文/中文双语版。状态必须区分下载完成、翻译完成、自动检查通过、视觉检查通过，不能把进程退出码当作内容质量证明。

用 PyMuPDF 检查单语版页数和尺寸与原文一致、逐页中文文本存在、原图像保留、字体缺字或超出页面；全文正文、图注、表格说明应翻译，参考文献及图内标签的保留策略在交付说明中明确。生成所有页面缩略图并逐页检查，复杂公式、表格及密集页面用高分辨率查看。出现大段漏译、重叠、正文遮图时修复后重跑有关页面；不能把存在明显缺陷的版本标成最终版。

运行 `scripts/qa.py --root <collection>` 生成逐页检查 JSON、全文文本及每 6 页一张的预览图。对作者区等应原样保留的区域，先查看原 PDF 确认矩形边界，再使用 `scripts/preserve_regions.py --root <collection> --regions <regions.json>` 恢复原文矢量区域并重建双语版；JSON 为 `paper-id -> [{"page":1,"rect":[x0,y0,x1,y1]}]`，坐标使用 PyMuPDF 左上原点。不要用大矩形覆盖相邻标题或首图。恢复后重新生成 QA。

对漏译页使用 `batch.py --only <id> --pages 1 --force` 生成局部修正版，再用 `merge_pages.py --target <final-mono.pdf> --repair <pilot-mono.pdf> --pages 1` 只合入选定页；必须重新运行区域恢复、双语生成和 QA。`--pages` 输出中未选择的页仍是原文，不能直接当成全文中文交付。恢复工具也支持区域 `text` 和 `fontsize`，用于经人工确认的小段排版修复，不可覆盖图表。

目录页的点线与页码容易被分段重排：必要时以原目录页为底，按原文字基线逐项替换中文标题，保留原页码和缩进。混排中英文时，用同一实际中文字体文件测量字宽并写入；PyMuPDF 的 `china-s` 内置字体与单独测量的 Font 对象可能出现不同的西文字符宽度，导致点线压字。修改目录页后务必放大检查。

使用 `scripts/index.py --root <collection> --manifest <manifest> --title <title>` 建立阅读目录；视觉检查记录保存在 `qa/visual-review.json` 的 `papers` 映射中，逐项记录实际检查页码及限制。最后使用 `scripts/package.py --root <collection> --manifest <manifest>` 核对单语页数、双语交替对应关系和结构检查，再打包中文 PDF。不要在仍有论文失败或待视觉检查时打包为完成版本。

最终提供下载清单、可点击的输出目录/文件链接和实际检查范围，标明机器翻译及尚未校对的技术术语。保留原始 PDF 与日志以便复核。
