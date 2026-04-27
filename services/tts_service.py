import asyncio
import base64
import io
import os
import re
from typing import Any

import aiohttp
import numpy as np
import soundfile as sf

# 可选依赖：pedalboard 用于空间音效处理
try:
    from pedalboard import Convolution, Pedalboard, Reverb
    from pedalboard.io import AudioFile
    HAS_PEDALBOARD = True
except ImportError:
    HAS_PEDALBOARD = False
    Convolution = None
    Pedalboard = None
    Reverb = None
    AudioFile = None

from src.core.components.base.service import BaseService
from src.core.components.base.plugin import BasePlugin
from src.app.plugin_system.api.log_api import get_logger

from ..config import TTSConfig

logger = get_logger("tts_voice_plugin.service")

class TTSService(BaseService):
    """封装了TTS合成的核心逻辑"""
    service_name = "tts_service"
    service_description = "TTS 核心服务"
    version = "1.0.0"

    def __init__(self, plugin: BasePlugin) -> None:
        super().__init__(plugin)
        self.tts_styles: dict[str, Any] = {}
        # Get config from plugin instance
        self.config: TTSConfig = getattr(self.plugin, "config", None)
        self.timeout = 180
        self.max_text_length = 500
        self._load_config()

    def _get_reference_audio_path(self, refer_wav_path: str) -> str | None:
        """获取参考音频文件的完整路径"""
        try:
            # 如果是绝对路径，直接使用
            if os.path.isabs(refer_wav_path):
                return refer_wav_path
            
            # 如果是相对路径，基于项目根目录构建
            plugin_file = os.path.abspath(__file__)
            # services -> tts_voice_plugin -> plugins -> Bot
            bot_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(plugin_file))))
            full_path = os.path.join(bot_root, refer_wav_path)
            
            # 检查文件是否存在
            if os.path.exists(full_path):
                logger.info(f"找到参考音频文件: {full_path}")
                return full_path
            else:
                logger.warning(f"参考音频文件不存在: {full_path}")
                # 尝试在插件目录中查找
                plugin_dir = os.path.dirname(plugin_file)
                plugin_assets = os.path.join(plugin_dir, refer_wav_path)
                if os.path.exists(plugin_assets):
                    logger.info(f"在插件目录中找到参考音频文件: {plugin_assets}")
                    return plugin_assets
                else:
                    logger.error(f"在所有位置都未找到参考音频文件: {refer_wav_path}")
                    return None
        except Exception as e:
            logger.error(f"处理参考音频路径时出错: {e}")
            return None

    def _load_config(self) -> None:
        """加载配置"""
        if not self.config:
            logger.warning("TTSService 无法获取配置")
            return
            
        try:
            self.timeout = self.config.tts.timeout
            self.max_text_length = self.config.tts.max_text_length
            self.tts_styles = self._load_tts_styles()
            if self.tts_styles:
                logger.info(f"TTS服务已成功加载风格: {list(self.tts_styles.keys())}")
            else:
                logger.warning("TTS风格配置为空，请检查配置文件")
        except Exception as e:
            logger.error(f"TTS服务配置加载失败: {e}")

    def _load_tts_styles(self) -> dict[str, dict[str, Any]]:
        """加载 TTS 风格配置"""
        styles = {}
        if not self.config:
            return styles
            
        global_server = self.config.tts.server
        tts_styles_config = self.config.tts_styles.styles

        # 兼容 dict 和 TTSStyleSection 实例两种形态
        def _get(style, key, default=None):
            if isinstance(style, dict):
                return style.get(key, default)
            return getattr(style, key, default)

        default_cfg = next((s for s in tts_styles_config if _get(s, "style_name") == "default"), None)
        if not default_cfg:
            logger.error("在 tts_styles 配置中未找到 'default' 风格，这是必需的。")
            return styles

        default_refer_wav = _get(default_cfg, "refer_wav_path", "")
        default_prompt_text = _get(default_cfg, "prompt_text", "")
        default_gpt_weights = _get(default_cfg, "gpt_weights", "")
        default_sovits_weights = _get(default_cfg, "sovits_weights", "")

        for style_cfg in tts_styles_config:
            style_name = _get(style_cfg, "style_name")
            if not style_name:
                continue

            styles[style_name] = {
                "url": global_server,
                "name": _get(style_cfg, "name", style_name),
                "refer_wav_path": _get(style_cfg, "refer_wav_path", default_refer_wav),
                "prompt_text": _get(style_cfg, "prompt_text", default_prompt_text),
                "prompt_language": _get(style_cfg, "prompt_language", "zh"),
                "gpt_weights": _get(style_cfg, "gpt_weights", default_gpt_weights),
                "sovits_weights": _get(style_cfg, "sovits_weights", default_sovits_weights),
                "speed_factor": _get(style_cfg, "speed_factor", 1.0),
                "text_language": _get(style_cfg, "text_language", "auto"),
            }
        return styles

    def get_available_styles(self) -> list[str]:
        return list(self.tts_styles.keys()) if self.tts_styles else ['default']

    def _determine_final_language(self, text: str, mode: str) -> str:
        """根据配置的语言策略和文本内容，决定最终发送给API的语言代码"""
        # 如果策略是具体的语言（如 all_zh, ja），直接使用
        if mode not in ["auto", "auto_yue"]:
            return mode

        # 对于 auto 和 auto_yue 策略，进行内容检测
        # 优先检测粤语
        if mode == "auto_yue":
            cantonese_keywords = ["嘅", "喺", "咗", "唔", "係", "啲", "咩", "乜", "喂"]
            if any(keyword in text for keyword in cantonese_keywords):
                logger.info("在 auto_yue 模式下检测到粤语关键词，最终语言: yue")
                return "yue"

        # 检测日语（简单启发式规则）
        japanese_chars = len(re.findall(r"[\u3040-\u309f\u30a0-\u30ff]", text))
        if japanese_chars > 5 and japanese_chars > len(re.findall(r"[\u4e00-\u9fff]", text)) * 0.5:
            logger.info("检测到日语字符，最终语言: ja")
            return "ja"

        # 默认回退到中文
        logger.info(f"在 {mode} 模式下未检测到特定语言，默认回退到: zh")
        return "zh"

    def _clean_text_for_tts(self, text: str) -> str:
        # 1. 基本清理
        text = re.sub(r"[\(（\[【].*?[\)）\]】]", "", text)
        text = re.sub(r"([，。！？、；：,.!?;:~\-`])\1+", r"\1", text)
        text = re.sub(r"~{2,}|～{2,}", "，", text)
        text = re.sub(r"\.{3,}|…{1,}", "。", text)

        # 2. 词语替换
        replacements = {"www": "哈哈哈", "hhh": "哈哈", "233": "哈哈", "666": "厉害", "88": "拜拜"}
        for old, new in replacements.items():
            text = text.replace(old, new)

        # 3. 移除不必要的字符
        text = re.sub(r"[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ffa-zA-Z0-9\s，。！？、；：,.!?;:~～]", "", text)

        # 4. 确保结尾有标点
        if text and not text.endswith(tuple("，。！？、；：,.!?;:")):
            text += "。"

        # 5. 智能截断
        if len(text) > self.max_text_length:
            cut_text = text[:self.max_text_length]
            punctuation = "。！？.…"
            last_punc_pos = max(cut_text.rfind(p) for p in punctuation)

            if last_punc_pos != -1:
                text = cut_text[:last_punc_pos + 1]
            else:
                last_comma_pos = max(cut_text.rfind(p) for p in "，、；,;")
                if last_comma_pos != -1:
                    text = cut_text[:last_comma_pos + 1]
                else:
                    text = cut_text

        return text.strip()

    async def _call_tts_api(self, server_config: dict, text: str, text_language: str, **kwargs) -> bytes | None:
        """
        最终修复版：先切换模型，然后尝试多个可能的TTS端点
        """
        ref_wav_path = kwargs.get("refer_wav_path")
        if not ref_wav_path:
            logger.error(f"API 调用失败：缺少 refer_wav_path。当前风格配置: {server_config}")
            return None
            
        # 处理参考音频路径
        full_ref_path = self._get_reference_audio_path(ref_wav_path)
        if not full_ref_path:
            logger.error(f"无法找到参考音频文件: {ref_wav_path}")
            return None
            
        try:
            base_url = server_config["url"].rstrip("/")

            # --- 步骤一：像稳定版一样，先切换模型 ---
            async def switch_model_weights(weights_path: str | None, weight_type: str):
                if not weights_path:
                    return
                api_endpoint = f"/set_{weight_type}_weights"
                switch_url = f"{base_url}{api_endpoint}"
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                        async with session.get(switch_url, params={"weights_path": weights_path}) as resp:
                            if resp.status != 200:
                                error_text = await resp.text()
                                logger.error(f"切换 {weight_type} 模型失败: {resp.status} - {error_text}")
                            else:
                                logger.info(f"成功切换 {weight_type} 模型为: {weights_path}")
                except Exception as e:
                    logger.error(f"请求切换 {weight_type} 模型时发生网络异常: {e}")

            await switch_model_weights(kwargs.get("gpt_weights"), "gpt")
            await switch_model_weights(kwargs.get("sovits_weights"), "sovits")

            # --- 步骤二：构建纯净的、不含Base64的请求数据 ---
            data = {
                "text": text,
                "text_lang": text_language,
                "ref_audio_path": full_ref_path,
                "prompt_text": kwargs.get("prompt_text", ""),
                "prompt_lang": kwargs.get("prompt_language", "zh"),
                # 在稳定版中，这两个参数是通过API切换的，而不是直接放在请求体里
                # "gpt_model_path": kwargs.get("gpt_weights"),
                # "sovits_model_path": kwargs.get("sovits_weights"),
            }

            # 合并高级配置
            if self.config and hasattr(self.config, 'tts_advanced'):
                advanced_config = self.config.tts_advanced.model_dump()
                if isinstance(advanced_config, dict):
                    data.update({k: v for k, v in advanced_config.items() if v is not None})

            # 优先使用风格特定的语速
            if server_config.get("speed_factor") is not None:
                data["speed_factor"] = server_config["speed_factor"]

            # --- 步骤三：尝试多个可能的TTS端点 ---
            # 原版插件尝试了三个端点，按优先级排序
            possible_endpoints = [ "/tts", "/infer_single/tts",  "/infer_single"]
            
            for endpoint in possible_endpoints:
                test_url = f"{base_url}{endpoint}"
                logger.info(f"尝试TTS端点: {test_url}")
                
                try:
                    if endpoint == "/tts":
                        # 对于 /tts 端点，修复语言代码格式
                        endpoint_data = data.copy()
                        # 修复语言代码格式：zh-CN -> zh
                        if endpoint_data.get("text_lang") == "zh-CN":
                            endpoint_data["text_lang"] = "zh"
                        
                        async with aiohttp.ClientSession() as session:
                            async with session.post(test_url, json=endpoint_data, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                                if response.status == 200:
                                    logger.info(f"成功使用POST请求到 {test_url}")
                                    return await response.read()
                                else:
                                    error_text = await response.text()
                                    logger.warning(f"POST请求到 {test_url} 失败: {response.status} - {error_text}")
                    else:
                        # 对于 /infer_single 端点，修复布尔值参数问题
                        params = data.copy()
                        # 移除布尔值参数
                        params = {k: v for k, v in params.items() if isinstance(v, (str, int, float))}
                        
                        async with aiohttp.ClientSession() as session:
                            async with session.get(test_url, params=params, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                                if response.status == 200:
                                    logger.info(f"成功使用GET请求到 {test_url}")
                                    return await response.read()
                                else:
                                    error_text = await response.text()
                                    logger.warning(f"GET请求到 {test_url} 失败: {response.status} - {error_text}")
                                    
                except Exception as e:
                    logger.warning(f"请求 {test_url} 时发生异常: {e}")
                    continue
            
            logger.error(f"所有TTS端点尝试失败")
            return None
        except asyncio.TimeoutError:
            logger.error("TTS服务请求超时")
            return None
        except Exception as e:
            logger.error(f"TTS API调用异常: {e}")
            return None

    async def _apply_spatial_audio_effect(self, audio_data: bytes) -> bytes | None:
        """根据配置应用空间效果（混响和卷积）"""
        try:
            if not self.config:
                return audio_data
                
            effects_config = self.config.spatial_effects
            if not effects_config.enabled:
                return audio_data

            # 获取插件目录和IR文件路径
            # 基于 __file__ 构建稳健的、独立于当前工作目录的路径
            plugin_file = os.path.abspath(__file__)
            # services -> tts_voice_plugin -> plugins -> Bot
            bot_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(plugin_file))))
            ir_path = os.path.join(bot_root, "assets", "small_room_ir.wav")

            effects = []

            # 根据配置添加Reverb效果
            if effects_config.reverb_enabled:
                effects.append(Reverb(
                    room_size=effects_config.room_size,
                    damping=effects_config.damping,
                    wet_level=effects_config.wet_level,
                    dry_level=effects_config.dry_level,
                    width=effects_config.width
                ))

            # 根据配置添加Convolution效果
            if effects_config.convolution_enabled and os.path.exists(ir_path):
                effects.append(Convolution(
                    impulse_response_filename=ir_path,
                    mix=effects_config.convolution_mix
                ))
            elif effects_config.convolution_enabled:
                logger.warning(f"卷积混响已启用，但IR文件不存在 ({ir_path})，跳过该效果。")

            if not effects:
                return audio_data

            # 将原始音频数据加载到内存中的 AudioFile 对象
            with io.BytesIO(audio_data) as audio_stream:
                with AudioFile(audio_stream, "r") as f:
                    board = Pedalboard(effects)
                    effected = board(f.read(f.frames), f.samplerate)

            # 将处理后的音频数据写回内存中的字节流
            with io.BytesIO() as output_stream:
                # 使用 soundfile 写入，因为它更稳定
                sf.write(output_stream, effected.T, f.samplerate, format="WAV")
                processed_audio_data = output_stream.getvalue()

            logger.info("成功应用空间效果。")
            return processed_audio_data

        except Exception as e:
            logger.error(f"应用空间效果时出错: {e}")
            return audio_data  # 如果出错，返回原始音频

    async def generate_voice(self, text: str, style_hint: str = "default", language_hint: str | None = None) -> str | None:
        self._load_config()

        if not self.tts_styles:
            logger.error("TTS风格配置为空，无法生成语音。")
            return None

        style = style_hint if style_hint in self.tts_styles else "default"
        if style not in self.tts_styles:
            if "default" in self.tts_styles:
                style = "default"
                logger.warning(f"指定风格 '{style_hint}' 不存在，自动回退到: 'default'")
            elif self.tts_styles:
                style = next(iter(self.tts_styles))
                logger.warning(f"指定风格 '{style_hint}' 和 'default' 均不存在，自动回退到第一个可用风格: {style}")
            else:
                logger.error("没有任何可用的TTS风格配置")
                return None

        server_config = self.tts_styles[style]
        clean_text = self._clean_text_for_tts(text)
        if not clean_text:
            return None

        # 语言决策流程：
        # 1. 优先使用决策模型直接指定的 language_hint (最高优先级)
        if language_hint:
            final_language = language_hint
            logger.info(f"使用决策模型指定的语言: {final_language}")
        else:
            # 2. 如果模型未指定，则使用风格配置的 language_policy
            language_policy = server_config.get("text_language", "auto")
            final_language = self._determine_final_language(clean_text, language_policy)
            logger.info(f"决策模型未指定语言，使用策略 '{language_policy}' -> 最终语言: {final_language}")

        logger.info(f"开始TTS语音合成，文本：{clean_text[:50]}..., 风格：{style}, 最终语言: {final_language}")

        audio_data = await self._call_tts_api(
            server_config=server_config, text=clean_text, text_language=final_language,
            refer_wav_path=server_config.get("refer_wav_path"),
            prompt_text=server_config.get("prompt_text"),
            prompt_language=server_config.get("prompt_language"),
            gpt_weights=server_config.get("gpt_weights"),
            sovits_weights=server_config.get("sovits_weights"),
        )

        if audio_data:
            # 检查是否启用空间音频效果
            if self.config and self.config.spatial_effects.enabled:
                logger.info("检测到已启用空间音频效果，开始处理...")
                processed_audio = await self._apply_spatial_audio_effect(audio_data)
                if processed_audio:
                    logger.info("空间音频效果应用成功！")
                    audio_data = processed_audio
                else:
                    logger.warning("空间音频效果应用失败，将使用原始音频。")

            # 确保音频是标准格式（16kHz, 16bit, 单声道）
            try:
                with io.BytesIO(audio_data) as audio_stream:
                    data, samplerate = sf.read(audio_stream)
                    
                    # 转换为单声道
                    if len(data.shape) > 1:
                        data = data.mean(axis=1)
                    
                    # 重采样到 16kHz（如果不是）
                    if samplerate != 16000:
                        # 简单的线性重采样
                        old_length = len(data)
                        new_length = int(old_length * 16000 / samplerate)
                        indices = np.linspace(0, old_length - 1, new_length)
                        data = np.interp(indices, np.arange(old_length), data)
                    
                    # 转换为 16bit PCM
                    data = (data * 32767).astype(np.int16)
                    
                    # 写回 bytes
                    with io.BytesIO() as output_stream:
                        sf.write(output_stream, data, 16000, format="WAV", subtype="PCM_16")
                        audio_data = output_stream.getvalue()
                        
            except Exception as e:
                logger.warning(f"音频格式转换失败（将继续使用原始音频）: {e}")
            
            return base64.b64encode(audio_data).decode("utf-8")
        return None
