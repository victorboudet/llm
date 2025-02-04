import requests
import json
import os
import time
import re

# Chargement de la configuration depuis un fichier externe
from config import BASE_URL, MODEL_NAME, API_TIMEOUT
import difflib

def check_server_available():
    try:
        response = requests.get(f"{BASE_URL}/models", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def send_request(messages, tools=None):
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
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def extract_code(response_text):
    match = re.search(r'```(?:python|\w*)\n(.*?)```', response_text, re.DOTALL)
    return match.group(1) if match else response_text.strip()

def analyze_and_fix_code(filename, start_line=None, end_line=None, error=None, comments=None):
    with open(filename, "r", encoding="utf-8") as file:
        lines = file.readlines()
        full_code = ''.join(lines)
    
    file_extension = os.path.splitext(filename)[1].lstrip('.')
    
    if start_line is not None and end_line is not None:
        selected_lines = ''.join(lines[start_line-1:end_line])
        messages = [
            {"role": "system", "content": "You are an expert code debugging assistant. Analyze the provided code segment, with the following rules:"
                                        f"The code is in {file_extension}"
                                        "- identify errors and provide a corrected version as a code snippet."
                                        "- You must only send the corrected code in your response."
                                        "- Fix any errors in the code."
                                        "- Make improvements if necessary."
                                        "- Check for security vulnerabilities and fix them if there are any."
                                        "- You must have an optimised code"
                                        "- Keep the same number of lines as the input"
                                        "**- You DO NOT modify the context file**"
                                        },
            {"role": "user", "content": f"Fix only this code segment:\n```{file_extension}\n{selected_lines}\n```"
                                        f"Here the context file You DO NOT modify it:\n```{file_extension}\n{full_code}\n```"}
        ]
    elif error:
        messages = [
            {"role": "system", "content": "You are an expert code debugging assistant. Analyze the provided code, with the following rules:"
                                        f"The code is in {file_extension}"
                                        "- identify errors and provide a corrected version as a code snippet."
                                        "- You must only send the corrected code in your response."
                                        "- Fix any errors in the code."
                                        "- Make improvements if necessary."
                                        "- Check for security vulnerabilities and fix them if there are any."
                                        "- You must have an optimised code"},
            {"role": "user", "content": f"Here is the code with the error:\n```{file_extension}\n{full_code}\n```"
                                        f"The error is: {error}"}
        ]
    elif comments:
        messages = [
            {"role": "system", "content": "You are an expert code debugging assistant. Analyze the provided code, with the following rules:"
                                        f"The code is in {file_extension}"
                                        "- identify errors and provide a corrected version as a code snippet."
                                        "- You must only send the corrected code in your response."
                                        "- Fix any errors in the code."
                                        "- Make improvements if necessary."
                                        "- Check for security vulnerabilities and fix them if there are any."
                                        "- You must have an optimised code"
                                        "- You must add comments the code nicelly to understand it"},
            {"role": "user", "content": f"Here is the code answer with the raw fixed code:\n```{file_extension}\n{full_code}\n```"}
        ]
    else:
        messages = [
            {"role": "system", "content": "You are an expert code debugging assistant. Analyze the provided code, with the following rules:"
                                        f"The code is in {file_extension}"
                                        "- identify errors and provide a corrected version as a code snippet."
                                        "- You must only send the corrected code in your response without any comments."
                                        "- Fix any errors in the code."
                                        "- Make improvements if necessary."
                                        "- Check for security vulnerabilities and fix them if there are any."
                                        "- You must have an optimised code"},
            {"role": "user", "content": f"Here is the code with the error:\n```{file_extension}\n{full_code}\n```"}
        ]

    response = send_request(messages)
    if response:
        raw_output = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        fixed_code = extract_code(raw_output)
        
        if start_line is not None and end_line is not None:
            fixed_lines = fixed_code.splitlines(True)
            lines[start_line-1:end_line] = fixed_lines
            fixed_code = ''.join(lines)
            
        return full_code, fixed_code
    else:
        return full_code, None

def validate_and_save(original_file, original_code, fixed_code):
    if not fixed_code:
        print("No fixes suggested.")
        return

    diff = difflib.unified_diff(
        original_code.splitlines(), 
        fixed_code.splitlines(), 
        fromfile='original', 
        tofile='fixed', 
        lineterm=''
    )
    print("\nChanges suggested by the AI model:")
    for line in diff:
        print(line)
    
    print("\nApply these changes? [y/N]: ", end="")
    choice = input().strip().lower()
    if choice != "y":
        print("Operation cancelled.")
        return
    
    if not os.path.exists("_backup"):
        os.makedirs("_backup")
    backup_name = f"_backup/{original_file}.{time.strftime('%Y%m%d%H%M%S')}.bak"
    os.rename(original_file, backup_name)
    
    with open(original_file, "w", encoding="utf-8") as file:
        file.write(fixed_code)
    
    print(f"Backup saved to {backup_name}. Update successful!")

def main():
    if not check_server_available():
        print("LM Studio server not available. Ensure it's running at", BASE_URL)
        return
    
    import argparse
    parser = argparse.ArgumentParser(description='Fix code with AI assistance')
    parser.add_argument('filename', help='The file to analyze and fix')
    parser.add_argument('--start', type=int, help='Starting line number')
    parser.add_argument('--end', type=int, help='Ending line number')
    parser.add_argument('--error', help='The error you encounter')
    parser.add_argument('--comments', help='The comments you want to add')
    
    args = parser.parse_args()
    
    if (args.start is None) != (args.end is None):
        print("Error: Both --start and --end must be provided together")
        return
        
    if args.start is not None and args.end is not None:
        if args.start > args.end:
            print("Error: Start line must be less than or equal to end line")
            return
        if args.start < 1:
            print("Error: Start line must be greater than 0")
            return
            
    original_code, fixed_code = analyze_and_fix_code(args.filename, args.start, args.end, args.error, args.comments)
    validate_and_save(args.filename, original_code, fixed_code)


if __name__ == "__main__":
    main()
