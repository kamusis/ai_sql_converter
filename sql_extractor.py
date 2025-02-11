import os
from typing import List
import asyncio
import openai
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SQLExtraction(BaseModel):
    proc_name: str
    description: str
    in_params: list[str]
    out_params: list[str]
    inout_params: list[str]
    related_tables: list[str]

class SQLExtractor:
    """
    A class for extracting and analyzing information from SQL stored procedures.
    
    This class uses OpenAI's API to analyze SQL stored procedures and extract key information
    such as procedure names, parameters, descriptions, and table references. It handles large
    procedures by splitting them into manageable chunks and implements retry mechanisms for
    API calls.
    
    Attributes:
        client (OpenAI): OpenAI API client instance
        model (str): Name of the OpenAI model to use, defaults to 'gpt-4o-mini'
        partial_results (list): Temporary storage for procedure analysis results
        max_input_tokens (int): Maximum number of tokens for API input, set to 6000
    
    Key Features:
        - Intelligent chunking of large procedures
        - Comprehensive error handling with retries
        - Support for multi-part procedure analysis
        - Token limit management
        - Asynchronous processing
    """
    
    def __init__(self):
        """
        Initialize the SQLExtractor with OpenAI client and configuration.
        Sets up the API client, model selection, and token limits.
        """
        self.client = OpenAI()
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.partial_results = []
        # Set max input tokens to 6k to leave room for output in 8k context window of OpenAI GPT4
        self.max_input_tokens = 6000

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        
        Uses a conservative estimate where 1 token ≈ 3 characters for SQL code,
        which typically has more special characters than regular text.
        
        Args:
            text (str): The text to estimate tokens for
            
        Returns:
            int: Estimated number of tokens in the text
        """
        return len(text) // 3

    def _split_sql_into_chunks(self, sql_content: str) -> List[dict]:
        """
        Split SQL content into manageable chunks for processing.
        
        For large stored procedures, splits the content into header and body chunks
        to stay within token limits. Headers contain parameter information while
        bodies contain the main logic.
        
        Args:
            sql_content (str): The full SQL content to split
            
        Returns:
            List[dict]: List of chunks, each containing:
                - type: 'header', 'body', or 'full'
                - content: The SQL code
                - proc_name: Name of the procedure
                - chunk_index: Index for multi-part bodies
                - total_chunks: Total number of body chunks
        """
        if not sql_content:
            return []
            
        chunks = []
        current_chunk = []
        in_procedure = False
        current_proc_name = ""
        
        for line in sql_content.split('\n'):
            line_lower = line.strip().lower()
            
            # Start of a new procedure
            if line_lower.startswith('create proc') or line_lower.startswith('create procedure'):
                # If we were already in a procedure, save it
                if in_procedure and current_chunk:
                    chunks.append({
                        'type': 'full',
                        'content': '\n'.join(current_chunk),
                        'proc_name': current_proc_name
                    })
                    current_chunk = []
                in_procedure = True
                current_proc_name = line.split()[-1].strip()  # Get procedure name
            
            # If we're in a procedure, collect the line
            if in_procedure:
                current_chunk.append(line)
                
                # Check for end of procedure (GO statement)
                if line_lower == 'go':
                    proc_content = '\n'.join(current_chunk)
                    estimated_tokens = self._estimate_tokens(proc_content)
                    
                    # If procedure is too long, split it
                    if estimated_tokens > self.max_input_tokens:
                        # Split into header (for parameters) and body (for logic analysis)
                        header_lines = []
                        body_lines = []
                        in_body = False
                        for proc_line in current_chunk:
                            proc_line_lower = proc_line.strip().lower()
                            if proc_line_lower.startswith('as') or proc_line_lower.startswith('begin'):
                                in_body = True
                            if in_body:
                                body_lines.append(proc_line)
                            else:
                                header_lines.append(proc_line)
                        
                        # If body is still too long, split it into smaller chunks
                        body_content = '\n'.join(body_lines)
                        if self._estimate_tokens(body_content) > self.max_input_tokens:
                            # First chunk includes the procedure structure
                            body_chunks = []
                            current_body_chunk = []
                            current_tokens = 0
                            
                            for body_line in body_lines:
                                line_tokens = self._estimate_tokens(body_line)
                                if current_tokens + line_tokens > self.max_input_tokens and current_body_chunk:
                                    body_chunks.append('\n'.join(current_body_chunk))
                                    current_body_chunk = []
                                    current_tokens = 0
                                current_body_chunk.append(body_line)
                                current_tokens += line_tokens
                            
                            if current_body_chunk:
                                body_chunks.append('\n'.join(current_body_chunk))
                            
                            # Add header chunk
                            chunks.append({
                                'type': 'header',
                                'content': '\n'.join(header_lines),
                                'proc_name': current_proc_name
                            })
                            
                            # Add body chunks
                            for i, body_chunk in enumerate(body_chunks):
                                chunks.append({
                                    'type': 'body',
                                    'content': body_chunk,
                                    'proc_name': current_proc_name,
                                    'chunk_index': i,
                                    'total_chunks': len(body_chunks)
                                })
                        else:
                            chunks.append({
                                'type': 'header',
                                'content': '\n'.join(header_lines),
                                'proc_name': current_proc_name
                            })
                            chunks.append({
                                'type': 'body',
                                'content': body_content,
                                'proc_name': current_proc_name
                            })
                    else:
                        chunks.append({
                            'type': 'full',
                            'content': proc_content,
                            'proc_name': current_proc_name
                        })
                    current_chunk = []
                    in_procedure = False
                    current_proc_name = ""
        
        # Add final chunk if exists
        if current_chunk:
            chunks.append({
                'type': 'full',
                'content': '\n'.join(current_chunk),
                'proc_name': current_proc_name
            })
        
        return [chunk for chunk in chunks if chunk['content'].strip()]

    async def extract_from_chunk(self, chunk: dict, chunk_index: int = 0) -> SQLExtraction | None:
        """
        Extract information from a SQL chunk with comprehensive error handling.
        
        Processes a chunk of SQL code through the OpenAI API to extract relevant information.
        Implements retry logic for API calls and handles various error conditions.
        
        Args:
            chunk (dict): The chunk to process, containing type and content
            chunk_index (int): Index of the chunk for logging purposes
            
        Returns:
            SQLExtraction | None: Extracted information or None if processing failed
            
        Error Handling:
            - Retries on API timeouts and rate limits
            - Handles token limit exceedance
            - Manages API errors with exponential backoff
        """
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                system_prompt = "You are an expert in SQL who can analyze stored procedures and extract key information."
                if chunk['type'] == 'header':
                    system_prompt += """ For this header section, focus on:
                    1. The procedure name
                    2. All input, output, and inout parameters
                    Leave the description and related tables empty as they will be analyzed separately."""
                elif chunk['type'] == 'body':
                    chunk_context = ""
                    if 'chunk_index' in chunk:
                        chunk_context = f" (Part {chunk['chunk_index'] + 1} of {chunk['total_chunks']})"
                    system_prompt += f""" This is the body of procedure {chunk['proc_name']}{chunk_context}. Focus on:
                    1. Understanding the procedure's purpose for the description
                    2. Identifying all tables referenced in the code
                    The parameters have already been analyzed."""
                else:  # full
                    system_prompt += """ Analyze the complete procedure to extract:
                    1. The procedure name
                    2. A clear description of its purpose
                    3. All input, output, and inout parameters
                    4. All tables referenced in the code"""

                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": "extract_sql_info",
                            "description": "Extract information from SQL stored procedure",
                            "parameters": SQLExtraction.model_json_schema()
                        }
                    }
                ]

                try:
                    completion = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.client.chat.completions.create,
                            model=self.model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": chunk['content']}
                            ],
                            tools=tools,
                            tool_choice={"type": "function", "function": {"name": "extract_sql_info"}}
                        ),
                        timeout=30  # 30 seconds timeout
                    )
                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        print(f"Timeout on attempt {attempt + 1}, retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        continue
                    raise TimeoutError("API request timed out after all retries")

                if not completion.choices:
                    raise ValueError("No completion choices returned from API")

                message = completion.choices[0].message
                if not message.tool_calls:
                    if message.content and "I apologize" in message.content:
                        raise ValueError(f"Model refused to process: {message.content}")
                    raise ValueError("No tool calls in response")

                result = message.tool_calls[0].function.arguments
                extraction = SQLExtraction.model_validate_json(result)

                # If this is a body analysis, we only want to update description and related_tables
                if chunk['type'] == 'body':
                    # Find the header result in self.partial_results
                    for prev_result in self.partial_results:
                        if prev_result.proc_name == chunk['proc_name']:
                            # Keep original parameters from header
                            extraction.in_params = prev_result.in_params
                            extraction.out_params = prev_result.out_params
                            extraction.inout_params = prev_result.inout_params
                            
                            # For multi-chunk body, append description and merge tables
                            if 'chunk_index' in chunk:
                                if chunk['chunk_index'] > 0:
                                    prev_result.description += "\n" + extraction.description
                                    prev_result.related_tables = list(set(prev_result.related_tables + extraction.related_tables))
                                    return None  # Skip intermediate chunks
                                else:
                                    prev_result.description = extraction.description
                                    prev_result.related_tables = extraction.related_tables
                            break

                return extraction

            except openai.RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * retry_delay
                    print(f"Rate limit exceeded, waiting {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                raise Exception("Rate limit exceeded after all retries") from e

            except openai.APIError as e:
                if attempt < max_retries - 1:
                    print(f"API error on attempt {attempt + 1}, retrying: {str(e)}")
                    await asyncio.sleep(retry_delay)
                    continue
                raise Exception(f"OpenAI API error after all retries: {str(e)}") from e

            except openai.BadRequestError as e:
                if "maximum context length" in str(e).lower():
                    raise ValueError(f"Token limit exceeded for chunk {chunk_index}. Consider reducing chunk size.") from e
                raise Exception(f"Bad request error: {str(e)}") from e

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Unexpected error on attempt {attempt + 1}, retrying: {str(e)}")
                    await asyncio.sleep(retry_delay)
                    continue
                raise Exception(f"Failed to process chunk after all retries: {str(e)}") from e

        raise Exception("Failed to process chunk after exhausting all retries")

    async def process_sql_file(self, file_path: str) -> List[SQLExtraction]:
        """
        Process a SQL file and extract information from all stored procedures.
        
        Reads a SQL file, splits it into procedures and chunks if necessary,
        and processes each chunk to extract information. Handles the coordination
        of multi-chunk procedures and result aggregation.
        
        Args:
            file_path (str): Path to the SQL file to process
            
        Returns:
            List[SQLExtraction]: List of extracted information for each procedure
            
        Note:
            For multi-chunk procedures, only the final result is included in the
            return list, with intermediate results used for accumulating information.
        """
        try:
            # Read SQL file
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Split into chunks
            chunks = self._split_sql_into_chunks(sql_content)
            print(f"\n📊 Processing SQL file: {file_path}")
            print(f"   • Total chunks: {len(chunks)}")

            # Store partial results for long procedures
            self.partial_results = []
            final_results = []

            # Process chunks in sequence (to handle dependencies between header and body)
            for i, chunk in enumerate(chunks):
                result = await self.extract_from_chunk(chunk, i)
                if result:
                    if chunk['type'] == 'header':
                        self.partial_results.append(result)
                    elif chunk['type'] == 'full':
                        final_results.append(result)
                    elif chunk['type'] == 'body' and ('chunk_index' not in chunk or chunk['chunk_index'] == chunk['total_chunks'] - 1):
                        # Only add body result for single-chunk body or last chunk of multi-chunk body
                        final_results.append(result)

            return final_results

        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
            return []

async def main():
    extractor = SQLExtractor()
    sql_files_path = os.getenv('SOURCE_DB_CODE_FILE', './sql_files/*.sql')
    
    # Process all SQL files in the directory
    import glob
    sql_files = glob.glob(sql_files_path)
    
    all_results = []
    for file_path in sql_files:
        results = await extractor.process_sql_file(file_path)
        all_results.extend(results)
        
    # Print results
    for i, extraction in enumerate(all_results, 1):
        print(f"\n✨ Extraction {i}:")
        print(f"   • Procedure: {extraction.proc_name}")
        print(f"   • Description: {extraction.description}")
        print(f"   • Input params: {', '.join(extraction.in_params)}")
        print(f"   • Output params: {', '.join(extraction.out_params)}")
        print(f"   • InOut params: {', '.join(extraction.inout_params)}")
        print(f"   • Related tables: {', '.join(extraction.related_tables)}")

if __name__ == "__main__":
    asyncio.run(main())