import streamlit as st
import sqlite3
import bcrypt
from datetime import datetime

# --- 1. Database Utilities (from db_utils.py) ---


def connect_db():
    """Establishes a connection to the SQLite database."""
    # check_same_thread=False is needed for Streamlit's multi-threading nature
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

# --- 2. Utility Functions (from utils.py) ---


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

# --- 3. Page Functions (from pages/*.py) ---

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
                st.session_state.user_role = user[3]  # Store user role
                st.success(f"Login successful! Welcome, {user[1]}!")
                st.rerun()  # Use st.rerun() instead of st.switch_page() for single-file apps
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
# Distress keyword list (broadened for open platform)
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
    """Generates an AI response based on user input."""
    if detect_distress_ai(user_input):
        return EMERGENCY_RESPONSE

    # Simulated general support
    if "anxiety" in user_input.lower():
        return "It’s okay to feel anxious sometimes. Try to take slow, deep breaths. Would you like me to guide you through a simple breathing exercise? You can also explore our Educational Hub for articles on managing anxiety."
    elif "addiction" in user_input.lower() or "alcohol" in user_input.lower() or "drugs" in user_input.lower():
        return "Recovery is a journey, and you're not alone. Consider visiting the Peer Support Forum to connect with others on a similar path. Remember, professional help is also available."
    elif "stress" in user_input.lower():
        return "Stress can be tough. Sometimes a short break or mindfulness exercise can help. Our Educational Hub has great tips for stress management."
    elif "sad" in user_input.lower() or "depressed" in user_input.lower():
        return "It sounds like you're feeling down. Please remember that it's okay to ask for help. Sharing in the forum or exploring our resources on depression might be a start."
    else:
        return "I'm here to listen. You can share more about what's on your mind. You can also explore the Educational Hub for information or connect with others in the Forum."

    # TODO: Replace this with a more advanced NLP model (e.g., HuggingFace Transformer)
    # to provide personalized and context-aware responses in the future.


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
        submit = st.form_submit_button("Post")

        if submit:
            if not content.strip():
                st.warning("Post content can't be empty.")
            elif moderate_content(content):
                st.warning(
                    "Your post contains flagged words. Please revise it.")
            else:
                add_post(st.session_state.user_id, content, int(anonymous))
                st.success("Post submitted!")
                st.rerun()  # Rerun to refresh posts list

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
                # clear_on_submit to reset text area
                with st.form(f"comment_form_{post_id}", clear_on_submit=True):
                    comment_input = st.text_area(
                        "Add a comment", key=f"ci_{post_id}", height=70)
                    submit_comment = st.form_submit_button(
                        "Submit Comment", key=f"btn_{post_id}")
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
                            st.rerun()  # Rerun to refresh comments

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
    # TODO: Placeholder for AI Recommendation Engine:
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
    try:
        with open("resources/self-care-guide.pdf", "rb") as file:
            st.download_button(label="Download Self-Care Guide (PDF)", data=file,
                               file_name="self-care-guide.pdf", mime="application/pdf")
    except FileNotFoundError:
        st.warning("Self-Care Guide PDF not found. Please create a 'resources' folder and place 'self-care-guide.pdf' inside it to enable download.")

# --- Professional Volunteer Directory (Mock-Up) Page ---


def volunteers_page():
    """Renders the mock professional volunteer directory."""
    st.title("🤝 Professional Volunteers Directory (Mock-Up)")
    st.markdown(
        "Explore profiles of mock mental health professionals. These profiles are for **demonstration purposes only**.")

    st.info("⚠️ **Disclaimer:** This is a mock directory. WeCare does not directly offer professional services or endorse specific individuals. All volunteers here are for demonstration only. Always seek independent verification and professional advice for your mental health needs.")

    st.subheader("Featured Mock Professionals")

    # Example mock profiles
    mock_professionals = [
        {
            "Name": "Dr. Aisha Khan",
            "Role": "Clinical Psychologist",
            "Bio": "Specializes in cognitive-behavioral therapy (CBT) for anxiety and depression. Passionate about destigmatizing mental health conversations.",
        },
        {
            "Name": "Mr. David Omondi",
            "Role": "Addiction Counsellor",
            "Bio": "Experienced in supporting individuals and families through addiction recovery journeys, focusing on holistic well-being.",
        },
        {
            "Name": "Ms. Sarah Wanjiku",
            "Role": "Trauma-Informed Therapist",
            "Bio": "Dedicated to helping individuals process and heal from past trauma, using compassionate and evidence-based approaches.",
        },
    ]

    for i, prof in enumerate(mock_professionals):
        st.markdown("---")
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image("https://via.placeholder.com/100/ADD8E6/000000?text=PROF",
                     caption=prof["Name"])  # Placeholder image
        with col2:
            st.subheader(prof["Name"])
            st.write(f"**Role:** {prof['Role']}")
            st.write(f"**Bio:** {prof['Bio']}")
            # Mock contact button
            st.button(f"Mock Contact {prof['Name']}", key=f"contact_prof_{i}")

    st.markdown("---")
    st.write("For real professional help, please consult verified directories or your local health services.")

# --- Main Application Logic (from app.py) ---


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
            "Home": homepage,  # A simple homepage for now
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
            st.rerun()  # Rerun to redirect to login page


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
    - **🤝 Volunteers Directory:** (Mock-up) See how we might connect you with professionals in the future.
    """)
    st.info("Remember, you are not alone. Take a moment to breathe, and explore the resources available to you.")


if __name__ == "__main__":
    main()
