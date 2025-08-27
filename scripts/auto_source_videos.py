#!/usr/bin/env python3
"""
Auto-source videos for storyboard scenes with Safe Mode support.
When SAFE_MODE=1, only Creative Commons licensed videos are used.
"""

import os
import json
import subprocess
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoSourcer:
    def __init__(self):
        self.safe_mode = int(os.getenv('SAFE_MODE', '0'))
        self.cc_query_hint = int(os.getenv('CC_QUERY_HINT', '1' if self.safe_mode else '0'))
        self.results_per_query = int(os.getenv('RESULTS_PER_QUERY', '6'))
        self.max_video_len_sec = int(os.getenv('MAX_VIDEO_LEN_SEC', '900'))
        
        logger.info(f"Safe Mode: {self.safe_mode}")
        logger.info(f"CC Query Hint: {self.cc_query_hint}")
        
    def is_creative_commons(self, license_str: str) -> bool:
        """Check if license string contains Creative Commons."""
        if not license_str:
            return False
        license_lower = license_str.lower()
        return "creative" in license_lower and "commons" in license_lower
    
    def search_youtube(self, query: str) -> List[Dict[str, Any]]:
        """Search YouTube for videos matching the query."""
        # Add CC hint if enabled
        if self.safe_mode and self.cc_query_hint:
            query = f"{query} creative commons"
        
        logger.info(f"Searching YouTube for: {query}")
        
        try:
            # Use yt-dlp to search and dump JSON
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--max-downloads', str(self.results_per_query),
                '--match-filter', f'duration<{self.max_video_len_sec}',
                f'ytsearch{self.results_per_query}:{query}'
            ]
            
            # Add CC filter in safe mode
            if self.safe_mode:
                cmd.extend(['--match-filter', 'license*="Creative Commons"'])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"yt-dlp search failed: {result.stderr}")
                return []
            
            # Parse JSON results
            videos = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        video_data = json.loads(line)
                        
                        # Additional CC filtering in safe mode
                        if self.safe_mode:
                            license_info = video_data.get('license', '')
                            if not self.is_creative_commons(license_info):
                                logger.debug(f"Skipping non-CC video: {video_data.get('title', 'Unknown')}")
                                continue
                        
                        videos.append(video_data)
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"Found {len(videos)} videos for query: {query}")
            return videos
            
        except subprocess.TimeoutExpired:
            logger.error(f"Search timeout for query: {query}")
            return []
        except Exception as e:
            logger.error(f"Search error for query {query}: {e}")
            return []
    
    def download_video_segment(self, url: str, start_time: float, duration: float, 
                              output_path: str, video_meta: Dict[str, Any]) -> bool:
        """Download a specific segment of a video."""
        try:
            end_time = start_time + duration
            
            cmd = [
                'yt-dlp',
                '-f', 'best[height<=720]',  # Limit to 720p for efficiency
                '--download-sections', f'*{start_time}-{end_time}',
                '--output', output_path,
                '--no-playlist'
            ]
            
            # Add CC filter in safe mode
            if self.safe_mode:
                cmd.extend(['--match-filter', 'license*="Creative Commons"'])
            
            cmd.append(url)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"Download failed for {url}: {result.stderr}")
                return False
            
            logger.info(f"Downloaded segment: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Download error for {url}: {e}")
            return False
    
    def find_timestamps(self, video_path: str, narration: List[str]) -> Optional[List[Dict[str, Any]]]:
        """Find appropriate timestamps for video segments based on narration."""
        # This is a simplified timestamp finder
        # In a real implementation, you might use speech recognition or other methods
        
        try:
            # Get video duration using ffprobe
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return None
            
            duration = float(result.stdout.strip())
            
            # Simple timestamp distribution
            segments = []
            segment_duration = duration / len(narration)
            
            for i, text in enumerate(narration):
                start_time = i * segment_duration
                end_time = min((i + 1) * segment_duration, duration)
                
                segments.append({
                    'start': start_time,
                    'end': end_time,
                    'text': text
                })
            
            return segments
            
        except Exception as e:
            logger.error(f"Timestamp finding error: {e}")
            return None
    
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
    
    def process_scene(self, scene: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
        """Process a single scene to find and download video sources."""
        if scene.get("type") != "topic_video":
            return scene
        
        topic = scene.get("topic", "")
        narration = scene.get("narration", [])
        
        if not topic or not narration:
            logger.warning(f"Scene missing topic or narration: {scene}")
            return scene
        
        # Search for videos
        videos = self.search_youtube(topic)
        
        if not videos:
            if self.safe_mode:
                return self.create_host_sd_fallback(scene)
            else:
                logger.warning(f"No videos found for topic: {topic}")
                return scene
        
        # Try to find timestamps for the first video
        video = videos[0]
        video_url = video.get('webpage_url', '')
        
        if not video_url:
            if self.safe_mode:
                return self.create_host_sd_fallback(scene)
            else:
                logger.warning(f"No URL found for video: {video.get('title', 'Unknown')}")
                return scene
        
        # Create temporary file for full video
        temp_video_path = output_dir / f"temp_{hash(topic)}.mp4"
        
        # Download full video first
        if not self.download_video_segment(video_url, 0, self.max_video_len_sec, 
                                         str(temp_video_path), video):
            if self.safe_mode:
                return self.create_host_sd_fallback(scene)
            else:
                logger.warning(f"Failed to download video for topic: {topic}")
                return scene
        
        # Find timestamps
        timestamps = self.find_timestamps(str(temp_video_path), narration)
        
        if not timestamps:
            if self.safe_mode:
                return self.create_host_sd_fallback(scene)
            else:
                logger.warning(f"Failed to find timestamps for topic: {topic}")
                return scene
        
        # Clean up temp file
        if temp_video_path.exists():
            temp_video_path.unlink()
        
        # Update scene with source information
        scene["source"] = {
            "url": video_url,
            "start": timestamps[0]["start"],
            "end": timestamps[-1]["end"],
            "meta": {
                "title": video.get('title', 'Unknown'),
                "uploader": video.get('uploader', 'Unknown'),
                "license": video.get('license', 'Unknown')
            }
        }
        
        logger.info(f"Successfully sourced video for topic: {topic}")
        return scene
    
    def process_storyboard(self, input_path: str, output_path: str):
        """Process the entire storyboard file."""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                storyboard = json.load(f)
            
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Process each scene
            for i, scene in enumerate(storyboard.get("scenes", [])):
                logger.info(f"Processing scene {i+1}/{len(storyboard.get('scenes', []))}")
                storyboard["scenes"][i] = self.process_scene(scene, output_dir)
            
            # Write updated storyboard
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(storyboard, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Storyboard processed and saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Error processing storyboard: {e}")
            raise

def main():
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python auto_source_videos.py <storyboard_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = input_file.replace('storyboards/', 'build_auto/').replace('.json', '_with_sources.json')
    
    sourcer = VideoSourcer()
    sourcer.process_storyboard(input_file, output_file)

if __name__ == "__main__":
    main()
