# WeCare 🌱 - AI-Powered Mental Wellness Platform

**WeCare** is a community-driven mental health platform that uses AI to support users' emotional well-being through journaling, emotion tracking, and community engagement. Built with **Streamlit**, **Firebase**, and **SQLite**, this app encourages mental health literacy and self-awareness.

---

## 🚀 Features

- 🧠 **AI-Powered Journal**: Users can write daily journal entries and receive mood analysis.
- 📊 **Emotion Trend Tracker**: Visualize emotional trends over time with interactive charts.
- 🔐 **Secure Login**: User authentication via Firebase for secure and personalized experiences.
- 🤝 **Community Board**: Share anonymous experiences and find peer support.
- ⚙️ **Admin Dashboard**: Manage users and monitor overall platform health.

---

## 🛠️ Tech Stack

- **Frontend & App Interface**: [Streamlit](https://streamlit.io/)
- **Authentication**: Firebase Authentication
- **Database**: SQLite
- **Secrets & Configs**: `secrets.toml` (not tracked in Git for security)
- **Deployment**: [Streamlit Cloud](https://streamlit.io/cloud)

---

## 🔧 Setup & Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ClimateTech360/WeCare.git
   cd wecare_app
Create a virtual environment

bash
Copy
Edit
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
Install dependencies

bash
Copy
Edit
pip install -r requirements.txt
Add your Firebase config

Save your Firebase credentials to a file named firebase_config.json.

Do NOT upload this file to GitHub.

Set your Streamlit secrets

Create a file .streamlit/secrets.toml:

toml
Copy
Edit
OPENAI_API_KEY = "your_openai_key_here"
This file is excluded via .gitignore for security.

Run the app

bash
Copy
Edit
streamlit run app.py
🔒 Security Notes
API keys and sensitive data are managed using .streamlit/secrets.toml, which is excluded from Git.

Any push attempts with embedded secrets are automatically blocked by GitHub's push protection.

📌 Project Roadmap
✅ Phase 1: MVP Launch
Emotion journaling and trend analysis

User login and secure session handling

🚧 Phase 2: Community & AI Expansion
Peer-to-peer support board

Smarter mood detection using fine-tuned models

🚀 Phase 3: Regional Scaling
Launch across East Africa

Integration with local mental health NGOs and professionals

🤝 Contributing
We welcome developers, psychologists, and open-source enthusiasts to collaborate!

bash
Copy
Edit
git checkout -b feature/your-feature
git commit -m "Add some feature"
git push origin feature/your-feature
Submit a pull request for review.

📄 License
This project is licensed under the MIT License.
