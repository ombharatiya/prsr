import os
import uuid
import shutil
from typing import List, Optional, Literal
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Header, Depends, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add try-except blocks for imports that might fail
try:
    import pandas as pd
except ImportError:
    raise ImportError("Failed to import pandas. Please run './fix_dependencies.sh' (or fix_dependencies.bat on Windows) to fix dependency issues.")

try:
    # Use the new LLM parser
    from llm_pdf_parser import LLMPDFParser
except ImportError:
    raise ImportError("Failed to import llm_pdf_parser. Please check if all dependencies are installed correctly.")

try:
    from utils import ensure_directories, save_to_csv, save_items_to_csv
except ImportError:
    raise ImportError("Failed to import utils. Please check if the file exists.")

try:
    from models import ParsingResponse
except ImportError:
    raise ImportError("Failed to import models. Please check if the file exists.")

# LLM API key model
class LLMAPIKey(BaseModel):
    provider: Literal["google", "openai"] = "google"
    api_key: str

app = FastAPI(
    title="PDF Invoice Parser with LLM",
    description="API for parsing invoice PDFs and extracting structured data using LLM (Google Gemini or OpenAI)",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
ensure_directories()
os.makedirs("static", exist_ok=True)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Helper to get API key based on provider
async def get_api_key(
    provider: str = Query("google", description="LLM provider to use (google or openai)"),
    x_api_key: str = Header(None, description="API key for the selected LLM provider"),
    api_key: str = Query(None, description="API key for the selected LLM provider")
):
    """Get the API key based on the provider and user input."""
    if provider not in ["google", "openai"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid LLM provider. Supported providers are 'google' and 'openai'."
        )
        
    # First try header
    if x_api_key:
        return {"provider": provider, "api_key": x_api_key}
    
    # Then try query param
    if api_key:
        return {"provider": provider, "api_key": api_key}
    
    # Then try environment var
    if provider == "google":
        env_key = os.environ.get("GOOGLE_API_KEY")
        if env_key:
            return {"provider": "google", "api_key": env_key}
    elif provider == "openai":
        env_key = os.environ.get("OPENAI_API_KEY")
        if env_key:
            return {"provider": "openai", "api_key": env_key}
    
    # If no key provided, raise an error
    raise HTTPException(
        status_code=403,
        detail=f"API key for {provider} is required. Provide it via X-API-Key header, api_key query parameter, or {provider.upper()}_API_KEY environment variable."
    )

@app.get("/", include_in_schema=False)
async def root():
    """Serve the HTML interface."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF Invoice Parser with LLM</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
            h1 { color: #333; }
            .container { max-width: 800px; margin: 0 auto; }
            .info-box { background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            .api-key { margin-bottom: 20px; }
            input[type="text"] { width: 400px; padding: 8px; }
            select { padding: 8px; }
            button { padding: 8px 16px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
            button:hover { background-color: #45a049; }
            .footer { margin-top: 40px; font-size: 0.8em; color: #777; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PDF Invoice Parser with LLM</h1>
            
            <div class="info-box">
                <h2>About</h2>
                <p>This tool uses LLM (Large Language Model) technology to extract structured data from PDF invoices.</p>
                <p>It will attempt to identify key information like invoice numbers, dates, supplier/buyer details, and line items.</p>
            </div>
            
            <div class="api-key">
                <h2>API Key</h2>
                <p>Select an LLM provider and enter your API key:</p>
                <select id="llm-provider">
                    <option value="google">Google Gemini</option>
                    <option value="openai">OpenAI</option>
                </select>
                <input type="text" id="api-key" placeholder="Enter your API key">
            </div>
            
            <h2>Upload Invoice</h2>
            <input type="file" id="invoice-file" accept=".pdf">
            <button onclick="uploadInvoice()">Parse Invoice</button>
            
            <div id="result" style="margin-top: 20px;"></div>
            
            <div class="footer">
                <p>PDF Invoice Parser with LLM | Powered by Google Gemini and OpenAI APIs</p>
            </div>
        </div>
        
        <script>
            async function uploadInvoice() {
                const provider = document.getElementById('llm-provider').value;
                const apiKey = document.getElementById('api-key').value;
                const fileInput = document.getElementById('invoice-file');
                const resultDiv = document.getElementById('result');
                
                if (!apiKey) {
                    resultDiv.innerHTML = '<p style="color: red;">Please enter an API key.</p>';
                    return;
                }
                
                if (!fileInput.files || fileInput.files.length === 0) {
                    resultDiv.innerHTML = '<p style="color: red;">Please select a PDF file to upload.</p>';
                    return;
                }
                
                const file = fileInput.files[0];
                if (!file.name.endsWith('.pdf')) {
                    resultDiv.innerHTML = '<p style="color: red;">Please select a PDF file.</p>';
                    return;
                }
                
                resultDiv.innerHTML = '<p>Processing... This may take a minute.</p>';
                
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const response = await fetch('/upload-invoice/?provider=' + encodeURIComponent(provider) + '&api_key=' + encodeURIComponent(apiKey), {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        resultDiv.innerHTML = `
                            <h3>Success!</h3>
                            <p>The invoice has been processed successfully.</p>
                            <p><a href="${data.invoice_csv_url}" target="_blank">Download Invoice-Level Data</a></p>
                            <p><a href="${data.item_csv_url}" target="_blank">Download Item-Level Data</a></p>
                        `;
                    } else {
                        resultDiv.innerHTML = `<p style="color: red;">Error: ${data.detail}</p>`;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/upload-invoice/", response_model=ParsingResponse)
async def upload_invoice(
    file: UploadFile = File(...),
    api_info: dict = Depends(get_api_key)
):
    """
    Upload a PDF invoice file for processing with LLM.
    The file will be parsed and data will be extracted to CSV files.
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Get provider and API key
    provider = api_info["provider"]
    api_key = api_info["api_key"]
    
    # Save the uploaded file temporarily
    temp_file_path = f"temp/{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Initialize parser and parse PDF with the provided API key and provider
        if provider == "google":
            parser = LLMPDFParser(
                pdf_path=temp_file_path,
                api_key=api_key,
                llm_provider="google"
            )
        else:  # provider == "openai"
            parser = LLMPDFParser(
                pdf_path=temp_file_path,
                openai_api_key=api_key,
                llm_provider="openai"
            )
            
        invoice_data, item_data = parser.parse()
        
        # Check if we used the fallback method
        using_fallback = "Fallback" in invoice_data.get("Additional Remarks", "")
        
        # Generate unique filenames for output CSVs
        invoice_csv = f"output/invoice_level_{uuid.uuid4()}.csv"
        item_csv = f"output/item_level_{uuid.uuid4()}.csv"
        
        # Save data to CSV files
        save_to_csv(invoice_data, invoice_csv)
        save_items_to_csv(item_data, item_csv)
        
        message = f"Invoice processed successfully with {provider.capitalize()} LLM"
        if using_fallback:
            message = f"Invoice processed with fallback method (regex). For better results, please provide a valid {provider.capitalize()} API key."
        
        return ParsingResponse(
            status="success",
            invoice_csv_url=f"/download/{os.path.basename(invoice_csv)}",
            item_csv_url=f"/download/{os.path.basename(item_csv)}",
            message=message
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing invoice with {provider} API: {str(e)}")
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a generated CSV file.
    """
    file_path = f"output/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path, 
        media_type="text/csv", 
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.delete("/cleanup/{filename}")
async def cleanup_file(filename: str):
    """
    Delete a generated CSV file when it's no longer needed.
    """
    file_path = f"output/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        os.remove(file_path)
        return {"status": "success", "message": f"File {filename} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

@app.post("/set-api-key/")
async def set_api_key(llm_api_key: LLMAPIKey):
    """
    Set API key for the specified LLM provider.
    """
    try:
        # Store it temporarily (this will only last until server restart)
        if llm_api_key.provider == "google":
            os.environ["GOOGLE_API_KEY"] = llm_api_key.api_key
        else:  # provider == "openai"
            os.environ["OPENAI_API_KEY"] = llm_api_key.api_key
            
        return {
            "status": "success", 
            "message": f"{llm_api_key.provider.capitalize()} API key set successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting API key: {str(e)}")

@app.post("/bulk-upload/")
async def bulk_upload_invoices(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    api_info: dict = Depends(get_api_key)
):
    """
    Upload multiple PDF invoice files for processing with LLM.
    Files will be processed in the background.
    """
    # Validate file types
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"Only PDF files are accepted. {file.filename} is not a PDF.")
    
    # Get provider and API key
    provider = api_info["provider"]
    api_key = api_info["api_key"]
    
    # Process files in the background
    job_id = str(uuid.uuid4())
    processing_info = []
    
    for file in files:
        file_id = str(uuid.uuid4())
        temp_file_path = f"temp/{file_id}_{file.filename}"
        
        # Save file temporarily
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        processing_info.append({
            "file_id": file_id,
            "filename": file.filename,
            "temp_path": temp_file_path
        })
    
    # Queue background task for processing
    background_tasks.add_task(process_bulk_files, job_id, processing_info, provider, api_key)
    
    return {
        "status": "processing",
        "job_id": job_id,
        "message": f"Processing {len(files)} files in the background with {provider.capitalize()} LLM",
        "files": [info["filename"] for info in processing_info]
    }

@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    """
    Check the status of a bulk processing job.
    """
    status_file = f"output/job_{job_id}_status.json"
    if not os.path.exists(status_file):
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        status_data = pd.read_json(status_file).to_dict(orient="records")
        return {
            "job_id": job_id,
            "files": status_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking job status: {str(e)}")

async def process_bulk_files(job_id: str, processing_info: List[dict], provider: str, api_key: str):
    """
    Process multiple files in the background with LLM.
    Updates a status file as processing progresses.
    """
    status_file = f"output/job_{job_id}_status.json"
    results = []
    
    for info in processing_info:
        result = {
            "file_id": info["file_id"],
            "filename": info["filename"],
            "status": "processing",
            "provider": provider
        }
        results.append(result)
        
        # Update status
        pd.DataFrame(results).to_json(status_file, orient="records")
        
        try:
            # Parse the PDF with the appropriate LLM provider
            if provider == "google":
                parser = LLMPDFParser(
                    pdf_path=info["temp_path"],
                    api_key=api_key,
                    llm_provider="google"
                )
            else:  # provider == "openai"
                parser = LLMPDFParser(
                    pdf_path=info["temp_path"],
                    openai_api_key=api_key,
                    llm_provider="openai"
                )
                
            invoice_data, item_data = parser.parse()
            
            # Generate filenames
            invoice_csv = f"output/invoice_level_{info['file_id']}.csv"
            item_csv = f"output/item_level_{info['file_id']}.csv"
            
            # Save data
            save_to_csv(invoice_data, invoice_csv)
            save_items_to_csv(item_data, item_csv)
            
            # Update result
            result["status"] = "completed"
            result["invoice_csv"] = os.path.basename(invoice_csv)
            result["item_csv"] = os.path.basename(item_csv)
            
        except Exception as e:
            # Update result with error
            result["status"] = "failed"
            result["error"] = str(e)
            
        finally:
            # Clean up temp file
            if os.path.exists(info["temp_path"]):
                os.remove(info["temp_path"])
            
            # Update status file
            pd.DataFrame(results).to_json(status_file, orient="records")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 