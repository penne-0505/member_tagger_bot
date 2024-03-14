# README for Discord Member Tagger Bot

## Overview

A Discord bot that associates members in the guild with threads. This bot allows users to tag members to specific threads, making it easier to manage and track contributions or assignments within the guild. The bot is designed to be simple to use, with a focus on ease of tagging and untagging members, as well as viewing tagged posts.

## Features

- **Tagging Members**: Assign members to specific threads with a deadline for submission.
- **Untagging Members**: Remove the association of members from threads.
- **Viewing Tagged Posts**: See all posts associated with a member, including the deadline for each.
- **Interactive UI**: An intuitive user interface for tagging, untagging, and viewing tagged posts.
- **Database Integration**: Uses a database to store tagging information, ensuring data persistence and reliability.

## Setup

1. **Environment Setup**: Ensure you have Python 3.8 or higher installed.
2. **Dependencies**: Install the required dependencies by running `pip install discord.py boto3` (if you want colored log, add `colorama`).
3. **Database Setup**: Configure your AWS DynamoDB table as specified in `db_handler.py`.
4. **Bot Token**: Set your Discord bot token as an environment variable named `SECRET_TOKEN`.
5. **Run the Bot**: Execute `main.py` to start the bot.

## Usage

- **Commands**: Use the following commands to interact with the bot.
- **Help**: Use the `/help` command to see a list of available commands and their descriptions.
- **Tagging a Member**: Use the `/tag` command to start the process of tagging a member to a thread. Follow the interactive UI to select the thread and member, and set a deadline.
- **Untagging a Member**: Use the `/untag` command to remove a member's association from a thread. Follow the interactive UI to select the thread and member.
- **Viewing Tagged Posts**: Use the `/tagged_posts` command to see all posts associated with a member, including the deadline for each.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.