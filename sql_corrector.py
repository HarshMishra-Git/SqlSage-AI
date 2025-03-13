
import os
import json
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to track token usage
total_tokens = 0
last_token_count = 0

def get_total_tokens():
    """Get the total number of tokens used."""
    global total_tokens
    return total_tokens

def get_last_token_count():
    """Get the token count of the last API call."""
    global last_token_count
    return last_token_count

def call_gemini_api(prompt, temperature=0.0, max_tokens=1000):
    """
    Call the Google Gemini API to correct SQL queries.
    
    :param prompt: The prompt to send to the API
    :param temperature: Temperature for the model
    :param max_tokens: Maximum number of tokens to generate
    :return: The corrected SQL query
    """
    global total_tokens, last_token_count
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables.")
        return "Error: API key not found"
    
    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash-002:generateContent"

    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    
    data = {
        "contents": [
            {
                "role": "user",
                "parts": [{
                    "text": prompt
                }]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "topP": 0.8,
            "topK": 40
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        
        # Update token usage (Gemini doesn't return token count directly, 
        # so we'll estimate for now)
        last_token_count = 100  # Placeholder value
        total_tokens += last_token_count
        
        # Extract the corrected SQL
        sql_query = response_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        
        # Clean up the response to extract only the SQL query
        if sql_query.startswith("```sql"):
            sql_query = sql_query.split("```sql")[1]
        if "```" in sql_query:
            sql_query = sql_query.split("```")[0]
            
        sql_query = sql_query.strip()
        
        return sql_query
    
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        return None

def format_schema_for_prompt(schema_info):
    """
    Format the database schema information in a concise way for the prompt.
    
    :param schema_info: Database schema dictionary
    :return: Formatted schema string for the prompt
    """
    schema_text = "Database Schema:\n"
    
    for table_name, schema in schema_info.items():
        schema_text += f"\nTable: {table_name}\n"
        
        # Add columns
        schema_text += "Columns:\n"
        for col_name, col_info in schema['columns'].items():
            data_type = col_info['data_type']
            is_pk = col_name in schema['primary_keys']
            pk_str = "PRIMARY KEY" if is_pk else ""
            schema_text += f"  - {col_name} ({data_type}) {pk_str}\n"
        
        # Add foreign keys
        if schema['foreign_keys']:
            schema_text += "Foreign Keys:\n"
            for fk in schema['foreign_keys']:
                schema_text += f"  - {fk['column']} references {fk['foreign_table']}({fk['foreign_column']})\n"
    
    return schema_text

def identify_common_errors(sql_query):
    """
    Identify common errors in SQL queries.
    
    :param sql_query: The SQL query to analyze
    :return: List of potential errors
    """
    potential_errors = []
    
    # Check for missing quotes around string literals
    if " = " in sql_query:
        parts = sql_query.split(" = ")
        for i in range(1, len(parts)):
            part = parts[i].strip()
            if part and part[0].isalpha() and not part.startswith("'") and not part.startswith('"'):
                if part.split()[0].lower() not in ["true", "false", "null"]:
                    potential_errors.append(f"Possible missing quotes around string literal: {part.split()[0]}")
    
    # Check for incorrect JOIN syntax
    if "join" in sql_query.lower() and "on" not in sql_query.lower():
        potential_errors.append("JOIN used without ON clause")
    
    # Check for missing semicolon
    if not sql_query.endswith(';'):
        potential_errors.append("Missing semicolon at the end of the query")
    
    # Check for GROUP BY issues
    if "group by" in sql_query.lower() and "having" in sql_query.lower():
        having_part = sql_query.lower().split("having")[1].strip()
        potential_aggregate_funcs = ["sum", "avg", "count", "min", "max"]
        has_aggregate = any(func in having_part.lower() for func in potential_aggregate_funcs)
        if not has_aggregate:
            potential_errors.append("HAVING clause might be missing aggregate function")
    
    return potential_errors

def correct_sql_query(incorrect_sql, schema_info):
    """
    Correct an incorrect SQL query.
    
    :param incorrect_sql: The incorrect SQL query
    :param schema_info: Database schema information
    :return: Corrected SQL query
    """
    # Format the schema information
    schema_text = format_schema_for_prompt(schema_info)
    
    # Identify potential errors
    potential_errors = identify_common_errors(incorrect_sql)
    errors_text = "\n".join([f"- {error}" for error in potential_errors])
    
    # Create the prompt
    prompt = f"""
I need to correct this SQL query:

```sql
{incorrect_sql}
```

Based on the following database schema:

{schema_text}

Potential errors identified:
{errors_text}

Please provide the corrected SQL query. Make sure to:
1. Fix any syntax errors
2. Use correct table and column names FROM THE SCHEMA EXACTLY AS THEY APPEAR
3. Fix any join conditions or relationships
4. Ensure all SQL syntax is valid
5. Pay special attention to column names - match them exactly to the schema

Return ONLY the corrected SQL query with no additional text or explanations."""
    
    # Call the API
    corrected_sql = call_gemini_api(prompt)
    
    if not corrected_sql:
        return "Error correcting SQL query"
    
    # Ensure the query ends with a semicolon
    if not corrected_sql.endswith(';'):
        corrected_sql += ';'
    
    return corrected_sql
