# TTS Voice Plugin

基于 GPT-SoVITS 的文本转语音插件，支持多种音色风格、情感控制和空间音效处理。

## 功能特性

- 🎙️ **多音色支持**：支持配置多种参考音频风格
- 🎭 **情感控制**：支持情感化的语音合成
- 🔊 **空间音效**：支持混响、卷积等空间音效处理
- ⚡ **异步处理**：非阻塞式语音合成
- 🔌 **即插即用**：完整支持 Neo-MoFox 插件系统

## 安装依赖

```bash
# 必需依赖（已包含在 manifest.json）
pip install aiohttp>=3.8.0
pip install numpy>=1.24.0
pip install soundfile>=0.12.1
pip install pedalboard>=0.9.8
```

## 配置说明

### 基础配置

```toml
[plugin]
enable = true  # 是否启用插件
keywords = ["发语音", "语音"]  # 触发关键词

[components]
action_enabled = true   # 启用 TTS 动作
command_enabled = true  # 启用 TTS 命令

[tts]
server = "http://127.0.0.1:9880"  # GPT-SoVITS API 地址
timeout = 180  # 请求超时时间（秒）
max_text_length = 1000  # 最大文本长度
```

### 音色风格配置

```toml
[[tts_styles.styles]]
style_name = "default"
name = "默认"
refer_wav_path = "assets/reference.wav"  # 参考音频路径
prompt_text = "参考音频的文本内容"
prompt_language = "zh"
gpt_weights = ""  # GPT 模型权重路径
sovits_weights = ""  # SoVITS 模型权重路径
speed_factor = 1.0
text_language = "auto"
```

### 空间音效配置

```toml
[spatial_effects]
enabled = false
reverb_enabled = false
room_size = 0.2
damping = 0.6
wet_level = 0.3
dry_level = 0.8
width = 1.0
convolution_enabled = false
convolution_mix = 0.7
```

## 使用方法

### 命令方式

```
/tts 你好，这是一条测试语音
/tts 使用特定风格 你好
```

### 动作方式

插件会自动响应配置的关键词，无需手动触发。

### API 直接调用

```python
from plugins.tts_voice_plugin import TTSVoicePlugin

plugin = TTSVoicePlugin()
service = plugin.get_service("tts_service")
audio_b64 = await service.generate_voice("你好，世界！")
```

## GPT-SoVITS 服务部署

1. **下载 GPT-SoVITS**：https://github.com/RVC-Boss/GPT-SoVITS
2. **启动 API 服务**：
   ```bash
   python api.py -s "你的SoVITS模型路径" -g "你的GPT模型路径"
   ```
3. **验证服务**：访问 `http://127.0.0.1:9880` 确认服务已启动

## 目录结构

```
plugins/tts_voice_plugin/
├── README.md              # 本文件
├── __init__.py            # 插件导出
├── plugin.py              # 主插件类
├── config.py              # 配置定义
├── manifest.json          # 插件清单
├── actions/               # 动作组件
│   ├── __init__.py
│   └── tts_action.py
├── commands/              # 命令组件
│   ├── __init__.py
│   └── tts_command.py
└── services/              # 服务组件
    ├── __init__.py
    └── tts_service.py
```

## 常见问题

**Q: 语音合成失败，提示连接超时？**  
A: 检查 GPT-SoVITS 服务是否已启动，以及配置的 `server` 地址是否正确。

**Q: 生成的语音质量差？**  
A: 检查参考音频的质量，确保参考音频清晰、无噪音。

**Q: 如何添加更多音色风格？**  
A: 在配置文件的 `tts_styles.styles` 数组中添加新的风格配置。

## 版本历史

- **v1.0.0** - 当前版本

## 特别鸣谢

本插件在开发过程中参考了言柒和靚仔开发的 TTS Voice 插件。

- **言柒** - 原 TTS Voice 插件作者
- **靚仔** - 原 TTS Voice 插件作者

感谢两位原作者的开源项目为本插件提供了重要的参考和基础！
