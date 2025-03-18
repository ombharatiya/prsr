#!/bin/bash

# Script to test the LLM PDF parser with a sample invoice

# Default LLM provider
LLM_PROVIDER="google"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--provider)
            LLM_PROVIDER="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -p, --provider PROVIDER  LLM provider to use (google or openai) [default: google]"
            echo "  -h, --help               Show this help message and exit"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# Validate LLM provider
if [[ "$LLM_PROVIDER" != "google" && "$LLM_PROVIDER" != "openai" ]]; then
    echo "Error: Invalid LLM provider: $LLM_PROVIDER"
    echo "Valid providers are: google, openai"
    exit 1
fi

echo "Using $LLM_PROVIDER as the LLM provider"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Ensure required directories exist
mkdir -p MyTest/input
mkdir -p MyTest/output

# Check if we have sample invoice in MyTest/input
SAMPLE_PDF="MyTest/input/Mensa_KA_BLR_830 (1).pdf"
if [ ! -f "$SAMPLE_PDF" ]; then
    echo "Sample invoice not found at $SAMPLE_PDF"
    echo "Please place a sample invoice at this location and try again."
    exit 1
fi

# Check if API key is set based on provider
if [ "$LLM_PROVIDER" == "google" ]; then
    if [ -z "$GOOGLE_API_KEY" ]; then
        echo "GOOGLE_API_KEY environment variable is not set."
        echo "Please set it with: export GOOGLE_API_KEY=your_api_key"
        echo ""
        echo "Running with fallback regex parser..."
    fi
elif [ "$LLM_PROVIDER" == "openai" ]; then
    if [ -z "$OPENAI_API_KEY" ]; then
        echo "OPENAI_API_KEY environment variable is not set."
        echo "Please set it with: export OPENAI_API_KEY=your_api_key"
        echo ""
        echo "Running with fallback regex parser..."
    fi
fi

# Run the LLM parser test with the specified provider
echo "Testing LLM PDF parser with sample invoice..."
python test_llm_parser.py --provider "$LLM_PROVIDER"

# Check if extraction was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "Test completed successfully!"
    echo "Results have been saved to:"
    echo "- MyTest/output/${LLM_PROVIDER}_invoice_level.csv"
    echo "- MyTest/output/${LLM_PROVIDER}_item_level.csv"
else
    echo ""
    echo "Test failed with errors."
fi

# Remind about API key if not set
if [ "$LLM_PROVIDER" == "google" ] && [ -z "$GOOGLE_API_KEY" ]; then
    echo ""
    echo "NOTE: For best results with Google Gemini, please set a valid API key:"
    echo "export GOOGLE_API_KEY=your_api_key"
elif [ "$LLM_PROVIDER" == "openai" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo ""
    echo "NOTE: For best results with OpenAI, please set a valid API key:"
    echo "export OPENAI_API_KEY=your_api_key"
fi 