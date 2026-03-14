from typing import Annotated, Any
from uuid import uuid4
from src.core.components.base.action import BaseAction
from src.core.components.types import ChatType
from src.app.plugin_system.api.log_api import get_logger

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


class TTSVoiceAction(BaseAction):
    """将你生成好的文本转换为语音并发送"""
    action_name = "tts_voice_action"
    action_description = "✨ 用声音与用户对话！将文字转换为温暖、自然的语音发送，让互动更有温度、更真实、更省力！语音对话能带来打字无法比拟的亲密感。注意：只能说话，不能唱歌！"
    chat_type = ChatType.ALL
    
    # 类级别的缓存，用于存储可用的语音风格
    _available_styles: list[str] = []

    @classmethod
    def to_schema(cls) -> dict[str, Any]:
        """动态生成 schema，包含可用的语音风格"""
        from src.core.components.utils.schema_utils import parse_function_signature
        
        # 先获取基础 schema
        schema = parse_function_signature(cls.execute, f"action-{cls.action_name}", cls.action_description)
        
        # 如果有可用风格，动态更新描述
        if cls._available_styles:
            style_list = "、".join(cls._available_styles)
            # 更新 action_description
            schema["function"]["description"] = f"✨ 用声音与用户对话！将文字转换为温暖、自然的语音发送，让互动更有温度、更真实、更省力！语音对话能带来打字无法比拟的亲密感。可用风格：{style_list}。注意：只能说话，不能唱歌！"
            # 更新 voice_style 字段的描述
            if "voice_style" in schema["function"]["parameters"]["properties"]:
                schema["function"]["parameters"]["properties"]["voice_style"]["description"] = f"🎭 选择语音风格来表达不同的情感！可选：{style_list}。根据对话氛围选择合适的风格，会让声音更有感染力！"
        
        return schema

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
        tts_voice_text: Annotated[str, "🎙️ 你要亲口说的话！用自然、口语化、温暖的语气组织语言，就像真的在和朋友聊天一样！加入适当的语气词（呀、呢、哦、啦）会让声音更生动。保持简短亲切，不要太长太书面。注意：只能是说话内容，不能是歌词或唱歌！"],
        voice_style: Annotated[str, "选择语音风格，让你的声音更有感染力！可选风格取决于配置文件中已设置的风格，通常包含 default（自然）等。如果不确定，使用 default 即可。"] = "default",
        text_language: Annotated[str, "根据文本内容选择最合适的语言模式，让发音更准确。可选：auto（自动识别）、zh（中文）、en（英文）、ja（日文）、ko（韩文）。"] = "auto",
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
        return True
