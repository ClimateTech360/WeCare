import streamlit as st
import sqlite3
import bcrypt
import os
from datetime import datetime
from PIL import Image
import openai

# --- SET OPENAI API KEY ---
# Ensure you have your OpenAI API key in Streamlit secrets.toml
# Example secrets.toml:
# [openai]
# api_key = "YOUR_OPENAI_API_KEY"
try:
    openai.api_key = st.secrets["openai"]["api_key"]
except KeyError:
    st.error("OpenAI API key not found in Streamlit secrets.toml. Please add it.")
    st.stop()  # Stop execution if API key is not found

# --- 1. Database Utilities ---


def connect_db():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect("wecare.db", check_same_thread=False)


def create_tables():
    """Creates necessary tables if they don't exist."""
    conn = connect_db()
    c = conn.cursor()

    # Users table for authentication
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    """)
    # Posts table for the forum
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            anonymous INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    # Comments table for the forum
    c.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user_id INTEGER,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(post_id) REFERENCES posts(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    # Volunteers table for the directory
    c.execute("""
        CREATE TABLE IF NOT EXISTS volunteers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            bio TEXT,
            image_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def add_user(username, hashed_password):
    """Adds a new user to the database."""
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
              (username, hashed_password))
    conn.commit()
    conn.close()


def get_user(username):
    """Retrieves a user by username from the database."""
    conn = connect_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, username, password, role FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user


def add_post(user_id, content, anonymous):
    """Adds a new forum post to the database."""
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT INTO posts (user_id, content, anonymous) VALUES (?, ?, ?)",
              (user_id, content, anonymous))
    conn.commit()
    conn.close()


def get_all_posts():
    """Retrieves all forum posts, ordered by recency."""
    conn = connect_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, user_id, content, timestamp, anonymous FROM posts ORDER BY timestamp DESC")
    posts = c.fetchall()
    conn.close()
    return posts


def get_username_by_id(user_id):
    """Retrieves a username given their ID."""
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "Unknown"


def add_comment(post_id, user_id, content):
    """Adds a new comment to a specific post."""
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
              (post_id, user_id, content))
    conn.commit()
    conn.close()


def get_comments(post_id):
    """Retrieves all comments for a specific post."""
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT user_id, content, timestamp FROM comments WHERE post_id = ? ORDER BY timestamp ASC", (post_id,))
    comments = c.fetchall()
    conn.close()
    return comments


def add_volunteer(name, role, bio, image_path):
    """Adds a new volunteer to the database."""
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT INTO volunteers (name, role, bio, image_path) VALUES (?, ?, ?, ?)",
              (name, role, bio, image_path))
    conn.commit()
    conn.close()


def get_volunteers():
    """Retrieves all registered volunteers."""
    conn = connect_db()
    c = conn.cursor()
    c.execute(
        "SELECT name, role, bio, image_path, timestamp FROM volunteers ORDER BY timestamp DESC")
    volunteers = c.fetchall()
    conn.close()
    return volunteers

# --- 2. Utility Functions ---


def hash_password(password):
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password, hashed):
    """Checks a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


# Forbidden words for content moderation
FORBIDDEN_WORDS = ["hate", "violence", "kill", "drugs", "slur", "explicit",
                   "harm myself", "harm others", "suicide", "murder", "rape", "sex act", "child abuse"]


def moderate_content(text):
    """Checks if text contains any forbidden words."""
    text_lower = text.lower()
    return any(word in text_lower for word in FORBIDDEN_WORDS)


# --- AI CHAT FUNCTIONS ---
DISTRESS_KEYWORDS = [
    "end it", "kill myself", "can't cope", "suicidal", "self harm",
    "overdose", "overdosed", "harm myself", "harm others",
    "want to die", "hopeless", "worthless", "no point"
]

# Emergency response message (generalized for open platform)
EMERGENCY_RESPONSE = (
    "🚨 It sounds like you might be in serious distress. Please know you're not alone. "
    "Here are some emergency contacts and steps you can take immediately:\n\n"
    "- **Kenya Red Cross Mental Health Hotline:** 1199 (24/7)\n"
    "- **Befrienders Kenya:** +254 722 178177 (7 AM - 7 PM)\n"
    "- **EMKF Suicide Prevention & Crisis Helpline:** 0800 723 253\n"
    "- Or dial your **local emergency services (e.g., 999 or 112 in Kenya)**.\n\n"
    "**Please reach out to a professional or trusted person right away. You deserve support.**\n\n"
    "_I’m an AI and cannot provide medical diagnosis or crisis intervention. Please seek immediate human professional help._"
)


def detect_distress_ai(message):
    """Checks if a message contains any distress keywords."""
    message = message.lower()
    return any(keyword in message for keyword in DISTRESS_KEYWORDS)


def generate_ai_response(user_input):
    """Generates an AI response based on user input using OpenAI's GPT model."""
    if detect_distress_ai(user_input):
        return EMERGENCY_RESPONSE

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Or "gpt-3.5-turbo" for lower cost/faster response
            messages=[
                {"role": "system", "content": "You are a friendly, empathetic, and supportive mental health assistant. Provide general advice and encourage users to seek professional help when appropriate. Do not provide medical diagnoses or replace professional therapy."},
                {"role": "user", "content": user_input}
            ],
            max_tokens=300,
            temperature=0.7
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        return f"⚠️ I'm sorry, I'm having trouble connecting right now. Please try again later. Error: {str(e)}"

# --- 3. Page Functions ---

# --- Login & Registration Page ---


def login_page():
    """Handles user login and registration."""
    st.title("Welcome to WeCare 🌱")
    st.markdown("Your Digital Sanctuary for Mental Well-being.")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login to your account")
        username = st.text_input("Username", key="login_username")
        password = st.text_input(
            "Password", type="password", key="login_password")
        if st.button("Login", key="login_button"):
            user = get_user(username)
            if user and check_password(password, user[2]):
                st.session_state.logged_in = True
                st.session_state.username = user[1]
                st.session_state.user_id = user[0]
                st.session_state.user_role = user[3]
                st.success(f"Login successful! Welcome, {user[1]}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab2:
        st.subheader("Create a new account")
        new_user = st.text_input("Choose a Username", key="register_username")
        new_password = st.text_input(
            "Choose a Password", type="password", key="register_password")
        confirm_password = st.text_input(
            "Confirm Password", type="password", key="register_confirm_password")

        if st.button("Register", key="register_button"):
            if not new_user or not new_password or not confirm_password:
                st.warning("Please fill in all fields.")
            elif len(new_user) < 3:
                st.warning("Username must be at least 3 characters long.")
            elif len(new_password) < 6:
                st.warning("Password must be at least 6 characters long.")
            elif new_password != confirm_password:
                st.warning("Passwords do not match.")
            else:
                try:
                    add_user(new_user, hash_password(new_password))
                    st.success("Registration successful! You can now log in.")
                except sqlite3.IntegrityError:
                    st.error(
                        "Username already exists. Please choose a different one.")
                except Exception as e:
                    st.error(f"An error occurred during registration: {e}")

# --- AI Helper Chatbot Page ---


def ai_helper_page():
    """Renders the AI Helper chatbot interface."""
    st.title("🤖 AI Mental Health Assistant")
    st.write("This is a safe, non-judgmental space. You can share how you're feeling.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("How are you feeling today?")
    if user_input:
        st.session_state.chat_history.append(
            {"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        ai_response = generate_ai_response(user_input)
        st.session_state.chat_history.append(
            {"role": "assistant", "content": ai_response})
        with st.chat_message("assistant"):
            st.markdown(ai_response)

# --- Peer Support Forum Page ---


def forum_page():
    """Renders the Peer Support Forum interface."""
    st.title("🫂 Peer Support Forum")
    st.markdown(
        "Share your thoughts, struggles, or recovery journey. You're not alone.")

    # Post form
    st.subheader("📝 Create a New Post")
    with st.form("post_form"):
        content = st.text_area("What's on your mind?")
        anonymous = st.checkbox("Post anonymously?", value=False)
        submit = st.form_submit_button("Post")  # No 'key' here

        if submit:
            if not content.strip():
                st.warning("Post content can't be empty.")
            elif moderate_content(content):
                st.warning(
                    "Your post contains flagged words. Please revise it.")
            else:
                add_post(st.session_state.user_id, content, int(anonymous))
                st.success("Post submitted!")
                st.rerun()

    st.divider()
    st.subheader("📋 Recent Posts")

    posts = get_all_posts()
    if not posts:
        st.info("No posts yet. Be the first to share!")
    else:
        for post in posts:
            post_id, user_id, content, timestamp, is_anon = post
            author = "Anonymous" if is_anon else get_username_by_id(user_id)

            with st.expander(f"**{author}** • {datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').strftime('%b %d, %Y %I:%M %p')}"):
                st.markdown(content)

                # Show comments
                comments = get_comments(post_id)
                if comments:
                    st.markdown("---")
                    st.markdown("**💬 Comments:**")
                    for c in comments:
                        comment_user = get_username_by_id(c[0])
                        st.markdown(
                            f"- **{comment_user}**: {c[1]}  _(at {datetime.strptime(c[2], '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p')})_")

                # Add comment form
                # The 'key' for st.form is necessary when in a loop
                with st.form(f"comment_form_{post_id}", clear_on_submit=True):
                    # The 'key' for st.text_area is necessary when in a loop
                    comment_input = st.text_area(
                        "Add a comment", key=f"ci_{post_id}", height=70)
                    # The 'key' for st.form_submit_button is NOT needed here in modern Streamlit
                    # as the form's key handles it implicitly.
                    submit_comment = st.form_submit_button("Submit Comment")
                    if submit_comment:
                        if not comment_input.strip():
                            st.warning("Comment can't be empty.")
                        elif moderate_content(comment_input):
                            st.warning(
                                "Comment contains flagged content. Please revise.")
                        else:
                            add_comment(
                                post_id, st.session_state.user_id, comment_input)
                            st.success("Comment added!")
                            st.rerun()

# --- Educational Hub Page ---


def educational_hub_page():
    """Renders the Educational Hub interface."""
    st.title("📚 Mental Wellness Learning Hub")
    st.markdown(
        "Explore self-care techniques, mental health insights, and professional resources.")

    # Section 1: Self-Care Tips
    st.subheader("🧘 Self-Care Tips")
    st.markdown("""
    - **Breathe deeply** for 2 minutes when feeling overwhelmed.
    - **Take breaks** — 5-minute walks every hour help refresh your mind.
    - **Sleep matters**: Aim for 7–9 hours per night.
    - **Journaling**: Write down your emotions to gain clarity.
    - **Mindful Eating**: Pay attention to your food and how it makes you feel.
    """)

    # Section 2: Mental Health Articles
    st.subheader("📖 Featured Articles")
    with st.expander("📌 Understanding Anxiety"):
        st.markdown("""
        Anxiety is a natural response to stress, but excessive worry can disrupt daily life.
        Learn to recognize symptoms like racing thoughts, restlessness, and tension.
        Practice grounding techniques and seek help when needed.

        🔗 [Read More from Mayo Clinic](https://www.mayoclinic.org/diseases-conditions/anxiety/symptoms-causes/syc-20350961)
        """)
    with st.expander("📌 Depression: What You Should Know"):
        st.markdown("""
        Depression is more than sadness — it affects sleep, appetite, and motivation.
        Early support can prevent worsening. Talking to someone and seeking help is brave.

        🔗 [More from WHO](https://www.who.int/news-room/fact-sheets/detail/depression)
        """)
    with st.expander("📌 Stress Management Strategies"):
        st.markdown("""
        Not all stress is bad. But chronic stress can weaken your immune system.
        Tips include deep breathing, stretching, reducing caffeine, and healthy boundaries.

        📘 Try this quick exercise: *Name 3 things you can see, hear, and feel right now.*

        🔗 [Stress Coping Tools - APA](https://www.apa.org/topics/stress)
        """)
    st.markdown("---")
    st.info("💡 **AI Tip:** In the future, this section could recommend articles based on your interactions with the AI Helper or forum!")

    # Section 3: External Resources
    st.subheader("🌐 Trusted Mental Health Resources")
    st.markdown("""
    - [Mental Health Foundation (UK)](https://www.mentalhealth.org.uk/)
    - [Mind.org.uk](https://www.mind.org.uk/)
    - [WHO Mental Health](https://www.who.int/mental_health/en/)
    - [Psychology Today (Find a Therapist)](https://www.psychologytoday.com/us/therapists)
    """)

    # Optional PDF Resource (ensure 'resources/self-care-guide.pdf' exists)
    # Ensure 'resources' directory exists and self-care-guide.pdf is placed there.
    # To run this part, create a folder named 'resources' in the same directory as your app.py
    # and place your PDF file named 'self-care-guide.pdf' inside it.
    resources_dir = "resources"
    pdf_path = os.path.join(resources_dir, "self-care-guide.pdf")

    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as file:
            st.download_button(label="Download Self-Care Guide (PDF)", data=file,
                               file_name="self-care-guide.pdf", mime="application/pdf")
    else:
        st.warning(
            f"Self-Care Guide PDF not found at '{pdf_path}'. Please create a '{resources_dir}' folder and place 'self-care-guide.pdf' inside it to enable download.")

# --- Professional Volunteer Directory Page ---


def volunteers_page():
    """Renders the professional volunteer directory with registration."""
    st.title("🤝 Professional Volunteers Directory")
    st.markdown(
        "Connect with mental health professionals who have registered to offer support. You can add new volunteers here.")

    # Volunteer Registration Form
    st.subheader("➕ Register a New Volunteer")
    with st.form("volunteer_registration_form", clear_on_submit=True):
        name = st.text_input("Full Name of Volunteer")
        role = st.text_input(
            "Role/Expertise (e.g., Clinical Psychologist, Addiction Counsellor)")
        bio = st.text_area("Brief Biography/Specialization")
        image_file = st.file_uploader(
            "Upload Profile Image (JPG, JPEG, PNG)", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button(
            "Register Volunteer")  # No 'key' here

        if submitted:
            if not name or not role or not bio:
                st.warning("Please fill in all text fields.")
            elif not image_file:
                st.warning("Please upload a profile image.")
            else:
                try:
                    # Create directory if it doesn't exist
                    os.makedirs("volunteer_images", exist_ok=True)
                    # Save image
                    img_path = os.path.join(
                        "volunteer_images", image_file.name)
                    with open(img_path, "wb") as f:
                        f.write(image_file.getbuffer())

                    add_volunteer(name, role, bio, img_path)
                    st.success(f"Volunteer '{name}' registered successfully!")
                    st.rerun()  # Rerun to display the new volunteer
                except Exception as e:
                    st.error(f"Error registering volunteer: {e}")

    st.divider()
    st.subheader("👥 Registered Volunteers")

    volunteers = get_volunteers()
    if not volunteers:
        st.info("No volunteers registered yet. Be the first to add one!")
    else:
        for name, role, bio, img_path, timestamp in volunteers:
            st.markdown("---")
            col1, col2 = st.columns([1, 3])
            with col1:
                if os.path.exists(img_path):
                    st.image(img_path, width=100, caption=name)
                else:
                    st.image("https://via.placeholder.com/100/ADD8E6/000000?text=NO+IMAGE",
                             caption=f"{name} (Image Missing)", width=100)
            with col2:
                st.markdown(f"**{name}** — *{role}*")
                st.markdown(bio)
                st.caption(
                    f"Joined: {datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').strftime('%b %d, %Y at %I:%M %p')}")
                # The 'key' argument for st.button is still fine outside of st.form_submit_button within a form
                st.button(
                    f"Contact {name}", key=f"contact_{name}_{datetime.now().timestamp()}")
                st.write("")  # Add a bit of space

    st.markdown("---")
    st.info("⚠️ **Disclaimer:** This directory is for informational purposes. WeCare facilitates connections but does not directly endorse or verify individual credentials. Always conduct your own due diligence and seek independent professional advice.")

# --- Main Application Logic ---


def homepage():
    """A simple welcome page after login."""
    st.title("🏡 Home: Your Sanctuary")
    st.markdown(
        f"Welcome, **{st.session_state.username}**! WeCare is here to support your mental well-being and addiction recovery journey.")
    st.markdown("""
    This platform offers a safe and non-judgmental space to connect, learn, and grow.
    Use the menu on the left to navigate:
    - **🤖 AI Helper:** Chat with our empathetic AI for immediate support and guidance.
    - **🫂 Peer Support Forum:** Share your experiences and connect with others.
    - **📚 Educational Hub:** Explore articles, videos, and resources to empower yourself.
    - **🤝 Volunteers Directory:** Connect with professional volunteers.
    """)
    st.info("Remember, you are not alone. Take a moment to breathe, and explore the resources available to you.")


def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(page_title="WeCare: Digital Sanctuary",
                       layout="wide", initial_sidebar_state="expanded")

    # Ensure tables are created on app start
    create_tables()

    # Initialize session state for login if not present
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Login"  # Default to Login page

    # Conditional page rendering based on login status
    if not st.session_state.logged_in:
        login_page()
    else:
        st.sidebar.title("WeCare Menu")
        st.sidebar.markdown(f"**Welcome, {st.session_state.username}!**")

        # Define pages for logged-in users
        pages = {
            "Home": homepage,
            "AI Helper": ai_helper_page,
            "Peer Support Forum": forum_page,
            "Educational Hub": educational_hub_page,
            "Volunteers Directory": volunteers_page,
        }

        # Sidebar navigation
        choice = st.sidebar.radio("Navigate", list(pages.keys()), index=list(pages.keys()).index(
            st.session_state.current_page) if st.session_state.current_page in pages else 0)

        # Update current_page in session state
        st.session_state.current_page = choice

        # Render the chosen page
        pages[choice]()

        # Logout button
        st.sidebar.markdown("---")
        if st.sidebar.button("Logout"):
            # Clear all relevant session state variables
            for key in ["logged_in", "username", "user_id", "user_role", "chat_history", "current_page"]:
                st.session_state.pop(key, None)
            st.success("You have been successfully logged out.")
            st.rerun()


if __name__ == "__main__":
    main()
