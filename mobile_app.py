import os
import sys
import threading
import webbrowser
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import yt_dlp
import subprocess
import logging
from datetime import datetime
import re
from urllib.parse import urlparse
import enum
from sqlalchemy import Enum

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the mobile app
mobile_app = Flask(__name__)
mobile_app.secret_key = "mobile-video-downloader-secret-key"

# Configure for mobile use
mobile_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mobile_video_downloader.db"
mobile_app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Mobile-specific configuration
mobile_app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB for mobile
mobile_app.config['DOWNLOAD_FOLDER'] = os.path.join(os.path.expanduser('~'), 'VideoDownloads')

# Create downloads directory
os.makedirs(mobile_app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Initialize database
db.init_app(mobile_app)

# Models
class DownloadStatus(enum.Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading" 
    COMPLETED = "completed"
    FAILED = "failed"
    CONVERTING = "converting"

class VideoFormat(enum.Enum):
    MP4 = "mp4"
    MP3 = "mp3"
    WEBM = "webm"
    AVI = "avi"

class MobileDownload(db.Model):
    __tablename__ = 'mobile_downloads'
    
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(200))
    thumbnail_url = db.Column(db.String(500))
    duration = db.Column(db.Integer)
    file_size = db.Column(db.BigInteger)
    quality = db.Column(db.String(20))
    format = db.Column(Enum(VideoFormat), default=VideoFormat.MP4)
    status = db.Column(Enum(DownloadStatus), default=DownloadStatus.PENDING)
    progress = db.Column(db.Float, default=0.0)
    file_path = db.Column(db.String(500))
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    platform = db.Column(db.String(50))
    
    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'thumbnail_url': self.thumbnail_url,
            'duration': self.duration,
            'file_size': self.file_size,
            'quality': self.quality,
            'format': self.format.value if self.format else None,
            'status': self.status.value,
            'progress': self.progress,
            'file_path': self.file_path,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'platform': self.platform
        }

# Mobile Video Downloader Class
class MobileVideoDownloader:
    def __init__(self):
        self.download_folder = mobile_app.config['DOWNLOAD_FOLDER']
    
    def get_platform_from_url(self, url):
        """Determine platform from URL"""
        domain = urlparse(url).netloc.lower()
        
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return 'YouTube'
        elif 'instagram.com' in domain:
            return 'Instagram'
        elif 'twitter.com' in domain or 'x.com' in domain:
            return 'Twitter/X'
        elif 'tiktok.com' in domain:
            return 'TikTok'
        elif 'facebook.com' in domain or 'fb.watch' in domain:
            return 'Facebook'
        elif 'vimeo.com' in domain:
            return 'Vimeo'
        elif 'dailymotion.com' in domain:
            return 'Dailymotion'
        elif 'twitch.tv' in domain:
            return 'Twitch'
        elif 'reddit.com' in domain:
            return 'Reddit'
        elif 't.me' in domain or 'telegram.org' in domain:
            return 'Telegram'
        else:
            return 'Other'
    
    def validate_url(self, url):
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def download_video(self, download_id):
        """Download video using yt-dlp"""
        download = None
        try:
            with mobile_app.app_context():
                download = MobileDownload.query.get(download_id)
                if not download:
                    logger.error(f"Download {download_id} not found")
                    return
                
                # Update status
                download.status = DownloadStatus.DOWNLOADING
                db.session.commit()
                
                # Get video info
                self._get_video_info(download)
                
                # Download
                ydl_opts = self._get_ydl_options(download)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([download.url])
                
                # Mark completed
                download.status = DownloadStatus.COMPLETED
                download.progress = 100.0
                download.completed_at = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"Mobile download {download_id} completed")
                
        except Exception as e:
            logger.error(f"Error downloading video {download_id}: {str(e)}")
            if download:
                with mobile_app.app_context():
                    download.status = DownloadStatus.FAILED
                    download.error_message = str(e)
                    db.session.commit()
    
    def _get_video_info(self, download):
        """Get video information"""
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True}
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(download.url, download=False)
                
                if info:
                    download.title = info.get('title', 'Unknown Title')[:200]
                    download.duration = info.get('duration')
                    download.thumbnail_url = info.get('thumbnail')
                    
                    if info.get('filesize'):
                        download.file_size = info.get('filesize')
                    elif info.get('filesize_approx'):
                        download.file_size = info.get('filesize_approx')
                
                db.session.commit()
                
        except Exception as e:
            logger.warning(f"Could not get video info: {str(e)}")
    
    def _get_ydl_options(self, download):
        """Get yt-dlp options"""
        safe_title = re.sub(r'[^\w\s-]', '', download.title or 'video').strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        
        filename = f"{download.id}_{safe_title}.%(ext)s"
        filepath = os.path.join(self.download_folder, filename)
        
        # Quality selection
        if download.quality == 'best':
            format_selector = 'best'
        elif download.quality == 'worst':
            format_selector = 'worst'
        else:
            format_selector = f'best[height<={download.quality[:-1]}]'
        
        ydl_opts = {
            'outtmpl': filepath,
            'format': format_selector,
            'noplaylist': True,
            'extractaudio': download.format == VideoFormat.MP3,
            'audioformat': 'mp3' if download.format == VideoFormat.MP3 else None,
            'progress_hooks': [lambda d: self._progress_hook(d, download.id)],
        }
        
        return ydl_opts
    
    def _progress_hook(self, d, download_id):
        """Progress tracking"""
        try:
            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                
                if total > 0:
                    progress = (downloaded / total) * 100
                    
                    with mobile_app.app_context():
                        download = MobileDownload.query.get(download_id)
                        if download:
                            download.progress = min(progress, 99.0)
                            db.session.commit()
            
            elif d['status'] == 'finished':
                with mobile_app.app_context():
                    download = MobileDownload.query.get(download_id)
                    if download:
                        download.file_path = d['filename']
                        download.progress = 100.0
                        
                        if os.path.exists(d['filename']):
                            download.file_size = os.path.getsize(d['filename'])
                        
                        db.session.commit()
                        
        except Exception as e:
            logger.error(f"Progress hook error: {str(e)}")

# Initialize downloader
downloader = MobileVideoDownloader()

# Routes
@mobile_app.route('/')
def mobile_home():
    """Mobile home page"""
    recent_downloads = MobileDownload.query.order_by(MobileDownload.created_at.desc()).limit(5).all()
    return render_template('mobile_index.html', recent_downloads=recent_downloads)

@mobile_app.route('/download', methods=['POST'])
def mobile_start_download():
    """Start mobile download"""
    try:
        urls = request.form.get('urls', '').strip()
        quality = request.form.get('quality', 'best')
        format_type = request.form.get('format', 'mp4')
        
        if not urls:
            flash('Please enter at least one URL', 'error')
            return redirect(url_for('mobile_home'))
        
        url_list = [url.strip() for url in urls.split('\n') if url.strip()]
        download_ids = []
        
        for url in url_list:
            if not downloader.validate_url(url):
                flash(f'Invalid URL: {url}', 'error')
                continue
            
            # Create download
            download = MobileDownload()
            download.url = url
            download.quality = quality
            download.format = VideoFormat(format_type)
            download.platform = downloader.get_platform_from_url(url)
            
            db.session.add(download)
            db.session.commit()
            
            download_ids.append(download.id)
            
            # Start download in background
            thread = threading.Thread(target=downloader.download_video, args=(download.id,))
            thread.daemon = True
            thread.start()
        
        if download_ids:
            flash(f'Started {len(download_ids)} download(s)', 'success')
        
        return redirect(url_for('mobile_downloads'))
        
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}")
        flash('Error starting download', 'error')
        return redirect(url_for('mobile_home'))

@mobile_app.route('/downloads')
def mobile_downloads():
    """Mobile downloads page"""
    active_downloads = MobileDownload.query.filter(
        MobileDownload.status.in_([DownloadStatus.PENDING, DownloadStatus.DOWNLOADING, DownloadStatus.CONVERTING])
    ).order_by(MobileDownload.created_at.desc()).all()
    
    completed_downloads = MobileDownload.query.filter_by(
        status=DownloadStatus.COMPLETED
    ).order_by(MobileDownload.completed_at.desc()).limit(10).all()
    
    return render_template('mobile_downloads.html', 
                         active_downloads=active_downloads,
                         completed_downloads=completed_downloads)

@mobile_app.route('/download-file/<int:download_id>')
def mobile_download_file(download_id):
    """Download file"""
    download = MobileDownload.query.get_or_404(download_id)
    
    if download.status != DownloadStatus.COMPLETED or not download.file_path:
        flash('File not available', 'error')
        return redirect(url_for('mobile_downloads'))
    
    if not os.path.exists(download.file_path):
        flash('File not found', 'error')
        return redirect(url_for('mobile_downloads'))
    
    return send_file(download.file_path, as_attachment=True)

@mobile_app.route('/api/downloads')
def mobile_api_downloads():
    """API for downloads status"""
    downloads = MobileDownload.query.order_by(MobileDownload.created_at.desc()).all()
    return jsonify([download.to_dict() for download in downloads])

def create_mobile_tables():
    """Create database tables"""
    with mobile_app.app_context():
        db.create_all()

def start_mobile_app():
    """Start the mobile app"""
    create_mobile_tables()
    
    # For mobile/APK, we'll run on localhost
    print("Starting Mobile Video Downloader...")
    print(f"Downloads will be saved to: {mobile_app.config['DOWNLOAD_FOLDER']}")
    
    mobile_app.run(host='127.0.0.1', port=8080, debug=False)

if __name__ == '__main__':
    start_mobile_app()
