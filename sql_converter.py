import os
import glob
import json
from datetime import datetime
import time
from dotenv import load_dotenv
from prompt_optimizer import PromptOptimizer
import openai
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed

class SQLConverter:
    def __init__(self, api_key=None, model=None):
        """Initialize SQLConverter with environment variables"""
        load_dotenv()
        
        # Load configuration from environment
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.source_db_type = os.getenv('SOURCE_DB_TYPE', 'SYBASE')
        self.target_db_type = os.getenv('TARGET_DB_TYPE', 'POSTGRESQL')
        self.source_path = os.getenv('SOURCE_DB_CODE_FILE', './sql_files/*.sql')
        self.target_config = os.getenv('TARGET_DB_CODE_FILE', 'auto')
        self.model = model or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        # Initialize components
        self.client = openai.OpenAI(api_key=self.api_key)
        self.prompt_optimizer = PromptOptimizer()
        self.executor = ThreadPoolExecutor(max_workers=5)  # 限制并发数
        
        # Supported database types
        self.supported_db_types = {
            'SYBASE', 'MYSQL', 'POSTGRESQL',
            'ORACLE', 'SQLSERVER', 'DB2'
        }
    
    def _validate_db_type(self, db_type):
        """Validate database type"""
        if db_type not in self.supported_db_types:
            raise ValueError(f"Unsupported database type: {db_type}")
        return True
    
    async def _convert_sql_chunk(self, chunk, system_prompt=None):
        """Convert a single SQL chunk"""
        try:
            # Validate database types
            self._validate_db_type(self.source_db_type)
            self._validate_db_type(self.target_db_type)
            
            # Use default system prompt if none provided
            if system_prompt is None:
                system_prompt = self.prompt_optimizer.load_original_prompt()
            
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Convert this {self.source_db_type} SQL to {self.target_db_type}:\n\n{chunk}"}
            ]
            
            # 使用 executor 运行同步 API 调用
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=4000
                )
            )
            
            # 提取并返回转换后的 SQL
            converted = response.choices[0].message.content.strip()
            return converted.replace('```sql', '').replace('```', '').strip()
            
        except Exception as e:
            print(f"Error in convert_sql_chunk: {str(e)}")
            return None
    
    def _split_sql_into_chunks(self, sql_content, max_chunk_size=8000):
        """Split SQL content into chunks based on statement boundaries"""
        # Split on GO statements (common in Sybase/SQL Server)
        chunks = []
        current_chunk = []
        current_size = 0
        
        # First split by GO statements
        statements = [stmt.strip() for stmt in sql_content.split('go') if stmt.strip()]
        
        for stmt in statements:
            stmt_size = len(stmt)
            
            # If single statement exceeds max size, need to split further
            if stmt_size > max_chunk_size:
                # Split by stored procedures
                procs = stmt.split('create proc')
                for proc in procs:
                    if not proc.strip():
                        continue
                    if len(proc) > max_chunk_size:
                        # If proc is still too large, split by begin/end blocks
                        blocks = proc.split('begin')
                        for block in blocks:
                            if not block.strip():
                                continue
                            chunks.append(f"create proc{block}" if block == proc else f"begin{block}")
                    else:
                        chunks.append(f"create proc{proc}")
            else:
                chunks.append(stmt)
        
        return chunks
    
    async def _convert_sql_parallel(self, sql_content, system_prompt=None):
        """Convert SQL content in parallel"""
        # Split SQL into chunks
        chunks = self._split_sql_into_chunks(sql_content)
        print(f"\nSplit SQL into {len(chunks)} chunks")
        
        # Convert chunks in parallel
        tasks = []
        for chunk in chunks:
            task = asyncio.create_task(
                self._convert_sql_chunk(chunk, system_prompt)
            )
            tasks.append(task)
        
        # Wait for all conversions to complete
        results = await asyncio.gather(*tasks)
        
        # Filter out None results and join
        converted = [r for r in results if r]
        return "\n\nGO\n\n".join(converted) if converted else None
    
    async def convert_sql(self, sql_content, source_type=None, target_type=None):
        """Convert SQL from source database type to target database type"""
        # Use provided types or fall back to instance defaults
        source_type = source_type or self.source_db_type
        target_type = target_type or self.target_db_type
        
        print(f"\nConverting from {source_type} to {target_type} using {self.model}...\n")
        conversion_start_time = time.time()
        
        # Create prompts directory if it doesn't exist
        os.makedirs('prompts', exist_ok=True)
        
        # Load original prompt template
        prompt_template = self.prompt_optimizer.load_original_prompt()
        if not prompt_template:
            print("Error: Could not load prompt template")
            return None
        
        # Try to load optimized prompt
        optimized_template = self.prompt_optimizer.load_optimized_prompt()
        if not optimized_template:
            # Start timing prompt optimization
            optimize_start_time = time.time()
            
            # Optimize the prompt template
            optimized_template = self.prompt_optimizer.optimize_prompt(prompt_template)
            
            # Save the optimized prompt for future use
            self.prompt_optimizer.save_optimized_prompt(optimized_template)
            
            # Record prompt optimization time
            optimize_end_time = time.time()
            optimize_duration = optimize_end_time - optimize_start_time
            print(f"\nPrompt optimization completed in {optimize_duration:.3f} seconds")
        else:
            print("\nUsing cached optimized prompt")
            optimize_duration = 0

        # Split SQL into chunks if it's too large
        chunks = self._split_sql_into_chunks(sql_content)
        print(f"\nSplit SQL into {len(chunks)} chunks")
        
        # Start timing conversion
        convert_start_time = time.time()
        
        # Convert SQL chunks in parallel
        converted_sql = await self._convert_sql_parallel(sql_content, optimized_template)
        
        # Record conversion time
        convert_end_time = time.time()
        convert_duration = convert_end_time - convert_start_time
        print(f"\nSQL conversion completed in {convert_duration:.3f} seconds")
        
        # Record total time
        total_duration = time.time() - conversion_start_time
        print(f"\nTotal process completed in {total_duration:.3f} seconds")
        
        return converted_sql

def load_sql_files(source_path):
    """
    Load SQL files based on the source path configuration.
    Returns a list of tuples (file_path, content)
    """
    files_content = []
    
    # Check if path contains semicolons (multiple files)
    if ';' in source_path:
        paths = source_path.split(';')
        for path in paths:
            # Handle wildcards
            if '*' in path:
                for file_path in glob.glob(path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        files_content.append((file_path, f.read()))
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    files_content.append((path, f.read()))
    
    # Check if it's a directory
    elif os.path.isdir(source_path):
        for root, _, files in os.walk(source_path):
            for file in files:
                if file.endswith('.sql'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        files_content.append((file_path, f.read()))
    
    # Single file
    else:
        with open(source_path, 'r', encoding='utf-8') as f:
            files_content.append((source_path, f.read()))
    
    return files_content

def get_target_file_path(source_file, target_config):
    """
    Generate target file path based on configuration
    """
    if target_config.lower() == 'auto':
        # Generate result file name based on source file
        base_name = os.path.splitext(source_file)[0]
        return f"{base_name}_result.sql"
    return target_config

def save_prompt(prompt, file_path, metadata=None):
    """
    Save prompt with metadata to a file
    """
    prompt_data = {
        "prompt": prompt,
        "metadata": metadata or {},
        "timestamp": datetime.now().isoformat()
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(prompt_data, f, indent=2, ensure_ascii=False)

def load_original_prompt():
    """
    Load the original prompt from file
    """
    prompt_path = os.path.join('prompts', 'original_prompt.prompt')
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Original prompt file not found: {prompt_path}")

def load_optimized_prompt():
    """
    Load the optimized prompt from file if it exists
    """
    prompt_path = os.path.join('prompts', 'optimized_prompt.prompt')
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def convert_sql(sql_content, source_type, target_type):
    """
    Convert SQL from source database type to target database type using OpenAI
    """
    conversion_start_time = time.time()
    
    # Create prompts directory if it doesn't exist
    os.makedirs('prompts', exist_ok=True)
    
    # Load original prompt template
    try:
        prompt_data = load_original_prompt()
        prompt_template = prompt_data["prompt"]
    except (FileNotFoundError, KeyError) as e:
        print(f"Error loading prompt template: {str(e)}")
        return None
    
    # 检查是否存在优化后的提示词
    optimized_data = load_optimized_prompt()
    if optimized_data:
        print("\nUsing cached optimized prompt")
        optimized_template = optimized_data["prompt"]
        optimize_duration = 0
    else:
        # Generate timestamp for new optimization
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save the original prompt template used
        original_prompt_path = os.path.join('prompts', f'conversion_{timestamp}_template.prompt')
        save_prompt(prompt_template, original_prompt_path, {
            "type": "template",
            "source_type": source_type,
            "target_type": target_type,
            "base_template": "original_prompt.prompt"
        })
        
        # Start timing prompt optimization
        optimize_start_time = time.time()
        
        # Optimize the prompt template
        optimized_template = PromptOptimizer().optimize_prompt(prompt_template)
        
        # Record prompt optimization time
        optimize_end_time = time.time()
        optimize_duration = optimize_end_time - optimize_start_time
        print(f"\nPrompt optimization completed in {optimize_duration:.3f} seconds")
        
        # Save optimized prompt for future use
        save_prompt(optimized_template, os.path.join('prompts', 'optimized_prompt.prompt'), {
            "type": "optimized_template",
            "source_type": "ANY",
            "target_type": "ANY",
            "base_template": "original_prompt.prompt",
            "optimization_time": optimize_duration,
            "optimization_timestamp": datetime.now().isoformat()
        })
        
        # Save optimization record
        optimized_prompt_path = os.path.join('prompts', f'conversion_{timestamp}_optimized_template.prompt')
        save_prompt(optimized_template, optimized_prompt_path, {
            "type": "optimized_template",
            "source_type": source_type,
            "target_type": target_type,
            "base_template": "original_prompt.prompt",
            "optimization_time": optimize_duration
        })

    try:
        # Split SQL content into chunks
        sql_chunks = split_sql_content(sql_content)
        
        # Start timing SQL conversion
        conversion_api_start_time = time.time()
        
        # Initialize converter with faster model
        converter = SQLConverter(
            api_key=os.getenv('OPENAI_API_KEY'),
            model="gpt-3.5-turbo-16k"  # 使用更快的模型
        )
        
        # 构建系统消息
        system_prompt = optimized_template.format(
            source_type=source_type,
            target_type=target_type
        )
        
        # 使用异步方式并行转换所有块
        async def convert_all():
            return await converter.convert_sql(sql_content, source_type, target_type)
        
        # 运行异步转换
        converted_chunks = asyncio.run(convert_all())
        
        # Record SQL conversion time
        conversion_api_end_time = time.time()
        conversion_api_duration = conversion_api_end_time - conversion_api_start_time
        print(f"\nSQL conversion completed in {conversion_api_duration:.3f} seconds")
        
        if not converted_chunks:
            print("Error: No chunks were successfully converted")
            return None
        
        # Combine converted chunks
        result = converted_chunks
        
        # Record total time
        total_duration = time.time() - conversion_start_time
        print(f"\nTotal processing time: {total_duration:.3f} seconds")
        
        return result
        
    except Exception as e:
        print(f"Error in SQL conversion: {str(e)}")
        return None

def split_sql_content(sql_content, max_chunk_size=8000):  # 增加块大小以减少请求次数
    """
    Split SQL content into chunks based on statement boundaries
    """
    # Split on GO statements (common in Sybase/SQL Server)
    chunks = []
    current_chunk = []
    current_size = 0
    
    # 首先按GO语句分割
    statements = [stmt.strip() for stmt in sql_content.split('go') if stmt.strip()]
    
    for stmt in statements:
        stmt_size = len(stmt)
        
        # 如果单个语句超过最大块大小，需要进一步分割
        if stmt_size > max_chunk_size:
            # 按存储过程分割
            procs = stmt.split('create proc')
            for proc in procs:
                if not proc.strip():
                    continue
                if len(proc) > max_chunk_size:
                    # 如果存储过程还是太大，按begin/end块分割
                    blocks = proc.split('begin')
                    for block in blocks:
                        if not block.strip():
                            continue
                        chunks.append(f"create proc{block}" if block == proc else f"begin{block}")
                else:
                    chunks.append(f"create proc{proc}")
        else:
            chunks.append(stmt)
    
    return chunks

async def main():
    """Main entry point of the SQL converter"""
    try:
        # Initialize converter
        converter = SQLConverter()
        
        # Load SQL files
        sql_files = load_sql_files(converter.source_path)
        if not sql_files:
            print("No SQL files found to convert")
            return
        
        print(f"\nFound {len(sql_files)} SQL files to convert")
        
        # Process each SQL file
        for source_file, sql_content in sql_files:
            print(f"\nProcessing file: {source_file}")
            
            # Convert SQL content
            converted_sql = await converter.convert_sql(
                sql_content,
                converter.source_db_type,
                converter.target_db_type
            )
            
            if converted_sql:
                # Generate target file path
                target_file = get_target_file_path(source_file, converter.target_config)
                
                # Create target directory if it doesn't exist
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                
                # Write converted SQL to file
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(converted_sql)
                print(f"Converted SQL saved to: {target_file}")
            else:
                print(f"Failed to convert SQL from file: {source_file}")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
