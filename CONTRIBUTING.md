# Contributing

Pull requests and suggestions are welcome! Please open an issue or PR for bug fixes, new features, or system support.

---

## Development Prerequisites

- Developed on Python 3.12.10
- A Discord bot token ([how to create one](https://discord.com/developers/applications))
- PostgreSQL database server (local or hosted)
- [python-dotenv](https://pypi.org/project/python-dotenv/) for environment variable management

## Installation for Development

1. **Clone the repository**
   ```sh
   git clone https://github.com/CptConstantine/RoleByPost.git
   cd RoleByPost
   ```

2. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL database**
   - Install PostgreSQL locally or use a hosted service
   - Create a new database for the bot
   - Note your connection details (host, port, database name, username, password)

4. **Set up your environment**
   - Create a `.env` file in the project root with the following variables:
     ```
     DISCORD_BOT_TOKEN=your-bot-token-here
     DATABASE_URL=postgresql://username:password@localhost:5432/your_database_name
     ENCRYPTION_KEY=your-encryption-key-here
     ```
   - Replace the `DATABASE_URL` values with your actual PostgreSQL connection details
   - For hosted databases (like Heroku Postgres), use the full connection string provided by your service
   - You can get an encryption key by running `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

5. **Run the bot**
   ```sh
   python main.py
   ```
   The bot will automatically create the necessary database schema on first run.
