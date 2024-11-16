import requests
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def score_response(response, criteria):
    """Score the response based on multiple criteria and return JSON format"""
    scores = {}
    for criterion, prompt in criteria.items():
        api_response = requests.post(
            url="https://api.red-pill.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('REDPILL_API_KEY')}",
            },
            data=json.dumps({
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "You are a Web3 community analyst. You must ONLY return a JSON object with a single 'score' field containing a number between 0-10. Example: {\"score\": 7}. Do not include any other text or explanation."},
                    {"role": "user", "content": f"{prompt}\n\nMessage to analyze:\n{response}"}
                ],
                "temperature": 0.3  # Lower temperature for more consistent outputs
            })
        )
        try:
            # Parse JSON response to extract score
            score_text = api_response.json()['choices'][0]['message']['content'].strip()
            # If response doesn't start with {, wrap it in proper JSON
            if not score_text.startswith('{'):
                score_text = f'{{"score": {score_text}}}'
            score_data = json.loads(score_text)
            score = float(score_data['score'])
            scores[criterion] = min(max(score, 0), 10)
        except Exception as e:
            print(f"Error parsing score for {criterion}: {e}")
            # Retry once with a more direct prompt
            try:
                retry_response = requests.post(
                    url="https://api.red-pill.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {os.getenv('REDPILL_API_KEY')}",
                    },
                    data=json.dumps({
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": "Return ONLY a number between 0-10."},
                            {"role": "user", "content": f"Rate from 0-10: {prompt}\n\nContent:\n{response}"}
                        ],
                        "temperature": 0.1
                    })
                )
                score_text = retry_response.json()['choices'][0]['message']['content'].strip()
                score = float(score_text)
                scores[criterion] = min(max(score, 0), 10)
            except:
                scores[criterion] = 0
    return scores

# Original conversation setup
system_content = "You are a Web3 expert. Be informative and helpful while explaining blockchain concepts, DeFi, NFTs, and crypto topics."
user_content = "Quién subió cambios al repositorio?"

# Get the main response
response = requests.post(
    url="https://api.red-pill.ai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.getenv('REDPILL_API_KEY')}",
    },
    data=json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]
    })
)

# Debug the response structure
print("API Response:", response.json())

# Extract content from the response - using the correct path
response_content = response.json()['choices'][0]['message']['content']
print("Response:\n", response_content)

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
scores = score_response(response_content, scoring_criteria)

# Print JSON output
print("\nScores JSON:")
print(json.dumps(scores, indent=2))

# Calculate average score
non_zero_scores = [s for s in scores.values() if s > 0]
average_score = sum(non_zero_scores) / len(non_zero_scores) if non_zero_scores else 0

# Add average to scores dictionaryS
scores['average_score'] = round(average_score, 1)

# Print final JSON output
print("\nFinal JSON with average:")
print(json.dumps(scores, indent=2))