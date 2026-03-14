"""TTS Voice 插件"""
from src.core.components.base.plugin import BasePlugin
from src.core.components.loader import register_plugin
from src.app.plugin_system.api.log_api import get_logger

from .config import TTSConfig
from .actions.tts_action import TTSVoiceAction
from .commands.tts_command import TTSVoiceCommand
from .services.tts_service import TTSService

logger = get_logger("tts_voice_plugin")

# ─── Plugin：根组件 ───────────────────────────────────────────
@register_plugin
class TTSVoicePlugin(BasePlugin):
    """GPT-SoVITS 语音合成插件"""
    plugin_name = "tts_voice_plugin"
    plugin_description = "基于GPT-SoVITS的文本转语音插件"
    plugin_version = "1.0.0"
    
    # 注入配置类
    configs = [TTSConfig]

    def __init__(self, config=None):
        super().__init__(config)
        self._services: dict[str, object] = {}

    def register_service(self, name: str, service_instance: object) -> None:
        """注册服务实例"""
        self._services[name] = service_instance

    def get_service(self, name: str) -> object | None:
        """获取服务实例"""
        return self._services.get(name)

    def get_components(self) -> list[type]:
        # 返回所有组件，不依赖配置动态加载
        return [
            TTSService,
            TTSVoiceAction,
            TTSVoiceCommand,
        ]

    async def on_plugin_loaded(self) -> None:
        config = getattr(self, "config", None)
        plugin_enabled = bool(getattr(getattr(config, "plugin", None), "enable", False))

        if not plugin_enabled:
            logger.info(f"插件 {self.plugin_name} 已加载，但当前为禁用状态（plugin.enable=false）")
            return

        # 初始化并注册 TTS 服务
        tts_service = TTSService(self)
        self.register_service("tts_service", tts_service)
        logger.info(f"插件 {self.plugin_name} 加载完成！TTS 服务已注册")

        # 动态更新 TTSVoiceAction 的描述，让 LLM 知道可用的语音风格
        try:
            from .actions.tts_action import TTSVoiceAction
            available_styles = tts_service.get_available_styles()
            if available_styles:
                # 设置类级别的可用风格
                TTSVoiceAction._available_styles = available_styles
                style_list = "、".join(available_styles)
                logger.info(f"已动态更新 TTSVoiceAction 可用风格: {style_list}")
        except Exception as e:
            logger.warning(f"动态更新 TTSVoiceAction 描述失败: {e}")
