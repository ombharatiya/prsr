@echo off
:: Script to test the LLM PDF parser with a sample invoice

:: Default LLM provider
set LLM_PROVIDER=google

:: Parse command-line arguments
:parse_args
if "%~1"=="" goto :end_parse_args
if "%~1"=="-p" (
    set LLM_PROVIDER=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--provider" (
    set LLM_PROVIDER=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="-h" (
    echo Usage: %0 [options]
    echo.
    echo Options:
    echo   -p, --provider PROVIDER  LLM provider to use (google or openai) [default: google]
    echo   -h, --help               Show this help message and exit
    exit /b 0
)
if "%~1"=="--help" (
    echo Usage: %0 [options]
    echo.
    echo Options:
    echo   -p, --provider PROVIDER  LLM provider to use (google or openai) [default: google]
    echo   -h, --help               Show this help message and exit
    exit /b 0
)
echo Unknown option: %~1
echo Use --help for usage information.
exit /b 1

:end_parse_args

:: Validate LLM provider
if not "%LLM_PROVIDER%"=="google" (
    if not "%LLM_PROVIDER%"=="openai" (
        echo Error: Invalid LLM provider: %LLM_PROVIDER%
        echo Valid providers are: google, openai
        exit /b 1
    )
)

echo Using %LLM_PROVIDER% as the LLM provider

:: Activate virtual environment if it exists
if exist .venv (
    echo Activating virtual environment...
    call .venv\Scripts\activate
)

:: Ensure required directories exist
if not exist MyTest\input mkdir MyTest\input
if not exist MyTest\output mkdir MyTest\output

:: Check if we have sample invoice in MyTest/input
set SAMPLE_PDF=MyTest\input\Mensa_KA_BLR_830 (1).pdf
if not exist "%SAMPLE_PDF%" (
    echo Sample invoice not found at %SAMPLE_PDF%
    echo Please place a sample invoice at this location and try again.
    exit /b 1
)

:: Check if API key is set based on provider
if "%LLM_PROVIDER%"=="google" (
    if "%GOOGLE_API_KEY%"=="" (
        echo GOOGLE_API_KEY environment variable is not set.
        echo Please set it with: set GOOGLE_API_KEY=your_api_key
        echo.
        echo Running with fallback regex parser...
    )
) else if "%LLM_PROVIDER%"=="openai" (
    if "%OPENAI_API_KEY%"=="" (
        echo OPENAI_API_KEY environment variable is not set.
        echo Please set it with: set OPENAI_API_KEY=your_api_key
        echo.
        echo Running with fallback regex parser...
    )
)

:: Run the LLM parser test with the specified provider
echo Testing LLM PDF parser with sample invoice...
python test_llm_parser.py --provider %LLM_PROVIDER%

:: Check if extraction was successful
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Test completed successfully!
    echo Results have been saved to:
    echo - MyTest\output\%LLM_PROVIDER%_invoice_level.csv
    echo - MyTest\output\%LLM_PROVIDER%_item_level.csv
) else (
    echo.
    echo Test failed with errors.
)

:: Remind about API key if not set
if "%LLM_PROVIDER%"=="google" (
    if "%GOOGLE_API_KEY%"=="" (
        echo.
        echo NOTE: For best results with Google Gemini, please set a valid API key:
        echo set GOOGLE_API_KEY=your_api_key
    )
) else if "%LLM_PROVIDER%"=="openai" (
    if "%OPENAI_API_KEY%"=="" (
        echo.
        echo NOTE: For best results with OpenAI, please set a valid API key:
        echo set OPENAI_API_KEY=your_api_key
    )
)

:: Pause so the user can see the results
pause 