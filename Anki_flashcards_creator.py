# import required packages
import google.generativeai as genai
import os
#import fitz
#from weasyport import HTML
import newspaper

# Initialize gemini API with your key
gemini_api_key = os.environ.get("GEMINI_API_KEY")
if gemini_api_key is None:
    raise ValueError("GEMINI_API_KEY environment variable not set")
genai.configure(api_key=gemini_api_key)

def model_picker():
    # Define the model to use
    model_choice = input(
        "Enter the number of the model you want to use:\n"
        "1. Gemini 1.5 Flash\n"
        "2. Gemini 1.5 Flash-8B\n"
        "3. Gemini 1.5 Pro\n"
        "4. Gemini 1.0 Pro\n"
        "5. Text Embedding 004\n"
    )

    if int(model_choice) == 1:
        system_instruction = [
            "You are a quiz generator. Return Question;Answer pairs, with cloze deletions as {{c1::deletion}}. Focus on factual recall and simple reasoning. Keep questions concise."
        ]
        model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_instruction)
        model_max_tokens = 1000000 # Maximum number of tokens per minute
        # 15 requests per minute
        # 1500 requests per day
    elif int(model_choice) == 2:
        system_instruction = [
            "You are a quiz generator. Return Question;Answer pairs, with cloze deletions as {{c1::deletion}}. You can handle slightly more complex reasoning and factual recall than the smaller flash model. Keep questions relatively concise."
        ]
        model = genai.GenerativeModel("gemini-1.5-flash-8b", system_instruction=system_instruction)
        model_max_tokens = 1000000 # Maximum number of tokens per minute
        # 15 requests per minute
        # 1500 requests per day
    elif int(model_choice) == 3:
        system_instruction = [
            "You are a quiz generator. Return Question;Answer pairs, with cloze deletions as {{c1::deletion}}. You can handle complex reasoning, nuanced factual recall, and generate longer, more detailed questions if needed. Prioritize clarity and accuracy."
        ]

        # I am working on the system_intruction prompt. I will use this model for the time being.

        system_instruction = [
            "You are a quiz generator. Return Question;Answer pairs, each on a new line. Use a semicolon (;) to separate the question and answer. Use cloze deletions in the answer as {{c1::deletion}}. Ensure each anwer/question pair does not exceed 1 line. Use html formatting for code snippets. Example format:\nQuestion: What is X?;Answer: X is {{c1::Y}}\nQuestion: How does A work?;Answer: A works by B"
        ]
        model = genai.GenerativeModel("gemini-1.5-pro", system_instruction=system_instruction)
        model_max_tokens = 32000 # Maximum number of tokens per minute
        # 2 requests per minute
        # 50 requests per day
    elif int(model_choice) == 4:
        system_instruction = [
            "You are a quiz generator. Return Question;Answer pairs, with cloze deletions as {{c1::deletion}}. Focus on factual recall and straightforward reasoning. Keep questions concise and similar in complexity to the flash models."
        ]
        model = genai.GenerativeModel("gemini-1.0-pro", system_instruction=system_instruction)
        model_max_tokens = 32000 # Maximum number of tokens per minute
        # 15 requests per minute
        # 1500 requests per day
    elif int(model_choice) == 5:
        system_instruction = [
            "You are a quiz generator. Although you are primarily an embedding model, attempt to return Question;Answer pairs with cloze deletions as {{c1::deletion}}. Due to your limitations, focus on very simple factual questions where the answer is likely to be a single, well-known entity or concept. Expect limited performance."
        ]
        model = genai.GenerativeModel("text-embedding-004", system_instruction=system_instruction)
        # 1,500 requests per minute
    return model, model_max_tokens, system_instruction

# Define the root directory of the project

ROOT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

# Read and chunk PDF
def read_and_chunk_pdf(pdf_path, max_chunk_size):
    doc = fitz.open(pdf_path)
    chunks = []
    for page in doc:
        blocks = page.get_text("blocks")
        current_chunk = ""
        for block in blocks:
            text = block[4]  # Text content of the block
            if len(current_chunk) + len(text) <= max_chunk_size:
                current_chunk += text
            else:
                chunks.append(current_chunk)
                current_chunk = text
        if current_chunk:  # Add any remaining text
            chunks.append(current_chunk)
    return chunks

# Read and chunk PDF
def chunk_text(text, max_chunk_size):
    chunks = []
    current_chunk = ""
    for block in text:
        if len(current_chunk) + len(block) <= max_chunk_size:
            current_chunk += block
        else:
            chunks.append(current_chunk)
            current_chunk = block
    if current_chunk:  # Add any remaining text
        chunks.append(current_chunk)
    return chunks

# Realised that chunking is probably note necessary since we are using docs as the input right now

def url_to_pdf(url):
    # Convert the URL to a PDF
    pdf_path = url.split("/").join(".") + ".pdf"
    HTML(url).write_pdf(pdf_path)
    return pdf_path

def url_to_text(url):
    # Convert the URL to text
    article = newspaper.Article(url)
    article.download()
    article.parse()
    return article.text

def estimate_gemini_tokens(text, system_instruction="", expected_output_chars=0, chars_per_token=3.2, safety_margin=5): # chars_per_token is the calibration value
    input_tokens = int(len(text) / chars_per_token)
    system_instruction_tokens = int(len(system_instruction) / chars_per_token)
    output_tokens = int(expected_output_chars / chars_per_token)
    total_tokens = input_tokens + system_instruction_tokens + output_tokens + safety_margin
    return total_tokens

# Create Anki cards
def create_anki_cards(url, model, model_max_tokens, system_instruction):
    text = url_to_text(url)
    # Estimate the number of tokens needed
    total_tokens = estimate_gemini_tokens(text, system_instruction=system_instruction, expected_output_chars=len(text)*0.1)
    generated_flashcards = ' '

    if total_tokens > model_max_tokens:
        # Split the text into chunks
        chunks = chunk_text(text, model_max_tokens)
        for chunk in chunks:
            response = model.generate_content(chunk)
            generated_flashcards += response.text
    else:
        response = model.generate_content(text)
        generated_flashcards = response.text
    response = model.generate_content(text)
    # # Save the cards to a text file
    file_suffix = url.split("//")[-1]
    file_name = ".".join(file_suffix.split("/")) + ".flashcards.txt"
    with open(file_name, "w") as f:
        fields = ",".join(file_suffix.split("/")[2:])
        generated_flashcards = "\n".join([line + ";" + fields for line in generated_flashcards.split("\n")])
        f.write(generated_flashcards + ";" + fields)


# Main script execution
if __name__ == "__main__":
    # Need to add a time-based token counter...
    create_anki_cards("https://docs.djangoproject.com/en/5.1/intro/tutorial01/", *model_picker())





