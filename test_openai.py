#!/usr/bin/env python3
"""
Simple test script to verify OpenAI API integration.
This script tests the OpenAI API key and connection.
"""

import os
import sys
import argparse
import requests
import json

def test_openai_api():
    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key using:")
        print("export OPENAI_API_KEY=your_api_key  # Linux/macOS")
        print("set OPENAI_API_KEY=your_api_key     # Windows")
        return False

    # Test API connection
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, this is a test of the OpenAI API connection."}
        ],
        "max_tokens": 50
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            print("✅ OpenAI API connection successful!")
            print(f"Response: {response.json()['choices'][0]['message']['content']}")
            return True
        else:
            print(f"❌ OpenAI API connection failed with status code: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to OpenAI API: {str(e)}")
        return False

def main():
    print("Testing OpenAI API integration...")
    success = test_openai_api()
    if success:
        print("\nYour OpenAI API key is valid and working!")
        print("You can now use the LLM PDF Parser with the OpenAI provider.")
    else:
        print("\nFailed to connect to the OpenAI API.")
        print("Please check your API key and internet connection.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 