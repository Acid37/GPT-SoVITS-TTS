from typing import Annotated
from uuid import uuid4
from src.core.components.base.action import BaseAction
from src.core.components.types import ChatType
from src.app.plugin_system.api.log_api import get_logger
from pydantic import BaseModel, Field

from ..config import TTSConfig
from ..services.tts_service import TTSService

# 导入Neo-MoFox项目中的语音缓存和发送工具
try:
    from src.app.plugin_system.api.send_api import send_voice
    HAS_TOOLS = True
except ImportError as e:
    logger = get_logger("tts_voice_plugin.action")
    logger.warning(f"无法导入语音工具: {e}，将使用备用方案")
    HAS_TOOLS = False

logger = get_logger("tts_voice_plugin.action")


class TTSVoiceActionSchema(BaseModel):
    """TTS语音动作参数模式"""
    tts_voice_text: str = Field(
        ...,
        description="需要转换为语音并发送的完整、自然、适合口语的文本内容。注意：只能是说话内容，不能是歌词或唱歌！"
    )
    voice_style: str = Field(
        "default",
        description="语音的风格。请根据对话的情感和上下文选择一个最合适的风格。如果未提供，将使用默认风格。"
    )
    text_language: str = Field(
        "auto",
        description="指定用于合成的语言模式，请务必根据文本内容选择最精确、范围最小的选项以获得最佳效果。"
    )


class TTSVoiceAction(BaseAction):
    """将你生成好的文本转换为语音并发送"""
    action_name = "tts_voice_action"
    action_description = "将你生成好的文本转换为语音并发送。注意：这是纯语音合成，只能说话，不能唱歌！"
    chat_type = ChatType.ALL
    schema = TTSVoiceActionSchema

    def _get_config(self) -> TTSConfig | None:
        cfg = getattr(self.plugin, "config", None)
        return cfg if isinstance(cfg, TTSConfig) else None

    def _is_action_enabled(self) -> bool:
        cfg = self._get_config()
        if not cfg:
            return False
        return bool(cfg.plugin.enable and cfg.components.action_enabled)

    async def execute(
        self,
        tts_voice_text: Annotated[str, "需要转换为语音并发送的完整、自然、适合口语的文本内容。注意：只能是说话内容，不能是歌词或唱歌！"],
        voice_style: Annotated[str, "语音的风格。请根据对话的情感和上下文选择一个最合适的风格。如果未提供，将使用默认风格。"] = "default",
        text_language: Annotated[str, "指定用于合成的语言模式，请务必根据文本内容选择最精确、范围最小的选项以获得最佳效果。"] = "auto",
        **kwargs
    ) -> tuple[bool, str]:
        if not self._is_action_enabled():
            return False, "TTS 语音动作未启用（plugin.enable/components.action_enabled）"
        
        service: TTSService | None = self.plugin.get_service("tts_service")
        if not service:
            return False, "TTS服务不可用"
        
        audio_b64 = await service.generate_voice(
            text=tts_voice_text,
            style_hint=voice_style,
            language_hint=text_language
        )
        
        if audio_b64:
            try:
                # 使用Neo-MoFox的语音发送API
                if HAS_TOOLS:
                    # 直接使用send_voice API发送语音
                    success = await send_voice(
                        voice_data=audio_b64,
                        stream_id=self.chat_stream.stream_id,
                        platform=self.chat_stream.platform
                    )
                    if success:
                        logger.info("语音发送成功")
                        return True, f"成功生成并发送语音，文本长度: {len(tts_voice_text)}字符"
                    else:
                        logger.error("语音发送失败")
                        return False, "发送语音失败"
                else:
                    # 备用方案：使用基类的发送方法
                    from src.core.models.message import Message, MessageType
                    
                    # 创建语音消息
                    voice_message = Message(
                        message_id=f"tts_{uuid4().hex}",
                        content=audio_b64,
                        processed_plain_text=tts_voice_text,  # 存储原始文本
                        message_type=MessageType.VOICE,
                        platform=self.chat_stream.platform,
                        chat_type=self.chat_stream.chat_type,
                        stream_id=self.chat_stream.stream_id,
                        sender_id=self.chat_stream.context.triggering_user_id or "",
                        sender_name="Bot"
                    )
                    
                    # 发送语音消息
                    success = await self._send_to_stream(voice_message)
                    if success:
                        logger.info("语音发送成功")
                        return True, f"成功生成并发送语音，文本长度: {len(tts_voice_text)}字符"
                    else:
                        logger.error("语音发送失败")
                        return False, "发送语音失败"
            except Exception as e:
                logger.error(f"发送语音失败: {e}")
                return False, f"发送语音失败: {e}"
        return False, "语音合成失败"

    async def go_activate(self) -> bool:
        if not self._is_action_enabled():
            return False

        # 激活条件: 关键词或随机
        cfg = self._get_config()
        keywords = cfg.plugin.keywords if cfg else []

        if await self._keyword_match(keywords):
            return True
        if await self._random_activation(0.25):
            return True
            
        action_require = [
            "【核心限制】此动作只能用于说话，绝对不能用于唱歌！TTS无法发出有音调的歌声，只会输出平淡的念白。如果用户要求唱歌，不要使用此动作！",
            "在调用此动作时，你必须在 'tts_voice_text' 参数中提供要合成语音的完整回复内容。这是强制性的。",
            "当用户明确请求使用语音进行回复时，例如'发个语音听听'、'用语音说'等。"
        ]
        if await self._llm_judge_activation(action_require=action_require):
            return True
        return False
