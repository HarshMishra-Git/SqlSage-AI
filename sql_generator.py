
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
    Call the Google Gemini API to generate SQL from natural language.
    
    :param prompt: The prompt to send to the API
    :param temperature: Temperature for the model
    :param max_tokens: Maximum number of tokens to generate
    :return: The generated SQL query
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
        
        # Extract the generated SQL
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

def generate_sql_from_nl(nl_query, schema_info):
    """
    Generate SQL from a natural language query.
    
    :param nl_query: Natural language query
    :param schema_info: Database schema information
    :return: Generated SQL query
    """
    # Format the schema information
    schema_text = format_schema_for_prompt(schema_info)
    
    # Create the prompt
    prompt = f"""
I need to convert this natural language query to PostgreSQL:

"{nl_query}"

Based on the following database schema:

{schema_text}

Generate a valid PostgreSQL query for this request. 
Make sure to:
1. Use the EXACT table and column names as shown in the schema (case-sensitive)
2. Join tables correctly when needed
3. Use appropriate WHERE conditions
4. Include any necessary GROUP BY, ORDER BY, or LIMIT clauses
5. Ensure all SQL syntax is valid
6. Double-check that all column and table names match the schema exactly

Return ONLY the SQL query with no additional text or explanations.
"""
    
    # Call the API
    sql_query = call_gemini_api(prompt)
    
    if not sql_query:
        return "Error generating SQL query"
    
    # Ensure the query ends with a semicolon
    if not sql_query.endswith(';'):
        sql_query += ';'
    
    return sql_query
