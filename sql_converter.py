import os
import json
import glob
import time
import asyncio
from dotenv import load_dotenv
from typing import Dict, List, Optional, Union

class SQLConverter:
    def __init__(self, source_db_type=None, target_db_type=None, provider=None):
        """Initialize the SQL converter with optional configuration"""
        # Load environment variables
        load_dotenv()
        
        # Initialize clients
        self.clients = {}
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-3-haiku-20240307')
        
        # Setup AI providers
        if os.getenv('OPENAI_ENABLED', 'true').lower() == 'true':
            import openai
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.clients['openai'] = openai.OpenAI()
            
        if os.getenv('CLAUDE_ENABLED', 'true').lower() == 'true':
            self.clients['claude'] = anthropic.Anthropic(
                api_key=os.getenv('CLAUDE_API_KEY')
            )
        
        # Set default provider
        self.default_provider = provider or os.getenv('DEFAULT_AI_PROVIDER', 'openai')
        if self.default_provider not in self.clients:
            enabled_providers = list(self.clients.keys())
            if enabled_providers:
                self.default_provider = enabled_providers[0]
                print(f"Warning: Default provider '{self.default_provider}' not available. Using '{enabled_providers[0]}' instead.")
            else:
                raise ValueError("No AI providers are properly configured.")
        
        # Set database types
        self.source_db_type = source_db_type or os.getenv('SOURCE_DB_TYPE', 'SYBASE')
        self.target_db_type = target_db_type or os.getenv('TARGET_DB_TYPE', 'POSTGRESQL')
        
        # Set file paths
        self.source_path = os.getenv('SOURCE_DB_CODE_FILE', './sql_files/*.sql')
        self.target_config = os.getenv('TARGET_DB_CODE_FILE', 'auto')
        
        # Create prompts directory if it doesn't exist
        os.makedirs('prompts', exist_ok=True)

    async def _convert_chunk_openai(self, chunk, system_prompt=None, chunk_index=None):
        """Convert a chunk of SQL using OpenAI"""
        try:
            start_time = time.perf_counter()
            print(f"\n🔄 Processing chunk {chunk_index + 1}...")
            
            response = await asyncio.to_thread(
                self.clients['openai'].chat.completions.create,
                model=self.openai_model,
                temperature=0.7,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": chunk}
                ]
            )
            
            elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds
            if not response or not response.choices:
                print(f"❌ Chunk {chunk_index + 1}: OpenAI returned empty response (took {elapsed_time:.2f}ms)")
                return None
                
            result = response.choices[0].message.content.strip()
            print(f"✅ Chunk {chunk_index + 1} completed in {elapsed_time:.2f}ms")
            print(f"   • Size: {len(chunk):,} → {len(result):,} chars ({(len(result)-len(chunk))/len(chunk)*100:+.1f}%)")
            return result
        except Exception as e:
            elapsed_time = (time.perf_counter() - start_time) * 1000
            print(f"❌ Chunk {chunk_index + 1} failed after {elapsed_time:.2f}ms: {str(e)}")
            return None

    async def _convert_chunk_claude(self, chunk, system_prompt=None, chunk_index=None):
        """Convert a chunk of SQL using Claude"""
        try:
            start_time = time.perf_counter()
            print(f"\n🔄 Processing chunk {chunk_index + 1}...")
            
            message = await asyncio.to_thread(
                self.clients['claude'].messages.create,
                model=self.claude_model,
                max_tokens=4000,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": chunk}]
            )
            
            elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds
            if not message or not message.content:
                print(f"❌ Chunk {chunk_index + 1}: Claude returned empty response (took {elapsed_time:.2f}ms)")
                return None
                
            result = message.content[0].text.strip()
            print(f"✅ Chunk {chunk_index + 1} completed in {elapsed_time:.2f}ms")
            print(f"   • Size: {len(chunk):,} → {len(result):,} chars ({(len(result)-len(chunk))/len(chunk)*100:+.1f}%)")
            return result
        except Exception as e:
            elapsed_time = (time.perf_counter() - start_time) * 1000
            print(f"❌ Chunk {chunk_index + 1} failed after {elapsed_time:.2f}ms: {str(e)}")
            return None

    def _split_sql_into_chunks(self, sql_content, chunk_size=2000):
        """Split SQL content into manageable chunks"""
        if not sql_content:
            return []
            
        # Split by GO statements first
        chunks = []
        current_chunk = []
        current_size = 0
        
        for line in sql_content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # If line is 'GO', add current chunk and start new one
            if line.upper() == 'GO':
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                continue
            
            # Add line to current chunk
            line_size = len(line)
            if current_size + line_size > chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size
        
        # Add final chunk if exists
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    async def _convert_sql_parallel(self, sql_content, system_prompt=None, provider=None):
        """Convert SQL content in parallel"""
        start_time = time.perf_counter()
        
        # If no system_prompt is provided, use the default prompt
        if system_prompt is None:
            try:
                prompt_path = os.path.join('prompts', 'optimized_prompt.txt')
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    system_prompt = f.read().strip()
                system_prompt = system_prompt.format(
                    source_type=self.source_db_type,
                    target_type=self.target_db_type
                )
            except Exception as e:
                print(f"Error loading prompt: {str(e)}")
                system_prompt = f"""
                You are a SQL conversion expert. Convert the provided SQL code from {self.source_db_type} 
                to {self.target_db_type}, maintaining the same functionality while following best practices 
                for the target database system. Preserve comments and formatting where possible.
                """
        
        # Split SQL into chunks
        chunks = self._split_sql_into_chunks(sql_content)
        total_chunks = len(chunks)
        total_chars = sum(len(c) for c in chunks)
        avg_chunk_size = total_chars // total_chunks
        max_chunk_size = max(len(c) for c in chunks)
        
        print(f"\n📊 Starting SQL Conversion:")
        print(f"   • Total chunks: {total_chunks:,}")
        print(f"   • Total size: {total_chars:,} chars")
        print(f"   • Average chunk: {avg_chunk_size:,} chars")
        print(f"   • Largest chunk: {max_chunk_size:,} chars")
        print(f"   • Provider: {provider or self.default_provider}")
        print(f"   • Model: {self._get_model_name(provider or self.default_provider)}")
        
        # Convert chunks in parallel
        tasks = []
        for i, chunk in enumerate(chunks):
            if provider == 'openai' or (provider is None and self.default_provider == 'openai'):
                tasks.append(self._convert_chunk_openai(chunk, system_prompt, i))
            elif provider == 'claude' or (provider is None and self.default_provider == 'claude'):
                tasks.append(self._convert_chunk_claude(chunk, system_prompt, i))
        
        results = await asyncio.gather(*tasks)
        
        # Process results
        total_time = (time.perf_counter() - start_time) * 1000
        successful = len([r for r in results if r])
        converted = [r for r in results if r]
        total_output_chars = sum(len(r) for r in converted) if converted else 0
        
        print(f"\n📈 Conversion Summary:")
        print(f"   • Total time: {total_time:.2f}ms")
        print(f"   • Average time per chunk: {total_time/total_chunks:.2f}ms")
        print(f"   • Successful chunks: {successful:,}/{total_chunks:,}")
        print(f"   • Failed chunks: {total_chunks - successful:,}")
        print(f"   • Input size: {total_chars:,} chars")
        print(f"   • Output size: {total_output_chars:,} chars ({(total_output_chars-total_chars)/total_chars*100:+.1f}%)")
        
        return "\n\nGO\n\n".join(converted) if converted else None

    async def convert_sql(self, sql_content, source_type=None, target_type=None, provider=None):
        """Convert SQL from source database type to target database type"""
        source_type = source_type or self.source_db_type
        target_type = target_type or self.target_db_type
        provider = provider or self.default_provider
        
        if provider not in self.clients:
            raise ValueError(f"Provider {provider} is not configured")
        
        print(f"\nConverting from {source_type} to {target_type} using {provider} ({self._get_model_name(provider)})...\n")
        conversion_start_time = time.time()
        
        # 转换SQL
        converted_sql = await self._convert_sql_parallel(sql_content, None, provider)
        
        # 记录总时间
        total_duration = time.time() - conversion_start_time
        print(f"\nTotal process completed in {total_duration:.2f} seconds")
        
        return converted_sql

    def _get_model_name(self, provider):
        """Get the model name for the specified provider"""
        if provider == 'openai':
            return self.openai_model
        elif provider == 'claude':
            return self.claude_model
        return 'unknown'

    @staticmethod
    def load_sql_files(source_path):
        """
        Load SQL files based on the source path configuration.
        
        Args:
            source_path (str): Path to SQL file(s). Supports:
                - Single file: "./path/to/file.sql"
                - Multiple files: "./file1.sql;./file2.sql;./dir/*.sql"
                - Directory: "./sql_files/" (processes all .sql files recursively)
        
        Returns:
            List[Tuple[str, str]]: List of tuples (file_path, content)
        
        Raises:
            FileNotFoundError: If any specified file is not found
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
        
        # Check for wildcard pattern
        elif '*' in source_path:
            for file_path in glob.glob(source_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    files_content.append((file_path, f.read()))
        
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

def get_target_file_path(source_file, target_config, target_db_type, provider, model_name):
    """
    Generate target file path based on configuration
    Args:
        source_file: Source SQL file path
        target_config: Target configuration ('auto' or specific path)
        target_db_type: Target database type
        provider: AI provider used
        model_name: AI model name used
    """
    if target_config.lower() == 'auto':
        # Get directory and filename without extension
        dir_name = os.path.dirname(source_file)
        base_name = os.path.splitext(os.path.basename(source_file))[0]
        
        # Create new filename with target db type and full model name
        new_name = f"{base_name}_{target_db_type}_{model_name}.sql"
        
        # Combine with directory path
        return os.path.join(dir_name, new_name)
    return target_config

async def main():
    """Main entry point of the SQL converter"""
    try:
        # Initialize converter
        converter = SQLConverter()
        
        # Load SQL files
        sql_files = SQLConverter.load_sql_files(converter.source_path)
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
                target_file = get_target_file_path(
                    source_file,
                    converter.target_config,
                    converter.target_db_type,
                    converter.default_provider,
                    converter._get_model_name(converter.default_provider)
                )
                
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
