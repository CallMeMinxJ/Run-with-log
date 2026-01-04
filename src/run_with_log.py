#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run with Log (RWL) - A tool to capture and log program output with real-time display
Author: Python Engineer
Version: 1.0.0
"""

import os
import sys
import time
import signal
import shlex
import yaml
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
from threading import Thread, Event
import queue
import re

# Third-party imports
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
    from rich.table import Table
    from rich.columns import Columns
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.syntax import Syntax
    from rich import box
    from rich.style import Style
    from rich.rule import Rule
    from rich.prompt import Prompt, Confirm
    from rich.console import Group
    from rich.align import Align
except ImportError as e:
    print(f"Error: rich library is required. Please install with: pip install rich==1.12.0")
    sys.exit(1)

try:
    import inquirer
    from inquirer.themes import Theme, load_theme_from_dict
except ImportError as e:
    print(f"Error: inquirer library is required. Please install with: pip install inquirer==2.8.0")
    sys.exit(1)


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


class LogLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FAIL = "fail"


@dataclass
class KeywordConfig:
    """Configuration for keyword highlighting"""
    color: str
    enabled: bool = True


@dataclass
class Config:
    """Configuration for a logging profile"""
    name: str
    timestamp: bool = True
    silent: bool = False
    log_dir: str = "~/logs/"
    description: str = ""
    keywords: Dict[str, KeywordConfig] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary for YAML serialization"""
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "silent": self.silent,
            "log_dir": self.log_dir,
            "description": self.description,
            "keywords": {k: asdict(v) for k, v in self.keywords.items()}
        }
    
    @classmethod
    def from_dict(cls, name: str, data: Dict) -> 'Config':
        """Create Config from dictionary"""
        keywords = {}
        for kw, kw_config in data.get("keywords", {}).items():
            keywords[kw] = KeywordConfig(**kw_config)
        
        return cls(
            name=name,
            timestamp=data.get("timestamp", True),
            silent=data.get("silent", False),
            log_dir=data.get("log_dir", "~/logs/"),
            description=data.get("description", ""),
            keywords=keywords
        )


@dataclass
class Statistics:
    """Runtime statistics"""
    start_time: float
    end_time: Optional[float] = None
    lines_processed: int = 0
    keyword_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors: List[str] = field(default_factory=list)
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def has_errors(self) -> bool:
        """Check if any errors were captured"""
        return any(count > 0 for kw, count in self.keyword_counts.items() 
                  if kw.lower() in ['error', 'fail'])


class OutputPanel:
    """Panel for displaying program output with live updates"""
    
    def __init__(self, height: int = 20, width: Optional[int] = None):
        self.height = height
        self.width = width
        self.lines = []
        self.max_lines = height - 2  # Account for borders
        self.scroll_offset = 0
        
    def add_line(self, line: str) -> None:
        """Add a line to the panel"""
        self.lines.append(line)
        if len(self.lines) > self.max_lines * 3:  # Keep some history
            self.lines = self.lines[-self.max_lines * 3:]
        
        # Auto-scroll to show latest
        if len(self.lines) > self.max_lines:
            self.scroll_offset = len(self.lines) - self.max_lines
    
    def scroll_up(self) -> None:
        """Scroll up in the panel"""
        if self.scroll_offset > 0:
            self.scroll_offset -= 1
    
    def scroll_down(self) -> None:
        """Scroll down in the panel"""
        if self.scroll_offset < len(self.lines) - self.max_lines:
            self.scroll_offset += 1
    
    def scroll_to_bottom(self) -> None:
        """Scroll to the bottom"""
        if len(self.lines) > self.max_lines:
            self.scroll_offset = len(self.lines) - self.max_lines
        else:
            self.scroll_offset = 0
    
    def scroll_to_top(self) -> None:
        """Scroll to the top"""
        self.scroll_offset = 0
    
    def render(self) -> Panel:
        """Render the panel as a Rich Panel"""
        # Get visible lines
        start = self.scroll_offset
        end = min(start + self.max_lines, len(self.lines))
        visible_lines = self.lines[start:end]
        
        # Create text with proper styling
        text = Text()
        for line in visible_lines:
            text.append(line + "\n")
        
        # Add scroll indicator
        if len(self.lines) > self.max_lines:
            total_lines = len(self.lines)
            percent = (self.scroll_offset / (total_lines - self.max_lines)) * 100
            scroll_info = f" [{self.scroll_offset+1}-{end}/{total_lines}]"
        else:
            scroll_info = f" [1-{len(self.lines)}/{len(self.lines)}]"
        
        return Panel(
            text,
            title=f"Program Output{scroll_info}",
            border_style="cyan",
            height=self.height
        )


class RWLTool:
    """Main RWL Tool class"""
    
    def __init__(self):
        self.console = Console()
        self.config_path = self._get_fixed_config_path()  # 使用固定路径
        self.configs: Dict[str, Config] = {}
        self.current_config_name: str = "default"
        self.current_config: Optional[Config] = None
        self.settings: Dict[str, Any] = {"panel_height": 20}  # Default panel height
        self.output_panel: Optional[OutputPanel] = None
        self.statistics: Optional[Statistics] = None
        self.running = False
        self.process: Optional[subprocess.Popen] = None
        self.output_queue = queue.Queue()
        self.stop_event = Event()
        self.log_path: Optional[Path] = None
        
        # Default keywords if not configured
        self.default_keywords = {
            "error": KeywordConfig(color="red"),
            "warning": KeywordConfig(color="yellow"),
            "fail": KeywordConfig(color="red")
        }
        
        # Load configuration and settings
        self._load_config()
        # Initialize output panel with saved height
        self.output_panel = OutputPanel(height=self.settings.get("panel_height", 20))
    
    def _get_script_directory(self) -> Path:
        """获取脚本或可执行文件所在目录"""
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            return Path(sys.executable).parent.resolve()
        else:
            # Python脚本
            return Path(__file__).parent.resolve()
    
    def _get_fixed_config_path(self) -> Path:
        script_dir = self._get_script_directory()
        
        parent_dir = script_dir.parent
        parent_config = parent_dir / "rwl.yaml"
        
        if parent_config.exists():
            self.console.print(f"[cyan]Found config in parent directory: {parent_config}[/cyan]")
            return parent_config
        
        same_dir_config = script_dir / "rwl.yaml"
        
        if same_dir_config.exists():
            self.console.print(f"[cyan]Found config in same directory: {same_dir_config}[/cyan]")
            return same_dir_config
        
        return same_dir_config
    
    def _create_default_config(self, config_path: Path) -> None:
        """Create default configuration file"""
        default_config = {
            "current": "default",
            "settings": {
                "panel_height": 20
            },
            "configs": {
                "default": {
                    "name": "default",
                    "timestamp": True,
                    "silent": False,
                    "log_dir": "~/logs/",
                    "description": "Default configuration with error highlighting",
                    "keywords": {
                        "error": {"color": "red", "enabled": True},
                        "warning": {"color": "yellow", "enabled": True},
                        "fail": {"color": "red", "enabled": True}
                    }
                }
            }
        }
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        self.console.print(f"[green]Created default configuration at: {config_path}[/green]")
    
    def _load_config(self) -> None:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                raise ValueError("Configuration file is empty")
            
            # Load settings
            self.settings = config_data.get("settings", {"panel_height": 20})
            
            # Load all configs
            self.configs.clear()
            for name, config_dict in config_data.get("configs", {}).items():
                self.configs[name] = Config.from_dict(name, config_dict)
            
            # Set current config
            self.current_config_name = config_data.get("current", "default")
            if self.current_config_name not in self.configs:
                self.current_config_name = "default"
            
            self.current_config = self.configs.get(self.current_config_name)
            
            # Ensure default config exists
            if "default" not in self.configs:
                self.configs["default"] = Config(
                    name="default",
                    timestamp=True,
                    silent=False,
                    log_dir="~/logs/",
                    description="Default configuration",
                    keywords=self.default_keywords
                )
                self._save_config()
            
        except FileNotFoundError:
            self.console.print(f"[yellow]Configuration file not found, creating default at: {self.config_path}[/yellow]")
            self._create_default_config(self.config_path)
            self._load_config()
        except Exception as e:
            self.console.print(f"[red]Error loading config: {e}[/red]")
            # Create default config
            self.settings = {"panel_height": 20}
            self.configs = {
                "default": Config(
                    name="default",
                    timestamp=True,
                    silent=False,
                    log_dir="~/logs/",
                    description="Default configuration",
                    keywords=self.default_keywords
                )
            }
            self.current_config = self.configs["default"]
            self.current_config_name = "default"
            self._save_config()
    
    def _save_config(self) -> None:
        """Save configuration to YAML file"""
        config_data = {
            "current": self.current_config_name,
            "settings": self.settings,
            "configs": {name: config.to_dict() for name, config in self.configs.items()}
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)
    
    def _expand_path(self, path: str) -> Path:
        """Expand user and environment variables in path"""
        expanded = os.path.expanduser(os.path.expandvars(path))
        return Path(expanded)
    
    def _get_log_file_path(self, program_name: str) -> Path:
        """Get the log file path for current config and program"""
        if not self.current_config:
            raise ValueError("No configuration loaded")
        
        log_dir = self._expand_path(self.current_config.log_dir)
        config_dir = log_dir / self.current_config.name
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{program_name}_{timestamp}.log"
        
        return config_dir / filename
    
    def _apply_keyword_highlighting_to_text(self, text: Text, line: str) -> Tuple[Text, Dict[str, int]]:
        """
        Apply keyword highlighting to a Rich Text object.
        Returns highlighted Text and keyword counts.
        """
        if not self.current_config:
            return text, {}
        
        keyword_counts = defaultdict(int)
        
        for keyword, kw_config in self.current_config.keywords.items():
            if not kw_config.enabled:
                continue
            
            # Case-insensitive search for keyword
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            matches = list(pattern.finditer(line))
            
            if matches:
                keyword_counts[keyword] += 1
                
                # Apply highlighting
                for match in matches:
                    start, end = match.span()
                    text.stylize(f"bold {kw_config.color}", start, end)
        
        return text, keyword_counts
    
    def _process_output_line(self, line: str, log_file) -> None:
        """Process a single line of output"""
        if not line:
            return
        
        # Remove ANSI color codes
        clean_line = strip_ansi_codes(line)
        
        # Add timestamp if enabled
        if self.current_config and self.current_config.timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S")
            displayed_line = f"[{timestamp}] {clean_line}"
            log_line = f"[{timestamp}] {clean_line}"
        else:
            displayed_line = clean_line
            log_line = clean_line
        
        # Create Text object and apply keyword highlighting
        text_line = Text(displayed_line)
        keyword_counts = {}
        
        if self.current_config:
            text_line, keyword_counts = self._apply_keyword_highlighting_to_text(text_line, displayed_line)
        
        # Update statistics
        if self.statistics:
            self.statistics.lines_processed += 1
            for keyword, count in keyword_counts.items():
                self.statistics.keyword_counts[keyword] += count
        
        # Write to log file (without color codes)
        if log_file:
            log_file.write(log_line + "\n")
            log_file.flush()
        
        # Add to output panel if not silent
        if not (self.current_config and self.current_config.silent):
            # Store the plain text for panel display
            self.output_panel.add_line(displayed_line)
            # Queue the highlighted version for display
            self.output_queue.put(("output", text_line))
    
    def _read_process_output(self, process, stdout, stderr, log_file) -> None:
        """Read output from process stdout and stderr"""
        import select
        
        while not self.stop_event.is_set() and process.poll() is None:
            # Use select to check if there's data to read
            readers, _, _ = select.select([stdout, stderr], [], [], 0.1)
            
            for reader in readers:
                if reader == stdout:
                    line = stdout.readline()
                    if line:
                        self._process_output_line(line.rstrip('\n'), log_file)
                elif reader == stderr:
                    line = stderr.readline()
                    if line:
                        self._process_output_line(line.rstrip('\n'), log_file)
        
        # Read any remaining output
        for line in iter(stdout.readline, ''):
            if line:
                self._process_output_line(line.rstrip('\n'), log_file)
        
        for line in iter(stderr.readline, ''):
            if line:
                self._process_output_line(line.rstrip('\n'), log_file)
    
    def _create_info_panel(self, is_final: bool = False) -> Panel:
        """Create information panel with config and stats"""
        if not self.current_config or not self.statistics:
            return Panel("", title="Run Information", border_style="blue")
        
        # Build info text
        info_lines = []
        
        # Configuration info
        config_line = f"Configuration: {self.current_config.name}"
        if self.current_config.description:
            config_line += f" - {self.current_config.description}"
        info_lines.append(config_line)
        
        # Settings
        settings = []
        settings.append(f"Log: {self.current_config.log_dir}")
        settings.append(f"Timestamp: {'✓' if self.current_config.timestamp else '✗'}")
        settings.append(f"Silent: {'✓' if self.current_config.silent else '✗'}")
        info_lines.append(", ".join(settings))
        
        # Statistics
        elapsed = self.statistics.elapsed_time
        status_text = "[green]✓ Completed[/green]" if is_final else "[yellow]● Running[/yellow]"
        stats_line = f"Statistics: {status_text}, Time: {elapsed:.2f}s, Lines: {self.statistics.lines_processed}"
        info_lines.append(stats_line)
        
        # Keyword counts
        keyword_strs = []
        for keyword, count in self.statistics.keyword_counts.items():
            if count > 0:
                color = self.current_config.keywords.get(keyword, KeywordConfig(color="white")).color
                keyword_strs.append(f"[{color}]{keyword}: {count}[/{color}]")
        
        if keyword_strs:
            keywords_line = "          Keywords: " + ", ".join(keyword_strs)
            info_lines.append(keywords_line)
        
        # Log file info for final display
        if is_final and self.log_path:
            info_lines.append("")
            info_lines.append(f"Log saved to: {self.log_path}")
        
        # Create panel
        panel_content = "\n".join(info_lines)
        
        if is_final:
            return Panel(panel_content, title="Final Statistics", border_style="green", padding=(0, 1))
        else:
            return Panel(panel_content, title="Run Information", border_style="blue", padding=(0, 1))
    
    def _create_highlighted_output_panel(self) -> Panel:
        """Create output panel with keyword highlighting applied"""
        if not self.output_panel:
            return Panel("", title="Program Output", border_style="cyan")
        
        # Get visible lines
        start = self.output_panel.scroll_offset
        end = min(start + self.output_panel.max_lines, len(self.output_panel.lines))
        visible_lines = self.output_panel.lines[start:end]
        
        # Create text with keyword highlighting
        text = Text()
        for i, line in enumerate(visible_lines):
            # Apply keyword highlighting to each line
            line_text = Text(line)
            if self.current_config:
                line_text, _ = self._apply_keyword_highlighting_to_text(line_text, line)
            text.append(line_text)
            if i < len(visible_lines) - 1:
                text.append("\n")
        
        # Add scroll indicator
        if len(self.output_panel.lines) > self.output_panel.max_lines:
            total_lines = len(self.output_panel.lines)
            scroll_info = f" [{start+1}-{end}/{total_lines}]"
        else:
            scroll_info = f" [1-{len(self.output_panel.lines)}/{len(self.output_panel.lines)}]"
        
        return Panel(
            text,
            title=f"Program Output{scroll_info}",
            border_style="cyan",
            height=self.output_panel.height
        )
    
    def _run_with_live_display(self, cmd: List[str], program_name: str) -> int:
        """Run command with live display"""
        # Clear screen and move to top
        self.console.clear()
        self.console.print("\n" * 2)  # Add some padding at top
        
        # Get log file path
        self.log_path = self._get_log_file_path(program_name)
        
        # Open log file
        log_file = open(self.log_path, 'w')
        
        # Start process
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Initialize statistics
        self.statistics = Statistics(start_time=time.time())
        self.running = True
        self.stop_event.clear()
        
        # Reset output panel for new run
        if self.output_panel:
            self.output_panel = OutputPanel(height=self.settings.get("panel_height", 20))
        
        # Start output reader thread
        reader_thread = Thread(
            target=self._read_process_output,
            args=(self.process, self.process.stdout, self.process.stderr, log_file),
            daemon=True
        )
        reader_thread.start()
        
        # Create layout for live display
        layout = Layout()
        layout.split_column(
            Layout(name="info", size=5),    # Info panel
            Layout(name="output", ratio=1)  # Output panel
        )
        
        # Main display loop
        with Live(layout, console=self.console, refresh_per_second=10, screen=True) as live:
            try:
                while self.process.poll() is None and not self.stop_event.is_set():
                    # Update info panel
                    layout["info"].update(self._create_info_panel(is_final=False))
                    
                    # Update output panel with keyword highlighting
                    layout["output"].update(self._create_highlighted_output_panel())
                    
                    # Check for new output
                    try:
                        while True:
                            msg_type, content = self.output_queue.get_nowait()
                            if msg_type == "output":
                                # Output is already added to panel, just refresh
                                pass
                    except queue.Empty:
                        pass
                    
                    time.sleep(0.1)
                
                # Process any remaining output
                reader_thread.join(timeout=1)
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted by user, terminating process...[/yellow]")
                if self.process and self.process.poll() is None:
                    self.process.terminate()
                    self.process.wait(timeout=5)
        
        # Cleanup
        self.running = False
        self.stop_event.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
        
        if self.statistics:
            self.statistics.end_time = time.time()
        
        # Close log file
        log_file.close()
        
        # Now display final summary
        self._display_final_output()
        
        return self.process.returncode if self.process else 1
    
    def _display_final_output(self) -> None:
        """Display final output with summary"""
        if not self.log_path or not self.output_panel:
            return
        
        # Create final layout
        layout = Layout()
        layout.split_column(
            Layout(name="info", size=6),    # Final info panel
            Layout(name="output", ratio=1)  # Output panel
        )
        
        # Display final info
        layout["info"].update(self._create_info_panel(is_final=True))
        
        # Display final output panel with keyword highlighting
        layout["output"].update(self._create_highlighted_output_panel())
        
        # Display the final screen
        self.console.clear()
        self.console.print("\n" * 2)  # Add some padding at top
        self.console.print(layout)
        
        # Wait for user to press Enter
        self.console.print("\n[dim]Press Enter to exit...[/dim]", end="")
        input()
    
    def _run_silent(self, cmd: List[str], program_name: str) -> int:
        """Run command silently (no display)"""
        # Get log file path
        self.log_path = self._get_log_file_path(program_name)
        
        # Open log file
        with open(self.log_path, 'w') as log_file:
            # Start process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Initialize statistics
            self.statistics = Statistics(start_time=time.time())
            
            # Read output
            while True:
                stdout_line = self.process.stdout.readline()
                stderr_line = self.process.stderr.readline()
                
                if not stdout_line and not stderr_line and self.process.poll() is not None:
                    break
                
                if stdout_line:
                    self._process_output_line(stdout_line.rstrip('\n'), log_file)
                
                if stderr_line:
                    self._process_output_line(stderr_line.rstrip('\n'), log_file)
            
            # Update statistics
            self.statistics.end_time = time.time()
        
        # Display summary
        self.console.print(f"\n[green]✓ Process completed silently[/green]")
        self.console.print(f"[cyan]Log saved to: {self.log_path}[/cyan]")
        self.console.print(f"[cyan]Total time: {self.statistics.elapsed_time:.2f}s[/cyan]")
        self.console.print(f"[cyan]Total lines: {self.statistics.lines_processed}[/cyan]")
        
        if self.statistics.keyword_counts:
            self.console.print("[yellow]Keyword counts:[/yellow]")
            for keyword, count in self.statistics.keyword_counts.items():
                color = self.current_config.keywords.get(keyword, KeywordConfig(color="white")).color
                self.console.print(f"  {keyword}: [{color}]{count}[/{color}]")
        
        return self.process.returncode
    
    def run(self, cmd: List[str]) -> int:
        """Run a command with logging"""
        if not cmd:
            self.console.print("[red]Error: No command specified[/red]")
            return 1
        
        program_name = Path(cmd[0]).stem
        
        if self.current_config and self.current_config.silent:
            return self._run_silent(cmd, program_name)
        else:
            return self._run_with_live_display(cmd, program_name)
    
    def config_interactive(self) -> None:
        """Interactive configuration management"""
        # Clear screen
        self.console.clear()
        
        # Create custom theme using dictionary (fix for inquirer 2.8.0)
        custom_theme = load_theme_from_dict({
            'Question': {
                'mark_color': 'cyan',
                'brackets_color': 'cyan',
                'default_color': 'white',
            },
            'List': {
                'selection_color': 'cyan',
                'selection_cursor': '➤',
            }
        })
        
        while True:
            questions = [
                inquirer.List(
                    'action',
                    message="Configuration Management",
                    choices=[
                        'Select Configuration',
                        'Create New Configuration',
                        'Edit Configuration',
                        'Delete Configuration',
                        'View Current Configuration',
                        'Back to Main Menu'
                    ],
                    carousel=True
                )
            ]
            
            try:
                answers = inquirer.prompt(questions, theme=custom_theme)
                if not answers:
                    break
                
                action = answers['action']
                
                if action == 'Back to Main Menu':
                    break
                
                elif action == 'Select Configuration':
                    self._select_configuration()
                
                elif action == 'Create New Configuration':
                    self._create_configuration()
                
                elif action == 'Edit Configuration':
                    self._edit_configuration()
                
                elif action == 'Delete Configuration':
                    self._delete_configuration()
                
                elif action == 'View Current Configuration':
                    self._view_configuration()
            
            except KeyboardInterrupt:
                break
        
        # Save configuration
        self._save_config()
    
    def _select_configuration(self) -> None:
        """Select a configuration to use"""
        config_names = list(self.configs.keys())
        
        questions = [
            inquirer.List(
                'config',
                message="Select configuration to use",
                choices=config_names
            )
        ]
        
        try:
            answers = inquirer.prompt(questions)
            if answers:
                self.current_config_name = answers['config']
                self.current_config = self.configs[self.current_config_name]
                self.console.print(f"[green]✓ Switched to configuration: {self.current_config_name}[/green]")
        except KeyboardInterrupt:
            pass
    
    def _create_configuration(self) -> None:
        """Create a new configuration"""
        questions = [
            inquirer.Text('name', message="Configuration name"),
            inquirer.Confirm('timestamp', message="Enable timestamps?", default=True),
            inquirer.Confirm('silent', message="Silent mode?", default=False),
            inquirer.Text('log_dir', message="Log directory", default="~/logs/"),
            inquirer.Text('description', message="Description", default="")
        ]
        
        try:
            answers = inquirer.prompt(questions)
            if not answers:
                return
            
            # Create new config based on default
            new_config = Config.from_dict("default", self.configs["default"].to_dict())
            new_config.name = answers['name']
            new_config.timestamp = answers['timestamp']
            new_config.silent = answers['silent']
            new_config.log_dir = answers['log_dir']
            new_config.description = answers['description']
            
            # Add to configs
            self.configs[new_config.name] = new_config
            self.console.print(f"[green]✓ Created configuration: {new_config.name}[/green]")
            
            # Ask to switch to new config
            if Confirm.ask("Switch to this configuration?"):
                self.current_config_name = new_config.name
                self.current_config = new_config
        
        except KeyboardInterrupt:
            pass
    
    def _edit_configuration(self) -> None:
        """Edit a configuration using text editor"""
        config_names = list(self.configs.keys())
        
        questions = [
            inquirer.List(
                'config',
                message="Select configuration to edit",
                choices=config_names
            )
        ]
        
        try:
            answers = inquirer.prompt(questions)
            if not answers:
                return
            
            config_name = answers['config']
            
            # Try to open editor
            editors = ['nvim', 'vim', 'vi', 'nano', 'code', 'subl']
            editor = None
            
            for e in editors:
                if self._which(e):
                    editor = e
                    break
            
            if not editor:
                self.console.print("[red]Error: No suitable editor found[/red]")
                return
            
            # Create temporary file with config
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                config_dict = self.configs[config_name].to_dict()
                yaml.dump(config_dict, f, default_flow_style=False)
                temp_path = f.name
            
            # Open editor
            subprocess.run([editor, temp_path])
            
            # Read back changes
            with open(temp_path, 'r') as f:
                new_config_dict = yaml.safe_load(f)
            
            # Update config
            self.configs[config_name] = Config.from_dict(config_name, new_config_dict)
            
            # Cleanup
            os.unlink(temp_path)
            
            self.console.print(f"[green]✓ Updated configuration: {config_name}[/green]")
            
            # Update current if this is the current config
            if config_name == self.current_config_name:
                self.current_config = self.configs[config_name]
        
        except Exception as e:
            self.console.print(f"[red]Error editing configuration: {e}[/red]")
    
    def _delete_configuration(self) -> None:
        """Delete a configuration"""
        config_names = [c for c in self.configs.keys() if c != "default"]
        
        if not config_names:
            self.console.print("[yellow]No configurations to delete (default cannot be deleted)[/yellow]")
            return
        
        questions = [
            inquirer.List(
                'config',
                message="Select configuration to delete",
                choices=config_names
            ),
            inquirer.Confirm('confirm', message="Are you sure?", default=False)
        ]
        
        try:
            answers = inquirer.prompt(questions)
            if not answers or not answers['confirm']:
                return
            
            config_name = answers['config']
            del self.configs[config_name]
            
            # If we deleted the current config, switch to default
            if config_name == self.current_config_name:
                self.current_config_name = "default"
                self.current_config = self.configs["default"]
            
            self.console.print(f"[green]✓ Deleted configuration: {config_name}[/green]")
        
        except KeyboardInterrupt:
            pass
    
    def _view_configuration(self) -> None:
        """View current configuration details"""
        if not self.current_config:
            self.console.print("[red]No configuration loaded[/red]")
            return
        
        self.console.print("\n[bold cyan]Current Configuration:[/bold cyan]")
        self.console.print(f"  Name: {self.current_config.name}")
        self.console.print(f"  Description: {self.current_config.description}")
        self.console.print(f"  Log Directory: {self.current_config.log_dir}")
        self.console.print(f"  Timestamp: {'Enabled' if self.current_config.timestamp else 'Disabled'}")
        self.console.print(f"  Silent Mode: {'Enabled' if self.current_config.silent else 'Disabled'}")
        
        if self.current_config.keywords:
            self.console.print("\n  [bold]Keyword Highlighting:[/bold]")
            for keyword, config in self.current_config.keywords.items():
                status = "✓" if config.enabled else "✗"
                self.console.print(f"    {keyword}: [{config.color}]{config.color}[/{config.color}] {status}")
        
        self.console.print()
    
    def _which(self, program: str) -> Optional[str]:
        """Find executable in PATH"""
        for path in os.environ.get("PATH", "").split(os.pathsep):
            exe_path = Path(path) / program
            if exe_path.exists() and os.access(exe_path, os.X_OK):
                return str(exe_path)
        return None
    
    def setting_interactive(self) -> None:
        """Interactive panel settings"""
        self.console.clear()
        
        current_height = self.settings.get("panel_height", 20)
        
        questions = [
            inquirer.Text(
                'height',
                message=f"Output panel height (current: {current_height})",
                default=str(current_height),
                validate=lambda _, x: x.isdigit() and 5 <= int(x) <= 50
            )
        ]
        
        try:
            answers = inquirer.prompt(questions)
            if answers:
                new_height = int(answers['height'])
                # Update settings
                self.settings["panel_height"] = new_height
                # Update output panel height
                if self.output_panel:
                    self.output_panel.height = new_height
                # Save configuration
                self._save_config()
                self.console.print(f"[green]✓ Set panel height to {new_height}[/green]")
        except KeyboardInterrupt:
            pass
    
    def show_help(self) -> None:
        """Show help information"""
        help_text = """
[bold cyan]RWL - Run With Log[/bold cyan]
A tool to capture and log program output with real-time display

[bold]Usage:[/bold]
  rwl [options] <command> [args...]
  python run_with_log.py [options] <command> [args...]

[bold]Options:[/bold]
  -h, --help        Show this help message
  --config          Interactive configuration management
  --setting         Configure output panel settings

[bold]Examples:[/bold]
  rwl make all              # Run command with logging
  rwl --config              # Open configuration manager
  rwl --setting             # Configure panel settings
  rwl gcc -o test test.c    # Compile with logging

[bold]Features:[/bold]
  • Real-time output capture and display
  • Configurable logging profiles
  • Keyword highlighting (errors, warnings, etc.)
  • Statistics and metrics
  • Silent mode for background operations
  • Interactive configuration management
  • Final summary display with all statistics

[bold]Configuration:[/bold]
  Configuration is stored in rwl.yaml in the same directory as the tool.
  Multiple profiles can be created and switched between.

[bold]Keyboard Controls:[/bold]
  • Ctrl+C to interrupt the running process
  • Output panel auto-scrolls to show latest output
  • After process completion, press Enter to exit
        """
        
        self.console.print(Panel(help_text, title="Help", border_style="cyan"))

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run With Log - Capture and log program output",
        add_help=False
    )
    
    parser.add_argument(
        '--config',
        action='store_true',
        help='Interactive configuration management'
    )
    
    parser.add_argument(
        '--setting',
        action='store_true',
        help='Configure output panel settings'
    )
    
    parser.add_argument(
        '-h', '--help',
        action='store_true',
        help='Show help information'
    )
    
    
    # Parse known args first, leave command for rwl
    args, remaining = parser.parse_known_args()
    
    # Create tool instance
    tool = RWLTool()
    
    # Handle options
    if args.help:
        tool.show_help()
        return 0
    
    if args.config:
        tool.config_interactive()
        return 0
    
    if args.setting:
        tool.setting_interactive()
        return 0
    
    # If no command provided, show help
    if not remaining:
        tool.show_help()
        return 0
    
    # Run command
    try:
        return tool.run(remaining)
    except KeyboardInterrupt:
        tool.console.print("\n[yellow]Interrupted by user[/yellow]")
        return 130
    except Exception as e:
        tool.console.print(f"[red]Error: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
