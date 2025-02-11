import streamlit as st
import tweepy
import openai
from datetime import datetime, timedelta, timezone
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
        # More lenient query
        query = "lang:en -is:retweet"  # Removed minimum likes requirement
        
        tweets = client.search_recent_tweets(
            query=query,
            tweet_fields=['public_metrics', 'created_at', 'text'],
            max_results=2,  # Reduced to minimum
            user_fields=['username', 'name'],
            expansions=['author_id']
        )
        
        # Add monthly tweet counter
        if 'monthly_tweets' not in st.session_state:
            st.session_state.monthly_tweets = 0
        
        if tweets.data:
            st.session_state.monthly_tweets += len(tweets.data)
            # Show usage in sidebar
            st.sidebar.write(f"Monthly Tweet Usage: {st.session_state.monthly_tweets}/1500")
            
            # Debug information
            st.sidebar.write("Latest tweets found:", len(tweets.data))
            for tweet in tweets.data:
                st.sidebar.write(f"Tweet likes: {tweet.public_metrics['like_count']}")
        else:
            st.sidebar.warning("No tweets found with current criteria")
        
        return tweets.data if tweets.data else []
        
    except tweepy.TooManyRequests as e:
        st.error("""
        Twitter API rate limit reached. Basic tier limits:
        - 1,500 tweets/month
        - 1 request/second
        Consider waiting a few minutes or upgrading to Elevated access.
        """)
        # Debug information
        st.sidebar.error(f"Rate limit details: {str(e)}")
        return []
    except tweepy.Unauthorized as e:
        st.error("Authentication error. Please check your Twitter API credentials.")
        st.sidebar.error(f"Auth error details: {str(e)}")
        return []
    except Exception as e:
        st.error(f"Error fetching tweets: {str(e)}")
        st.sidebar.error(f"Full error details: {str(e)}")
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
        user = client.get_me()
        st.sidebar.success(f"Twitter API Connected (User: @{user.data.username})")
        
        # Add rate limit information
        st.sidebar.info("""
        Basic Tier Limits:
        - 1,500 tweets/month total
        - 1 request/second
        - 50 tweets/day for posting
        
        To avoid rate limits:
        1. Wait 1-2 minutes between requests
        2. Use the tool sparingly
        3. Consider applying for Elevated access
        """)
        
    except tweepy.TooManyRequests:
        st.sidebar.error("""
        Rate limited. Basic tier limitations:
        - Wait at least 1 minute between requests
        - Maximum 1,500 tweets per month
        """)
    except tweepy.Unauthorized:
        st.sidebar.error("Authentication failed. Check API credentials.")
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
