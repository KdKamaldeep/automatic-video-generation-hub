#!/usr/bin/env python3
"""
Build final video from storyboard with sources.
Handles both topic_video and host_sd scenes, generates CREDITS.md.
"""

import os
import json
import subprocess
import logging
from typing import Dict, List, Any
from pathlib import Path
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoBuilder:
    def __init__(self):
        self.output_dir = os.getenv('OUTPUT_DIR', 'build')
        self.sd_stub = int(os.getenv('SD_STUB', '1'))
        self.sd_model_id = os.getenv('SD_MODEL_ID', 'runwayml/stable-diffusion-v1-5')
        self.sd_vae_id = os.getenv('SD_VAE_ID', 'stabilityai/sd-vae-ft-mse')
        self.sd_steps = int(os.getenv('SD_STEPS', '28'))
        self.sd_cfg = float(os.getenv('SD_CFG', '8.0'))
        
        # Ensure output directory exists
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
    def download_video_segment(self, url: str, start_time: float, end_time: float, 
                              output_path: str) -> bool:
        """Download a specific segment of a video."""
        try:
            cmd = [
                'yt-dlp',
                '-f', 'best[height<=720]',
                '--download-sections', f'*{start_time}-{end_time}',
                '--output', output_path,
                '--no-playlist',
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                logger.error(f"Download failed for {url}: {result.stderr}")
                return False
            
            logger.info(f"Downloaded segment: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Download error for {url}: {e}")
            return False
    
    def generate_sd_image(self, prompt: str, negative_prompt: str, output_path: str, 
                         duration: int) -> bool:
        """Generate Stable Diffusion image or create stub."""
        try:
            if self.sd_stub:
                # Create a simple colored image as stub
                cmd = [
                    'ffmpeg', '-y',
                    '-f', 'lavfi',
                    '-i', f'color=c=0x3366cc:size=1280x720:duration={duration}',
                    '-vf', 'drawtext=text=\'SD Image\':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2',
                    output_path
                ]
            else:
                # Real SD generation would go here
                # For now, create a placeholder
                logger.warning("Real SD generation not implemented, using stub")
                cmd = [
                    'ffmpeg', '-y',
                    '-f', 'lavfi',
                    '-i', f'color=c=0x3366cc:size=1280x720:duration={duration}',
                    '-vf', 'drawtext=text=\'SD Image\':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2',
                    output_path
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"Image generation failed: {result.stderr}")
                return False
            
            logger.info(f"Generated image: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return False
    
    def add_narration(self, video_path: str, narration: List[str], output_path: str) -> bool:
        """Add narration audio to video."""
        try:
            # Create temporary audio file with TTS
            temp_audio = f"temp_audio_{hash(video_path)}.wav"
            
            # Simple TTS using espeak (you might want to use a better TTS engine)
            cmd = [
                'espeak', '-w', temp_audio,
                '--punct=some',
                ' '.join(narration)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"TTS failed: {result.stderr}")
                return False
            
            # Combine video and audio
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', temp_audio,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-shortest',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # Clean up temp audio
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            
            if result.returncode != 0:
                logger.error(f"Audio combination failed: {result.stderr}")
                return False
            
            logger.info(f"Added narration: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Narration error: {e}")
            return False
    
    def process_scene(self, scene: Dict[str, Any], scene_index: int) -> Dict[str, Any]:
        """Process a single scene and return metadata for credits."""
        scene_type = scene.get("type", "")
        scene_file = f"scene_{scene_index:03d}.mp4"
        scene_path = Path(self.output_dir) / scene_file
        
        credits_info = None
        
        if scene_type == "topic_video":
            # Handle video scene
            source = scene.get("source", {})
            if source:
                url = source.get("url", "")
                start_time = source.get("start", 0)
                end_time = source.get("end", 10)
                
                if self.download_video_segment(url, start_time, end_time, str(scene_path)):
                    # Add narration
                    narration = scene.get("narration", [])
                    if narration:
                        narrated_path = Path(self.output_dir) / f"narrated_{scene_file}"
                        if self.add_narration(str(scene_path), narration, str(narrated_path)):
                            scene_path = narrated_path
                    
                    # Store credits info
                    meta = source.get("meta", {})
                    credits_info = {
                        "title": meta.get("title", "Unknown"),
                        "uploader": meta.get("uploader", "Unknown"),
                        "license": meta.get("license", "Unknown"),
                        "url": url
                    }
                else:
                    logger.error(f"Failed to process video scene {scene_index}")
                    return None
            else:
                logger.warning(f"Video scene {scene_index} has no source info")
                return None
                
        elif scene_type == "host_sd":
            # Handle SD image scene
            duration = scene.get("duration", 10)
            visual_prompt = scene.get("visual_prompt", "")
            negative_prompt = scene.get("negative_prompt", "")
            narration = scene.get("narration", [])
            
            if self.generate_sd_image(visual_prompt, negative_prompt, str(scene_path), duration):
                # Add narration
                if narration:
                    narrated_path = Path(self.output_dir) / f"narrated_{scene_file}"
                    if self.add_narration(str(scene_path), narration, str(narrated_path)):
                        scene_path = narrated_path
            else:
                logger.error(f"Failed to process SD scene {scene_index}")
                return None
        
        else:
            logger.warning(f"Unknown scene type: {scene_type}")
            return None
        
        return {
            "file": str(scene_path),
            "credits": credits_info
        }
    
    def concatenate_videos(self, scene_files: List[str], output_path: str) -> bool:
        """Concatenate all scene videos into final video."""
        try:
            # Create file list for ffmpeg
            file_list = Path(self.output_dir) / "file_list.txt"
            
            with open(file_list, 'w', encoding='utf-8') as f:
                for scene_file in scene_files:
                    f.write(f"file '{scene_file}'\n")
            
            # Concatenate videos
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(file_list),
                '-c', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Clean up file list
            if file_list.exists():
                file_list.unlink()
            
            if result.returncode != 0:
                logger.error(f"Concatenation failed: {result.stderr}")
                return False
            
            logger.info(f"Final video created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Concatenation error: {e}")
            return False
    
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
    
    def build_video(self, storyboard_path: str):
        """Build the complete video from storyboard."""
        try:
            with open(storyboard_path, 'r', encoding='utf-8') as f:
                storyboard = json.load(f)
            
            scenes = storyboard.get("scenes", [])
            scene_files = []
            credits_data = []
            
            logger.info(f"Processing {len(scenes)} scenes")
            
            # Process each scene
            for i, scene in enumerate(scenes):
                logger.info(f"Processing scene {i+1}/{len(scenes)}")
                
                result = self.process_scene(scene, i)
                if result:
                    scene_files.append(result["file"])
                    if result["credits"]:
                        credits_data.append(result["credits"])
                else:
                    logger.error(f"Failed to process scene {i+1}")
            
            if not scene_files:
                logger.error("No scenes were successfully processed")
                return
            
            # Concatenate videos
            final_video_path = Path(self.output_dir) / "final.mp4"
            if self.concatenate_videos(scene_files, str(final_video_path)):
                logger.info("Video build completed successfully")
            else:
                logger.error("Video concatenation failed")
                return
            
            # Generate credits
            credits_content = self.generate_credits(credits_data)
            credits_path = Path(self.output_dir) / "CREDITS.md"
            
            with open(credits_path, 'w', encoding='utf-8') as f:
                f.write(credits_content)
            
            logger.info(f"Credits generated: {credits_path}")
            
        except Exception as e:
            logger.error(f"Error building video: {e}")
            raise

def main():
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python build_video.py <storyboard_with_sources_file>")
        sys.exit(1)
    
    storyboard_file = sys.argv[1]
    builder = VideoBuilder()
    builder.build_video(storyboard_file)

if __name__ == "__main__":
    main()
