# PDF Invoice Parser with LLM

A powerful PDF invoice parser that uses Large Language Models (LLM) to extract structured data from PDF invoices. The parser is designed to handle various invoice formats and can extract key information like invoice numbers, dates, supplier/buyer details, and line items. It supports both Google Gemini and OpenAI APIs.

## Features

- Extract text from PDF invoices using PyPDF2, with fallback to OCR (pytesseract) for scanned documents
- Process the extracted text with either Google's Gemini API or OpenAI API to extract structured data
- Fallback to regex-based extraction when the LLM API is unavailable
- Extract invoice-level data (invoice number, date, supplier, buyer, totals, etc.)
- Extract line-item data (item codes, descriptions, quantities, prices, etc.)
- Output data to CSV files
- FastAPI web interface for uploading invoices and downloading the extracted data
- Bulk processing capabilities for multiple invoices

## Requirements

- Python 3.7+
- PyPDF2
- FastAPI
- Google Gemini API key and/or OpenAI API key
- Various dependencies (see requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pdf-invoice-parser.git
cd pdf-invoice-parser
```

2. Create a virtual environment and install dependencies:
```bash
# On Linux/macOS
./setup.sh

# On Windows
setup.bat
```

Or manually:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

## Configuration

To use the LLM features, you'll need an API key for either Google Gemini or OpenAI:

### Google Gemini

1. Get a Google API key from https://makersuite.google.com/
2. Set it as an environment variable:
```bash
export GOOGLE_API_KEY=your_api_key  # Linux/macOS
set GOOGLE_API_KEY=your_api_key     # Windows
```

### OpenAI

1. Get an OpenAI API key from https://platform.openai.com/
2. Set it as an environment variable:
```bash
export OPENAI_API_KEY=your_api_key  # Linux/macOS
set OPENAI_API_KEY=your_api_key     # Windows
```

Alternatively, you can provide the API key directly in the web interface or pass it as a parameter to the API endpoints.

## Usage

### Running the Web Interface

Start the FastAPI server:
```bash
# On Linux/macOS
./run.sh

# On Windows
run.bat
```

Or manually:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then open your browser and go to http://localhost:8000/

In the web interface, you can select which LLM provider to use (Google Gemini or OpenAI) and provide the corresponding API key.

### Using the API

The API has the following endpoints:

- `POST /upload-invoice/`: Upload a single invoice for processing
- `POST /bulk-upload/`: Upload multiple invoices for batch processing
- `GET /download/{filename}`: Download a generated CSV file
- `DELETE /cleanup/{filename}`: Delete a generated CSV file
- `POST /set-api-key/`: Set the LLM provider and API key
- `GET /job-status/{job_id}`: Check the status of a bulk processing job

You can provide the API key in one of three ways:
1. As an `X-API-Key` header
2. As an `api_key` query parameter
3. As an environment variable (`GOOGLE_API_KEY` or `OPENAI_API_KEY`)

You can also specify the LLM provider using the `provider` query parameter (values: `google` or `openai`).

### Command Line Usage

You can also use the parser from the command line:

```bash
# Using Google Gemini API
python test_llm_parser.py --provider google

# Using OpenAI API
python test_llm_parser.py --provider openai
```

Or using the provided shell/batch scripts:

```bash
# Using Google Gemini API (default)
./test_llm.sh

# Using OpenAI API
./test_llm.sh --provider openai
```

This will parse a sample invoice located at `MyTest/input/Mensa_KA_BLR_830 (1).pdf` and save the extracted data to CSV files based on the provider used.

## How It Works

1. **Text Extraction**: The parser first extracts text from the PDF using PyPDF2. If the text extraction is insufficient (e.g., for scanned documents), it falls back to OCR using pytesseract.

2. **LLM Processing**: The extracted text is sent to the selected LLM API (Google Gemini or OpenAI) with a specially crafted prompt that asks the LLM to extract structured data from the invoice text.

3. **Fallback Mechanism**: If the LLM API is unavailable or returns an error, the parser falls back to regex-based extraction to extract key information from the invoice.

4. **Data Normalization**: The extracted data is normalized and structured into a standard format.

5. **CSV Output**: The structured data is saved to CSV files for invoice-level and item-level data.

## LLM Provider Comparison

This project supports two LLM providers:

1. **Google Gemini**: Google's newer AI model, with strong capabilities in structured data extraction
2. **OpenAI**: Uses GPT-4 (or GPT-3.5-turbo for a cheaper alternative) for high-quality extraction

The choice between providers depends on:
- API key availability
- Cost considerations (OpenAI's GPT-4 is typically more expensive)
- Extraction quality needed (both perform well, but results may vary by invoice type)

The parser also includes a fallback regex-based extraction mechanism when the LLM API is unavailable or fails.

## Supported Invoice Fields

### Invoice-Level Data
- Document Type
- Invoice Number
- Invoice Date
- Supplier Name
- Supplier GSTIN
- Supplier Address
- Buyer Name
- Buyer GSTIN
- Buyer Address
- Total Invoice Value
- And many more...

### Line-Item Data
- Item/SKU Code
- Item Description
- HSN Code
- Quantity
- Unit of Measurement
- Unit Price
- Tax Rate
- Line Total Value
- And more...

## License

MIT License

## Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/)
- [doctr](https://github.com/mindee/doctr) for OCR
- [pytesseract](https://github.com/madmaze/pytesseract) for Tesseract OCR integration 