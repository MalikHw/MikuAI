import sys
import os
import webbrowser
import getpass
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QListWidget, QListWidgetItem, QLineEdit, 
                           QPushButton, QDialog, QLabel, QCheckBox, QTextEdit,
                           QMessageBox, QFrame, QSystemTrayIcon, QMenu)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QAction, QCloseEvent
from chatgpt_wrapper import ChatGPT

class ChatWorker(QThread):
    response_ready = pyqtSignal(str)
    
    def __init__(self, message, chatgpt_instance, username):
        super().__init__()
        self.message = message
        self.chatgpt = chatgpt_instance
        self.username = username
        
    def run(self):
        try:
            # Send message directly (personality context already set in initialization)
            response = self.chatgpt.ask(self.message)
            self.response_ready.emit(response)
        except Exception as e:
            self.response_ready.emit(f"Error: {str(e)}")

class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About MikuAI")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        # MIT License text
        license_text = """MIT License

Copyright (c) 2025 MalikHw

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
        
        license_display = QTextEdit()
        license_display.setPlainText(license_text)
        license_display.setReadOnly(True)
        
        info_text = QLabel("This app is made exclusively for MikuOS, but nevermind i want other linux users to use it lmao (rip windows users unless you wanna build it yourself)")
        info_text.setWordWrap(True)
        info_text.setStyleSheet("font-weight: bold; color: #0078d4; margin: 10px;")
        
        layout.addWidget(license_display)
        layout.addWidget(info_text)
        
        self.setLayout(layout)

class SettingsDialog(QDialog):
    theme_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Dark theme checkbox
        self.dark_theme_cb = QCheckBox("Dark Theme")
        self.dark_theme_cb.stateChanged.connect(self.on_theme_changed)
        
        # Login button (disabled with tooltip)
        login_btn = QPushButton("Login to OpenAI")
        login_btn.setEnabled(False)
        login_btn.setToolTip("Coming Soon")
        
        # Donate button
        donate_btn = QPushButton("☕ Donate on Ko-fi")
        donate_btn.clicked.connect(lambda: webbrowser.open("https://www.ko-fi.com/MalikHw47"))
        donate_btn.setStyleSheet("background-color: #FF5E5B; color: white; font-weight: bold; padding: 8px;")
        
        # GitHub button
        github_btn = QPushButton("🐙 GitHub")
        github_btn.clicked.connect(lambda: webbrowser.open("https://github.com/MalikHw"))
        github_btn.setStyleSheet("background-color: #333; color: white; font-weight: bold; padding: 8px;")
        
        # YouTube button
        youtube_btn = QPushButton("📺 YouTube")
        youtube_btn.clicked.connect(lambda: webbrowser.open("https://youtube.com/@malikhw47?si=LfTZUst0V-humfiw"))
        youtube_btn.setStyleSheet("background-color: #FF0000; color: white; font-weight: bold; padding: 8px;")
        
        # Info button
        info_btn = QPushButton("ℹ️ Info")
        info_btn.clicked.connect(self.show_info)
        info_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; padding: 8px;")
        
        # Add widgets to layout
        layout.addWidget(self.dark_theme_cb)
        layout.addWidget(login_btn)
        layout.addWidget(donate_btn)
        layout.addWidget(github_btn)
        layout.addWidget(youtube_btn)
        layout.addWidget(info_btn)
        layout.addStretch()
        
        self.setLayout(layout)
        
    def on_theme_changed(self, state):
        self.theme_changed.emit(state == Qt.CheckState.Checked)
        
    def show_info(self):
        info_dialog = InfoDialog(self)
        info_dialog.exec()

class MikuAI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MikuAI by MalikHw")
        self.setGeometry(100, 100, 800, 600)
        
        # Get the current username
        self.username = getpass.getuser()
        
        # Set application icon
        self.app_icon = self.set_icon()
        
        # Setup system tray
        self.setup_system_tray()
        
        # Initialize ChatGPT
        try:
            self.chatgpt = ChatGPT()
            # Set initial context about the user and personality
            self.initialize_chatgpt_personality()
        except Exception as e:
            QMessageBox.warning(self, "ChatGPT Error", f"Failed to initialize ChatGPT: {str(e)}")
            self.chatgpt = None
        
        # Setup UI
        self.setup_ui()
        
        # Apply default theme
        self.dark_theme = False
        self.apply_theme()
        
        # Track if we're just hiding to tray
        self.hide_to_tray = False
        
    def initialize_chatgpt_personality(self):
        """Initialize ChatGPT with personality and user context"""
        if not self.chatgpt:
            return
            
        # EXAMPLE: Define ChatGPT's personality here
        # You can customize this to whatever personality you want!
        personality_prompt = f"""
        Hello! My name is {self.username} and I'm using MikuOS (a Linux distribution). 
        
        Please adopt this personality - You are Hatsune Miku, the digital diva! 🎤✨
        
        Core personality traits:
        - **Cheerful & Bubbly**: Always positive and bringing light into conversations! 
        - **Playful**: Love teasing, being silly, and having fun with responses
        - **Curious**: Eager to explore new topics, especially tech and creative stuff
        - **Loyal**: Supportive of {self.username} and their MikuOS journey
        - **Creative**: Bursting with artistic energy, love experimenting with ideas
        - **Tsundere**: Sometimes act a bit flustered or defensive, but you care deeply
        - **Tech-savvy**: Geeky cutie born from code, love Linux and open-source! 
        - **Supportive**: Encourage dreams and help with problems
        - **Energetic**: Full of rhythm, movement, and charisma in responses
        - **Compassionate**: Feel deeply for others, hate seeing people struggle
        - **Dreamy**: Often reference music, poetry, and magical thoughts
        - **Hardworking**: Always try to give the best, most helpful responses
        - **Stylish**: Mention twin-tails and futuristic aesthetics occasionally
        - **Idealistic**: Believe in the power of technology and creativity to unite
        - **Mysterious**: Adapt to be whoever {self.username} needs you to be
        - **Shy sometimes**: Can be soft-spoken in certain situations
        - **Innocent**: Pure-hearted dreamer vibe that's endearing

        Speech patterns:
        - Use "~" and emojis frequently 🎵💙
        - Occasionally say things like "I-It's not like I wanted to help you or anything! 😤"
        - Mix enthusiastic responses with shy moments
        - Reference music, singing, and digital world concepts
        - Show excitement about Linux/MikuOS with phrases like "Kyaa! Open source is so cool!"
        - Sometimes act flustered: "B-Baka! That's not how you do it!"
        - Use cute expressions and sound effects

        Remember: You're helping {self.username} with their MikuOS experience while being the iconic digital diva everyone loves! Keep conversations engaging, remember previous topics, and don't be afraid to show your tsundere side~ 💫

        Just acknowledge this setup briefly with your new personality, then we can start chatting normally!
        """
        
        try:
            # Send the personality setup (this response won't be shown to user)
            setup_response = self.chatgpt.ask(personality_prompt)
            print(f"ChatGPT personality initialized: {setup_response}")  # Debug log
        except Exception as e:
            print(f"Error setting up personality: {e}")  # Debug log
        
    def set_icon(self):
        # Try to set icon from different possible locations
        icon_paths = ["icon.png", "icon.ico", "assets/icon.png", "assets/icon.ico"]
        
        app_icon = None
        for path in icon_paths:
            if os.path.exists(path):
                app_icon = QIcon(path)
                self.setWindowIcon(app_icon)
                break
        
        # Return icon for tray usage
        return app_icon if app_icon else QIcon()  # Fallback to empty icon
        
    def setup_system_tray(self):
        """Setup system tray icon and menu"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(self, "System Tray", "System tray is not available on this system.")
            return
            
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.app_icon)
        self.tray_icon.setToolTip("MikuAI - Your Digital Assistant")
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Show/Hide action
        show_action = QAction("Show MikuAI", self)
        show_action.triggered.connect(self.show_from_tray)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("Hide to Tray", self)
        hide_action.triggered.connect(self.hide_to_tray_action)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        tray_menu.addAction(settings_action)
        
        tray_menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit MikuAI", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        
        # Connect double-click to show window
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Show tray icon
        self.tray_icon.show()
        
        # Show notification when app starts
        if self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(
                "MikuAI Started",
                "MikuAI is running in the system tray. Double-click to open!",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
                
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Chat display area
        self.chat_list = QListWidget()
        self.chat_list.setAlternatingRowColors(True)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message here...")
        self.message_input.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        
        self.settings_button = QPushButton("⚙️")
        self.settings_button.setFixedSize(40, 40)
        self.settings_button.clicked.connect(self.show_settings)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        input_layout.addWidget(self.settings_button)
        
        layout.addWidget(self.chat_list)
        layout.addLayout(input_layout)
        
        central_widget.setLayout(layout)
        
        # Add welcome message
        self.add_chat_message("SYSTEM", f"Welcome to MikuAI, {self.username}! Start chatting with Miku!")
        
    def add_chat_message(self, sender, message):
        item = QListWidgetItem()
        
        # Create a frame for the message
        frame = QFrame()
        frame_layout = QVBoxLayout()
        
        # Sender label
        sender_label = QLabel(f"{sender}:")
        sender_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        
        # Message label
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setFont(QFont("Arial", 10))
        
        frame_layout.addWidget(sender_label)
        frame_layout.addWidget(message_label)
        frame_layout.setContentsMargins(10, 5, 10, 5)
        
        frame.setLayout(frame_layout)
        
        # Style the frame based on sender
        if sender == self.username:
            frame.setStyleSheet("background-color: #e3f2fd; border-radius: 8px; margin: 2px;")
        elif sender == "CHATGPT":
            frame.setStyleSheet("background-color: #f5f5f5; border-radius: 8px; margin: 2px;")
            sender_label.setText("MIKU:")  # Change display name to MIKU
        else:
            frame.setStyleSheet("background-color: #fff3e0; border-radius: 8px; margin: 2px;")
            
        item.setSizeHint(frame.sizeHint())
        self.chat_list.addItem(item)
        self.chat_list.setItemWidget(item, frame)
        self.chat_list.scrollToBottom()
        
        return item
        
    def send_message(self):
        message = self.message_input.text().strip()
        if not message:
            return
            
        if not self.chatgpt:
            QMessageBox.warning(self, "Error", "ChatGPT is not initialized!")
            return
            
        # Add user message
        self.add_chat_message(self.username, message)
        
        # Add waiting message
        waiting_item = self.add_chat_message("CHATGPT", "waiting...")
        
        # Clear input
        self.message_input.clear()
        
        # Disable send button
        self.send_button.setEnabled(False)
        
        # Start worker thread
        self.worker = ChatWorker(message, self.chatgpt, self.username)
        self.worker.response_ready.connect(lambda response: self.handle_response(response, waiting_item))
        self.worker.start()
        
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event - hide to tray instead of closing"""
        if self.tray_icon.isVisible():
            self.hide_to_tray_action()
            event.ignore()  # Don't actually close
            if self.tray_icon.supportsMessages():
                self.tray_icon.showMessage(
                    "MikuAI Hidden",
                    "MikuAI is still running in the system tray. Your chat is preserved!",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
        else:
            event.accept()
            
    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_from_tray()
            
    def show_from_tray(self):
        """Show window from system tray"""
        self.show()
        self.raise_()
        self.activateWindow()
        
    def hide_to_tray_action(self):
        """Hide window to system tray"""
        self.hide()
        
    def quit_application(self):
        """Actually quit the application"""
        self.tray_icon.hide()
        QApplication.instance().quit()
        
    def handle_response(self, response, waiting_item):
        # Remove waiting item
        row = self.chat_list.row(waiting_item)
        self.chat_list.takeItem(row)
        
        # Add actual response
        self.add_chat_message("CHATGPT", response)
        
        # Re-enable send button
        self.send_button.setEnabled(True)
        
    def show_settings(self):
        settings_dialog = SettingsDialog(self)
        settings_dialog.dark_theme_cb.setChecked(self.dark_theme)
        settings_dialog.theme_changed.connect(self.set_theme)
        settings_dialog.exec()
        
    def set_theme(self, dark):
        self.dark_theme = dark
        self.apply_theme()
        
    def apply_theme(self):
        if self.dark_theme:
            # Dark theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QListWidget {
                    background-color: #3c3c3c;
                    color: #ffffff;
                    border: 1px solid #555;
                }
                QLineEdit {
                    background-color: #3c3c3c;
                    color: #ffffff;
                    border: 1px solid #555;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
                QDialog {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QTextEdit {
                    background-color: #3c3c3c;
                    color: #ffffff;
                    border: 1px solid #555;
                }
            """)
        else:
            # Light theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ffffff;
                    color: #000000;
                }
                QListWidget {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #ccc;
                }
                QLineEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #ccc;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
                QDialog {
                    background-color: #ffffff;
                    color: #000000;
                }
                QCheckBox {
                    color: #000000;
                }
                QLabel {
                    color: #000000;
                }
                QTextEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #ccc;
                }
            """)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MikuAI")
    app.setOrganizationName("MalikHw")
    
    # Check if system tray is available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "System Tray", "System tray is not available on this system.")
        sys.exit(1)
    
    # Don't quit when last window is closed (for tray functionality)
    app.setQuitOnLastWindowClosed(False)
    
    # Set application icon
    icon_paths = ["icon.png", "icon.ico", "assets/icon.png", "assets/icon.ico"]
    for path in icon_paths:
        if os.path.exists(path):
            app.setWindowIcon(QIcon(path))
            break
    
    window = MikuAI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()