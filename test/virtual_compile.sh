#!/bin/bash
# virtual_compile.sh - Simple test script for RWL tool
# Randomly outputs compilation messages

set -e

# 编译过程中可能出现的消息数组
messages=(
    "Checking dependencies..."
    "Configuring build system..."
    "Generating build files..."
    "Compiling main.cpp..."
    "Compiling utils.cpp..."
    "Compiling parser.cpp..."
    "Compiling lexer.cpp..."
    "Compiling ast.cpp..."
    "Compiling symbol_table.cpp..."
    "Building object files..."
    "Linking objects..."
    "Creating executable..."
    "Optimizing binary..."
    "Running tests..."
    "Generating documentation..."
    "Installing headers..."
    "Cleaning up..."
    "Build complete!"
    "[WARNING] Unused variable 'temp' in file main.cpp:45"
    "[WARNING] Implicit conversion from 'int' to 'float' in utils.cpp:23"
    "[WARNING] Deprecated function 'old_function' used in parser.cpp:12"
    "[WARNING] Comparison between signed and unsigned integers in lexer.cpp:67"
    "[WARNING] Unused parameter 'arg' in function helper() in ast.cpp:89"
    "[ERROR] Undefined reference to 'some_function' in symbol_table.cpp:34"
    "[ERROR] Expected ';' before '}' token in main.cpp:56"
    "[ERROR] 'some_variable' was not declared in this scope in utils.cpp:78"
    "[ERROR] Too many arguments to function 'parse' in parser.cpp:91"
    "[ERROR] Division by zero detected in lexer.cpp:123"
    "Compilation FAILED: 3 errors, 2 warnings"
    "Compilation SUCCESS: Build completed with 0 errors, 0 warnings"
    "Generating debug symbols..."
    "Stripping debug symbols..."
    "Creating static library..."
    "Creating shared library..."
    "Running pre-build checks..."
    "Running post-build checks..."
    "Validating build output..."
    "Calculating code metrics..."
    "Checking code style..."
    "Running static analysis..."
    "[WARNING] Potential memory leak detected in utils.cpp:45"
    "[ERROR] Segmentation fault in test suite"
    "FAIL: Test case 'test_parser' failed"
    "PASS: Test case 'test_lexer' passed"
    "SKIP: Test case 'test_network' skipped"
    "TIMEOUT: Test case 'test_performance' timed out"
    "Building package..."
    "Creating distribution..."
    "Signing package..."
    "Uploading artifacts..."
)

# 获取随机消息
get_random_message() {
    local index=$((RANDOM % ${#messages[@]}))
    echo "${messages[$index]}"
}

# 获取随机延迟 (0.1 到 3.0 秒)
get_random_delay() {
    echo $(awk -v min=0.1 -v max=0.5 'BEGIN{srand(); print min+rand()*(max-min)}')
}

# 确定消息的输出流
get_output_stream() {
    local message="$1"
    
    if [[ "$message" == *"[ERROR]"* ]] || [[ "$message" == *"FAIL:"* ]] || [[ "$message" == *"FAILED"* ]] || [[ "$message" == *"[WARNING]"* ]]; then
        echo "stderr"
    else
        echo "stdout"
    fi
}

# 主函数
main() {
    local num_lines=0
    
    # 解析参数
    if [ $# -eq 0 ]; then
        echo "Usage: $0 <num_lines>"
        echo "Example: $0 100  # Output 100 random compilation messages"
        exit 1
    fi
    
    if [[ "$1" =~ ^[0-9]+$ ]]; then
        num_lines=$1
    else
        echo "Error: Please provide a number for the number of lines to output"
        exit 1
    fi
    
    echo "Starting virtual compiler with $num_lines random messages"
    echo "========================================"
    
    # 输出指定数量的随机消息
    for ((i=1; i<=num_lines; i++)); do
        # 获取随机消息
        local message
        message=$(get_random_message)
        
        # 获取消息的输出流
        local output_stream
        output_stream=$(get_output_stream "$message")
        
        # 输出消息
        if [ "$output_stream" = "stderr" ]; then
            echo "$message" >&2
        else
            echo "$message"
        fi
        
        # 如果不是最后一行，添加随机延迟
        if [ $i -lt $num_lines ]; then
            sleep $(get_random_delay)
        fi
    done
    
    echo "========================================"
    echo "Virtual compilation completed: $num_lines messages generated"
    
    # 随机决定退出码 (0 或 1)
    local exit_code=$((RANDOM % 2))
    
    if [ $exit_code -eq 0 ]; then
        echo "Exit code: 0 (Success)"
    else
        echo "Exit code: 1 (Failed)"
    fi
    
    return $exit_code
}

# 运行主函数
main "$@"
