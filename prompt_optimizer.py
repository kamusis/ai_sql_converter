import openai
import os
from dotenv import load_dotenv

class PromptOptimizer:
    def __init__(self):
        """Initialize the PromptOptimizer"""
        # Load environment variables
        load_dotenv()
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo-16k')

    def optimize_prompt(self, original_prompt):
        """
        Optimize the given prompt using OpenAI's GPT model to make it more professional and effective.
        The function will automatically detect and respond in the same language as the input.
        """
        meta_prompt = f"""Please help improve and optimize the following prompt to make it more professional, 
        clear, and effective. The optimized prompt should:
        1. Maintain the original intent and language (respond in the same language as the input prompt)
        2. Be more specific and detailed
        3. Use professional terminology appropriate for that language
        4. Have better structure and organization
        5. Include necessary context or constraints

        Original prompt:
        {original_prompt}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional prompt engineer. Always respond in the same language as the user's input."},
                    {"role": "user", "content": meta_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error occurred: {str(e)}"

    def load_original_prompt(self):
        """Load the original prompt template"""
        prompt_path = os.path.join('prompts', 'original_prompt.prompt')
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def load_optimized_prompt(self):
        """Load the optimized prompt if it exists"""
        prompt_path = os.path.join('prompts', 'optimized_prompt.prompt')
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def save_optimized_prompt(self, prompt):
        """Save the optimized prompt to a file"""
        prompt_path = os.path.join('prompts', 'optimized_prompt.prompt')
        os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(prompt)

def main():
    optimizer = PromptOptimizer()
    print("Welcome to Prompt Optimizer! / 欢迎使用提示优化器！")
    print("Enter your prompt (press Enter twice to finish):")
    print("输入您的提示（按两次回车键结束）：")
    
    # Collect multi-line input
    lines = []
    while True:
        line = input()
        if line:
            lines.append(line)
        elif lines:  # Empty line and we have content
            break
    
    original_prompt = '\n'.join(lines)
    
    if not original_prompt:
        print("No prompt provided. Exiting... / 未提供提示，正在退出...")
        return
    
    print("\nOptimizing your prompt... / 正在优化您的提示...\n")
    optimized_prompt = optimizer.optimize_prompt(original_prompt)
    print("-" * 50)
    print(optimized_prompt)
    print("-" * 50)

if __name__ == "__main__":
    main()
