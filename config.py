"""配置组件定义"""
import os
from src.core.components.base.config import BaseConfig, config_section, Field, SectionBase


DEFAULT_TTS_KEYWORDS = [
    "发语音", "语音", "说句话", "用语音说", "听你", "听声音", "想听你", "想听声音",
    "讲个话", "说段话", "念一下", "读一下", "用嘴说", "说", "能发语音吗", "亲口",
]

class TTSConfig(BaseConfig):
    config_name = "config"
    config_description = "TTS 插件配置"

    @config_section("plugin")
    class PluginSection(SectionBase):
        enable: bool = Field(default=True, description="是否启用插件")
        keywords: list[str] = Field(
            default_factory=lambda: list(DEFAULT_TTS_KEYWORDS),
            description="触发语音合成的关键词列表"
        )
        config_version: str = Field(default="3.1.2", description="配置文件版本")

    @config_section("components")
    class ComponentsSection(SectionBase):
        action_enabled: bool = Field(default=True, description="是否启用TTS语音动作")
        command_enabled: bool = Field(default=True, description="是否启用TTS语音命令")

    @config_section("tts")
    class TTSSection(SectionBase):
        server: str = Field(default="http://127.0.0.1:9880", description="GPT-SoVITS API服务器地址")
        timeout: int = Field(default=180, description="请求超时时间（秒）")
        max_text_length: int = Field(default=1000, description="最大文本长度限制")

    # tts_styles 采用动态数组列表配置，目前通过 Pydantic 字典列表来承接
    @config_section("tts_styles")
    class TTSStylesSection(SectionBase):
        styles: list[dict] = Field(
            default=[
                {
                    "style_name": "default",
                    "name": "默认",
                    "refer_wav_path": "assets/reference.wav",
                    "prompt_text": "这是一个示例文本，请替换为您自己的参考音频文本。",
                    "prompt_language": "zh",
                    "gpt_weights": "",
                    "sovits_weights": "",
                    "speed_factor": 1.0,
                    "text_language": "auto"
                }
            ],
            description="TTS风格列表配置"
        )

    @config_section("tts_advanced")
    class TTSAdvancedSection(SectionBase):
        media_type: str = Field(default="wav", description="媒体类型（如wav, mp3等）")
        top_k: int = Field(default=9, description="Top-K采样参数")
        top_p: float = Field(default=0.8, description="Top-P采样参数")
        temperature: float = Field(default=0.8, description="温度参数")
        batch_size: int = Field(default=6, description="批处理大小")
        batch_threshold: float = Field(default=0.75, description="批处理阈值")
        text_split_method: str = Field(default="cut5", description="文本分割方法")
        repetition_penalty: float = Field(default=1.4, description="重复惩罚系数")
        sample_steps: int = Field(default=150, description="采样步数")
        super_sampling: bool = Field(default=True, description="是否启用超采样")

    @config_section("spatial_effects")
    class SpatialEffectsSection(SectionBase):
        enabled: bool = Field(default=False, description="是否启用空间音效处理")
        reverb_enabled: bool = Field(default=False, description="是否启用标准混响效果")
        room_size: float = Field(default=0.2, description="混响的房间大小 (建议范围 0.0-1.0)")
        damping: float = Field(default=0.6, description="混响的阻尼/高频衰减 (建议范围 0.0-1.0)")
        wet_level: float = Field(default=0.3, description="混响的湿声（效果声）比例 (建议范围 0.0-1.0)")
        dry_level: float = Field(default=0.8, description="混响的干声（原声）比例 (建议范围 0.0-1.0)")
        width: float = Field(default=1.0, description="混响的立体声宽度 (建议范围 0.0-1.0)")
        convolution_enabled: bool = Field(default=False, description="是否启用卷积混响")
        convolution_mix: float = Field(default=0.7, description="卷积混响的干湿比 (建议范围 0.0-1.0)")

    plugin: PluginSection = Field(default_factory=PluginSection)
    components: ComponentsSection = Field(default_factory=ComponentsSection)
    tts: TTSSection = Field(default_factory=TTSSection)
    tts_styles: TTSStylesSection = Field(default_factory=TTSStylesSection)
    tts_advanced: TTSAdvancedSection = Field(default_factory=TTSAdvancedSection)
    spatial_effects: SpatialEffectsSection = Field(default_factory=SpatialEffectsSection)

    def generate_config_file(self, output_path: str = "config.toml") -> None:
        """
        生成美观的TOML配置文件
        
        Args:
            output_path: 输出文件路径，默认为"config.toml"
        """
        # 获取插件文件路径
        plugin_file = os.path.abspath(__file__)
        plugin_dir = os.path.dirname(plugin_file)
        
        # 构建完整的输出路径
        if not os.path.isabs(output_path):
            output_path = os.path.join(plugin_dir, output_path)
        
        # 生成配置内容
        config_content = self._generate_config_content()
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print(f"配置文件已生成: {output_path}")

    def _generate_config_content(self) -> str:
        """生成配置文件内容"""
        raw_keywords = getattr(self.plugin, "keywords", None)
        if isinstance(raw_keywords, list):
            keywords = [k.strip() for k in raw_keywords if isinstance(k, str) and k.strip()]
        else:
            keywords = []
        if not keywords:
            keywords = list(DEFAULT_TTS_KEYWORDS)

        keyword_lines = []
        for i in range(0, len(keywords), 8):
            chunk = keywords[i:i + 8]
            line = ", ".join(f'"{kw}"' for kw in chunk)
            if i + 8 < len(keywords):
                line += ","
            keyword_lines.append(f"    {line}")

        content = [
            "# TTS语音插件配置文件",
            "# 请根据实际情况修改配置",
            "",
            "[plugin]",
            "# 是否启用插件",
            f"enable = {self.plugin.enable}",
            "",
            "# 触发语音合成的关键词列表",
            "keywords = [",
            *keyword_lines,
            "]",
            "",
            f"# 配置文件版本",
            f'config_version = "{self.plugin.config_version}"',
            "",
            "[components]",
            "# 是否启用TTS语音动作",
            f"action_enabled = {self.components.action_enabled}",
            "",
            "# 是否启用TTS语音命令",
            f"command_enabled = {self.components.command_enabled}",
            "",
            "[tts]",
            "# GPT-SoVITS API服务器地址",
            f'server = "{self.tts.server}"',
            "",
            "# 请求超时时间（秒）",
            f"timeout = {self.tts.timeout}",
            "",
            "# 最大文本长度限制",
            f"max_text_length = {self.tts.max_text_length}",
            "",
            "[tts_styles]",
            "# TTS风格列表配置",
            "styles = [",
        ]
        
        # 添加风格配置
        for style in self.tts_styles.styles:
            content.extend([
                "    {",
                f'        style_name = "{style["style_name"]}"',
                f'        name = "{style["name"]}"',
                "",
                "# 参考音频文件路径",
                f'        refer_wav_path = "{style["refer_wav_path"]}"',
                "",
                "# 参考音频的文本内容",
                f'        prompt_text = "{style["prompt_text"]}"',
                "",
                "# 参考音频的语言",
                f'        prompt_language = "{style["prompt_language"]}"',
                "",
                "# GPT模型权重文件路径（留空表示使用默认）",
                f'        gpt_weights = "{style["gpt_weights"]}"',
                "",
                "# SoVITS模型权重文件路径（留空表示使用默认）",
                f'        sovits_weights = "{style["sovits_weights"]}"',
                "",
                "# 语速因子",
                f'        speed_factor = {style["speed_factor"]}',
                "",
                "# 文本语言模式",
                f'        text_language = "{style["text_language"]}"',
                "    },",
            ])
        
        # 添加高级配置
        content.extend([
            "]",
            "",
            "[tts_advanced]",
            "# 媒体类型（如wav, mp3等）",
            f'media_type = "{self.tts_advanced.media_type}"',
            "",
            "# Top-K采样参数",
            f"top_k = {self.tts_advanced.top_k}",
            "",
            "# Top-P采样参数",
            f"top_p = {self.tts_advanced.top_p}",
            "",
            "# 温度参数",
            f"temperature = {self.tts_advanced.temperature}",
            "",
            "# 批处理大小",
            f"batch_size = {self.tts_advanced.batch_size}",
            "",
            "# 批处理阈值",
            f"batch_threshold = {self.tts_advanced.batch_threshold}",
            "",
            "# 文本分割方法",
            f'text_split_method = "{self.tts_advanced.text_split_method}"',
            "",
            "# 重复惩罚系数",
            f"repetition_penalty = {self.tts_advanced.repetition_penalty}",
            "",
            "# 采样步数",
            f"sample_steps = {self.tts_advanced.sample_steps}",
            "",
            "# 是否启用超采样",
            f"super_sampling = {self.tts_advanced.super_sampling}",
            "",
            "[spatial_effects]",
            "# 是否启用空间音效处理",
            f"enabled = {self.spatial_effects.enabled}",
            "",
            "# 是否启用标准混响效果",
            f"reverb_enabled = {self.spatial_effects.reverb_enabled}",
            "",
            "# 混响的房间大小 (建议范围 0.0-1.0)",
            f"room_size = {self.spatial_effects.room_size}",
            "",
            "# 混响的阻尼/高频衰减 (建议范围 0.0-1.0)",
            f"damping = {self.spatial_effects.damping}",
            "",
            "# 混响的湿声（效果声）比例 (建议范围 0.0-1.0)",
            f"wet_level = {self.spatial_effects.wet_level}",
            "",
            "# 混响的干声（原声）比例 (建议范围 0.0-1.0)",
            f"dry_level = {self.spatial_effects.dry_level}",
            "",
            "# 混响的立体声宽度 (建议范围 0.0-1.0)",
            f"width = {self.spatial_effects.width}",
            "",
            "# 是否启用卷积混响",
            f"convolution_enabled = {self.spatial_effects.convolution_enabled}",
            "",
            "# 卷积混响的干湿比 (建议范围 0.0-1.0)",
            f"convolution_mix = {self.spatial_effects.convolution_mix}",
        ])
        
        return "\n".join(content)
