# Workshop LLM Code Fixing Agent

This is the result of a workshop made by @clementbolin (https://github.com/clementbolin/epitech-workshop-genai)

I've done it with @AurelienBaraquin @Louis-rollet @messtt @Notilus11 in 1h30

The code is pretty messy because we did it on live share, without much organization. The objective was principally to find solutions in group, speaking directly to each others
The objective was to find the best solution for recreating a program using one or many agents for correcting code (like Copilot for example)

## Prerequisites

- Python 3.10 or higher
- [LM Studio](https://lmstudio.ai) installed
- `phi-4` model loaded in LM Studio (You can change it in config.py)

## Setup

Start LM Studio:
   - Load the model in the config.py file
   - Start the server on port 1234 (you can also change it in config.py)
   - Enable "Just-in-time model loading"

## Usage

Basic usage
```bash
python3 main.py <filename>
```

Usage to select only specific lines
```bash
python3 main.py <filename> --start 10 --end 20
```

Adding comments in the code
```bash
python3 main.py <filename> --comments True
```

Specify what the error in the code is if necessary. You can also use this method to send any other information you want the agent to know 
```bash
python3 main.py <filename> --errors 'The code core dumps'
```

You can use the --help to get all these directly in the CLI

## What we did

What we actually did:
- Use one agent to handle the code
- Personalize the prompt sent to the agent (in addition to the code), according to the launched CLI command
- Specify the lines to modify
- Get the diff between the initial and the corrected code
- Detect the language by the name of the file

## To go further

To go further, we had some ideas but because of the short time we couldn't implement them:
- VSCode extension
- Multiple agents each specialized in one specific task
- Automated testing of the corrected code
