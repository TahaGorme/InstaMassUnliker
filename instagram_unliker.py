#!/usr/bin/env python3

# Auto-install required modules BEFORE any other imports
import subprocess
import sys

required_modules = [
    "psutil",
    "tqdm",
    "colorama",
    "requests",
    "moviepy",
    "ensta==5.2.9"
]

def install_missing():
    for module in required_modules:
        mod_name = module.split("==")[0] if "==" in module else module
        try:
            __import__(mod_name)
        except ImportError:
            print(f"[!] Installing missing module: {module}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", module])

install_missing()

import os
import sys
import json
import time
import random
import logging
import platform
import subprocess
import shutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from getpass import getpass
import webbrowser
import signal
from tqdm import tqdm
import urllib.request
import tempfile
from logging.handlers import RotatingFileHandler
import atexit

# Global logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Global variables for configuration
CONFIG = {
    "delay": {
        "min": 60,  # 1 minutes minimum
        "max": 300,  # 5 minutes maximum
    },
    "break": {
        "min": 900,  # 15 minutes
        "max": 3600,  # 1 hour
        "probability": 0.1  # 10% chance of taking a break
    },
    "accounts": {},
    "log_level": "INFO",
    "max_retries": 3,
    "retry_delay": 60,  # 1 minute
    "auto_update": True,
    "python_min_version": "3.7.0"  # Minimum required Python version
}

class ConsoleColors:
    HEADER = '\033[95m'  # Pink
    BLUE = '\033[94m'    # Blue
    GREEN = '\033[92m'   # Green
    YELLOW = '\033[93m'  # Yellow
    RED = '\033[91m'     # Red
    PURPLE = '\033[95m'  # Purple
    CYAN = '\033[96m'    # Cyan
    WHITE = '\033[97m'   # White
    MAGENTA = '\033[35m' # Magenta
    BOLD = '\033[1m'     # Bold
    UNDERLINE = '\033[4m'# Underline
    RESET = '\033[0m'    # Reset all formatting

class InstagramUnliker:
    def __init__(self):
        """Initialize the Instagram Unliker application"""
        logging.info("Starting Instagram Unliker application...")

        self.config_file = "config.json"
        self.accounts_dir = Path("accounts")
        self.logs_dir = Path("logs")
        self.running = True

        # Create necessary directories
        self._create_required_directories()

        # Check and setup Python environment
        self._ensure_python_environment()
        self._setup_signal_handlers()
        self.setup_logging()

        # Load configuration
        self.check_and_create_config()

    def _ensure_python_environment(self):
        """Ensure Python and pip are properly installed"""
        try:
            # Check if pip is installed
            import pip
        except ImportError:
            logging.warning("pip is not installed. Installing pip...")
            self._install_pip()

    def _install_pip(self):
        """Install pip if not present"""
        try:
            # Download get-pip.py
            import urllib.request
            urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", "get-pip.py")

            # Install pip
            subprocess.check_call([sys.executable, "get-pip.py"])
            logging.info("Successfully installed pip")

            # Clean up
            os.remove("get-pip.py")
        except Exception as e:
            logging.error(f"Failed to install pip: {str(e)}")
            print("Please visit https://pip.pypa.io/en/stable/installation/ for manual installation instructions")
            sys.exit(1)

    def _setup_signal_handlers(self):
        """Set up handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n{ConsoleColors.YELLOW}[!] Received shutdown signal. Cleaning up...{ConsoleColors.RESET}")
        self.running = False
        time.sleep(1)  # Give time for cleanup
        sys.exit(0)

    def setup_logging(self):
        """Configure logging with enhanced rotation and cleanup"""
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Set up rotating file handler
        log_file = self.logs_dir / "unliker.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5*1024*1024,  # 5MB per file
            backupCount=5,  # Keep 5 backup files
            encoding='utf-8'
        )

        # Set up formatters with more detailed information
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )

        file_handler.setFormatter(file_formatter)

        # Console handler with color support
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)

        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        # Remove existing handlers and add new ones
        root_logger.handlers.clear()
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # Register cleanup on exit
        atexit.register(self._cleanup_logs)

        logging.info("Logging system initialized")

    def _cleanup_logs(self):
        """Cleanup function that runs on program exit"""
        try:
            logging.info("Performing final cleanup...")
            # Save any pending configurations
            self.save_config()

            # Close all handlers
            for handler in logging.getLogger().handlers:
                handler.close()

        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

    def _log_system_info(self):
        """Log detailed system information"""
        logging.info("-" * 50)
        logging.info("System Information:")
        logging.info(f"OS: {platform.system()} {platform.release()}")
        logging.info(f"Python: {sys.version}")
        logging.info(f"Platform: {platform.platform()}")
        logging.info(f"Working Directory: {os.getcwd()}")
        logging.info("-" * 50)

    def _cleanup_old_logs(self, days=5):
        """Clean up log files older than specified days"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            for log_file in self.logs_dir.glob("*.log"):
                if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                    log_file.unlink()
        except Exception as e:
            logging.warning(f"Failed to cleanup old logs: {str(e)}")

    def _create_required_directories(self):
        """Create necessary directories if they don't exist"""
        try:
            self.accounts_dir.mkdir(exist_ok=True)
            self.logs_dir.mkdir(exist_ok=True)
            logging.info("Required directories created successfully")
        except Exception as e:
            logging.error(f"Failed to create directories: {str(e)}")
            print("Please ensure you have write permissions in the current directory")

    def check_python_version(self) -> bool:
        """Verify Python version meets requirements"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 7):
            print(f"{ConsoleColors.RED}[✗] Error: Python 3.7 or higher required (current: {version.major}.{version.minor}){ConsoleColors.RESET}")
            return False
        print(f"{ConsoleColors.GREEN}[✓] Python version check passed ({version.major}.{version.minor}){ConsoleColors.RESET}")
        return True

    def install_requirements(self) -> bool:
        """Install all required Python packages"""
        try:
            required_packages = [
                "psutil",
                "tqdm",
                "colorama",
                "requests",
                "ensta==5.2.9",
                "moviepy==1.0.3"
            ]

            # Uninstall ensta just in case it's broken
            subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "ensta"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Install everything fresh
            result = subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", *required_packages],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if result.returncode != 0:
                logging.error(f"Failed to install packages: {result.stderr.decode()}")
                print(f"{ConsoleColors.RED}[✗] Failed to install packages. Error:\n{result.stderr.decode()}{ConsoleColors.RESET}")
                return False

            logging.info("Successfully installed all required packages.")
            print(f"{ConsoleColors.GREEN}[✓] Dependencies installed successfully{ConsoleColors.RESET}")
            return True

        except Exception as e:
            logging.error(f"Error during dependency installation: {str(e)}")
            print(f"{ConsoleColors.RED}[✗] Installation error: {str(e)}{ConsoleColors.RESET}")
            return False


    def check_and_create_config(self):
        """Create or load configuration file"""
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w') as f:
                json.dump(CONFIG, f, indent=4)
            print(f"{ConsoleColors.GREEN}[✓] Created default configuration file{ConsoleColors.RESET}")
        else:
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Update global CONFIG with loaded values
                    for key, value in loaded_config.items():
                        if key in CONFIG:
                            CONFIG[key] = value
                print(f"{ConsoleColors.GREEN}[✓] Loaded existing configuration{ConsoleColors.RESET}")
            except json.JSONDecodeError:
                print(f"{ConsoleColors.RED}[✗] Error: Corrupted configuration file{ConsoleColors.RESET}")
                backup_file = f"{self.config_file}.bak"
                os.rename(self.config_file, backup_file)
                print(f"{ConsoleColors.YELLOW}[!] Backed up corrupted config to {backup_file}{ConsoleColors.RESET}")
                self.check_and_create_config()

    def add_account(self):
        """Add account with improved UI"""
        print(f"\n{ConsoleColors.CYAN}➕ Add Instagram Account{ConsoleColors.RESET}")
        print("-" * 40)

        username = input(f"{ConsoleColors.BOLD}Username: {ConsoleColors.RESET}").strip()
        password = input(f"{ConsoleColors.BOLD}Password: {ConsoleColors.RESET}").strip()

        if not username or not password:
            print(f"{ConsoleColors.RED}Username and password are required{ConsoleColors.RESET}")
            return

        self.accounts_dir.mkdir(exist_ok=True)
        account_file = self.accounts_dir / f"{username}.json"

        if account_file.exists():
            override = input(f"{ConsoleColors.YELLOW}Account exists. Replace? (y/N): {ConsoleColors.RESET}").lower()
            if override != 'y':
                return

        account_data = {
            "username": username,
            "password": password,
            "last_run": None,
            "total_unliked": 0,
            "last_error": None,
            "created_at": datetime.now().isoformat()
        }

        try:
            with open(account_file, 'w') as f:
                json.dump(account_data, f, indent=4)

            CONFIG['accounts'][username] = {
                "enabled": True,
                "delay_multiplier": 1.0
            }
            self.save_config()

            print(f"{ConsoleColors.GREEN}✨ Account @{username} added successfully!{ConsoleColors.RESET}")
        except Exception as e:
            print(f"{ConsoleColors.RED}Could not save account: {str(e)}{ConsoleColors.RESET}")

    def remove_account(self):
        """Remove an Instagram account"""
        accounts = self.list_accounts()
        if not accounts:
            print(f"{ConsoleColors.YELLOW}[!] No accounts configured{ConsoleColors.RESET}")
            return

        print(f"\n{ConsoleColors.BLUE}[×] Remove Account{ConsoleColors.RESET}")
        print("-" * 30)
        for i, acc in enumerate(accounts, 1):
            print(f"{i}. {acc}")

        try:
            choice = input(f"\n{ConsoleColors.BOLD}Select account to remove (0 to cancel): {ConsoleColors.RESET}")
            if not choice.isdigit() or int(choice) == 0:
                return

            choice = int(choice)
            if choice < 1 or choice > len(accounts):
                print(f"{ConsoleColors.RED}[✗] Invalid selection{ConsoleColors.RESET}")
                return

            username = accounts[choice - 1]
            account_file = self.accounts_dir / f"{username}.json"

            confirm = input(f"{ConsoleColors.YELLOW}[!] Are you sure you want to remove {username}? (y/N): {ConsoleColors.RESET}").lower()
            if confirm != 'y':
                return

            if account_file.exists():
                account_file.unlink()

            if username in CONFIG['accounts']:
                del CONFIG['accounts'][username]
                self.save_config()

            print(f"{ConsoleColors.GREEN}[✓] Account {username} removed successfully{ConsoleColors.RESET}")

        except Exception as e:
            print(f"{ConsoleColors.RED}[✗] Error: {str(e)}{ConsoleColors.RESET}")

    def list_accounts(self) -> List[str]:
        """List all configured accounts"""
        if not self.accounts_dir.exists():
            return []

        return [f.stem for f in self.accounts_dir.glob("*.json")]

    def save_config(self):
        """Save current configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(CONFIG, f, indent=4)
        except Exception as e:
            print(f"{ConsoleColors.RED}[✗] Failed to save configuration: {str(e)}{ConsoleColors.RESET}")

    def unlike_posts(self, username: str):
        """Unlike posts using JSON file"""
        account_file = self.accounts_dir / f"{username}.json"
        progress_bar = None  # Initialize progress_bar at the beginning of the method

        if not account_file.exists():
            error_msg = f"Account file not found for {username}"
            logging.error(error_msg)
            print(f"\n{ConsoleColors.RED}[✗] {error_msg}. Please add it first.{ConsoleColors.RESET}")
            return

        try:
            with open(account_file, 'r') as f:
                account_data = json.load(f)

            print(f"\n{ConsoleColors.CYAN}Starting to unlike posts for @{username}...{ConsoleColors.RESET}")
            print(f"{ConsoleColors.YELLOW}This will run in the background. You can close anytime.{ConsoleColors.RESET}")

            try:
                from ensta import Web
                client = Web(account_data['username'], account_data['password'])
                print(f"{ConsoleColors.GREEN}✓ Successfully logged in{ConsoleColors.RESET}")
                account = client.private_info()
                print(f"{ConsoleColors.GREEN}Logged in as: {ConsoleColors.CYAN}{account.username}{ConsoleColors.RESET}")
            except Exception as e:
                error_msg = f"Login failed: {str(e)}"
                logging.error(error_msg)
                print(f"{ConsoleColors.RED}[✗] {error_msg}")
                print(f"→ Please check your username and password.{ConsoleColors.RESET}")
                return

            # Try to load liked posts from JSON file
            if not os.path.exists('liked_posts.json'):
                error_msg = "liked_posts.json file not found"
                logging.error(error_msg)
                print(f"{ConsoleColors.RED}[✗] {error_msg}. Please ensure it exists.{ConsoleColors.RESET}")
                return

            try:
                with open('liked_posts.json', 'r') as f:
                    liked_data = json.load(f)

                if not liked_data.get('likes_media_likes'):
                    error_msg = "No liked posts found in JSON file"
                    logging.warning(error_msg)
                    print(f"{ConsoleColors.YELLOW}[!] {error_msg}!{ConsoleColors.RESET}")
                    return

                total_posts = len(liked_data['likes_media_likes'])
                first_likes_media_likes = total_posts
                unliked_count = 0

                print(f"{ConsoleColors.BLUE}Found {total_posts} liked posts{ConsoleColors.RESET}")

                progress_bar = tqdm(
                    total=total_posts,
                    desc=f"🔄 Unliking posts",
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [ETA: {remaining}]'
                )

                while liked_data['likes_media_likes'] and self.running:
                    try:
                        base_delay = random.uniform(CONFIG['delay']['min'], CONFIG['delay']['max'])
                        actual_delay = base_delay * CONFIG['accounts'][username].get('delay_multiplier', 1.0)
                        time.sleep(actual_delay)

                        post = liked_data['likes_media_likes'].pop(0)
                        media_id = instagram_code_to_media_id(post['string_list_data'][0]['href'])

                        # Unlike with retry mechanism and detailed error logging
                        for retry in range(CONFIG['max_retries']):
                            try:
                                client.unlike(media_id)
                                break
                            except Exception as e:
                                error_msg = f"Failed to unlike post (attempt {retry + 1}/{CONFIG['max_retries']}): {str(e)}"
                                logging.warning(error_msg)
                                if retry < CONFIG['max_retries'] - 1:
                                    print(f"{ConsoleColors.YELLOW}[!] {error_msg}. Retrying...{ConsoleColors.RESET}")
                                    time.sleep(CONFIG['retry_delay'])
                                else:
                                    raise Exception(error_msg)

                        unliked_count += 1
                        account_data['total_unliked'] += 1
                        progress_bar.update(1)

                        # Update JSON file
                        with open('liked_posts.json', 'w') as f:
                            json.dump(liked_data, f, indent=4)

                        # Random break
                        if random.random() < CONFIG['break']['probability']:
                            break_time = random.uniform(CONFIG['break']['min'], CONFIG['break']['max'])
                            print(f"\n{ConsoleColors.BLUE}[*] Taking a break for {break_time/60:.1f} minutes...{ConsoleColors.RESET}")
                            time.sleep(break_time)

                    except Exception as e:
                        error_msg = f"Failed to unlike post: {str(e)}"
                        logging.error(error_msg, exc_info=True)  # Include full traceback in logs
                        print(f"{ConsoleColors.RED}[✗] {error_msg}")
                        print(f"→ Taking a 5-minute cooldown...{ConsoleColors.RESET}")
                        account_data['last_error'] = error_msg
                        time.sleep(300)  # 5 minute cooldown on error

            finally:
                if progress_bar is not None:
                    progress_bar.close()

            # Update account stats
            account_data['last_run'] = datetime.now().isoformat()
            with open(account_file, 'w') as f:
                json.dump(account_data, f, indent=4)

            print(f"\n{ConsoleColors.GREEN}[✓] Unliking complete for {username}{ConsoleColors.RESET}")
            print(f"{ConsoleColors.BLUE}[*] Total unliked: {account_data['total_unliked']}{ConsoleColors.RESET}")

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON format in account file: {str(e)}"
            logging.error(error_msg)
            print(f"{ConsoleColors.RED}[✗] {error_msg}")
            print("→ Try removing and re-adding your account.{ConsoleColors.RESET}")
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(error_msg, exc_info=True)  # Include full traceback in logs
            print(f"\n{ConsoleColors.RED}[✗] {error_msg}")
            print("→ The error has been logged. Please check the logs for details.{ConsoleColors.RESET}")
            try:
                account_data['last_error'] = error_msg
                with open(account_file, 'w') as f:
                    json.dump(account_data, f, indent=4)
            except:
                logging.error("Failed to save error information to account file", exc_info=True)

    def center_text_in_box(text, box_width=48):
        """Center text in a box line, accounting for color codes"""
        # Get visible length excluding color codes
        visible_length = get_visible_length(text)
        # Calculate padding needed for centering
        padding = (box_width - 2 - visible_length) // 2  # -2 for the box edges
        return f"║{' ' * padding}{text}{' ' * (box_width - 2 - visible_length - padding)}║"

    def show_menu(self):
        """Display interactive menu with improved UI"""
        while True:
            # Clear screen for better visibility
            # print("\033[H\033[J" if platform.system() != "Windows" else os.system('cls'))

            # Display decorated header
            print(f"\n{ConsoleColors.CYAN}{ConsoleColors.BOLD}╔{'═' * 46}╗")
            print(InstagramUnliker.center_text_in_box(f"{ConsoleColors.BOLD}Instagram Mass Unliker{ConsoleColors.RESET}{ConsoleColors.CYAN}{ConsoleColors.BOLD}"))
            print(InstagramUnliker.center_text_in_box(f"{ConsoleColors.BOLD}Erase your digital footprint{ConsoleColors.RESET}{ConsoleColors.CYAN}{ConsoleColors.BOLD}"))
            print(f"╚{'═' * 46}╝{ConsoleColors.RESET}")
            # Display account status if any exist
            accounts = self.list_accounts()
            if accounts:
                print(f"\n{ConsoleColors.BLUE}Connected Accounts: {ConsoleColors.GREEN}{len(accounts)}{ConsoleColors.RESET}")
                for acc in accounts[:3]:  # Show up to 3 accounts
                    print(f"  {ConsoleColors.WHITE}•{ConsoleColors.RESET} @{acc}")
                if len(accounts) > 3:
                    print(f"  {ConsoleColors.WHITE}•{ConsoleColors.RESET} ...and {len(accounts) - 3} more")
            else:
                print(f"\n{ConsoleColors.YELLOW}No accounts connected yet{ConsoleColors.RESET}")

            # Main menu options with better visual hierarchy
            print(f"\n{ConsoleColors.CYAN}Available Actions:{ConsoleColors.RESET}")
            print(f"╭{'─' * 40}╮")
            print(menu_line("1", "Add Instagram Account"))
            print(menu_line("2", "Remove Account"))
            print(menu_line("3", "Start Unliking"))
            print(menu_line("4", "View Stats"))
            print(menu_line("5", "Settings"))
            print(menu_line("0", "Exit"))
            print(f"╰{'─' * 40}╯")

            # Input prompt with better styling
            try:
                print(f"\n{ConsoleColors.WHITE}╭─ Enter your choice{ConsoleColors.RESET}")
                choice = input(f"{ConsoleColors.WHITE}╰─▸{ConsoleColors.RESET} ").strip()

                if choice == "1":
                    self.add_account()
                elif choice == "2":
                    self.remove_account()
                elif choice == "3":
                    self._start_unliking_menu()
                elif choice == "4":
                    self.show_statistics()
                elif choice == "5":
                    self.show_settings()
                elif choice == "0":
                    print(f"\n{ConsoleColors.GREEN}✨ Thanks for using Instagram Unliker!")
                    print(f"👋 Have a great day!{ConsoleColors.RESET}")
                    break
                else:
                    print(f"\n{ConsoleColors.RED}✗ Invalid choice. Please try again.{ConsoleColors.RESET}")
                    time.sleep(1)

            except KeyboardInterrupt:
                print(f"\n\n{ConsoleColors.GREEN}✨ Thanks for using Instagram Unliker!")
                print(f"👋 Have a great day!{ConsoleColors.RESET}")
                break
            except Exception as e:
                print(f"\n{ConsoleColors.RED}✗ Error: {str(e)}{ConsoleColors.RESET}")
                time.sleep(2)

    def _display_header(self):
        """Display program header with improved UI"""
        print(f"\n{ConsoleColors.CYAN}{ConsoleColors.BOLD}")
        print("╔══════════════════════════════════════════╗")
        print("║           Instagram Unliker              ║")
        print("║      Easily Unlike Your Old Posts        ║")
        print("╚══════════════════════════════════════════╝")
        print(f"{ConsoleColors.RESET}")

    def _start_unliking_menu(self):
        """Display account selection menu for unliking"""
        accounts = self.list_accounts()
        if not accounts:
            print(f"{ConsoleColors.RED}[✗] No accounts configured. Please add an account first.{ConsoleColors.RESET}")
            return

        print(f"\n{ConsoleColors.BLUE}[#] Select Account{ConsoleColors.RESET}")
        print("-" * 30)

        for i, acc in enumerate(accounts, 1):
            # Get account status
            account_file = self.accounts_dir / f"{acc}.json"
            status = "Ready"
            if account_file.exists():
                with open(account_file) as f:
                    data = json.load(f)
                    if data.get('last_error'):
                        status = f"Error: {data['last_error']}"
                    elif data.get('last_run'):
                        status = f"Last run: {datetime.fromisoformat(data['last_run']).strftime('%Y-%m-%d %H:%M')}"

            print(f"{ConsoleColors.BOLD}{i}{ConsoleColors.RESET}. [{acc}] - {status}")

        try:
            choice = input(f"\n{ConsoleColors.BOLD}[>] Select account (0 to cancel): {ConsoleColors.RESET}")
            if not choice.isdigit() or int(choice) == 0:
                return

            choice = int(choice)
            if choice < 1 or choice > len(accounts):
                print(f"{ConsoleColors.RED}[✗] Invalid selection{ConsoleColors.RESET}")
                return

            self.unlike_posts(accounts[choice - 1])

        except ValueError:
            print(f"{ConsoleColors.RED}[✗] Invalid input{ConsoleColors.RESET}")
        except Exception as e:
            print(f"{ConsoleColors.RED}[✗] Error: {str(e)}{ConsoleColors.RESET}")

    def show_statistics(self):
        """Display statistics with improved UI"""
        accounts = self.list_accounts()
        if not accounts:
            print(f"{ConsoleColors.YELLOW}No accounts added yet{ConsoleColors.RESET}")
            input(f"\n{ConsoleColors.BOLD}Press Enter to continue...{ConsoleColors.RESET}")  # Added pause
            return

        print(f"\n{ConsoleColors.CYAN}📊 Statistics{ConsoleColors.RESET}")
        print("=" * 40)

        total_unliked = 0
        for username in accounts:
            account_file = self.accounts_dir / f"{username}.json"
            try:
                with open(account_file, 'r') as f:
                    data = json.load(f)

                total_unliked += data.get('total_unliked', 0)
                print(f"\n{ConsoleColors.BOLD}{ConsoleColors.BLUE}@{username}{ConsoleColors.RESET}")
                print(f"📌 Unliked posts: {data.get('total_unliked', 0)}")
                if data.get('last_run'):
                    print(f"🕒 Last active: {datetime.fromisoformat(data['last_run']).strftime('%Y-%m-%d %H:%M')}")
                print(f"✨ Status: {'OK' if not data.get('last_error') else 'Error'}")
            except Exception as e:
                print(f"{ConsoleColors.RED}Could not read data for {username}{ConsoleColors.RESET}")

        print(f"\n{ConsoleColors.GREEN}🎉 Total unliked: {total_unliked} posts{ConsoleColors.RESET}")
        input(f"\n{ConsoleColors.BOLD}Press Enter to continue...{ConsoleColors.RESET}")  # Added pause

    def show_settings(self):
        """Display and modify settings with enhanced UI"""
        while True:
            # Clear previous content
            print("\033c", end="")  # ANSI escape to clear screen

            # Header
            print(f"\n{ConsoleColors.CYAN}{ConsoleColors.BOLD}╔══════════════════════════════════╗")
            print(f"║          Settings Menu           ║")
            print(f"╚══════════════════════════════════╝{ConsoleColors.RESET}")

            # Delay Settings
            print(f"\n{ConsoleColors.YELLOW}▸ Delay Settings{ConsoleColors.RESET}")
            print(f"  {ConsoleColors.BOLD}1.{ConsoleColors.RESET} Minimum Delay     : {ConsoleColors.GREEN}{CONFIG['delay']['min']}{ConsoleColors.RESET} seconds")
            print(f"  {ConsoleColors.BOLD}2.{ConsoleColors.RESET} Maximum Delay     : {ConsoleColors.GREEN}{CONFIG['delay']['max']}{ConsoleColors.RESET} seconds")

            # Break Settings
            print(f"\n{ConsoleColors.YELLOW}▸ Break Settings{ConsoleColors.RESET}")
            print(f"  {ConsoleColors.BOLD}3.{ConsoleColors.RESET} Break Probability : {ConsoleColors.GREEN}{CONFIG['break']['probability'] * 100}%{ConsoleColors.RESET}")
            print(f"  {ConsoleColors.BOLD}4.{ConsoleColors.RESET} Minimum Break     : {ConsoleColors.GREEN}{CONFIG['break']['min'] / 60:.1f}{ConsoleColors.RESET} minutes")
            print(f"  {ConsoleColors.BOLD}5.{ConsoleColors.RESET} Maximum Break     : {ConsoleColors.GREEN}{CONFIG['break']['max'] / 60:.1f}{ConsoleColors.RESET} minutes")

            # Retry Settings
            print(f"\n{ConsoleColors.YELLOW}▸ Retry Settings{ConsoleColors.RESET}")
            print(f"  {ConsoleColors.BOLD}6.{ConsoleColors.RESET} Maximum Retries   : {ConsoleColors.GREEN}{CONFIG['max_retries']}{ConsoleColors.RESET}")
            print(f"  {ConsoleColors.BOLD}7.{ConsoleColors.RESET} Retry Delay       : {ConsoleColors.GREEN}{CONFIG['retry_delay']}{ConsoleColors.RESET} seconds")

            # Navigation
            print(f"\n{ConsoleColors.CYAN}▸ Navigation{ConsoleColors.RESET}")
            print(f"  {ConsoleColors.BOLD}0.{ConsoleColors.RESET} Save and Return")

            # Input
            try:
                print(f"\n{ConsoleColors.WHITE}╭─{ConsoleColors.RESET}")
                choice = input(f"{ConsoleColors.WHITE}╰─▸{ConsoleColors.RESET} ").strip()

                if choice == "0":
                    print(f"\n{ConsoleColors.GREEN}✓ Settings saved successfully!{ConsoleColors.RESET}")
                    time.sleep(1)
                    break

                # Process the choice and get new value
                try:
                    if choice in ["1", "2", "3", "4", "5", "6", "7"]:
                        print(f"{ConsoleColors.WHITE}╭─{ConsoleColors.RESET}")

                        if choice == "1":
                            prompt = "Enter new minimum delay (seconds)"
                            new_value = float(input(f"{ConsoleColors.WHITE}╰─▸ {prompt}: {ConsoleColors.RESET}"))
                            CONFIG['delay']['min'] = new_value

                        elif choice == "2":
                            prompt = "Enter new maximum delay (seconds)"
                            new_value = float(input(f"{ConsoleColors.WHITE}╰─▸ {prompt}: {ConsoleColors.RESET}"))
                            CONFIG['delay']['max'] = new_value

                        elif choice == "3":
                            prompt = "Enter new break probability (0-1)"
                            new_value = float(input(f"{ConsoleColors.WHITE}╰─▸ {prompt}: {ConsoleColors.RESET}"))
                            if 0 <= new_value <= 1:
                                CONFIG['break']['probability'] = new_value
                            else:
                                raise ValueError("Probability must be between 0 and 1")

                        elif choice == "4":
                            prompt = "Enter new minimum break time (minutes)"
                            new_value = float(input(f"{ConsoleColors.WHITE}╰─▸ {prompt}: {ConsoleColors.RESET}"))
                            CONFIG['break']['min'] = new_value * 60

                        elif choice == "5":
                            prompt = "Enter new maximum break time (minutes)"
                            new_value = float(input(f"{ConsoleColors.WHITE}╰─▸ {prompt}: {ConsoleColors.RESET}"))
                            CONFIG['break']['max'] = new_value * 60

                        elif choice == "6":
                            prompt = "Enter new maximum retries"
                            new_value = int(input(f"{ConsoleColors.WHITE}╰─▸ {prompt}: {ConsoleColors.RESET}"))
                            CONFIG['max_retries'] = new_value

                        elif choice == "7":
                            prompt = "Enter new retry delay (seconds)"
                            new_value = int(input(f"{ConsoleColors.WHITE}╰─▸ {prompt}: {ConsoleColors.RESET}"))
                            CONFIG['retry_delay'] = new_value

                        # Save after each change
                        self.save_config()
                        print(f"\n{ConsoleColors.GREEN}✓ Setting updated successfully!{ConsoleColors.RESET}")
                        time.sleep(1)

                    else:
                        print(f"\n{ConsoleColors.RED}✗ Invalid choice. Please try again.{ConsoleColors.RESET}")
                        time.sleep(1)

                except ValueError as e:
                    print(f"\n{ConsoleColors.RED}✗ Invalid input: {str(e)}{ConsoleColors.RESET}")
                    time.sleep(2)

            except KeyboardInterrupt:
                print(f"\n{ConsoleColors.YELLOW}⚠ Settings menu closed.{ConsoleColors.RESET}")
                break
            except Exception as e:
                print(f"\n{ConsoleColors.RED}✗ Error: {str(e)}{ConsoleColors.RESET}")
                time.sleep(2)

    def check_system_requirements(self) -> bool:
        """Check if system meets all requirements"""
        try:
            # First ensure psutil is installed
            try:
                import psutil
            except ImportError:
                logging.warning("psutil not installed. Installing...")
                if not self.install_requirements():
                    return False

            # Check operating system
            os_name = platform.system()
            logging.info(f"Operating System: {os_name}")

            # Check system architecture
            arch = platform.architecture()[0]
            logging.info(f"System Architecture: {arch}")

            # Check available memory
            if os_name == "Windows":
                memory = psutil.virtual_memory()
                available_mb = memory.available / (1024 * 1024)
                logging.info(f"Available Memory: {available_mb:.2f} MB")

                if available_mb < 500:  # Less than 500MB available
                    logging.warning("Low memory available. Performance may be affected.")
                    print(f"{ConsoleColors.YELLOW}[!] Warning: Low memory available. Performance may be affected.{ConsoleColors.RESET}")

            # Check disk space
            target_dir = Path.cwd()
            try:
                free_space = shutil.disk_usage(target_dir).free / (1024 * 1024)  # MB
                logging.info(f"Free Disk Space: {free_space:.2f} MB")

                if free_space < 100:  # Less than 100MB free
                    logging.warning("Low disk space available.")
                    print(f"{ConsoleColors.YELLOW}[!] Warning: Low disk space. Please free up some space.{ConsoleColors.RESET}")
            except PermissionError:
                logging.warning("Could not check disk space due to permissions")
                print(f"{ConsoleColors.YELLOW}[!] Warning: Could not check disk space due to permissions{ConsoleColors.RESET}")

            return True

        except Exception as e:
            logging.error(f"Error checking system requirements: {str(e)}")
            print(f"{ConsoleColors.RED}[✗] Error checking system requirements: {str(e)}{ConsoleColors.RESET}")
            return False

    def check_dependencies(self) -> bool:
        """Check and validate all required dependencies"""
        try:
            import importlib.util

            # Required libraries
            required_modules = ["ensta"]

            for mod in required_modules:
                spec = importlib.util.find_spec(mod.split('.')[0])
                if spec is None:
                    logging.error(f"{mod} not found. Attempting to install...")
                    if not self.install_requirements():
                        return False

            try:
                import ensta
                from moviepy.editor import VideoFileClip
                logging.info("Successfully imported ensta and moviepy")
                return True
            except Exception as e:
                logging.error(f"Import error: {str(e)}", exc_info=True)
                print(f"{ConsoleColors.RED}[✗] Import error: {str(e)}{ConsoleColors.RESET}")
                return False

        except Exception as e:
            logging.error(f"Dependency check failed: {str(e)}", exc_info=True)
            print(f"{ConsoleColors.RED}[✗] Dependency check failed: {str(e)}{ConsoleColors.RESET}")
            return False


def ensure_python_installed():
    """Check if Python is installed and install if needed"""
    try:
        # Check Python version
        version = sys.version_info
        if version.major >= 3 and version.minor >= 7:
            return True

        print("Python 3.7 or higher is required.")

        # For Windows
        if platform.system() == "Windows":
            print("Downloading Python installer...")
            # Download Python installer
            with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as f:
                url = "https://www.python.org/ftp/python/3.9.7/python-3.9.7-amd64.exe"
                urllib.request.urlretrieve(url, f.name)
                installer = f.name

            print("Installing Python...")
            # Install Python silently
            subprocess.run([installer, "/quiet", "InstallAllUsers=1", "PrependPath=1"])
            os.unlink(installer)
            print("Python installed successfully. Please restart the application.")
            sys.exit(0)

        # For Linux/Mac
        else:
            print("Please install Python 3.7 or higher:")
            if platform.system() == "Linux":
                print("Run: sudo apt-get install python3")
            else:  # Mac
                print("Visit: https://www.python.org/downloads/")
            sys.exit(1)

    except Exception as e:
        print(f"Error checking/installing Python: {str(e)}")
        sys.exit(1)

def instagram_code_to_media_id(code):
    """Convert Instagram shortcode to media ID"""
    charmap = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    code = code.split('/')[-2]
    return sum(charmap.index(char) * (64 ** i) for i, char in enumerate(reversed(code)))

def get_visible_length(text):
    """Calculate the visible length of text by removing ANSI color codes"""
    # Pattern to match ANSI escape sequences
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return len(ansi_escape.sub('', text))

def menu_line(number, text, box_width=40):
    """Create a properly aligned menu line with consistent formatting"""
    prefix = f"│ {ConsoleColors.BOLD}{number}.{ConsoleColors.RESET} {ConsoleColors.WHITE}"
    content = f"{text}{ConsoleColors.RESET}"

    # Calculate visible content length to determine proper padding
    visible_length = get_visible_length(f"{prefix}{content}")
    padding = box_width - visible_length + 1  # -2 for the box edges

    return f"{prefix}{content}{' ' * padding}│{ConsoleColors.RESET}"

def main():
    """Main entry point with improved initialization and dependency checking"""
    try:
        # Display welcome message
        print("\nWelcome to Instagram Mass Unliker!")
        print("Checking system requirements...")

        # Create instance and check dependencies first
        unliker = InstagramUnliker()
        if not unliker.check_dependencies():
            print("Error: Failed to install required dependencies.")
            print("Please try installing them manually:")
            print("pip install psutil tqdm colorama requests ensta moviepy")
            sys.exit(1)

        # Continue with other checks
        if not unliker.check_system_requirements():
            print("Error: System requirements not met.")
            print("Please check the logs for more information.")
            sys.exit(1)

        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))

        # Perform initial setup
        if not unliker.check_python_version():
            sys.exit(1)

        unliker.check_and_create_config()

        # Show interactive menu
        unliker.show_menu()

    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        print("\nAn unexpected error occurred. Please check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
