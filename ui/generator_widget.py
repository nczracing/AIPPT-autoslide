# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QSpinBox, QComboBox, QProgressBar, QFileDialog, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QTime
from settings_module import get_settings, Presentation
from core.outline_generator import OutlineGenerator
from core.image_generator import ImageGenerator
from core.pptx_builder import PPTXBuilder
from core.doc_parser import parse_reference_file
import logging
import time
from pathlib import Path

# 设置模块级日志
logger = logging.getLogger(__name__)

# 阶段权重：大纲 3~45%，插图 45~95%，打包 96~100%
STAGE_OUTLINE_START = 3
STAGE_OUTLINE_END = 45
STAGE_IMAGES_END = 95


class GenerateThread(QThread):
    progress = pyqtSignal(str)
    # 细化进度信号：(百分比, 当前步骤描述, 预计剩余秒数；<0 表示未知)
    progress_step = pyqtSignal(int, str, float)
    generated = pyqtSignal(object)  # 生成成功信号（重命名，避免遮蔽 QThread 内建 finished）
    error = pyqtSignal(str)

    # 经验值：单张 AI 插图生成约 10~40 秒，首次 ETA 用 25 秒/张估算
    # （仅首张使用，后续自动被实测均耗时覆盖）
    PER_IMAGE_ETA_GUESS = 25.0

    def __init__(self, topic, page_count, language, style, references="", context=""):
        super().__init__()
        self.topic = topic
        self.page_count = page_count
        self.language = language
        self.style = style
        self.references = references
        self.context = context

    def run(self):
        try:
            logger.info(f"开始生成: {self.topic}")
            self.progress.emit('正在生成内容...')
            self.progress_step.emit(
                STAGE_OUTLINE_START,
                '正在调用 AI 生成大纲、正文与排版方案（通常需 30~90 秒）...',
                60.0,
            )

            gen = OutlineGenerator()
            logger.info("OutlineGenerator创建成功")

            presentation = gen.generate(
                self.topic,
                self.page_count,
                self.language,
                self.style,
                references=self.references,
                context=self.context,
            )
            logger.info(f"内容生成完成: {len(presentation.slides)} 页")
            self.progress_step.emit(
                STAGE_OUTLINE_END,
                f'大纲与内容就绪（共 {len(presentation.slides)} 页），开始生成插图...',
                -1.0,
            )

            # 生成插图（可配置开关；单页失败不阻断整体）
            self._generate_images(presentation)

            self.progress_step.emit(96, '正在打包 PPTX 文件...', 3.0)
            self.generated.emit(presentation)

        except Exception as e:
            logger.error(f"生成失败: {e}", exc_info=True)
            self.error.emit(f"生成失败: {str(e)}")

    def _generate_images(self, presentation):
        """为带 image_prompt 的内容页生成插图，逐页报告进度与剩余时间预估。"""
        try:
            ppt_cfg = get_settings().get_ppt_config()
        except Exception:
            ppt_cfg = {}
        if not ppt_cfg.get("enable_images", True):
            logger.info("插图生成已关闭（enable_images=False）")
            return

        image_slides = [s for s in presentation.slides if s.image_prompt]
        if not image_slides:
            logger.info("无插图提示词，跳过插图生成")
            return

        theme = presentation.theme or "business"
        img_gen = ImageGenerator()
        total = len(image_slides)
        image_durations = []
        for idx, slide in enumerate(image_slides, 1):
            percent = STAGE_OUTLINE_END + int(
                (STAGE_IMAGES_END - STAGE_OUTLINE_END) * (idx - 1) / total
            )
            if image_durations:
                avg = sum(image_durations) / len(image_durations)
                eta = avg * (total - idx + 1)
            else:
                eta = self.PER_IMAGE_ETA_GUESS * (total - idx + 1)
            title_hint = (slide.title or '')[:16]
            self.progress_step.emit(
                percent, f'正在生成插图 {idx}/{total}：{title_hint}', eta
            )
            t1 = time.monotonic()
            try:
                path = img_gen.generate(
                    slide.image_prompt,
                    slide_title=slide.title,
                    theme=theme,
                    filename_prefix=f"slide_{slide.page}",
                    layout=slide.image_layout,
                )
                slide.image_path = path or ""
                if path:
                    logger.info(f"第 {slide.page} 页插图就绪: {path}")
                    # 仅成功样本计入 ETA（F-22-01：快速失败会拉偏均值）
                    image_durations.append(time.monotonic() - t1)
                else:
                    logger.warning(f"第 {slide.page} 页插图生成失败，已跳过")
            except Exception as e:
                logger.warning(f"第 {slide.page} 页插图异常，已跳过: {e}")
        # F-22-02：补发图像阶段收尾进度，避免进度条从中间值直接跳到打包阶段
        self.progress_step.emit(
            STAGE_IMAGES_END, '插图生成完成，正在准备打包...', 3.0
        )

class GeneratorWidget(QWidget):
    # 请求在主窗口预览（信号解耦，不依赖 parent() 层级）
    preview_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = get_settings()
        self.current_presentation = None
        self.thread = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # 主题标题
        topic_label = QLabel('PPT 主题 / 标题 (Topic / Title)')
        topic_label.setObjectName('fieldLabel')
        topic_label.setStyleSheet('font-size: 13px; margin-top: 2px;')
        layout.addWidget(topic_label)
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText('请输入 PPT 主题，例如：人工智能的发展与应用...')
        layout.addWidget(self.topic_input)

        # 页数
        pages_layout = QHBoxLayout()
        pages_label = QLabel('页数 (Pages):')
        pages_label.setObjectName('fieldLabel')
        pages_layout.addWidget(pages_label)
        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(5, 50)
        self.pages_spin.setValue(10)
        pages_layout.addWidget(self.pages_spin)
        pages_layout.addStretch()
        layout.addLayout(pages_layout)

        # 风格
        style_layout = QHBoxLayout()
        style_label = QLabel('风格 (Style):')
        style_label.setObjectName('fieldLabel')
        style_layout.addWidget(style_label)
        self.style_combo = QComboBox()
        self.style_combo.addItem('商务 (Business)', 'Business')
        self.style_combo.addItem('学术 (Academic)', 'Academic')
        self.style_combo.addItem('创意 (Creative)', 'Creative')
        self.style_combo.addItem('科技 (Tech)', 'Tech')
        self.style_combo.addItem('活力 (Vibrant)', 'Vibrant')
        style_layout.addWidget(self.style_combo)
        style_layout.addStretch()
        layout.addLayout(style_layout)

        # 语言
        lang_layout = QHBoxLayout()
        lang_label = QLabel('语言 (Language):')
        lang_label.setObjectName('fieldLabel')
        lang_layout.addWidget(lang_label)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem('中文 (Chinese)', 'zh')
        self.lang_combo.addItem('英文 (English)', 'en')
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        # 参考文献
        ref_label = QLabel('参考文献 (References, 选填)')
        ref_label.setObjectName('fieldLabel')
        layout.addWidget(ref_label)
        self.references_input = QTextEdit()
        self.references_input.setPlaceholderText(
            '在此粘贴参考文献，每行一条（例：作者. 标题. 期刊, 年份）。\n'
            '生成的 PPT 内容将参考这些文献，并在末尾自动添加「参考文献」页。'
        )
        self.references_input.setFixedHeight(90)
        self.references_input.setStyleSheet('border-radius: 10px; padding: 10px;')
        layout.addWidget(self.references_input)

        # 参考材料
        ctx_label = QLabel('参考材料 (Reference Materials, 选填)')
        ctx_label.setObjectName('fieldLabel')
        layout.addWidget(ctx_label)

        # 上传参考文件按钮（PDF / MD）
        upload_layout = QHBoxLayout()
        self.upload_btn = QPushButton('上传参考文件 (PDF / MD)')
        self.upload_btn.setObjectName('secondaryBtn')
        self.upload_btn.setCursor(self.cursor())
        self.upload_btn.clicked.connect(self.upload_reference_files)
        upload_layout.addWidget(self.upload_btn)
        self.uploaded_label = QLabel('')
        self.uploaded_label.setObjectName('uploadedHint')
        self.uploaded_label.setWordWrap(True)
        upload_layout.addWidget(self.uploaded_label, 1)
        layout.addLayout(upload_layout)

        self.context_input = QTextEdit()
        self.context_input.setPlaceholderText(
            '在此粘贴背景材料以帮助理解内容，例如：要点、数据、资料片段、希望强调的内容等\n'
            '（自由文本，非必填，最长约 4000 字）。也可点击上方按钮上传 PDF/MD 文件自动填入。\n'
            'AI 会参考这些材料来丰富正文内容，但不会自动追加额外页面。'
        )
        self.context_input.setFixedHeight(90)
        self.context_input.setStyleSheet('border-radius: 10px; padding: 10px;')
        layout.addWidget(self.context_input)

        layout.addStretch()

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # 进度文字
        self.progress_label = QLabel('')
        self.progress_label.setObjectName('progressLabel')
        self.progress_label.setWordWrap(True)
        layout.addWidget(self.progress_label)

        # 时间标签
        self.time_label = QLabel('')
        self.time_label.setObjectName('timeLabel')
        layout.addWidget(self.time_label)

        # 计时器
        self._start_msec = 0
        self._eta_seconds = -1.0
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_time_label)
        layout.addStretch()

        # 生成按钮
        self.generate_btn = QPushButton('生成 (Generate)')
        self.generate_btn.setObjectName('primaryBtn')
        self.generate_btn.setCursor(self.cursor())
        self.generate_btn.clicked.connect(self.start_generate)
        layout.addWidget(self.generate_btn)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        export_btn = QPushButton('导出 PPTX (Export)')
        export_btn.clicked.connect(self.export_pptx)
        btn_layout.addWidget(export_btn)
        preview_btn = QPushButton('预览 (Preview)')
        preview_btn.clicked.connect(self.show_preview)
        btn_layout.addWidget(preview_btn)
        layout.addLayout(btn_layout)

    def upload_reference_files(self):
        """选择并解析参考文件（PDF/MD），解析结果追加到参考材料输入框。"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            '选择参考文件 (PDF / MD)',
            '',
            '参考文件 (*.pdf *.md *.markdown);;PDF (*.pdf);;Markdown (*.md *.markdown)',
        )
        if not files:
            return

        parsed_names = []
        errors = []
        # existing 在每次迭代后都要累加新内容，避免多选文件时前一个被后一个覆盖
        existing = self.context_input.toPlainText().strip()

        for f in files:
            try:
                text = parse_reference_file(f)
                name = Path(f).name
                parsed_names.append(name)
                # 带来源标注，便于 AI 区分不同文件内容；existing 累加，保留已加载文件
                existing = (existing + '\n\n' if existing else '') + f'=== 来源: {name} ===\n{text}'
                self.context_input.setPlainText(existing)
            except ValueError as e:
                errors.append(str(e))

        if parsed_names:
            self.uploaded_label.setText(
                f'已加载: {", ".join(parsed_names)}'
                + (f'（{len(errors)}个失败）' if errors else '')
            )
            self.context_input.setPlainText(self.context_input.toPlainText())  # 刷新
        if errors:
            QMessageBox.warning(self, '解析提示', '\n'.join(errors))

    def start_generate(self):
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, '提示', '正在生成中，请稍候...')
            return
        topic = self.topic_input.text().strip()
        if not topic:
            QMessageBox.warning(self, '提示', '请输入主题！')
            return
        ai_config = self.settings.get_ai_config()
        if not ai_config.get('api_key'):
            QMessageBox.warning(self, '缺少配置', '请先在「设置」中配置 API Key！')
            return
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(STAGE_OUTLINE_START)
        self._start_msec = QTime.currentTime().msecsSinceStartOfDay()
        self._eta_seconds = -1.0
        self._update_time_label()
        self._elapsed_timer.start()
        language = 'zh' if self.lang_combo.currentIndex() == 0 else 'en'
        references = self.references_input.toPlainText().strip()
        context = self.context_input.toPlainText().strip()
        self.thread = GenerateThread(
            topic,
            self.pages_spin.value(),
            language,
            self.style_combo.currentData(),
            references,
            context,
        )
        # 先连接信号再启动线程
        self.thread.progress.connect(self.update_progress)
        self.thread.progress_step.connect(self.update_progress_step)
        self.thread.generated.connect(self.on_generated)
        self.thread.error.connect(self.on_error)
        # 线程真正结束后安全清理，避免 "QThread: Destroyed while thread is still running"
        self.thread.finished.connect(self._on_thread_finished)
        self.thread.start()

    def update_progress(self, msg):
        self.progress_label.setText(msg)

    def update_progress_step(self, percent, msg, eta_seconds):
        """细化进度：百分比进度条 + 当前步骤 + 预计剩余时间。"""
        self.progress_bar.setValue(max(0, min(100, percent)))
        self.progress_label.setText(msg)
        self._eta_seconds = eta_seconds
        self._update_time_label()

    def _update_time_label(self):
        """刷新"已用时 / 预计剩余"显示（UI 线程定时触发）。

        防御：若计时起点未初始化（信号竞态或直接调用），以当前时刻兜底，
        避免时间标签持续空白。
        """
        if not self._start_msec:
            self._start_msec = QTime.currentTime().msecsSinceStartOfDay()
        now = QTime.currentTime().msecsSinceStartOfDay()
        elapsed = max(0, (now - self._start_msec) / 1000.0)
        text = f'已用时 {self._fmt_duration(elapsed)}'
        if self._eta_seconds >= 0:
            text += f' · 预计剩余约 {self._fmt_duration(self._eta_seconds)}'
        self.time_label.setText(text)

    @staticmethod
    def _fmt_duration(seconds):
        seconds = int(max(0, seconds))
        return f'{seconds // 60:02d}:{seconds % 60:02d}'

    def on_generated(self, presentation):
        self.current_presentation = presentation
        self.generate_btn.setEnabled(True)
        self._elapsed_timer.stop()
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        self.time_label.setText('')
        self.progress_label.setObjectName('doneLabel')
        self.progress_label.style().unpolish(self.progress_label)
        self.progress_label.style().polish(self.progress_label)
        self.progress_label.setText(f'完成！共 {len(presentation.slides)} 页')
        # 通过信号通知主窗口更新预览（不依赖 parent() 层级）
        self.preview_requested.emit(presentation)

    def _on_thread_finished(self):
        """QThread 内建 finished：run() 返回后发射，线程已真正结束，可安全释放。"""
        if self.thread is not None:
            self.thread.deleteLater()
            self.thread = None

    def on_error(self, error_msg):
        self.generate_btn.setEnabled(True)
        self._elapsed_timer.stop()
        self.progress_bar.setVisible(False)
        self.time_label.setText('')
        QMessageBox.critical(self, '错误', error_msg)

    def export_pptx(self):
        if not self.current_presentation:
            QMessageBox.warning(self, '提示', '请先生成 PPT！')
            return
        file_path, _ = QFileDialog.getSaveFileName(self, '保存 PPTX', '', 'PowerPoint (*.pptx)')
        if not file_path:
            return
        try:
            builder = PPTXBuilder()
            builder.build(self.current_presentation, file_path)
            QMessageBox.information(self, '成功', f'已保存到: {file_path}')
        except Exception as e:
            QMessageBox.critical(self, '导出错误', str(e))

    def show_preview(self):
        if self.current_presentation:
            self.preview_requested.emit(self.current_presentation)
