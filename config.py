"""配置组件定义"""
from src.core.components.base.config import BaseConfig, config_section, Field, SectionBase


DEFAULT_TTS_KEYWORDS = [
    "发语音", "语音", "说句话", "用语音说", "听你", "听声音", "想听你", "想听声音",
    "讲个话", "说段话", "念一下", "读一下", "用嘴说", "说", "能发语音吗", "亲口",
]


class TTSStyleSection(SectionBase):
    """单个 TTS 语音风格配置"""
    style_name: str = Field(default="default", description="风格标识名称（唯一）")
    name: str = Field(default="默认", description="风格显示名称")
    refer_wav_path: str = Field(default="assets/reference.wav", description="参考音频文件路径")
    prompt_text: str = Field(default="这是一个示例文本，请替换为您自己的参考音频文本。", description="参考音频的文本内容")
    prompt_language: str = Field(default="zh", description="参考音频的语言")
    gpt_weights: str = Field(default="", description="GPT模型权重文件路径（留空表示使用默认）")
    sovits_weights: str = Field(default="", description="SoVITS模型权重文件路径（留空表示使用默认）")
    speed_factor: float = Field(default=1.0, description="语速因子")
    text_language: str = Field(default="auto", description="文本语言模式")


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

    @config_section("tts_styles")
    class TTSStylesSection(SectionBase):
        styles: list[TTSStyleSection] = Field(
            default_factory=lambda: [TTSStyleSection()],
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
