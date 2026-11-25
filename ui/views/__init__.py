# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - UI 子视图与业务面板组件包
包含主窗口顶栏/底栏、转录任务队列、配置卡片、进度日志监控以及字幕压制播放器、规格栏、样式与配对队列子面板
"""

from ui.views.app_header_footer import AppHeaderBar, AppFooterBar
from ui.views.transcribe_queue_panel import TranscribeQueuePanel
from ui.views.transcribe_config_panel import TranscribeConfigPanel
from ui.views.transcribe_progress_panel import TranscribeProgressPanel
from ui.views.transcribe_model_card import TranscribeModelCard
from ui.views.transcribe_prompt_card import TranscribePromptCard
from ui.views.transcribe_advanced_card import TranscribeAdvancedCard
from ui.controllers.transcribe_runner import TranscribeRunner
from ui.controllers.settings_sync import SettingsSync
from ui.workers.gpu_detector import detect_gpu_environment

from ui.views.burner_player_panel import BurnerPlayerPanel
from ui.views.burner_ctrl_bar import BurnerCtrlBar
from ui.views.burner_media_spec_bar import TimelineDialogueBanner, MediaSpecBar
from ui.views.burner_sub_list_card import BurnerSubListCard
from ui.views.burner_style_panel import BurnerStylePanel
from ui.views.burner_queue_panel import BurnerQueuePanel
from ui.controllers.tray_manager import TrayMenuManager, TrayStatusHeader, TrayMenu

__all__ = [
    "AppHeaderBar",
    "AppFooterBar",
    "TranscribeQueuePanel",
    "TranscribeConfigPanel",
    "TranscribeProgressPanel",
    "TranscribeModelCard",
    "TranscribePromptCard",
    "TranscribeAdvancedCard",
    "TranscribeRunner",
    "SettingsSync",
    "detect_gpu_environment",
    "BurnerPlayerPanel",
    "BurnerCtrlBar",
    "TimelineDialogueBanner",
    "MediaSpecBar",
    "BurnerSubListCard",
    "BurnerStylePanel",
    "BurnerQueuePanel",
    "TrayMenuManager",
    "TrayStatusHeader",
    "TrayMenu",
]
