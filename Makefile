# Video Automation Makefile

.PHONY: help install test source build clean safe-mode normal-mode

# Default target
help:
	@echo "Video Automation System with Safe Mode"
	@echo ""
	@echo "Available targets:"
	@echo "  install      - Install dependencies"
	@echo "  test         - Run Safe Mode tests"
	@echo "  source       - Source videos from storyboard (uses SAFE_MODE from .env)"
	@echo "  build        - Build final video from sourced storyboard"
	@echo "  safe-mode    - Enable Safe Mode and source videos"
	@echo "  normal-mode  - Disable Safe Mode and source videos"
	@echo "  clean        - Clean build artifacts"
	@echo ""
	@echo "Environment:"
	@echo "  SAFE_MODE=1  - Enable Creative Commons-only mode"
	@echo "  SAFE_MODE=0  - Allow all YouTube content"

# Install dependencies
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "Installing system dependencies..."
	@echo "Please ensure you have ffmpeg, yt-dlp, and espeak installed:"
	@echo "  - ffmpeg: https://ffmpeg.org/download.html"
	@echo "  - yt-dlp: pip install yt-dlp"
	@echo "  - espeak: https://espeak.sourceforge.net/"

# Run tests
test:
	@echo "Running Safe Mode tests..."
	python scripts/test_safe_mode.py

# Source videos (uses current SAFE_MODE setting)
source:
	@echo "Sourcing videos from storyboard..."
	@if [ ! -f storyboards/topics_storyboard.json ]; then \
		echo "Error: storyboards/topics_storyboard.json not found"; \
		echo "Please create a storyboard file or use the sample:"; \
		echo "  cp storyboards/sample_storyboard.json storyboards/topics_storyboard.json"; \
		exit 1; \
	fi
	python scripts/auto_source_videos.py storyboards/topics_storyboard.json

# Build final video
build:
	@echo "Building final video..."
	@if [ ! -f build_auto/topics_storyboard_with_sources.json ]; then \
		echo "Error: build_auto/topics_storyboard_with_sources.json not found"; \
		echo "Please run 'make source' first"; \
		exit 1; \
	fi
	python scripts/build_video.py build_auto/topics_storyboard_with_sources.json

# Safe Mode workflow
safe-mode:
	@echo "Enabling Safe Mode (Creative Commons only)..."
	@export SAFE_MODE=1; \
	export CC_QUERY_HINT=1; \
	echo "SAFE_MODE=1 - Only Creative Commons content will be used"; \
	echo "CC_QUERY_HINT=1 - Adding 'creative commons' to search queries"; \
	make source

# Normal Mode workflow
normal-mode:
	@echo "Disabling Safe Mode (all content allowed)..."
	@export SAFE_MODE=0; \
	export CC_QUERY_HINT=0; \
	echo "SAFE_MODE=0 - All YouTube content allowed"; \
	echo "CC_QUERY_HINT=0 - No query modification"; \
	make source

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf build_auto/
	rm -f *.mp4
	rm -f *.wav
	rm -f temp_*
	@echo "Clean complete"

# Full workflow with Safe Mode
safe-workflow: safe-mode build
	@echo "Safe Mode workflow complete!"
	@echo "Check build/final.mp4 and build/CREDITS.md"

# Full workflow with Normal Mode
normal-workflow: normal-mode build
	@echo "Normal Mode workflow complete!"
	@echo "Check build/final.mp4 and build/CREDITS.md"
