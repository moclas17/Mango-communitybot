from telethon import TelegramClient, events
import sqlite3
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Telegram API credentials
api_id = 29993447  # Make sure this is an integer, not a string
api_hash = '6b0b83610cfaee134223ac7bfc28fd09'
bot_token = '7602848639:AAFtfiK_GN76qZT8l3w7EIWWIDNhc5wG0W0'

async def main():
    try:
        # Initialize Telegram client
        logger.info("Initializing Telegram client...")
        client = TelegramClient('bot_session', int(api_id), api_hash)
        
        # Connect and start the client
        await client.start(bot_token=bot_token)
        logger.info("Bot successfully connected to Telegram!")

        # Database setup
        logger.info("Setting up database...")
        conn = sqlite3.connect('telegram_scores.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_scores 
                         (user_id INTEGER, username TEXT, score INTEGER)''')
        conn.commit()
        logger.info("Database setup complete!")

        @client.on(events.NewMessage)
        async def handle_new_message(event):
            try:
                logger.debug(f"Received message event: {event}")
                
                # Get sender information
                sender = await event.get_sender()
                user_id = sender.id
                username = sender.username or str(user_id)
                message = event.raw_text
                
                # Only process scoring in groups
                if event.is_group:
                    logger.info(f"Processing message: '{message}' from user: {username}")
                    
                    message_score = score_message(message)
                    logger.info(f"Calculated score: {message_score}")

                    if message_score > 0:
                        try:
                            cursor.execute('SELECT score FROM user_scores WHERE user_id = ?', (user_id,))
                            result = cursor.fetchone()

                            if result:
                                new_score = result[0] + message_score
                                cursor.execute('UPDATE user_scores SET score = ? WHERE user_id = ?', 
                                             (new_score, user_id))
                            else:
                                cursor.execute('INSERT INTO user_scores (user_id, username, score) VALUES (?, ?, ?)',
                                             (user_id, username, message_score))

                            conn.commit()
                            logger.info(f"Successfully updated score for user {username}")
                            
                            # Send confirmation message
                            await event.respond(f"Points awarded: {message_score}")
                            
                        except sqlite3.Error as e:
                            logger.error(f"Database error: {e}")
                            
            except Exception as e:
                logger.error(f"Error in message handler: {e}", exc_info=True)

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
                username = sender.username or "Unknown"
                
                # Check individual score
                cursor.execute('SELECT score FROM user_scores WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                user_score = result[0] if result else 0
                
                await event.respond(f"@{username}, your score is: {user_score}")
                
            except Exception as e:
                logger.error(f"Error in score handler: {e}")
                await event.respond("Sorry, there was an error checking your score.")

        # Add leaderboard command
        @client.on(events.NewMessage(pattern='/leaderboard'))
        async def show_leaderboard(event):
            try:
                cursor.execute('SELECT username, score FROM user_scores ORDER BY score DESC LIMIT 5')
                top_users = cursor.fetchall()
                
                if top_users:
                    leaderboard = "🏆 Top 5 Users:\n\n"
                    for i, (username, score) in enumerate(top_users, 1):
                        leaderboard += f"{i}. @{username}: {score} points\n"
                else:
                    leaderboard = "No scores yet!"
                
                await event.respond(leaderboard)
                
            except Exception as e:
                logger.error(f"Error in leaderboard handler: {e}")

        logger.info("Bot is running...")
        await client.run_until_disconnected()

    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)

# Run the bot
if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
