import requests
import json
import os
import time
import re

# Chargement de la configuration depuis un fichier externe
from config import BASE_URL, MODEL_NAME, API_TIMEOUT

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

def analyze_and_fix_code(filename):
    with open(filename, "r", encoding="utf-8") as file:
        code = file.read()
    
    messages = [
        {"role": "system", "content": "You are an expert code debugging assistant. Analyze the provided code, "
                                          "identify errors, and provide a corrected version as a code snippet."},
        {"role": "user", "content": f"Analyze and fix this code, answer with the raw fixed code:\n```{code}```"}
    ]
    
    response = send_request(messages)
    if response:
        raw_output = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        fixed_code = extract_code(raw_output)
        return code, fixed_code
    else:
        return code, None

def validate_and_save(original_file, fixed_code):
    if not fixed_code:
        print("No fixes suggested.")
        return
    
    print("\nOriginal Code:")
    print(fixed_code)
    print("\nApply these changes? [y/N]: ", end="")
    choice = input().strip().lower()
    if choice != "y":
        print("Operation cancelled.")
        return
    
    backup_name = f"{original_file}.{time.strftime('%Y%m%d%H%M%S')}.bak"
    os.rename(original_file, backup_name)
    
    with open(original_file, "w", encoding="utf-8") as file:
        file.write(fixed_code)
    
    print(f"Backup saved to {backup_name}. Update successful!")

def main():
    if not check_server_available():
        print("LM Studio server not available. Ensure it's running at", BASE_URL)
        return
    
    if len(os.sys.argv) < 2:
        print("Usage: python codefixer.py <filename>")
        return
    
    filename = os.sys.argv[1]
    original_code, fixed_code = analyze_and_fix_code(filename)
    validate_and_save(filename, fixed_code)

if __name__ == "__main__":
    main()
