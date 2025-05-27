# Meeting Question Assistant

An application to help answer questions during meetings, with speech recognition and multilingual support.

## Features

- Record questions from others during meetings
- Automatically convert speech to text (using OpenAI Whisper)
- Send content to GPT to generate appropriate answers
- Display answers in two columns: Vietnamese and the selected target language (English, Japanese)

## Installation

### Prerequisites

- Python 3.8+
- MacOS operating system
- OpenAI API key

### Setup

1. Clone this repository

2. Create a virtual environment:

```bash
python -m venv venv
```

3. Activate the virtual environment:

```bash
source venv/bin/activate
```

4. Install the required packages:

```bash
pip install -r requirements.txt
```

5. Copy the `.env.template` file to `.env` and add your OpenAI API key:

```bash
cp .env.template .env
# Edit the .env file with your API key
```

## Running the Application

Activate your virtual environment if not already active:

```bash
source venv/bin/activate
```

Run the application:

```bash
python src/app.py
```

## Running Tests

To run the unit tests:

```bash
python -m pytest tests/
```

## Project Structure

```
├── src/             # Source code
│   └── app.py       # Main application
├── tests/           # Unit tests
├── .env.template    # Template for environment variables
├── requirements.txt # Python dependencies
└── README.md        # This file
```

## Development Rules

1. All comments and labels must be in English
2. Code must have unit tests
