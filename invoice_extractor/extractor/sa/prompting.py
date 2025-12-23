sa_prompt = """
        Here is the extracted text from the invoice PDF, but it may have errors due to OCR limitations.  
        You will also receive images of the original PDF pages.  
        
        Extracted Text FROM the PDF:
        {extracted_text}

        ## Your task:  
        - Cross-check the extracted text with the images.  
        - Correct any OCR errors and missing content.
        - Preserve formatting (tables, bullet points, headers, etc.).  
        - Ensure accuracy in numbers, symbols, and special characters.
        - YOU HAVE THE TEXT EXTRACTED FROM THE PDF AND YOU HAVE THE IMAGES OF THE PDF, Now you need to extract the data as demanded from the text and the images.
        - Provide the final, corrected text in a structured format json.
        
        ----------

        ## Extraction Instructions

        - **CRITICAL**: Extract ONLY the following information from the Google invoice with **EXACT precision**. Any deviation will cause ERRORS:

        🔹 **MANDATORY CORE FIELDS (MUST extract these):**
            - `"invoice_number"`: ONLY the exact "Invoice number" value, nothing else
            - `"billing_period"`: ONLY the exact period after "Summary for"
            - `"vat_rate"`: ONLY the exact **VAT Rate** value with no modifications

        🔹 **TABLE EXTRACTION - STRICT REQUIREMENTS:**
            - Extract all invoice line items **from all pages**.
            - Columns:
                - `"description"` → Extracted from "Description" column.
                - `"advertiser_name"` → Parse from **Description field** (format: "Advertiser: <name>")
                - `"account_id"` → Parse from **Description field** (format: "Account ID: <id>")
                - `"quantity"` → Extracted from "Quantity" column.
                - `"uom"` → Extracted from "UoM" column.
                
        🔹 **CRITICAL FORMATTING RULES:**
            - MUST replace **ALL colons ':' with pipes '|' in descriptions**
            - MUST use **snake_case for all JSON keys**
            - Output MUST be valid JSON.


        ### ⚠️ Important:

        - **VERIFY each extracted field matches exactly what is specified above from the text given and the images.**
        - **Ensure all relevant rows are included, even if split across multiple pages.**
        - **Handle wrapped text properly, ensuring full descriptions are captured.**

        Now, analyze the images and refine the text accordingly.
        """