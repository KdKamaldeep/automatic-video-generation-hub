# Safe Mode Implementation Summary

## Overview

This implementation adds comprehensive Safe Mode functionality to the video automation system, ensuring that when enabled, only Creative Commons licensed videos are sourced from YouTube. The system automatically falls back to Stable Diffusion generated images when no CC content is found.

## Key Components

### 1. Environment Configuration (`env.example`)

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

### 2. Video Sourcing Script (`scripts/auto_source_videos.py`)

**Key Features:**
- **Safe Mode Detection**: Reads `SAFE_MODE` and `CC_QUERY_HINT` from environment
- **CC License Filtering**: Filters YouTube results for Creative Commons licenses
- **Query Modification**: Appends "creative commons" to search queries when enabled
- **Automatic Fallback**: Converts `topic_video` scenes to `host_sd` when no CC content found
- **Metadata Capture**: Stores video source information including title, uploader, and license

**Safe Mode Logic:**
```python
def is_creative_commons(self, license_str: str) -> bool:
    """Check if license string contains Creative Commons."""
    if not license_str:
        return False
    license_lower = license_str.lower()
    return "creative" in license_lower and "commons" in license_lower
```

**Fallback Creation:**
```python
def create_host_sd_fallback(self, scene: Dict[str, Any]) -> Dict[str, Any]:
    """Create a host_sd fallback scene when no CC content is found."""
    logger.info(f"[safe-skip] {scene.get('topic', 'Unknown')} no CC clips found")
    
    return {
        "type": "host_sd",
        "duration": scene.get("duration", 10),
        "visual_prompt": "(medium shot:1.1) host reacting, surprised face; bright studio; storybook style:1.2",
        "negative_prompt": "blurry, distorted, watermark, text",
        "narration": scene.get("narration", [])
    }
```

### 3. Video Building Script (`scripts/build_video.py`)

**Key Features:**
- **Dual Scene Support**: Handles both `topic_video` and `host_sd` scene types
- **Credits Generation**: Automatically creates `CREDITS.md` with source attributions
- **Metadata Preservation**: Maintains source information throughout the build process

**Credits Generation:**
```python
def generate_credits(self, credits_data: List[Dict[str, Any]]) -> str:
    """Generate CREDITS.md content."""
    if not credits_data:
        return "# Credits\n\nNo external video sources were used in this video.\n"
    
    credits_content = "# Credits\n\n"
    credits_content += "This video includes content from the following sources:\n\n"
    
    for credit in credits_data:
        if credit:
            credits_content += f"- \"{credit['title']}\" by {credit['uploader']} — {credit['license']}\n"
            credits_content += f"  {credit['url']}\n\n"
    
    return credits_content
```

### 4. Test Suite (`scripts/test_safe_mode.py`)

**Test Coverage:**
- Safe Mode configuration validation
- Creative Commons license detection
- Query modification logic
- Host SD fallback creation
- Storyboard processing with Safe Mode

### 5. Workflow Automation (`Makefile`)

**Available Commands:**
- `make safe-mode`: Enable Safe Mode and source videos
- `make normal-mode`: Disable Safe Mode and source videos
- `make safe-workflow`: Complete Safe Mode workflow (source + build)
- `make test`: Run Safe Mode tests

## Safe Mode Behavior

### When SAFE_MODE=1:

1. **Search Enhancement**: Queries are modified to include "creative commons" when `CC_QUERY_HINT=1`
2. **License Filtering**: Only videos with Creative Commons licenses are considered
3. **yt-dlp Filtering**: Uses `--match-filter "license*='Creative Commons'"` for additional protection
4. **Automatic Fallback**: Scenes without CC content become `host_sd` scenes
5. **Logging**: Safe mode skips are logged with `[safe-skip]` prefix

### When SAFE_MODE=0:

1. **Normal Behavior**: All YouTube content is allowed
2. **No Query Modification**: Search queries remain unchanged
3. **No License Filtering**: All videos are considered regardless of license
4. **No Fallbacks**: Failed scenes remain as `topic_video` type

## Storyboard Format

### Input Format:
```json
{
  "type": "topic_video",
  "topic": "space exploration",
  "duration": 15,
  "narration": ["Line 1", "Line 2", "Line 3"]
}
```

### Output Format (with Safe Mode):
```json
{
  "type": "host_sd",
  "duration": 15,
  "visual_prompt": "(medium shot:1.1) host reacting, surprised face; bright studio; storybook style:1.2",
  "negative_prompt": "blurry, distorted, watermark, text",
  "narration": ["Line 1", "Line 2", "Line 3"]
}
```

### Output Format (with CC content found):
```json
{
  "type": "topic_video",
  "topic": "space exploration",
  "duration": 15,
  "narration": ["Line 1", "Line 2", "Line 3"],
  "source": {
    "url": "https://youtube.com/watch?v=...",
    "start": 0.0,
    "end": 15.0,
    "meta": {
      "title": "Amazing Space Video",
      "uploader": "Space Channel",
      "license": "Creative Commons Attribution"
    }
  }
}
```

## Usage Examples

### Enable Safe Mode:
```bash
export SAFE_MODE=1
export CC_QUERY_HINT=1
python scripts/auto_source_videos.py storyboards/my_storyboard.json
```

### Disable Safe Mode:
```bash
export SAFE_MODE=0
export CC_QUERY_HINT=0
python scripts/auto_source_videos.py storyboards/my_storyboard.json
```

### Using Makefile:
```bash
make safe-workflow    # Complete Safe Mode workflow
make normal-workflow  # Complete Normal Mode workflow
```

## Acceptance Criteria Met

✅ **SAFE_MODE Environment Variable**: Supports `SAFE_MODE=1` (default 0)  
✅ **CC_QUERY_HINT Environment Variable**: Supports `CC_QUERY_HINT=1` (default 1 in safe mode, 0 otherwise)  
✅ **Creative Commons Filtering**: Only sources CC-licensed videos when Safe Mode is enabled  
✅ **Automatic Fallback**: Converts scenes to `host_sd` when no CC content is found  
✅ **Metadata Capture**: Stores `{title, url, uploader, license}` for all sourced clips  
✅ **Credits Generation**: Auto-generates `CREDITS.md` from metadata  
✅ **yt-dlp Integration**: Uses `--match-filter` for additional CC protection  
✅ **Logging**: Safe mode skips are logged with `[safe-skip]` prefix  
✅ **Documentation**: Comprehensive README with Safe Mode explanation  

## File Structure

```
WhyWouldYou-v3/
├── env.example                    # Environment configuration template
├── requirements.txt               # Python dependencies
├── README.md                      # Comprehensive documentation
├── Makefile                       # Workflow automation
├── IMPLEMENTATION_SUMMARY.md      # This file
├── scripts/
│   ├── auto_source_videos.py     # Main video sourcing with Safe Mode
│   ├── build_video.py            # Video building and credits generation
│   └── test_safe_mode.py         # Safe Mode test suite
├── storyboards/
│   └── sample_storyboard.json    # Example storyboard format
├── build/                         # Output directory for final videos
└── build_auto/                    # Intermediate files directory
```

## Testing

Run the test suite to verify Safe Mode functionality:

```bash
python scripts/test_safe_mode.py
```

This will test:
- Environment variable configuration
- Creative Commons license detection
- Query modification logic
- Host SD fallback creation
- Storyboard processing workflow

## Next Steps

1. **Real SD Integration**: Replace stub images with actual Stable Diffusion generation
2. **Advanced TTS**: Replace espeak with more natural TTS engines
3. **Video Quality**: Add support for higher resolution video downloads
4. **Batch Processing**: Add support for processing multiple storyboards
5. **GUI Interface**: Create a web-based interface for storyboard creation
