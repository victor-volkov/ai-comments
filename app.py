import streamlit as st
import tweepy
import openai
from datetime import datetime, timedelta
import time

# Configure API keys
twitter_bearer_token = st.secrets["AAAAAAAAAAAAAAAAAAAAADRmzAEAAAAAfFwYHNIvEMGkqft0EJugHh3%2BT7s%3Dv9lq8e1VEBfZNdoDsgvGKq2ErPE1qibYtFXbTsAh84tim3beqX"]
twitter_api_key = st.secrets["CaSx2wfSV8mHC4yrxroEliNht"]
twitter_api_secret = st.secrets["CY6b74Cag3k2Q6iEZ4PEvCSkiByCHzvDX2hGtxjxI1d2Qjn1r8"]
twitter_access_token = st.secrets["1872275420386611200-67Yrv49o4CFlSAhCTau4tvMhuCb4OB"]
twitter_access_token_secret = st.secrets["GYmTWhx4ZLKSlUAuYtQbPrEj1S3Obf16utkM7b0Z7DTgp"]
openai_api_key = st.secrets["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"]

# Initialize Twitter client
client = tweepy.Client(
    bearer_token=twitter_bearer_token,
    consumer_key=twitter_api_key,
    consumer_secret=twitter_api_secret,
    access_token=twitter_access_token,
    access_token_secret=twitter_access_token_secret
)

def get_trending_tweets():
    """Get tweets that are receiving high engagement in the last 10 hours"""
    # Calculate time 10 hours ago
    start_time = datetime.utcnow() - timedelta(hours=10)
    
    # Search for tweets with high engagement
    query = "min_faves:1000 -is:retweet lang:en"  # You can adjust the minimum likes
    tweets = client.search_recent_tweets(
        query=query,
        start_time=start_time,
        tweet_fields=['public_metrics', 'created_at', 'text'],
        max_results=10
    )
    
    return tweets.data if tweets.data else []

def generate_comment(tweet_text):
    """Generate a meaningful comment using GPT"""
    openai.api_key = openai_api_key
    
    prompt = f"""
    Generate a thoughtful and engaging comment for the following tweet. 
    The comment should be relevant, respectful, and add value to the conversation.
    
    Tweet: {tweet_text}
    
    Comment:
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates engaging social media comments."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()

def post_comment(tweet_id, comment):
    """Post the generated comment as a reply to the tweet"""
    try:
        response = client.create_tweet(
            text=comment,
            in_reply_to_tweet_id=tweet_id
        )
        return True, "Comment posted successfully!"
    except Exception as e:
        return False, f"Error posting comment: {str(e)}"

# Streamlit interface
def main():
    st.title("Twitter Auto-Commenter")
    
    if st.button("Get Trending Tweets"):
        tweets = get_trending_tweets()
        
        if not tweets:
            st.warning("No trending tweets found.")
            return
            
        for tweet in tweets:
            st.markdown("---")
            st.write(f"**Tweet:** {tweet.text}")
            st.write(f"Likes: {tweet.public_metrics['like_count']}")
            
            if tweet.text.strip():  # Check if tweet has text content
                comment = generate_comment(tweet.text)
                st.write(f"**Generated Comment:** {comment}")
                
                if st.button(f"Post Comment for Tweet {tweet.id}", key=tweet.id):
                    success, message = post_comment(tweet.id, comment)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

if __name__ == "__main__":
    main() 
