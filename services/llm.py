from openai import OpenAI
from typing import List

client = OpenAI(api_key = """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""")

def generate_answer(question: str, code_chunks: List[str]) -> str:
    "Code comments"

    context = ""
    for i, chunk in enumerate(code_chunks, 1):
        context += f"Code Snippet {i}:\n{chunk}\n\n"

    prompt = f"""You are a code assistant. Answer based on this code: {context} 
    Question: {question} 
    Answer: """

    response = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], 
        temperature=0.25, max_completion_tokens=500,
        top_p=0.90
    )

    return response.choices[0].message.content