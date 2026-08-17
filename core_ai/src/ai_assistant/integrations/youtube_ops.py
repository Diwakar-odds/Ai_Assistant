import os
import logging
from pathlib import Path

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    print("Warning: yt_dlp not available. YouTube download features disabled.")

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    pass

# Configure logging
logger = logging.getLogger(__name__)

class YouTubeDownloader:
    def __init__(self, download_path=None):
        if download_path:
            self.download_path = Path(download_path)
        else:
            # Default to user's Music folder or a 'downloads' folder in the project
            self.download_path = Path(os.path.expanduser("~/Music/YourDaddy_Downloads"))
        
        self.download_path.mkdir(parents=True, exist_ok=True)

    def search_and_download_audio(self, query):
        """
        Searches for a video on YouTube and downloads the audio.
        Returns a dictionary with the result status and details.
        """
        if not YT_DLP_AVAILABLE:
            return {"status": "error", "message": "yt_dlp library not installed"}

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(self.download_path / '%(title)s.%(ext)s'),
            'quiet': True,
            'noplaylist': True,
            'default_search': 'ytsearch1',  # Search and download the first result
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Searching and downloading: {query}")
                info_dict = ydl.extract_info(query, download=True)
                
                if 'entries' in info_dict:
                    # It's a search result
                    video_info = info_dict['entries'][0]
                else:
                    # It's a direct link
                    video_info = info_dict

                video_title = video_info.get('title', 'Unknown Title')
                filename = ydl.prepare_filename(video_info)
                # The actual file will have the extension changed by postprocessor
                final_filename = Path(filename).with_suffix('.mp3')
                
                return {
                    "status": "success",
                    "message": f"Successfully downloaded '{video_title}'",
                    "file_path": str(final_filename),
                    "title": video_title
                }

        except Exception as e:
            logger.error(f"Error downloading {query}: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to download: {str(e)}"
            }

# Singleton instance for easy import
youtube_downloader = YouTubeDownloader()
