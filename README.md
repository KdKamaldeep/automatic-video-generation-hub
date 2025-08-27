# Video Automation System with Safe Mode

A Python-based video automation system that can source videos from YouTube and generate content with optional Creative Commons-only Safe Mode.

## Features

- **Safe Mode**: When enabled, only sources Creative Commons licensed videos
- **Automatic Fallback**: Converts scenes to Stable Diffusion images when no CC content is found
- **Metadata Tracking**: Captures and credits all video sources
- **Flexible Storyboarding**: Support for both video and AI-generated content
- **Automatic Credits Generation**: Creates CREDITS.md with all source attributions

## Safe Mode

Safe Mode ensures that your videos only use Creative Commons licensed content, making them safe for commercial use and distribution.

### How to Enable Safe Mode

Set the environment variable `SAFE_MODE=1`:

```bash
export SAFE_MODE=1
```

Or create a `.env` file based on `env.example`:

```bash
cp env.example .env
# Edit .env and set SAFE_MODE=1
```

### What Happens in Safe Mode

1. **CC Query Hint**: When `CC_QUERY_HINT=1` (default in safe mode), "creative commons" is appended to search queries
2. **License Filtering**: Only videos with Creative Commons licenses are considered
3. **Automatic Fallback**: If no CC content is found, scenes are converted to `host_sd` type with Stable Diffusion images
4. **Logging**: Safe mode skips are logged with `[safe-skip]` prefix

### What Happens if No CC Content is Found

When Safe Mode is enabled and no Creative Commons content is found for a topic, the scene is automatically converted to a `host_sd` fallback:

```json
{
  "type": "host_sd",
  "duration": 10,
  "visual_prompt": "(medium shot:1.1) host reacting, surprised face; bright studio; storybook style:1.2",
  "negative_prompt": "blurry, distorted, watermark, text",
  "narration": ["Original narration preserved"]
}
```

## Installation

### Prerequisites

- Python 3.8+
- ffmpeg
- yt-dlp
- espeak (for TTS)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd WhyWouldYou-v3
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment configuration:
```bash
cp env.example .env
```

4. Edit `.env` to configure your settings:
```bash
# Safe Mode Configuration
SAFE_MODE=1            # 1 = CC-only, 0 = allow all
CC_QUERY_HINT=1        # append "creative commons" to queries in safe mode

# Video Sourcing Configuration
RESULTS_PER_QUERY=6    # Number of results to fetch per query
MAX_VIDEO_LEN_SEC=900  # Maximum video length in seconds

# Stable Diffusion Configuration
SD_STUB=1              # 1 = stub images, 0 = real Diffusers
SD_MODEL_ID=runwayml/stable-diffusion-v1-5
SD_VAE_ID=stabilityai/sd-vae-ft-mse
SD_STEPS=28
SD_CFG=8.0
```

## Usage

### 1. Create a Storyboard

Create a JSON storyboard file in the `storyboards/` directory:

```json
{
  "title": "My Video",
  "description": "A sample video",
  "scenes": [
    {
      "type": "topic_video",
      "topic": "space exploration",
      "duration": 15,
      "narration": [
        "Space exploration has captured human imagination for decades.",
        "From the first moon landing to modern Mars missions."
      ]
    },
    {
      "type": "host_sd",
      "duration": 8,
      "visual_prompt": "(medium shot:1.1) host explaining, professional appearance",
      "negative_prompt": "blurry, distorted, watermark, text",
      "narration": [
        "Thank you for watching our exploration."
      ]
    }
  ]
}
```

### 2. Source Videos

Run the video sourcing script:

```bash
python scripts/auto_source_videos.py storyboards/my_storyboard.json
```

This will:
- Search YouTube for videos matching each topic
- Filter for Creative Commons content if Safe Mode is enabled
- Download video segments and find appropriate timestamps
- Convert to `host_sd` fallbacks if no CC content is found
- Output `build_auto/my_storyboard_with_sources.json`

### 3. Build Final Video

Build the complete video:

```bash
python scripts/build_video.py build_auto/my_storyboard_with_sources.json
```

This will:
- Download video segments and generate SD images
- Add narration using TTS
- Concatenate all scenes into a final video
- Generate `build/CREDITS.md` with source attributions
- Output `build/final.mp4`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SAFE_MODE` | `0` | Enable Creative Commons-only mode |
| `CC_QUERY_HINT` | `1` (if SAFE_MODE=1) | Append "creative commons" to search queries |
| `RESULTS_PER_QUERY` | `6` | Number of YouTube results to fetch per query |
| `MAX_VIDEO_LEN_SEC` | `900` | Maximum video length in seconds |
| `SD_STUB` | `1` | Use stub images instead of real SD generation |
| `SD_MODEL_ID` | `runwayml/stable-diffusion-v1-5` | Stable Diffusion model |
| `SD_STEPS` | `28` | Number of SD generation steps |
| `SD_CFG` | `8.0` | SD guidance scale |
| `OUTPUT_DIR` | `build` | Output directory for final video |
| `BUILD_AUTO_DIR` | `build_auto` | Directory for intermediate files |

## Storyboard Format

### Scene Types

#### topic_video
For scenes that source content from YouTube:

```json
{
  "type": "topic_video",
  "topic": "search query",
  "duration": 15,
  "narration": [
    "First narration line",
    "Second narration line"
  ]
}
```

#### host_sd
For scenes using Stable Diffusion generated images:

```json
{
  "type": "host_sd",
  "duration": 10,
  "visual_prompt": "SD generation prompt",
  "negative_prompt": "SD negative prompt",
  "narration": [
    "Narration text"
  ]
}
```

### Source Metadata

After sourcing, `topic_video` scenes will include source information:

```json
{
  "type": "topic_video",
  "topic": "space exploration",
  "source": {
    "url": "https://youtube.com/watch?v=...",
    "start": 0.0,
    "end": 15.0,
    "meta": {
      "title": "Video Title",
      "uploader": "Channel Name",
      "license": "Creative Commons Attribution"
    }
  }
}
```

## Credits Generation

The system automatically generates a `CREDITS.md` file in the build directory:

```markdown
# Credits

This video includes content from the following sources:

- "Amazing Space Video" by Space Channel — Creative Commons Attribution
  https://youtube.com/watch?v=...

- "Ocean Life Documentary" by Nature Videos — Creative Commons Attribution
  https://youtube.com/watch?v=...
```

## Best Practices

### For Safe Mode Users

1. **Keep clips short**: Use brief, focused narration to minimize the need for long video segments
2. **Add commentary**: Transform sourced content with your own narration and insights
3. **Check credits**: Review the generated CREDITS.md to ensure proper attribution
4. **Test queries**: Try different search terms if no CC content is found

### General Tips

1. **Plan your storyboard**: Mix `topic_video` and `host_sd` scenes for variety
2. **Optimize narration**: Keep narration lines concise and impactful
3. **Monitor logs**: Check the console output for any issues or safe mode skips
4. **Backup sources**: The system preserves original storyboards in `storyboards/`

## Troubleshooting

### Common Issues

1. **No videos found**: Try different search terms or disable Safe Mode temporarily
2. **Download failures**: Check your internet connection and yt-dlp installation
3. **TTS errors**: Ensure espeak is installed and working
4. **FFmpeg errors**: Verify ffmpeg installation and permissions

### Safe Mode Specific

1. **Too many fallbacks**: Consider using more specific search terms or mixing in `host_sd` scenes
2. **License detection issues**: Some videos may have incorrect license metadata
3. **Query hints not working**: Verify `CC_QUERY_HINT=1` is set in your environment

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Contributing

Contributions are welcome! Please ensure that any video content you source follows the Safe Mode guidelines when enabled.
