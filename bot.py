from telethon import TelegramClient, events, functions, types
import sqlite3
import logging
import os
from dotenv import load_dotenv
import json
import requests

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Update Telegram API credentials
api_id = int(os.getenv('API_ID'))  # Convert to int since env vars are strings
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')

def score_response(message):
    """Score the message using Red Pill AI"""
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
    
    scores = {}
    for criterion, prompt in scoring_criteria.items():
        api_response = requests.post(
            url="https://api.red-pill.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('REDPILL_API_KEY')}",
            },
            data=json.dumps({
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "You are a Web3 community analyst. You must ONLY return a JSON object with a single 'score' field containing a number between 0-10. Example: {\"score\": 7}. Do not include any other text or explanation."},
                    {"role": "user", "content": f"{prompt}\n\nMessage to analyze:\n{message}"}
                ],
                "temperature": 0.3
            })
        )
        try:
            score_text = api_response.json()['choices'][0]['message']['content'].strip()
            if not score_text.startswith('{'):
                score_text = f'{{"score": {score_text}}}'
            score_data = json.loads(score_text)
            score = float(score_data['score'])
            scores[criterion] = min(max(score, 0), 10)
        except Exception as e:
            logger.error(f"Error scoring criterion {criterion}: {e}")
            scores[criterion] = 0
    
    # Calculate average score
    non_zero_scores = [s for s in scores.values() if s > 0]
    average_score = sum(non_zero_scores) / len(non_zero_scores) if non_zero_scores else 0
    scores['average_score'] = round(average_score, 1)
    
    return scores, average_score

async def main():
    try:
        # Initialize Telegram client
        logger.info("Initializing Telegram client...")
        client = TelegramClient('bot_session', int(api_id), api_hash)
        client.parse_mode = 'html'
        await client.start(bot_token=bot_token)
        await client.get_me()
        await client.catch_up()
        
        logger.info("Bot successfully connected to Telegram!")

        # Database setup
        logger.info("Setting up database...")
        conn = sqlite3.connect('telegram_scores.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_scores 
                         (user_id INTEGER, 
                          username TEXT, 
                          group_id INTEGER,
                          group_name TEXT,
                          message TEXT,
                          score_data JSON,
                          average_score FLOAT,
                          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        logger.info("Database setup complete!")

        @client.on(events.NewMessage(func=None))
        async def handle_new_message(event):
            try:
                print("\n=== INCOMING MESSAGE DEBUG ===")
                print(f"Raw text: {event.raw_text}")
                print(f"Message type: {type(event.message)}")
                print(f"Chat type: {type(await event.get_chat())}")
                print(f"Is group: {event.is_group}")
                
                # Get sender and message information
                sender = await event.get_sender()
                user_id = sender.id
                username = sender.username or str(user_id)
                message = event.raw_text
                
                # Skip command messages for scoring
                if message and not message.startswith('/'):  # Only process non-command messages
                    print("\n=== Processing Message ===")
                    logger.info(f"Processing message: '{message}' from user: {username}")
                    
                    # Score the message
                    print("Calling score_response function...")
                    scores, average_score = score_response(message)
                    print("\nScores received:")
                    print(json.dumps(scores, indent=2))
                    print(f"Average score: {average_score}")
                    
                    if average_score > 0:
                        # Store in database and respond
                        cursor.execute('''INSERT INTO user_scores 
                                        (user_id, username, group_id, group_name, message, score_data, average_score) 
                                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                     (user_id, username, event.chat_id, 
                                      (await event.get_chat()).title if event.is_group else "Private",
                                      message, json.dumps(scores), average_score))
                        conn.commit()
                        await event.respond(f"Message scored: {average_score}/10")
                        
            except Exception as e:
                print(f"ERROR in message handler: {str(e)}")
                logger.error(f"Error in message handler: {e}", exc_info=True)

        # Add a debug command to check database contents
        @client.on(events.NewMessage(pattern='/debug'))
        async def debug_database(event):
            try:
                print("\n=== Database Debug ===")
                cursor.execute('SELECT COUNT(*) FROM user_scores')
                count = cursor.fetchone()[0]
                print(f"Total records in database: {count}")
                
                cursor.execute('SELECT * FROM user_scores ORDER BY timestamp DESC LIMIT 5')
                recent_records = cursor.fetchall()
                
                response = f"Database Status:\nTotal records: {count}\n\nRecent entries:"
                for record in recent_records:
                    response += f"\n\nUser: @{record[1]}"
                    response += f"\nMessage: {record[4][:50]}..."
                    response += f"\nScore: {record[6]}/10"
                    response += f"\nTimestamp: {record[7]}"
                
                await event.respond(response)
                
            except Exception as e:
                print(f"Debug error: {e}")
                await event.respond(f"Debug error: {e}")

        @client.on(events.NewMessage(pattern='/ping'))
        async def ping(event):
            try:
                await event.reply('Pong!')  # Using reply instead of respond
                logger.info("Responded to ping command")
            except Exception as e:
                logger.error(f"Error in ping handler: {e}")

        # Add score checking command
        @client.on(events.NewMessage(pattern='/score'))
        async def check_score(event):
            try:
                # Get sender information from the message
                sender = await event.get_sender()
                user_id = sender.id
                username = sender.username or str(user_id)
                
                # Query the database for user's average scores
                cursor.execute('''
                    SELECT AVG(average_score) as avg_score, 
                           COUNT(*) as message_count 
                    FROM user_scores 
                    WHERE user_id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                
                if result and result[0] is not None:  # Check if user has any scores
                    avg_score = round(result[0], 2)
                    message_count = result[1]
                    await event.respond(f"@{username}'s stats:\nAverage Score: {avg_score}/10\nMessages Scored: {message_count}")
                else:
                    await event.respond(f"@{username}, you don't have any scored messages yet!")
                    
            except Exception as e:
                logger.error(f"Error in score handler: {e}")
                await event.respond("Sorry, there was an error checking your score.")

        # Add leaderboard command
        @client.on(events.NewMessage(pattern='/leaderboard'))
        async def show_leaderboard(event):
            try:
                # Get overall top contributors
                cursor.execute('''
                    SELECT 
                        username,
                        AVG(average_score) as avg_score,
                        COUNT(*) as message_count,
                        MAX(average_score) as best_score
                    FROM user_scores 
                    GROUP BY username
                    HAVING message_count >= 3  -- Minimum 3 messages to qualify
                    ORDER BY avg_score DESC 
                    LIMIT 5
                ''')
                
                top_users = cursor.fetchall()
                
                if top_users:
                    leaderboard = "🏆 Community Leaderboard\n\n"
                    leaderboard += "Top Contributors:\n"
                    for i, (username, avg_score, msg_count, best_score) in enumerate(top_users, 1):
                        avg_score = round(float(avg_score), 2)
                        best_score = round(float(best_score), 2)
                        leaderboard += f"{i}. @{username}\n"
                        leaderboard += f"   📊 Avg: {avg_score}/10\n"
                        leaderboard += f"   💬 Messages: {msg_count}\n"
                        leaderboard += f"   ⭐ Best: {best_score}/10\n\n"
                    
                    # Get today's top score
                    cursor.execute('''
                        SELECT username, average_score
                        FROM user_scores 
                        WHERE date(timestamp) = date('now')
                        ORDER BY average_score DESC 
                        LIMIT 1
                    ''')
                    
                    today_top = cursor.fetchone()
                    if today_top:
                        username, score = today_top
                        leaderboard += f"\n🌟 Today's Best: @{username} ({round(float(score), 2)}/10)"
                else:
                    leaderboard = "No scores yet! Be the first to contribute! 🚀"
                
                await event.respond(leaderboard)
                
            except Exception as e:
                logger.error(f"Error in leaderboard handler: {e}")
                await event.respond("Sorry, there was an error fetching the leaderboard.")

        logger.info("Bot is running...")
        await client.run_until_disconnected()

    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)

# Run the bot
if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
