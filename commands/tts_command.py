from src.core.components.base.command import BaseCommand, cmd_route
from src.app.plugin_system.api.send_api import send_voice, send_text

from ..services.tts_service import TTSService
from ..config import TTSConfig

class TTSVoiceCommand(BaseCommand):
    """TTS 语音合成命令"""
    command_name = "tts"
    command_description = "使用GPT-SoVITS将文本转换为语音并发送"
    command_prefix = "/"

    def _get_config(self) -> TTSConfig | None:
        cfg = getattr(self.plugin, "config", None)
        return cfg if isinstance(cfg, TTSConfig) else None

    def _is_command_enabled(self) -> bool:
        cfg = self._get_config()
        if not cfg:
            return False
        return bool(cfg.plugin.enable and cfg.components.command_enabled)

    @cmd_route()
    async def handle_tts(self, text: str, style: str = "default") -> tuple[bool, str]:
        """将文本转换为语音并发送"""
        if not self._is_command_enabled():
            await send_text("TTS 命令未启用（plugin.enable/components.command_enabled）", self.stream_id)
            return False, "TTS 命令未启用"

        if not text:
            await send_text("请提供要转换为语音的文本内容哦！", self.stream_id)
            return False, "文本内容为空"

        service: TTSService | None = self.plugin.get_service("tts_service")
        if not service:
            return False, "TTS服务不可用"
        
        audio_b64 = await service.generate_voice(text, style_hint=style)
        
        if audio_b64:
            await send_voice(voice_data=audio_b64, stream_id=self.stream_id)
            return True, "语音发送成功"
        else:
            await send_text("❌ 语音合成失败，请检查服务状态或配置。", self.stream_id)
            return False, "语音合成失败"

    @cmd_route("生成配置")
    async def handle_generate_config(self, output_path: str = "config.toml") -> tuple[bool, str]:
        """生成TTS配置文件"""
        try:
            config = TTSConfig()
            config.generate_config_file(output_path)
            await send_text(f"✅ 配置文件已成功生成: {output_path}", self.stream_id)
            return True, f"配置文件已生成: {output_path}"
        except Exception as e:
            error_msg = f"生成配置文件失败: {str(e)}"
            await send_text(f"❌ {error_msg}", self.stream_id)
            return False, error_msg
