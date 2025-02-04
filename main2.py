import argparse
import difflib
import logging
import os
import re
import time
import requests
from config import BASE_URL, MODEL_NAME, API_TIMEOUT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_server_available():
    """Check if the LM server is available."""
    try:
        response = requests.get(f"{BASE_URL}/models", timeout=5)
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error(f"Server check failed: {e}")
        return False

def send_request(messages, tools=None):
    """
    Send a request to the LM server with the provided messages.
    
    :param messages: List of message dictionaries for the conversation.
    :param tools: Optional extra tools configuration.
    :return: Parsed JSON response or None if there was an error.
    """
    url = f"{BASE_URL}/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": -1,
        "stream": False
    }
    if tools:
        data["tools"] = tools
    try:
        response = requests.post(url, headers=headers, json=data, timeout=API_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error sending request: {e}")
        return None

def extract_code(response_text):
    """
    Extract code from a text string delimited by triple backticks.
    
    :param response_text: The raw text from the LM response.
    :return: The extracted code or the entire text if no code block is found.
    """
    match = re.search(r'```(?:python|\w+)?\n(.*?)```', response_text, re.DOTALL)
    return match.group(1) if match else response_text.strip()

def analyze_and_fix_code(filename, start_line=None, end_line=None):
    """
    Analyze and fix code using the LM server.
    
    If start_line and end_line are provided, only that segment is fixed while the rest of
    the file is passed for context. Otherwise, the entire file is fixed.
    
    :param filename: The path to the file.
    :param start_line: The starting line number of the segment to fix.
    :param end_line: The ending line number of the segment to fix.
    :return: Tuple of (original_code, fixed_code)
    """
    try:
        with open(filename, "r", encoding="utf-8") as file:
            lines = file.readlines()
    except Exception as e:
        logger.error(f"Failed to read file {filename}: {e}")
        return None, None

    full_code = ''.join(lines)
    file_extension = os.path.splitext(filename)[1].lstrip('.') or "txt"
    
    if start_line is not None and end_line is not None:
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            logger.error("Invalid start_line or end_line values.")
            return full_code, None
        selected_lines = ''.join(lines[start_line - 1:end_line])
        system_content = (
            f"You are an expert code debugging assistant. The code is in {file_extension}.\n"
            "Analyze the provided code segment and identify errors, vulnerabilities, and "
            "opportunities for optimization. Return only the corrected code snippet without any extra commentary.\n"
            "Ensure that the corrected segment has the same number of lines as the input segment.\n"
            "Only modify the given segment; the rest of the file is provided for context.\n"
        )
        user_content = (
            f"Fix only this code segment:\n"
            f"```{file_extension}\n{selected_lines}\n```\n"
            f"Here is the entire file content for context (do not modify code outside the segment):\n"
            f"```{file_extension}\n{full_code}\n```"
        )
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
    else:
        system_content = (
            f"You are an expert code debugging assistant. The code is in {file_extension}.\n"
            "Analyze the provided code, fix any errors or vulnerabilities, and optimize it. "
            "Return only the corrected code snippet without any additional commentary.\n"
        )
        user_content = f"Fix the following code:\n```{file_extension}\n{full_code}\n```"
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
    
    response = send_request(messages)
    if response:
        raw_output = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        fixed_code_segment = extract_code(raw_output)
        
        if start_line is not None and end_line is not None:
            fixed_segment_lines = fixed_code_segment.splitlines(keepends=True)
            # Warn if the corrected segment's line count is different
            if len(fixed_segment_lines) != (end_line - start_line + 1):
                logger.warning("The corrected segment does not have the same number of lines as the original segment.")
            # Replace only the selected segment
            lines[start_line - 1:end_line] = fixed_segment_lines
            fixed_code = ''.join(lines)
        else:
            fixed_code = fixed_code_segment
        
        return full_code, fixed_code
    else:
        return full_code, None

def validate_and_save(original_file, original_code, fixed_code):
    """
    Show the diff between the original and fixed code, prompt the user for confirmation,
    back up the original file, and write the fixed code.
    
    :param original_file: The file path.
    :param original_code: The original code as a string.
    :param fixed_code: The fixed code as a string.
    """
    if not fixed_code:
        logger.error("No fixes were suggested.")
        return

    diff = difflib.unified_diff(
        original_code.splitlines(),
        fixed_code.splitlines(),
        fromfile='original',
        tofile='fixed',
        lineterm=''
    )
    diff_lines = list(diff)
    print("\nChanges suggested by the AI model:")
    if not diff_lines:
        print("No changes detected.")
        return
    for line in diff_lines:
        print(line)
    
    choice = input("\nApply these changes? [y/N]: ").strip().lower()
    if choice != "y":
        print("Operation cancelled.")
        return

    backup_dir = "_backup"
    os.makedirs(backup_dir, exist_ok=True)
    backup_name = os.path.join(backup_dir, f"{os.path.basename(original_file)}.{time.strftime('%Y%m%d%H%M%S')}.bak")
    try:
        os.rename(original_file, backup_name)
        with open(original_file, "w", encoding="utf-8") as file:
            file.write(fixed_code)
        print(f"Backup saved to {backup_name}. Update successful!")
    except Exception as e:
        logger.error(f"Failed to save changes: {e}")

def main():
    parser = argparse.ArgumentParser(description='Fix code with AI assistance')
    parser.add_argument('filename', help='The file to analyze and fix')
    parser.add_argument('--start', type=int, help='Starting line number of the segment to fix')
    parser.add_argument('--end', type=int, help='Ending line number of the segment to fix')
    args = parser.parse_args()

    if (args.start is None) != (args.end is None):
        logger.error("Both --start and --end must be provided together.")
        return

    if not check_server_available():
        logger.error("LM server not available. Ensure it is running at %s", BASE_URL)
        return

    if args.start is not None and args.end is not None:
        if args.start > args.end:
            logger.error("Start line must be less than or equal to end line.")
            return
        if args.start < 1:
            logger.error("Start line must be greater than 0.")
            return
        original_code, fixed_code = analyze_and_fix_code(args.filename, args.start, args.end)
    else:
        original_code, fixed_code = analyze_and_fix_code(args.filename)
    
    if original_code is None:
        return
    validate_and_save(args.filename, original_code, fixed_code)

if __name__ == "__main__":
    main()
