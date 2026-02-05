import os
import subprocess
from pathlib import Path

def check_ffmpeg():
    """Check if ffmpeg is installed"""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def convert_to_xvid(input_file, output_file):
    """Convert video to XVID format"""
    command = [
        'ffmpeg',
        '-i', str(input_file),
        '-c:v', 'mpeg4',
        '-vtag', 'xvid',
        '-q:v', '5',
        '-c:a', 'libmp3lame',
        '-b:a', '128k',
        '-y',
        str(output_file)
    ]
    
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0
    except Exception:
        return False

def convert_to_mp4(input_file, output_file):
    """Convert XVID video back to MP4 format"""
    command = [
        'ffmpeg',
        '-i', str(input_file),
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-y',
        str(output_file)
    ]
    
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0
    except Exception:
        return False

def process_videos(folder_path):
    """Process all videos in the folder"""
    
    if not check_ffmpeg():
        return
    
    folder = Path(folder_path)
    
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
        return
    
    # Supported video formats
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}
    
    # Get all video files
    video_files = [f for f in folder.iterdir() 
                   if f.is_file() and f.suffix.lower() in video_extensions]
    
    if not video_files:
        return
    
    for video_file in video_files:
        original_name = video_file.stem
        
        # Skip if this file is already converted (ends with 'c')
        if original_name.endswith('c'):
            continue
        
        # Skip if converted version already exists
        final_mp4_file = folder / f"{original_name}c.mp4"
        if final_mp4_file.exists():
            # Delete the original if converted version exists
            try:
                video_file.unlink()
            except Exception:
                pass
            continue
        
        # Step 1: Convert to XVID
        xvid_file = folder / f"{original_name}_temp.avi"
        
        if convert_to_xvid(video_file, xvid_file):
            # Delete original file
            try:
                video_file.unlink()
            except Exception:
                continue
            
            # Step 2: Convert back to MP4
            if convert_to_mp4(xvid_file, final_mp4_file):
                # Delete XVID temp file
                try:
                    xvid_file.unlink()
                except Exception:
                    pass

if __name__ == "__main__":
    # Specify your folder path here
    video_folder = r"static\Live Feed"
    
    # Alternative: Use current directory + static/Live Feed
    # video_folder = os.path.join(os.getcwd(), "static", "Live Feed")
    
    process_videos(video_folder)