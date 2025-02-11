import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import openai
import time
import random
from datetime import datetime

# Configure OpenAI
openai_api_key = st.secrets["OPENAI_API_KEY"]

COMMENT_TONES = {
    "Friendly": "You are a friendly and supportive Twitter user.",
    "Professional": "You are a knowledgeable professional providing insights.",
    "Humorous": "You are a witty Twitter user who adds humor to discussions.",
    "Empathetic": "You are an empathetic person who shows understanding.",
    "Analytical": "You are an analytical thinker who provides thoughtful perspectives."
}

def setup_driver():
    """Setup Chrome driver with necessary options"""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.224 Safari/537.36')

        try:
            # Try using Firefox as an alternative
            from selenium.webdriver.firefox.service import Service as FirefoxService
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from webdriver_manager.firefox import GeckoDriverManager
            
            firefox_options = FirefoxOptions()
            firefox_options.add_argument("--headless")
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")
            
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=firefox_options)
            driver.implicitly_wait(10)
            st.sidebar.success("Using Firefox browser")
            return driver
            
        except Exception as firefox_error:
            st.error(f"Failed to create Firefox driver: {str(firefox_error)}")
            
            try:
                # Try using undetected-chromedriver as last resort
                import undetected_chromedriver as uc
                driver = uc.Chrome(headless=True, options=chrome_options)
                driver.implicitly_wait(10)
                st.sidebar.success("Using undetected Chrome browser")
                return driver
            except Exception as uc_error:
                st.error(f"Failed to create undetected Chrome driver: {str(uc_error)}")
                return None
            
    except Exception as e:
        st.error(f"Failed to setup any browser driver: {str(e)}")
        st.error("Please contact support for assistance.")
        return None

def login_twitter(driver, username, password):
    """Login to Twitter"""
    try:
        # Go to Twitter login page
        driver.get("https://twitter.com/i/flow/login")
        time.sleep(3)  # Wait for page load

        # Enter username
        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
        )
        username_input.send_keys(username)
        username_input.send_keys(Keys.RETURN)
        time.sleep(2)

        # Handle possible security check
        try:
            security_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            st.warning("Security check detected! Please enter your email or phone.")
            security_value = st.text_input("Email/Phone:")
            if security_value:
                security_input.send_keys(security_value)
                security_input.send_keys(Keys.RETURN)
                time.sleep(2)
        except:
            pass  # No security check needed

        # Enter password
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="password"]'))
        )
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        time.sleep(3)

        # Verify login success
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="SideNav_NewTweet_Button"]'))
            )
            return True, "Login successful!"
        except:
            return False, "Login failed. Please check your credentials."

    except Exception as e:
        return False, f"Login error: {str(e)}"

def get_trending_tweets(driver, num_tweets=5):
    """Get trending tweets using Selenium"""
    tweets = []
    try:
        # Go to Twitter explore page with trending tab
        driver.get("https://twitter.com/explore/tabs/trending")
        time.sleep(3)

        # Scroll a few times to load more tweets
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

        # Find tweet elements
        tweet_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[data-testid="tweet"]'))
        )
        
        for element in tweet_elements[:num_tweets]:
            try:
                # Get tweet text
                text = element.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]').text
                
                # Get engagement metrics
                likes = element.find_element(By.CSS_SELECTOR, '[data-testid="like"]').text or "0"
                retweets = element.find_element(By.CSS_SELECTOR, '[data-testid="retweet"]').text or "0"
                
                # Get tweet link and author
                link = element.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]').get_attribute('href')
                author = element.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"]').text.split('\n')[0]
                
                tweets.append({
                    'id': link.split('/')[-1],
                    'text': text,
                    'likes': likes,
                    'retweets': retweets,
                    'link': link,
                    'author': author
                })
                
            except Exception as e:
                st.sidebar.warning(f"Error parsing tweet: {str(e)}")
                continue
                
    except Exception as e:
        st.error(f"Error fetching tweets: {str(e)}")
    
    return tweets

def post_comment(driver, tweet_link, comment):
    """Post comment using Selenium"""
    try:
        if not comment:
            return False, "No comment generated"
            
        # Go to tweet
        driver.get(tweet_link)
        time.sleep(random.uniform(2, 4))
        
        # Find and click reply button
        reply_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="reply"]'))
        )
        driver.execute_script("arguments[0].click();", reply_button)
        time.sleep(1)
        
        # Find and click the reply input field
        reply_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]'))
        )
        driver.execute_script("arguments[0].click();", reply_input)
        
        # Type comment with random delays
        for char in comment:
            reply_input.send_keys(char)
            time.sleep(random.uniform(0.01, 0.08))
        
        time.sleep(1)
        
        # Find and click reply submit button
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="tweetButton"]'))
        )
        driver.execute_script("arguments[0].click();", submit_button)
        
        time.sleep(2)
        return True, "Comment posted successfully!"
        
    except Exception as e:
        st.error(f"Error details: {str(e)}")
        return False, f"Error posting comment: {str(e)}"

def generate_comment(tweet_text, tone="Friendly", custom_instructions=""):
    """Generate a meaningful comment using GPT with customizable tone"""
    try:
        openai.api_key = st.secrets["OPENAI_API_KEY"]
        
        system_message = COMMENT_TONES.get(tone, COMMENT_TONES["Friendly"])
        if custom_instructions:
            system_message += f" Additional instructions: {custom_instructions}"
        
        prompt = f"""
        Generate a short, engaging comment (max 2 sentences) for this tweet.
        Make it sound natural and conversational.
        
        Tweet: {tweet_text}
        
        Rules:
        - Keep it under 240 characters
        - Be positive and constructive
        - Don't use hashtags
        - Sound natural, not corporate
        - Don't repeat the tweet content
        - Match the specified tone: {tone}
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=60,
            temperature=0.7,
            presence_penalty=0.6
        )
        
        comment = response.choices[0].message.content.strip()
        
        if len(comment) > 240:
            comment = comment[:237] + "..."
            
        return comment
        
    except Exception as e:
        st.error(f"Error generating comment: {str(e)}")
        return None

def save_session_cookies():
    """Save session cookies to Streamlit session state"""
    if 'driver' in st.session_state:
        cookies = st.session_state.driver.get_cookies()
        st.session_state.twitter_cookies = cookies

def restore_session_cookies():
    """Restore session cookies to the driver"""
    if 'twitter_cookies' in st.session_state and st.session_state.driver:
        for cookie in st.session_state.twitter_cookies:
            try:
                st.session_state.driver.add_cookie(cookie)
            except Exception as e:
                st.sidebar.warning(f"Failed to restore cookie: {str(e)}")

def main():
    st.title("Twitter Auto-Commenter (Selenium Version)")
    
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'twitter_cookies' not in st.session_state:
        st.session_state.twitter_cookies = None
    
    if 'driver' not in st.session_state:
        driver = setup_driver()
        if driver is None:
            st.error("Could not initialize browser. Please try again later.")
            return
        st.session_state.driver = driver
        if st.session_state.twitter_cookies:
            restore_session_cookies()
    
    # Login section in sidebar
    with st.sidebar:
        st.header("Twitter Login")
        if not st.session_state.logged_in:
            username = st.text_input("Username/Email")
            password = st.text_input("Password", type="password")
            
            if st.button("Login"):
                success, message = login_twitter(st.session_state.driver, username, password)
                if success:
                    st.session_state.logged_in = True
                    save_session_cookies()  # Save cookies after successful login
                    st.success(message)
                else:
                    st.error(message)
        else:
            st.success("Logged in successfully!")
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.twitter_cookies = None
                st.session_state.driver.delete_all_cookies()
                st.experimental_rerun()
    
    # Main content
    if st.session_state.logged_in:
        # Add comment generation options
        st.sidebar.header("Comment Settings")
        selected_tone = st.sidebar.selectbox("Comment Tone", list(COMMENT_TONES.keys()))
        custom_instructions = st.sidebar.text_area("Custom Instructions (Optional)", 
            help="Add any specific instructions for comment generation")
        
        col1, col2 = st.columns(2)
        with col1:
            num_tweets = st.number_input("Number of tweets to fetch", min_value=1, max_value=10, value=5)
        with col2:
            min_likes = st.number_input("Minimum likes", min_value=0, value=100)
        
        if st.button("Get Trending Tweets"):
            with st.spinner("Fetching tweets..."):
                tweets = get_trending_tweets(st.session_state.driver, num_tweets)
                tweets = [t for t in tweets if int(t['likes'].replace('K', '000').replace('.', '')) >= min_likes]
                
                if not tweets:
                    st.warning("No tweets found matching your criteria.")
                    return
                
                for tweet in tweets:
                    st.markdown("---")
                    st.write(f"**Author:** {tweet['author']}")
                    st.write(f"**Tweet:** {tweet['text']}")
                    st.write(f"Likes: {tweet['likes']} | Retweets: {tweet['retweets']}")
                    
                    if tweet['text'].strip():
                        with st.spinner("Generating comment..."):
                            generated_comment = generate_comment(
                                tweet['text'], 
                                tone=selected_tone,
                                custom_instructions=custom_instructions
                            )
                            
                            if generated_comment:
                                # Add comment preview and edit functionality
                                comment_key = f"comment_{tweet['id']}"
                                edited_comment = st.text_area(
                                    "Edit Comment Before Posting:",
                                    value=generated_comment,
                                    key=comment_key,
                                    max_chars=240
                                )
                                
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    if st.button("Regenerate", key=f"regen_{tweet['id']}"):
                                        st.session_state[comment_key] = generate_comment(
                                            tweet['text'],
                                            tone=selected_tone,
                                            custom_instructions=custom_instructions
                                        )
                                        st.experimental_rerun()
                                
                                with col2:
                                    if st.button(f"Post Comment", key=f"post_{tweet['id']}"):
                                        with st.spinner("Posting comment..."):
                                            success, message = post_comment(
                                                st.session_state.driver,
                                                tweet['link'],
                                                edited_comment
                                            )
                                            if success:
                                                st.success(message)
                                            else:
                                                st.error(message)
                                
                                with col3:
                                    st.markdown(f"[View Tweet]({tweet['link']})")
                            else:
                                st.error("Failed to generate comment")
    else:
        st.warning("Please login first to use the tool.")

    # Save session before shutdown
    save_session_cookies()

    # Cleanup on app shutdown
    def cleanup():
        if 'driver' in st.session_state:
            st.session_state.driver.quit()
    
    st.on_script_run_end(cleanup)

if __name__ == "__main__":
    main() 
