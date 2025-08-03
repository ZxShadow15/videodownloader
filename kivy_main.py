import os
import sys
import threading
import time
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.logger import Logger
import webbrowser

# Import our mobile app
from mobile_app import mobile_app, create_mobile_tables

class VideoDownloaderApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_thread = None
        self.server_running = False
    
    def build(self):
        """Build the Kivy app interface"""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        title = Label(
            text='Video Downloader',
            size_hint_y=None,
            height=50,
            font_size='20sp'
        )
        layout.add_widget(title)
        
        # Status label
        self.status_label = Label(
            text='Starting server...',
            size_hint_y=None,
            height=40
        )
        layout.add_widget(self.status_label)
        
        # Open Browser Button
        self.open_button = Button(
            text='Open Video Downloader',
            size_hint_y=None,
            height=50,
            disabled=True
        )
        self.open_button.bind(on_press=self.open_browser)
        layout.add_widget(self.open_button)
        
        # Info labels
        info_layout = BoxLayout(orientation='vertical', spacing=5)
        
        info_texts = [
            "• Supports YouTube, Instagram, TikTok, Twitter, Facebook, Telegram and more",
            "• Download videos in MP4, MP3, WebM formats",
            "• Batch download multiple videos at once",
            "• Real-time progress tracking",
            "• Mobile-optimized interface"
        ]
        
        for info_text in info_texts:
            info_label = Label(
                text=info_text,
                text_size=(None, None),
                halign='left',
                size_hint_y=None,
                height=30,
                font_size='14sp'
            )
            info_layout.add_widget(info_label)
        
        layout.add_widget(info_layout)
        
        # Downloads folder info
        downloads_path = mobile_app.config['DOWNLOAD_FOLDER']
        path_label = Label(
            text=f'Downloads saved to:\n{downloads_path}',
            text_size=(None, None),
            halign='center',
            size_hint_y=None,
            height=60,
            font_size='12sp'
        )
        layout.add_widget(path_label)
        
        # Start the server
        Clock.schedule_once(self.start_server, 1)
        
        return layout
    
    def start_server(self, dt):
        """Start the Flask server in a background thread"""
        try:
            # Create database tables
            create_mobile_tables()
            
            # Start server thread
            self.server_thread = threading.Thread(target=self.run_server)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # Schedule status check
            Clock.schedule_interval(self.check_server_status, 1)
            
        except Exception as e:
            Logger.error(f"VideoDownloader: Failed to start server: {e}")
            self.status_label.text = f'Error: {str(e)}'
    
    def run_server(self):
        """Run the Flask server"""
        try:
            Logger.info("VideoDownloader: Starting Flask server...")
            mobile_app.run(host='127.0.0.1', port=8080, debug=False, use_reloader=False)
        except Exception as e:
            Logger.error(f"VideoDownloader: Server error: {e}")
    
    def check_server_status(self, dt):
        """Check if server is running"""
        if not self.server_running:
            try:
                import requests
                response = requests.get('http://127.0.0.1:8080/', timeout=1)
                if response.status_code == 200:
                    self.server_running = True
                    self.status_label.text = 'Server running on http://127.0.0.1:8080'
                    self.open_button.disabled = False
                    return False  # Stop checking
            except:
                pass
        return True  # Continue checking
    
    def open_browser(self, instance):
        """Open the web interface"""
        try:
            import webbrowser
            webbrowser.open('http://127.0.0.1:8080')
            Logger.info("VideoDownloader: Opened browser")
        except Exception as e:
            Logger.error(f"VideoDownloader: Failed to open browser: {e}")
    
    def on_stop(self):
        """Clean up when app stops"""
        Logger.info("VideoDownloader: App stopping...")
        return True

# For buildozer
if __name__ == '__main__':
    VideoDownloaderApp().run()
