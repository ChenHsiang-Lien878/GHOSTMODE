import google.genai as genai
import os

# Set your API key (replace with your actual key or use environment variable)
# You can get a key from https://makersuite.google.com/app/apikey
API_KEY = os.getenv("GOOGLE_API_KEY")  # Recommended: store in environment variable
if not API_KEY:
    # Try to read from a file named 'key.txt' in the same directory as this script
    key_file = os.path.join(os.path.dirname(__file__), 'key.txt')
    if os.path.exists(key_file):
        with open(key_file, 'r') as f:
            API_KEY = f.read().strip()
    else:
        API_KEY = "AIzaSyDG02ethXcbz5UDupi68KwuvdY26vQbN6M"  # Replace with your key or create key.txt

client = genai.Client(api_key=API_KEY)

# Function to generate text using Gemini
def generate_text(prompt, model_name="models/gemini-2.0-flash"):
    """
    Generate text using Google's Gemini API.

    Args:
        prompt (str): The input prompt for generation.
        model_name (str): The model to use (e.g., 'models/gemini-2.0-flash', 'models/gemini-2.5-flash').

    Returns:
        str: The generated text.
    """
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# Example usage
if __name__ == "__main__":
    # List available models
    try:
        models = client.models.list()
        print("Available models:")
        for model in models:
            print(f"- {model.name}")
    except Exception as e:
        print(f"Error listing models: {e}")
    
    prompt = "Explain the benefits of renewable energy in one paragraph."
    result = generate_text(prompt)
    print("Generated Text:")
    print(result)
