# Extraction Guide

This directory contains the logic for extracting invoice data from various platforms.

## How to add a new Platform

To add a new platform (e.g., `MYPLATFORM`), follow these steps:

### 1. Create the platform directory
Create a new folder in `invoice_extractor/extractor/` (e.g., `invoice_extractor/extractor/myplatform/`). If placeholders for other platforms are not yet present.

### 2. Implement the Processor
Create a file `my_processor.py` and inherit from `BaseProcessor`. Use the `@ProcessorRegistry.register` decorator to register it.

```python
from invoice_extractor.core import BaseProcessor, ProcessorRegistry, settings

@ProcessorRegistry.register("MYPLATFORM")
class MyPlatformProcessor(BaseProcessor):
    def __init__(self):
        super().__init__("MYPLATFORM")
        # Initialize your API clients or BigQuery handlers here

    def run(self, **kwargs):
        # Implement your extraction logic
        self.logger.info("Running extraction for MYPLATFORM...")
        # ... fetch data ...
        # ... process data ...
        # ... save to BigQuery ...
```

### 3. Register the Processor in `main_extract.py`
To ensure your processor is discovered, import it in `invoice_extractor/extractor/main_extract.py`:

```python
# ... other imports ...
from invoice_extractor.extractor.myplatform.my_processor import MyPlatformProcessor
```

### 4. Update the Orchestrator (if needed)
In `main_extract.py`, the `run_extraction()` function calls `processor.run()`. If your processor requires specific arguments, update the call logic:

```python
if platform == "MYPLATFORM":
    processor.run(specific_arg=settings.some_setting)
```

## Running Extraction

You can run the extraction for all registered platforms using:
```bash
python -m invoice_extractor.extractor.main_extract
```

If you want to run a specific processor for testing, you can add a `if __name__ == "__main__":` block in your processor file.
