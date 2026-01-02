# RWL (Run With Log) 🚀



 <div align="center">

<p align="center">
  <img src="https://img.shields.io/badge/python-3.6%2B-blue" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Status">
</p>


 ​专业的命令行输出捕获与日志记录工具​ | ​Professional command-line output capture and logging tool​



 </div>



 ---



 ## 📋 简介 | Overview



 ​RWL​ 是一个强大的命令行工具，专门为开发者和系统管理员设计，用于实时捕获、记录和分析命令行程序的输出。它提供美观的实时显示界面、智能关键词高亮、完整的日志记录和详细的运行时统计。



 ​RWL​ is a powerful command-line tool designed for developers and system administrators to capture, log, and analyze program output in real-time. It features beautiful real-time display, intelligent keyword highlighting, comprehensive logging, and detailed runtime statistics.



 ---



 ## ✨ 核心特性 | Core Features



 ### 🎯 实时输出显示 | Real-time Output Display

 - ​交互式面板​：在终端中原位刷新的输出面板

 - ​智能高亮​：可配置的关键词高亮（错误/警告/失败等）

 - ​滚动浏览​：支持在面板内滚动查看历史输出



 ### ⚡ 灵活的日志管理 | Flexible Log Management

 - ​多配置管理​：支持多个独立的日志配置

 - ​自动归档​：按日期/时间自动命名和存储日志文件

 - ​完整记录​：精确到毫秒的时间戳记录



 ### 📊 智能分析 | Intelligent Analysis

 - ​实时统计​：行数统计、关键词计数、运行时间

 - ​错误追踪​：自动标记和统计错误信息

 - ​性能监控​：实时显示程序执行状态



 ### 🔧 易于配置 | Easy Configuration

 - ​交互式配置​：直观的终端配置界面

 - ​即时生效​：配置更改无需重启程序

 - ​模板支持​：基于默认配置快速创建新配置

 ---



 ## 🚀 快速开始 | Quick Start


 ### 安装 | Installation

 ```bash

 # 克隆仓库 | Clone repository

 git clone https://github.com/yourusername/rwl.git

 cd rwl



 # 安装依赖 | Install dependencies

 pip install -r requirements.txt

 ```



 ### 基本使用 | Basic Usage

 ```bash

 # 运行命令并记录输出 | Run command with logging
 rwl make all

 # 编译程序并记录输出 | Compile with logging
 rwl gcc -o program main.c

 # 运行Python脚本并记录 | Run Python script with logging
 rwl python3 script.py

 ```



 ### 配置文件 | Configuration

 ```yaml

 # rwl.yaml
 current: "development"
 configs:
   default:
     name: "default"
     timestamp: true
     silent: false
     log_dir: "~/logs/"
     keywords:
       error: {color: "red", enabled: true}
       warning: {color: "yellow", enabled: true}
   development:
     name: "development"
     timestamp: true
     silent: false
     log_dir: "~/logs/dev/"
 ```



 ---



 ## 📖 详细功能 | Detailed Features



 ### 1. 基础运行 | Basic Operation

 ```bash

 # 基本语法 | Basic syntax
 rwl [command] [arguments...]



 # 示例 | Example
 rwl make clean all test

 ```



 ### 2. 配置管理 | Configuration Management

 ```bash

 # 交互式配置管理 | Interactive configuration
 rwl -c
 rwl --config



 # 配置输出面板大小 | Configure panel size
 rwl -s
 rwl --setting

 ```



 ### 3. 静默模式 | Silent Mode

 ```bash

 # 不显示输出，仅记录到文件
 # Run without display, only log to file
 rwl --silent npm install

 ```



 ### 4. 获取帮助 | Get Help

 ```bash

 # 显示帮助信息 | Show help
 rwl -h
 rwl --help



 # 显示版本 | Show version
 rwl -v
 rwl --version

 ```



 ---



 ## 🎨 界面预览 | UI Preview



 ```

 ╭─ Run Information ──────────────────────────────────────╮

 │ Configuration: development - Development environment   │

 │ Log: ~/logs/dev/, Timestamp: ✓, Silent: ✗             │

 │ Statistics: ● Running, Time: 12.34s, Lines: 1234       │

 │           Keywords: error: 2, warning: 5              │

 ╰────────────────────────────────────────────────────────╯

 ╭─ Program Output [100-120/500] ─────────────────────────╮

 │ [15:30:45] Compiling main.c...                        │

 │ [15:30:46] warning: unused variable 'temp'            │

 │ [15:30:47] error: expected ';' before '}' token       │

 │ [15:30:48] Building executable...                     │

 │ [15:30:49] Build successful!                          │

 ╰────────────────────────────────────────────────────────╯

 ```



 ---



 ## 🔧 高级配置 | Advanced Configuration



 ### 关键词高亮 | Keyword Highlighting

 ```yaml

 keywords:
   error: {color: "red", enabled: true}
   warning: {color: "yellow", enabled: true}
   fail: {color: "red", enabled: true}
   success: {color: "green", enabled: true}
   info: {color: "blue", enabled: true}

 ```



 ### 日志文件命名 | Log File Naming

 ```

 # 格式: 程序名日期时间.log

 # Format: programname_YYYYMMDD_HHMMSS.log
 make_20260103_143022.log
 gcc_20260103_143025.log

 ```



 ### 面板设置 | Panel Settings

 ```yaml

 settings:
   panel_height: 20  # 输出面板高度 | Output panel height

 ```



 ---



 ## 📁 项目结构 | Project Structure

 ```

 .

 ├── LICENSE              # 许可证文件
 ├── README.md           # 说明文档
 ├── bin/               # 可执行文件
 │   └── rwl            # 主程序入口
 ├── rwl.yaml           # 配置文件
 ├── src/               # 源代码
 │   └── run_with_log.py
 └── test/              # 测试文件
     └── virtual_compile.py

 ```



 ---






 ## 🎯 适用场景 | Use Cases



 ### 🏗️ 开发编译 | Development Compilation

 ```bash

 # 记录构建过程，捕获编译错误
 # Log build process, capture compilation errors
 rwl make -j4
 rwl cmake --build .

 ```



 ### 🧪 测试运行 | Test Execution

 ```bash

 # 捕获测试输出，分析失败原因
 # Capture test output, analyze failures
 rwl python -m pytest
 rwl go test -v ./...

 ```



 ### 📦 包管理 | Package Management

 ```bash

 # 记录依赖安装过程
 # Log dependency installation
 rwl npm install
 rwl pip install -r requirements.txt

 ```



 ### 🔍 调试分析 | Debugging Analysis

 ```bash
 # 长时间运行的进程监控
 # Monitor long-running processes
 rwl python data_processing.py
 rwl ./long_running_script.sh

 ```



 ---




 ## 📄 许可证 | License



 本项目采用 MIT 许可证 - 查看 LICENSE文件了解详情。

 This project is licensed under the MIT License - see the LICENSEfile for details.



 ---



 ## 📞 支持与反馈 | Support & Feedback



 如果您在使用过程中遇到问题或有改进建议：



 If you encounter issues or have suggestions for improvement:



 - 🐛 提交问题报告

 - 💡 提出功能请求

 - 📧 发送邮件至：AStor.Jiang@outlook.com



 ---



 ## 🌟 致谢 | Acknowledgments



 感谢以下开源项目的支持：



 Thanks to the following open-source projects:



 - ​​Rich​​ - 精美的终端格式化

 - ​​Inquirer​​ - 交互式命令行界面

 - ​​PyYAML​​ - YAML 配置解析



 ---



 <div align="center">



 ​让每一次命令行输出都有迹可循​

 ​Make every command-line output traceable​



 开始使用 →



 </div> Run-with-log
