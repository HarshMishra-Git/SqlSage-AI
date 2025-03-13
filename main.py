# Import necessary libraries
import os
import json
import time
from dotenv import load_dotenv
from app import app
import sql_generator
import sql_corrector
from database_utils import load_database_schema

# Load environment variables from .env file
load_dotenv()

# Function to load input file
def load_input_file(file_path):
    """
    Load input file which is a list of dictionaries.
    
    :param file_path: Path to the input file
    :return: List of dictionaries
    """
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

# Function to generate SQL statements
def generate_sqls(data, schema_info):
    """
    Generate SQL statements from the NL queries.
    
    :param data: List of NL queries
    :param schema_info: Database schema information
    :return: List of SQL statements
    """
    sql_statements = []
    
    # Process each NL query
    for item in data:
        nl_query = item.get('NL', '')
        if nl_query:
            generated_sql = sql_generator.generate_sql_from_nl(nl_query, schema_info)
            sql_statements.append({
                'NL': nl_query,
                'Query': generated_sql
            })
    
    return sql_statements

# Function to correct SQL statements
def correct_sqls(data, schema_info):
    """
    Correct SQL statements if necessary.
    
    :param data: List of Dict with incorrect SQL statements
    :param schema_info: Database schema information
    :return: List of corrected SQL statements
    """
    corrected_sqls = []
    
    # Process each incorrect SQL query
    for item in data:
        incorrect_sql = item.get('IncorrectQuery', '')
        if incorrect_sql:
            corrected_sql = sql_corrector.correct_sql_query(incorrect_sql, schema_info)
            corrected_sqls.append({
                'IncorrectQuery': incorrect_sql,
                'CorrectQuery': corrected_sql
            })
    
    return corrected_sqls

# Main function
def main():
    # Load database schema
    schema_info = load_database_schema()
    
    # Specify the path to input files
    input_file_path_1 = 'attached_assets/train_generate_task.json'
    input_file_path_2 = 'attached_assets/train_query_correction_task.json'
    
    # Load data from input files
    data_1 = load_input_file(input_file_path_1)
    data_2 = load_input_file(input_file_path_2)
    
    start = time.time()
    # Generate SQL statements
    sql_statements = generate_sqls(data_1, schema_info)
    generate_sqls_time = time.time() - start
    
    start = time.time()
    # Correct SQL statements
    corrected_sqls = correct_sqls(data_2, schema_info)
    correct_sqls_time = time.time() - start
    
    assert len(data_2) == len(corrected_sqls)
    assert len(data_1) == len(sql_statements)
    
    # Save the outputs
    with open('output_sql_correction_task.json', 'w') as f:
        json.dump(corrected_sqls, f, indent=2)    
    
    with open('output_sql_generation_task.json', 'w') as f:
        json.dump(sql_statements, f, indent=2)
    
    print(f"Time taken to generate SQLs: {generate_sqls_time} seconds")
    print(f"Time taken to correct SQLs: {correct_sqls_time} seconds")
    
    # Get the total tokens from the generator and corrector
    total_tokens = sql_generator.get_total_tokens() + sql_corrector.get_total_tokens()
    print(f"Total tokens: {total_tokens}")
    
    return generate_sqls_time, correct_sqls_time

if __name__ == "__main__":
    # If running as a script, execute the main function
    if os.environ.get("RUN_PROCESSING", "False").lower() == "true":
        generate_sqls_time, correct_sqls_time = main()
    else:
        # Otherwise start the web server
        # app.run(host="0.0.0.0", port=5000, debug=True)
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=False)
