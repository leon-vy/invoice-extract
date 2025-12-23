# Validation Guide

This directory contains the logic for validating and comparing data between different sources (e.g., BigQuery vs Advertising Platforms).

## How to add a new Validator

To add a validator for a new platform, follow these steps:

### 1. Define Platform Configuration
Update `invoice_extractor/validators/config/platform_config.py` with the queries and output tables for the new platform.

```python
PLATFORM_CONFIGS = {
    "MYPLATFORM": {
        "query_bigq": "SELECT ... FROM ...",
        "query_provider": "SELECT ... FROM ...",
        "output_table": "myplatform_validation_results"
    },
    # ...
}
```

### 2. Implement the Validator Class
Create a new file in `validators/platforms/` (e.g., `myplatform_validator.py`) and inherit from `BaseApproval`.

```python
from invoice_extractor.validators.core.base_validator import BaseApproval

class MyPlatformApproval(BaseApproval):
    def cleaning_data(self, month_bigq, month_provider):
        # 1. Fetch data using self.fetch_bigq_data(month_bigq) 
        #    and self.fetch_provider_data(month_provider)
        # 2. Perform cleaning and merging
        # 3. Return the merged DataFrame
        pass
```

### 3. Register the Validator in `validate.py`
In `invoice_extractor/validators/validate.py`, add your new class to the `VALIDATOR_CLASSES` dictionary:

```python
from invoice_extractor.validators.platforms.myplatform_validator import MyPlatformApproval

VALIDATOR_CLASSES = {
    "ADSP": ADSPApproval,
    # ...
    "MYPLATFORM": MyPlatformApproval
}
```

## Running Validation

Run the validation process for all configured platforms:
```bash
python -m invoice_extractor.validators.validate
```

The script will automatically iterate through `PLATFORM_CONFIGS`, instantiate the corresponding validator class, apply business rules (defined in `BaseApproval`), and save the results to BigQuery.
