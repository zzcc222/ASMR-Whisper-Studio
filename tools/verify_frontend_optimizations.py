# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - 前端深度优化全量验证脚本 (verify_frontend_optimizations.py)
验证项目：
1. VAD 默认关闭 (ASMRTranscriberConfig, SettingsManager, SwitchToggle)
2. 主题色板 Token 系统与 ASS BGR 颜色转换 (ui/theme.py)
3. 确认已干净移除生硬的字数断句滑块 (slider_max_chars / max_chars) 且 SpinBox 步进箭头图标完整就绪
4. FileCardRowWidget 底部单文件内联进度条渲染与压制队列右键菜单
5. VideoSubtitleWidget 动态音频采样率/声道徽章与 WYSIWYG 字幕样式实时渲染
6. 字幕列表实时搜索过滤、增删改与保存回写 (save_subtitle_items)
7. 字幕样式微调与 FFmpeg force_style 命令生成及真实 FFmpeg 压制测试
8. 批量压制队列调度与快捷键响应 (Left/Right/Ctrl+S)
"""

import os
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["QT_QPA_PLATFORM"] = "offscreen"

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QPixmap

from core.config import ASMRTranscriberConfig, SettingsManager
from core.media.sub_burner import SubBurnerConfig, build_ffmpeg_command, build_force_style_clause
from core.subtitle.subtitle_exporter import save_subtitle_items
from core.subtitle.subtitle_parser import parse_subtitle_file
from ui.theme import THEME_TOKENS, hex_to_ass_bgr
from ui.main_window import ASMRTranscriberWindow as MainWindow


def run_all_checks():
    app = QApplication.instance() or QApplication(sys.argv)

    with tempfile.TemporaryDirectory() as settings_sandbox:
        sandbox_local = os.path.join(settings_sandbox, "local_settings.json")
        sandbox_appdata = os.path.join(settings_sandbox, "appdata_settings.json")
        SettingsManager.set_custom_paths(sandbox_local, sandbox_appdata)
        try:
            _run_all_checks_inner(app)
        finally:
            SettingsManager.reset_custom_paths()


def _run_all_checks_inner(app):
    print("=" * 68)
    print("🚀 [1/8] 检验 VAD 默认关闭状态与默认窗口尺寸 (1920x1080 居中，防无头虚拟屏污染)")
    cfg_default = ASMRTranscriberConfig()
    assert cfg_default.vad_filter is False, f"Expected ASMRTranscriberConfig.vad_filter=False, got {cfg_default.vad_filter}"
    default_settings = SettingsManager.get_default_settings()
    assert default_settings["vad_enabled"] is False, f"Expected default_settings['vad_enabled']=False, got {default_settings['vad_enabled']}"
    assert default_settings["window_width"] == 1920 and default_settings["window_height"] == 1080
    win = MainWindow()
    assert win.switch_vad.isChecked() is False, f"Expected win.switch_vad.isChecked()=False, got {win.switch_vad.isChecked()}"
    assert win._saved_window_w == 1920 and win._saved_window_h == 1080, (
        f"Expected 1920x1080 saved window size, got {win._saved_window_w}x{win._saved_window_h}"
    )
    print("  ✅ ASMRTranscriberConfig.vad_filter == False")
    print("  ✅ SettingsManager.get_default_settings()['vad_enabled'] == False")
    print("  ✅ MainWindow 默认窗口尺寸 1920x1080 保持完整 (不受 offscreen 800x800 虚拟屏篡改)")

    print("=" * 68)
    print("🚀 [2/8] 检验主题色板 Token 与 ASS 颜色转换")
    assert THEME_TOKENS["bg_canvas"] == "#F4F5F8"
    assert THEME_TOKENS["brand_primary"] == "#8B5CF6"
    assert hex_to_ass_bgr("#FFFFFF", "00") == "&H00FFFFFF"
    assert hex_to_ass_bgr("#FDE68A", "00") == "&H008AE6FD"
    print("  ✅ THEME_TOKENS & hex_to_ass_bgr 校验通过")

    print("=" * 68)
    print("🚀 [3/8] 检验已安全移除自定义断句滑块与规则 (slider_max_dur / slider_max_chars) & 校验 SpinBox 步进上下箭头样式")
    assert not hasattr(win, "slider_max_chars"), "slider_max_chars should be removed from MainWindow"
    assert not hasattr(win, "slider_max_dur"), "slider_max_dur should be removed from MainWindow"
    assert not hasattr(win, "lbl_max_dur"), "lbl_max_dur should be removed from MainWindow"
    assert not hasattr(cfg_default, "max_chars"), "max_chars should be removed from ASMRTranscriberConfig"
    assert not hasattr(cfg_default, "clamp_max_duration"), "clamp_max_duration should be removed from ASMRTranscriberConfig"
    assert not hasattr(cfg_default, "split_by_punctuation"), "split_by_punctuation should be removed from ASMRTranscriberConfig"
    assert "max_chars_slider" not in default_settings, "max_chars_slider should be removed from default_settings"
    assert "max_duration_slider" not in default_settings, "max_duration_slider should be removed from default_settings"
    from ui.styles import LIGHT_STYLE_SHEET
    assert "spin_up.svg" in LIGHT_STYLE_SHEET and "spin_down.svg" in LIGHT_STYLE_SHEET
    for svg_name in ("spin_up.svg", "spin_down.svg", "spin_up_hover.svg", "spin_down_hover.svg"):
        svg_path = os.path.join(ROOT_DIR, "assets", svg_name)
        assert os.path.isfile(svg_path), f"Missing SpinBox arrow icon: {svg_path}"
    print("  ✅ 已彻底移除自定义时长/字数断句规则与滑块，SpinBox 上下箭头图标与 QSS 校验通过")

    print("=" * 68)
    print("🚀 [4/8] 检验 FileCardRowWidget 底部单文件内联进度条渲染")
    from ui.components.file_card import FileCardRowWidget
    card = FileCardRowWidget(0, "D:/Videos/test_asmr.mp4", "128.5 MB")
    card.resize(360, 54)
    card.update_progress(66.5)
    assert abs(card._progress_pct - 66.5) < 0.01
    assert "66%" in card.lbl_badge.text()
    pix = QPixmap(card.size())
    card.render(pix)
    card.update_status("✅ 已完成")
    assert card._progress_pct == 0.0
    print("  ✅ FileCardRowWidget 底部渐变进度条渲染校验通过")

    print("=" * 68)
    print("🚀 [5/8] 检验 VideoSubtitleWidget 动态音频规格徽章 & WYSIWYG 字幕样式渲染")
    vw = win.sub_burner_tab.video_widget
    vw.resize(640, 360)
    vw.set_audio_specs({"sample_rate": 48000, "channels": 2, "audio_codec": "AAC"})
    assert "48kHz" in vw.lbl_audio_title.text() and "AAC" in vw.lbl_audio_title.text()
    vw.set_subtitle_text("耳元でささやくテスト\n第二行重なり字幕")
    burner = win.sub_burner_tab
    burner.spin_sub_size.setValue(60)
    burner.combo_sub_align.setCurrentIndex(1)  # 顶部居中 (8)
    burner.spin_sub_margin_v.setValue(50)
    style_dict = burner.style_panel.get_subtitle_style()
    assert style_dict["font_size"] == 60
    assert style_dict["align"] == 8
    assert style_dict["margin_v"] == 50
    v_pix = QPixmap(vw.size())
    vw.render(v_pix)
    # 恢复默认样式
    burner.spin_sub_size.setValue(54)
    burner.combo_sub_align.setCurrentIndex(0)  # 底部居中 (2)
    burner.spin_sub_margin_v.setValue(45)
    win._save_settings_direct()
    print(f"  ✅ 动态音轨徽章 ({vw.lbl_audio_title.text()}) & WYSIWYG 多行样式渲染通过")

    print("=" * 68)
    print("🚀 [6/8] 检验字幕列表实时搜索过滤、增删改与回写保存 (save_subtitle_items)")
    with tempfile.TemporaryDirectory() as tmpdir:
        srt_path = os.path.join(tmpdir, "sample.srt")
        items = [
            {"start": 0.5, "end": 2.5, "text": "こんにちは、ご主人様"},
            {"start": 2.0, "end": 4.0, "text": "今日も一日お疲れ様でした"},
            {"start": 5.0, "end": 7.5, "text": "ゆっくり休んでくださいね"},
        ]
        save_subtitle_items(srt_path, items)
        burner.load_media_and_subtitle("", srt_path)
        assert len(burner.sub_items) == 3

        # 测试重叠字幕同时显示 (pos = 2200ms 处于第1条和第2条交集)
        burner.player_panel._update_subtitle_at_pos(2200)
        assert "こんにちは" in vw.current_subtitle_text and "お疲れ様" in vw.current_subtitle_text, (
            f"Overlapping subtitles not joined: {vw.current_subtitle_text}"
        )

        # 测试搜索过滤
        sub_card = burner.player_panel.sub_list_card
        sub_card.edit_sub_search.setText("お疲れ様")
        hidden_flags = [sub_card.list_subtitles.item(r).isHidden() for r in range(3)]
        assert hidden_flags == [True, False, True], f"Unexpected filter hidden state: {hidden_flags}"
        sub_card.edit_sub_search.setText("")
        assert all(not sub_card.list_subtitles.item(r).isHidden() for r in range(3))

        # 测试保存字幕修改 (Ctrl+S 对应动作)
        burner.sub_items[0]["text"] = "こんばんは、ご主人様"
        sub_card.mark_dirty()
        saved_ok = burner.player_panel.save_current_subtitles()
        assert saved_ok is True
        re_parsed = parse_subtitle_file(srt_path)
        assert re_parsed[0]["text"] == "こんばんは、ご主人様"

        # 测试 ASS 卡拉 OK (\k) 标签在仅微调时间轴、未修改台词文本时 100% 保留
        ass_path = os.path.join(tmpdir, "karaoke.ass")
        with open(ass_path, "w", encoding="utf-8-sig") as f:
            f.write(
                "[Script Info]\nScriptType: v4.00+\n\n"
                "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                "Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,{\\k50}お{\\k60}やすみ\n"
            )
        ass_items = parse_subtitle_file(ass_path)
        assert len(ass_items) == 1 and "\\k50" in ass_items[0].get("raw_ass_text", "")
        ass_items[0]["start_ms"] = 1200  # 仅微调起始时间，不改动台词文本
        save_subtitle_items(ass_path, ass_items)
        with open(ass_path, "r", encoding="utf-8-sig") as f:
            saved_ass_content = f.read()
        assert "{\\k50}お{\\k60}やすみ" in saved_ass_content, f"Karaoke tags lost: {saved_ass_content}"
    print("  ✅ 重叠字幕并排显示、实时搜索过滤、原位保存与 ASS 卡拉OK标签无损保留校验通过")

    print("=" * 68)
    print("🚀 [7/8] 检验 FFmpeg force_style 构建与真实视频硬字幕压制")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_vid = os.path.join(tmpdir, "in.mp4")
        test_srt = os.path.join(tmpdir, "in.srt")
        test_out = os.path.join(tmpdir, "out.mp4")

        import subprocess
        ffmpeg_bin = os.path.join(ROOT_DIR, "bin", "ffmpeg.exe")
        if not os.path.isfile(ffmpeg_bin):
            ffmpeg_bin = "ffmpeg"

        subprocess.run(
            [
                ffmpeg_bin, "-y",
                "-f", "lavfi", "-i", "color=c=black:s=640x360:d=1.5",
                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                "-shortest", "-c:v", "libx264", "-c:a", "aac", test_vid,
            ],
            check=True,
            capture_output=True,
        )
        save_subtitle_items(test_srt, [{"start": 0.1, "end": 1.3, "text": "WYSIWYG 字幕压制测试"}])

        b_cfg = SubBurnerConfig(
            input_video=test_vid,
            input_subtitle=test_srt,
            output_file=test_out,
            mode="hard",
            encoder="libx264",
            cpu_preset="fast",
            use_custom_style=True,
            font_family="Yu Gothic UI",
            font_size=54,
            sub_align=2,
            sub_margin_v=45,
            sub_color_hex="#FFFFFF",
            sub_outline_hex="#000000",
            sub_outline_width=2.5,
        )
        force_clause = build_force_style_clause(b_cfg, is_ass=False)
        assert "Fontname=Yu Gothic UI" in force_clause and "Alignment=2" in force_clause
        cmd = build_ffmpeg_command(b_cfg)
        if os.path.isfile(ffmpeg_bin):
            cmd[0] = ffmpeg_bin
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert res.returncode == 0, f"FFmpeg failed: {res.stderr[-400:]}"
        assert os.path.isfile(test_out) and os.path.getsize(test_out) > 1000
    print("  ✅ FFmpeg force_style 构建与真实硬字幕压制成功")

    print("=" * 68)
    print("🚀 [8/8] 检验批量压制队列调度与快捷键响应")
    with tempfile.TemporaryDirectory() as tmpdir:
        v1 = os.path.join(tmpdir, "a.mp4")
        s1 = os.path.join(tmpdir, "a.ass")
        v2 = os.path.join(tmpdir, "b.mp4")
        s2 = os.path.join(tmpdir, "b.ass")
        for p in (v1, s1, v2, s2):
            with open(p, "w", encoding="utf-8") as f:
                f.write("dummy")
        burner.queue_panel.enqueue_batch_tasks([
            {"video": v1, "sub": s1},
            {"video": v2, "sub": s2},
        ])
        assert len(burner.queue_panel.batch_queue) == 1  # 第1个已自动加载，剩余1个在队列中
        assert not burner.queue_panel.batch_bar.isHidden()
        burner.queue_panel.clear_batch_queue()
        assert len(burner.queue_panel.batch_queue) == 0

    # 检验快捷键事件处理不报错
    ev_right = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Right, Qt.NoModifier)
    burner.keyPressEvent(ev_right)
    burner.player_panel.shutdown()
    print("  ✅ 批量压制队列与快捷键事件校验通过")

    print("=" * 68)
    print("🚀 [9/9] 检验显卡显存档位并发规划 (8G/12G/16G动态/24G/32G) 与分文件字幕预览隔离缓存")
    from core.concurrency_planner import (
        GpuVramSnapshot,
        normalize_nominal_vram_gb,
        calculate_tier_concurrency,
        plan_effective_concurrency,
    )
    assert normalize_nominal_vram_gb(8188) == 8
    assert normalize_nominal_vram_gb(12227) == 12
    assert normalize_nominal_vram_gb(16376) == 16
    assert normalize_nominal_vram_gb(24564) == 24
    assert normalize_nominal_vram_gb(32760) == 32

    assert calculate_tier_concurrency(8, free_gb=6.8) == 1
    assert calculate_tier_concurrency(12, free_gb=10.2) == 2
    assert calculate_tier_concurrency(16, free_gb=13.5) == 3  # 16G 剩余显存够 -> 跑 3 个任务
    assert calculate_tier_concurrency(16, free_gb=10.5) == 2  # 16G 剩余显存紧张 -> 跑 2 个任务
    assert calculate_tier_concurrency(24, free_gb=21.0) == 4
    assert calculate_tier_concurrency(32, free_gb=28.0) == 5
    assert calculate_tier_concurrency(48, free_gb=44.0) == 8
    assert calculate_tier_concurrency(60, free_gb=56.0) == 10
    assert calculate_tier_concurrency(80, free_gb=74.0) == 13
    assert calculate_tier_concurrency(96, free_gb=90.0) == 16

    # 检验下拉框通用文案（不含具体显卡型号）、1~16 路完整选项与滚动行数配置
    auto_item_text = win.combo_concurrency.itemText(0)
    assert "RTX" not in auto_item_text and "5070" not in auto_item_text, f"Auto label should be generic: {auto_item_text}"
    assert win.combo_concurrency.count() == 17, f"Expected 17 concurrency items (0..16), got {win.combo_concurrency.count()}"
    assert win.combo_concurrency.maxVisibleItems() == 6

    snap_5070 = GpuVramSnapshot(
        gpu_name="RTX 5070", raw_name="NVIDIA GeForce RTX 5070",
        total_mb=12227, free_mb=10476, used_mb=1468,
        nominal_gb=12, free_gb=10.23, is_cuda_available=True,
    )
    plan_single = plan_effective_concurrency("cuda", 0, total_files=1, snapshot=snap_5070)
    assert plan_single["effective_workers"] == 1  # 单文件按需分配 1 路
    plan_multi = plan_effective_concurrency("cuda", 0, total_files=5, snapshot=snap_5070)
    assert plan_multi["effective_workers"] == 2  # 多文件在 5070 12G 上分配 2 路
    plan_cpu = plan_effective_concurrency("cpu", 0, total_files=5, snapshot=snap_5070)
    assert plan_cpu["effective_workers"] == 1

    # 校验单大窗 + 顶部任务选择栏 (combo_preview_task) + 自动切换开关 (btn_auto_follow) 逻辑
    buf = win.runner.preview_buffer
    cview = win.progress_panel.concurrent_sub_view
    buf.prepare_batch(["D:/Videos/file_A.mp4", "D:/Videos/file_B.mp4", "D:/Videos/file_C.mp4"])
    assert cview.combo_preview_task.count() == 3
    assert cview.btn_auto_follow.isChecked() is True

    # 1. 启动任务 A 与任务 B (并发)，默认聚焦任务 A，任务 B 静默入库且下拉框显示实时状态
    buf.on_file_started(0, 3, "file_A.mp4")
    buf.on_file_started(1, 3, "file_B.mp4")
    buf.on_segment(0, 1.0, 3.0, "ファイルAの台詞")
    buf.on_segment(1, 2.0, 4.0, "ファイルBの台詞")
    assert "ファイルAの台詞" in win.txt_subtitles.toPlainText()
    assert "ファイルBの台詞" not in win.txt_subtitles.toPlainText()
    assert "正在转录" in cview.combo_preview_task.itemText(0) and "file_A.mp4" in cview.combo_preview_task.itemText(0)
    assert "正在转录" in cview.combo_preview_task.itemText(1) and "file_B.mp4" in cview.combo_preview_task.itemText(1)

    # 2. 用户手动选择观看任务 B 后：自动切换变为关闭 (📌 已固定当前)，后续任务 B 完成或新任务 C 开始均不自动跳转！
    buf.switch_focus(1, pinned_by_user=True)
    assert cview.btn_auto_follow.isChecked() is False
    assert "已固定" in cview.btn_auto_follow.text()
    assert "ファイルBの台詞" in win.txt_subtitles.toPlainText()

    buf.on_file_finished(1, "<div>B done</div>")
    buf.on_file_started(2, 3, "file_C.mp4")
    buf.on_segment(2, 0.5, 2.0, "ファイルCの接力台詞")
    # 验证因用户手动固定了任务 B，即使任务 B 完成且新任务 C 开始，窗口依然停留在任务 B 绝不乱跳！
    assert buf.focused_idx == 1
    assert "ファイルBの台詞" in win.txt_subtitles.toPlainText()
    assert "ファイルCの接力台詞" not in win.txt_subtitles.toPlainText()

    # 3. 当用户重新开启「🔄 自动切换」时，因为任务 B 已结束，立即自动跳转到正在转录的任务 A / C
    buf.set_auto_follow(True)
    assert cview.btn_auto_follow.isChecked() is True
    assert buf.focused_idx in (0, 2)
    buf.clear()
    print("  ✅ 通用文案、1~16路(96GB+)滚动下拉框、单大窗任务选择栏与手动固定防跳转校验 100% 通过")

    if hasattr(win, "gpu_detector") and win.gpu_detector and win.gpu_detector.isRunning():
        win.gpu_detector.wait(2000)
    if hasattr(win, "tray_manager") and win.tray_manager:
        win.tray_manager.cleanup()
    print("=" * 68)
    print("🎉 所有 9 项前端与并发规划深度测试 100% 通过！")
    sys.stdout.flush()


if __name__ == "__main__":
    run_all_checks()
    os._exit(0)
