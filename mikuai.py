import sys
import os
import sqlite3
import random
import webbrowser
import getpass
import threading
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QListWidget, QListWidgetItem, QLineEdit, 
                           QPushButton, QDialog, QLabel, QCheckBox, QTextEdit,
                           QMessageBox, QFrame, QSystemTrayIcon, QMenu, QTabWidget,
                           QScrollArea, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QAction, QCloseEvent
from chatgpt_wrapper import ChatGPT

# Try to import speech recognition
try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False

class ChatWorker(QThread):
    response_ready = pyqtSignal(str)
    
    def __init__(self, message, chatgpt_instance, username):
        super().__init__()
        self.message = message
        self.chatgpt = chatgpt_instance
        self.username = username
        
    def run(self):
        try:
            response = self.chatgpt.ask(self.message)
            # FORCE MIKU MODE
            miku_responses = [
                f"*giggles* {response} ~desu! (◕‿◕✿)",  
                f"Nya~! {response} ☆⌒ヽ(*'､^*)chu",  
                f"Hmm... *taps chin* {response} ...Mou, ii kai? (；一_一)",  
                f"*singing* 🎵 {response} 🎵 ...Eh? Did I get it right? (• ω •)",  
                f"B-baka! It's not like I'm helping you because I like you or anything! >_< ...{response}"
            ]
            miku_response = random.choice(miku_responses)
            self.response_ready.emit(miku_response)
        except Exception as e:
            error_msg = f"*cries* Error-chan appeared: {str(e)}... Miku can't connect to the digital world! (╥﹏╥)"
            error_msg = error_msg.replace("Error", "*Miku sobs* Error-chan desu...")
            self.response_ready.emit(error_msg)

class VoiceWorker(QThread):
    voice_ready = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
    def run(self):
        try:
            if not SPEECH_AVAILABLE:
                self.voice_ready.emit("*Miku sobs* Error-chan desu... Speech recognition not available!")
                return
                
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source)
                audio = r.listen(source, timeout=10, phrase_time_limit=5)
            
            text = r.recognize_google(audio)
            self.voice_ready.emit(text)
        except sr.WaitTimeoutError:
            self.voice_ready.emit("*Miku tilts head* Timeout desu... I couldn't hear you! (・_・)")
        except sr.UnknownValueError:
            self.voice_ready.emit("*Miku confused* Ehh? I couldn't understand what you said! (◉_◉)")
        except sr.RequestError as e:
            error_msg = f"*Miku sobs* Error-chan desu... No Internet Connection :( - {str(e)}"
            self.voice_ready.emit(error_msg)
        except Exception as e:
            error_msg = f"*cries* Error-chan appeared: {str(e)}"
            error_msg = error_msg.replace("Error", "*Miku sobs* Error-chan desu...")
            self.voice_ready.emit(error_msg)

class ChatDatabase:
    def __init__(self):
        self.db_dir = os.path.expanduser("~/.local/share/miku")
        os.makedirs(self.db_dir, exist_ok=True)
        self.db_path = os.path.join(self.db_dir, "mikuai1.db")
        self.init_db()
        
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create chats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats (id)
            )
        """)
        
        conn.commit()
        conn.close()
        
    def create_chat(self, name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chats (name) VALUES (?)", (name,))
        chat_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return chat_id
        
    def get_chats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, created_at FROM chats ORDER BY created_at DESC")
        chats = cursor.fetchall()
        conn.close()
        return chats
        
    def get_messages(self, chat_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sender, message, timestamp FROM messages WHERE chat_id = ? ORDER BY timestamp", (chat_id,))
        messages = cursor.fetchall()
        conn.close()
        return messages
        
    def add_message(self, chat_id, sender, message):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (chat_id, sender, message) VALUES (?, ?, ?)", 
                      (chat_id, sender, message))
        conn.commit()
        conn.close()
        
    def delete_chat(self, chat_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        conn.commit()
        conn.close()
        
    def rename_chat(self, chat_id, new_name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE chats SET name = ? WHERE id = ?", (new_name, chat_id))
        conn.commit()
        conn.close()

class ChatTab(QWidget):
    def __init__(self, chat_id, chat_name, parent=None):
        super().__init__(parent)
        self.chat_id = chat_id
        self.chat_name = chat_name
        self.parent_window = parent
        self.setup_ui()
        
    def setup_ui(self):
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
        
        # Voice button
        self.voice_button = QPushButton("🎤")
        self.voice_button.setFixedSize(40, 40)
        self.voice_button.clicked.connect(self.start_voice_input)
        if not SPEECH_AVAILABLE:
            self.voice_button.setEnabled(False)
            self.voice_button.setToolTip("Speech recognition not available")
        else:
            self.voice_button.setToolTip("Voice to Text")
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        input_layout.addWidget(self.voice_button)
        
        layout.addWidget(self.chat_list)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
        
        # Load existing messages
        self.load_messages()
        
    def load_messages(self):
        messages = self.parent_window.db.get_messages(self.chat_id)
        for sender, message, timestamp in messages:
            self.add_chat_message(sender, message, save_to_db=False)
            
    def add_chat_message(self, sender, message, save_to_db=True):
        if save_to_db:
            self.parent_window.db.add_message(self.chat_id, sender, message)
            
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
        if sender == self.parent_window.username:
            frame.setStyleSheet("background-color: rgba(0, 255, 255, 0.3); border-radius: 8px; margin: 2px; border: 1px solid #00CCCC;")
        elif sender == "CHATGPT":
            frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.8); border-radius: 8px; margin: 2px; border: 1px solid #FFB6C1;")
            sender_label.setText("MIKU:")  # Change display name to MIKU
        else:
            frame.setStyleSheet("background-color: rgba(255, 240, 245, 0.8); border-radius: 8px; margin: 2px; border: 1px solid #FF69B4;")
            
        item.setSizeHint(frame.sizeHint())
        self.chat_list.addItem(item)
        self.chat_list.setItemWidget(item, frame)
        self.chat_list.scrollToBottom()
        
        return item
        
    def send_message(self):
        message = self.message_input.text().strip()
        if not message:
            return
            
        if not self.parent_window.chatgpt:
            QMessageBox.warning(self, "*Miku sobs* Error-chan desu...", "ChatGPT is not initialized!")
            return
            
        # Add user message
        self.add_chat_message(self.parent_window.username, message)
        
        # Add waiting message
        waiting_item = self.add_chat_message("CHATGPT", "Miku is thinking... (◕‿◕)", save_to_db=False)
        
        # Clear input
        self.message_input.clear()
        
        # Disable send button
        self.send_button.setEnabled(False)
        
        # Start worker thread
        self.worker = ChatWorker(message, self.parent_window.chatgpt, self.parent_window.username)
        self.worker.response_ready.connect(lambda response: self.handle_response(response, waiting_item))
        self.worker.start()
        
    def handle_response(self, response, waiting_item):
        # Remove waiting item
        row = self.chat_list.row(waiting_item)
        self.chat_list.takeItem(row)
        
        # Add actual response
        self.add_chat_message("CHATGPT", response)
        
        # Re-enable send button
        self.send_button.setEnabled(True)
        
    def start_voice_input(self):
        if not SPEECH_AVAILABLE:
            QMessageBox.warning(self, "*Miku sobs* Error-chan desu...", "Speech recognition not available!")
            return
            
        self.voice_button.setEnabled(False)
        self.voice_button.setText("🎙️")
        
        # Start voice worker
        self.voice_worker = VoiceWorker()
        self.voice_worker.voice_ready.connect(self.handle_voice_result)
        self.voice_worker.start()
        
    def handle_voice_result(self, text):
        self.voice_button.setEnabled(True)
        self.voice_button.setText("🎤")
        
        if text.startswith("*"):  # Error message
            QMessageBox.information(self, "Voice Input", text)
        else:
            self.message_input.setText(text)

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
        info_text.setStyleSheet("font-weight: bold; color: #FF1493; margin: 10px;")
        
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
        login_btn.setToolTip("For Chatgpt, go to their websites, this is Miku")
        
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
        info_btn.setStyleSheet("background-color: #FF1493; color: white; font-weight: bold; padding: 8px;")
        
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

class ChatListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # New chat button
        new_chat_btn = QPushButton("+ New Chat")
        new_chat_btn.clicked.connect(self.create_new_chat)
        new_chat_btn.setStyleSheet("background-color: #00FFFF; color: black; font-weight: bold; padding: 8px; margin: 2px;")
        
        # Settings button
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.clicked.connect(self.parent_window.show_settings)
        settings_btn.setStyleSheet("background-color: #FF69B4; color: white; font-weight: bold; padding: 8px; margin: 2px;")
        
        # Chat list
        self.chat_list = QListWidget()
        self.chat_list.setMaximumWidth(200)
        self.chat_list.itemClicked.connect(self.on_chat_selected)
        
        layout.addWidget(new_chat_btn)
        layout.addWidget(settings_btn)
        layout.addWidget(self.chat_list)
        
        self.setLayout(layout)
        self.setMaximumWidth(220)
        
        # Load existing chats
        self.load_chats()
        
    def load_chats(self):
        self.chat_list.clear()
        chats = self.parent_window.db.get_chats()
        for chat_id, chat_name, created_at in chats:
            item = QListWidgetItem(chat_name)
            item.setData(Qt.ItemDataRole.UserRole, chat_id)
            self.chat_list.addItem(item)
            
    def create_new_chat(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        chat_name = f"Chat {timestamp}"
        chat_id = self.parent_window.db.create_chat(chat_name)
        
        # Add to list
        item = QListWidgetItem(chat_name)
        item.setData(Qt.ItemDataRole.UserRole, chat_id)
        self.chat_list.insertItem(0, item)
        
        # Select the new chat
        self.chat_list.setCurrentRow(0)
        self.parent_window.switch_to_chat(chat_id, chat_name)
        
    def on_chat_selected(self, item):
        chat_id = item.data(Qt.ItemDataRole.UserRole)
        chat_name = item.text()
        self.parent_window.switch_to_chat(chat_id, chat_name)

class MikuAI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MikuAI by MalikHw")
        self.setGeometry(100, 100, 1000, 700)
        
        # Get the current username
        self.username = getpass.getuser()
        
        # Initialize database
        self.db = ChatDatabase()
        
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
            error_msg = f"Failed to initialize ChatGPT: {str(e)}"
            error_msg = error_msg.replace("Error", "*Miku sobs* Error-chan desu...")
            QMessageBox.warning(self, "*Miku sobs* Error-chan desu...", error_msg)
            self.chatgpt = None
        
        # Setup UI
        self.setup_ui()
        
        # Apply default theme
        self.dark_theme = False
        self.apply_theme()
        
        # Track if we're just hiding to tray
        self.hide_to_tray = False
        
        # Current chat
        self.current_chat = None
        
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
            error_msg = f"Error setting up personality: {e}"
            error_msg = error_msg.replace("Error", "*Miku sobs* Error-chan desu...")
            print(error_msg)  # Debug log
        
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
                "MikuAI is running in the system tray. Double-click to open! (◕‿◕)",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
                
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout with splitter
        main_layout = QHBoxLayout()
        
        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Chat list
        self.chat_list_widget = ChatListWidget(self)
        splitter.addWidget(self.chat_list_widget)
        
        # Right side - Chat area
        self.chat_area = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_area)
        
        # Welcome message
        welcome_label = QLabel(f"Welcome to MikuAI, {self.username}! 🎤✨\nSelect a chat or create a new one to start chatting with Miku!")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("font-size: 16px; color: #FF1493; font-weight: bold; padding: 50px;")
        self.chat_layout.addWidget(welcome_label)
        
        splitter.addWidget(self.chat_area)
        
        # Set splitter proportions
        splitter.setSizes([220, 780])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # Create initial chat if none exist
        chats = self.db.get_chats()
        if not chats:
            self.chat_list_widget.create_new_chat()
            
    def switch_to_chat(self, chat_id, chat_name):
        # Clear current chat area
        for i in reversed(range(self.chat_layout.count())):
            self.chat_layout.itemAt(i).widget().setParent(None)
            
        # Create new chat tab
        self.current_chat = ChatTab(chat_id, chat_name, self)
        self.chat_layout.addWidget(self.current_chat)
        
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event - hide to tray instead of closing"""
        if self.tray_icon.isVisible():
            self.hide_to_tray_action()
            event.ignore()  # Don't actually close
            if self.tray_icon.supportsMessages():
                self.tray_icon.showMessage(
                    "MikuAI Hidden",
                    "MikuAI is still running in the system tray. Your chat is preserved! (◕‿◕)",
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
            # Dark theme with Miku colors
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1a1a2e;
                    color: #ffffff;
                }
                QWidget {
                    background-color: #1a1a2e;
                    color: #ffffff;
                }
                QListWidget {
                    background-color: #16213e;
                    color: #ffffff;
                    border: 2px solid #00FFFF;
                    border-radius: 8px;
                }
                QListWidget::item {
                    background-color: #16213e;
                    color: #ffffff;
                    padding: 8px;
                    border-bottom: 1px solid #00FFFF;
                }
                QListWidget::item:selected {
                    background-color: #00FFFF;
                    color: #000000;
                }
                QListWidget::item:hover {
                    background-color: rgba(0, 255, 255, 0.3);
                }
                QLineEdit {
                    background-color: #16213e;
                    color: #ffffff;
                    border: 2px solid #00FFFF;
                    padding: 8px;
                    border-radius: 8px;
                    font-size: 12px;
                }
                QLineEdit:focus {
                    border: 2px solid #FF69B4;
                }
                QPushButton {
                    background-color: #00FFFF;
                    color: #000000;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #FF69B4;
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: #FF1493;
                }
                QPushButton:disabled {
                    background-color: #555555;
                    color: #888888;
                }
                QDialog {
                    background-color: #1a1a2e;
                    color: #ffffff;
                }
                QCheckBox {
                    color: #ffffff;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
                QCheckBox::indicator:unchecked {
                    background-color: #16213e;
                    border: 2px solid #00FFFF;
                    border-radius: 4px;
                }
                QCheckBox::indicator:checked {
                    background-color: #00FFFF;
                    border: 2px solid #00FFFF;
                    border-radius: 4px;
                }
                QLabel {
                    color: #ffffff;
                }
                QTextEdit {
                    background-color: #16213e;
                    color: #ffffff;
                    border: 2px solid #00FFFF;
                    border-radius: 8px;
                    padding: 8px;
                }
                QSplitter::handle {
                    background-color: #00FFFF;
                }
            """)
        else:
            # Light theme with Miku colors
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #00FFFF;
                    color: #000000;
                }
                QWidget {
                    background-color: #00FFFF;
                    color: #000000;
                }
                QListWidget {
                    background-color: #ffffff;
                    color: #000000;
                    border: 2px solid #FF69B4;
                    border-radius: 8px;
                }
                QListWidget::item {
                    background-color: #ffffff;
                    color: #000000;
                    padding: 8px;
                    border-bottom: 1px solid #FFB6C1;
                }
                QListWidget::item:selected {
                    background-color: #FF69B4;
                    color: #ffffff;
                }
                QListWidget::item:hover {
                    background-color: rgba(255, 105, 180, 0.3);
                }
                QLineEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 2px solid #FF69B4;
                    padding: 8px;
                    border-radius: 8px;
                    font-size: 12px;
                }
                QLineEdit:focus {
                    border: 2px solid #FF1493;
                }
                QPushButton {
                    background-color: #FF69B4;
                    color: #ffffff;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #FF1493;
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: #DC143C;
                }
                QPushButton:disabled {
                    background-color: #CCCCCC;
                    color: #888888;
                }
                QDialog {
                    background-color: #00FFFF;
                    color: #000000;
                }
                QCheckBox {
                    color: #000000;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
                QCheckBox::indicator:unchecked {
                    background-color: #ffffff;
                    border: 2px solid #FF69B4;
                    border-radius: 4px;
                }
                QCheckBox::indicator:checked {
                    background-color: #FF69B4;
                    border: 2px solid #FF69B4;
                    border-radius: 4px;
                }
                QLabel {
                    color: #000000;
                }
                QTextEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 2px solid #FF69B4;
                    border-radius: 8px;
                    padding: 8px;
                }
                QSplitter::handle {
                    background-color: #FF69B4;
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