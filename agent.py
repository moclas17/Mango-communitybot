import os
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

def score_response(response, criteria):
    """Score the response based on multiple criteria"""
    scores = {}
    for criterion, prompt in criteria.items():
        scoring_completion = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-70B-Instruct",
            messages=[
                {"role": "system", "content": "You are a Web3 community analyst. Your task is to return ONLY a numeric score between 0-10. No explanation needed, just the number."},
                {"role": "user", "content": f"{prompt}\n\nMessage to analyze:\n{response}"}
            ],
            temperature=0.4,
            max_tokens=5,  # Reduced to force concise response
        )
        try:
            # Extract just the numeric score
            score = float(''.join(filter(lambda x: x.isdigit() or x == '.', scoring_completion.choices[0].message.content)))
            scores[criterion] = min(max(score, 0), 10)  # Allow 0 for irrelevant content
        except:
            scores[criterion] = 0
    return scores

# Original conversation setup
system_content = "You are a Web3 expert. Be informative and helpful while explaining blockchain concepts, DeFi, NFTs, and crypto topics."
user_content = "Quién subió cambios al repositorio?"

client = openai.OpenAI(
    api_key=os.getenv('HYPERBOLIC_API_KEY'),
    base_url="https://api.hyperbolic.xyz/v1",
)

# Get the main response
chat_completion = client.chat.completions.create(
    model="meta-llama/Meta-Llama-3.1-70B-Instruct",
    messages=[
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ],
    temperature=0.7,
    max_tokens=1024,
)

response = chat_completion.choices[0].message.content
print("Response:\n", response)

# Define scoring criteria
scoring_criteria = {
    "question_quality": "How interesting or thought-provoking is this question for the Web3 community?",
    "technical_value": "Does this message contain valuable technical information or insights?",
    "link_relevance": "Are there relevant links or references shared that add value?",
    "community_engagement": "How likely is this message to spark meaningful community discussion?",
    "unique_perspective": "Does this message offer a unique or innovative point of view?",
    "market_insight": "Does this message provide valuable market or trend insights?",
    "resource_sharing": "How valuable are the shared resources or tools mentioned?",
    "problem_solving": "Does this message help solve a community member's problem?",
    "knowledge_sharing": "How effectively does this message share knowledge or experience?",
    "credibility": "How credible and well-supported are the claims or statements?"
}

# Get scores
scores = score_response(response, scoring_criteria)

# Print scores
print("\nMessage Analysis:")
print("-" * 40)
for criterion, score in scores.items():
    if score > 0:  # Only show relevant scores
        print(f"{criterion.replace('_', ' ').title()}: {score:.1f}/10")

# Calculate and print average of non-zero scores
non_zero_scores = [s for s in scores.values() if s > 0]
if non_zero_scores:
    average_score = sum(non_zero_scores) / len(non_zero_scores)
    print("-" * 40)
    print(f"Overall Value Score: {average_score:.1f}/10")