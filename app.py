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
        # Fix deprecated datetime.utcnow() usage
        start_time = datetime.now(datetime.UTC) - timedelta(hours=10)
        
        # Add rate limit handling
        try:
            # Check rate limit status
            limits = client.get_recent_tweets_count("test")  # Light API call to check status
        except tweepy.TooManyRequests as e:
            wait_time = int(e.response.headers.get('x-rate-limit-reset', 900))  # Default to 15 mins
            st.warning(f"Rate limited. Please try again in {wait_time} seconds.")
            return []
            
        # Modified search query to be even less demanding
        query = "(min_faves:10 OR min_retweets:5) -is:retweet lang:en"
        
        tweets = client.search_recent_tweets(
            query=query,
            start_time=start_time,
            tweet_fields=['public_metrics', 'created_at', 'text'],
            max_results=5,  # Reduced from 10 to help with rate limits
            user_fields=['username', 'name'],
            expansions=['author_id']
        )
        
        if not tweets.data:
            return []
            
        return tweets.data
        
    except tweepy.TooManyRequests as e:
        st.error("Twitter API rate limit reached. Please try again later.")
        return []
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
        # Test Twitter API connection with rate limit info
        test = client.get_me()
        st.sidebar.success("Twitter API Connected")
        
        # Add rate limit information
        st.sidebar.info("""
        Twitter API Rate Limits:
        - Search tweets: 180 requests/15-min window
        - Post tweets: 50 tweets/24 hours
        """)
        
    except tweepy.TooManyRequests:
        st.sidebar.error("Rate limited. Please wait a few minutes.")
    except Exception as e:
        st.sidebar.error(f"Twitter API Error: {str(e)}")
    
    # Add a delay between requests button
    if 'last_request_time' not in st.session_state:
        st.session_state.last_request_time = 0
        
    current_time = time.time()
    time_since_last_request = current_time - st.session_state.last_request_time
    
    if time_since_last_request < 60:  # 1 minute cooldown
        st.warning(f"Please wait {60 - int(time_since_last_request)} seconds before making another request")
        st.button("Get Trending Tweets", disabled=True)
    else:
        if st.button("Get Trending Tweets"):
            st.session_state.last_request_time = current_time
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
