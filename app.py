import streamlit as st
import tweepy
import openai
from datetime import datetime, timedelta
import time

# Configure API keys
twitter_bearer_token = st.secrets["TWITTER_BEARER_TOKEN"]
twitter_api_key = st.secrets["TWITTER_API_KEY"]
twitter_api_secret = st.secrets["TWITTER_API_SECRET"]
twitter_access_token = st.secrets["TWITTER_ACCESS_TOKEN"]
twitter_access_token_secret = st.secrets["TWITTER_ACCESS_TOKEN_SECRET"]
openai_api_key = st.secrets["OPENAI_API_KEY"]

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
    try:
        # Calculate time 10 hours ago
        start_time = datetime.utcnow() - timedelta(hours=10)
        
        # Modified search query with more specific parameters
        query = "(min_faves:100 OR min_retweets:50) -is:retweet lang:en"
        
        tweets = client.search_recent_tweets(
            query=query,
            start_time=start_time,
            tweet_fields=['public_metrics', 'created_at', 'text'],
            max_results=10,
            user_fields=['username', 'name'],
            expansions=['author_id']
        )
        
        if not tweets.data:
            return []
            
        return tweets.data
        
    except Exception as e:
        st.error(f"Error fetching tweets: {str(e)}")
        return []

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
    
    # Add debug information
    st.sidebar.write("API Status:")
    try:
        # Test Twitter API connection
        test = client.get_me()
        st.sidebar.success("Twitter API Connected")
    except Exception as e:
        st.sidebar.error(f"Twitter API Error: {str(e)}")
    
    if st.button("Get Trending Tweets"):
        with st.spinner("Fetching tweets..."):
            tweets = get_trending_tweets()
            
            if not tweets:
                st.warning("No trending tweets found. This could be due to API limits or no tweets matching criteria.")
                return
                
            for tweet in tweets:
                st.markdown("---")
                st.write(f"**Tweet:** {tweet.text}")
                if hasattr(tweet, 'public_metrics'):
                    st.write(f"Likes: {tweet.public_metrics['like_count']}")
                
                if tweet.text.strip():  # Check if tweet has text content
                    with st.spinner("Generating comment..."):
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
