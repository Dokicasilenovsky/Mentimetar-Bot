# Mentimeter Bot

A Python-based automation tool that creates multiple virtual participants for Mentimeter quizzes and automatically tests possible answer combinations.

The project uses Selenium WebDriver to control browser instances, simulate real users joining a quiz, answering questions, and tracking the results.

## Features

* Automated browser control using Selenium
* Creates multiple virtual quiz participants
* Generates unique bot usernames automatically
* Automatically joins Mentimeter quizzes
* Supports multiple-choice questions
* Tests different answer combinations
* Runs multiple bots concurrently using threading
* Detects incorrect answers automatically
* Tracks success and failure statistics
* Includes a debugging mode for inspecting page elements

## How It Works

The bot generates all possible answer combinations for a 5-question quiz:

```
3 options × 5 questions = 3⁵ = 243 combinations
```

Each bot receives a unique combination of answers and joins the quiz as a separate participant.

Example:

```
Bot_001_abca
Bot_002_bcab
Bot_003_cabc
```

Every bot then:

1. Opens a browser session
2. Joins the Mentimeter quiz
3. Enters a generated username
4. Answers each question according to its assigned combination
5. Checks if the answers were correct
6. Reports the result

## Technologies

* Python
* Selenium WebDriver
* ChromeDriver
* Threading
* HTML element automation

## Example Output

```
🚀 STARTING MENTIMETER BOT
📊 Total combinations: 243

🤖 Bot 001 started | Answers: abcab
📝 Bot 001 entered name: Bot_001_xkqz
✅ Bot 001 joined quiz
✅ Bot 001 -> Question 1: A
✅ Bot 001 -> Question 2: B

🎉 Bot 001 FINISHED ALL QUESTIONS
```

## Purpose

This project was created as an experiment in browser automation, web scraping techniques, and concurrent task execution.

It demonstrates how automated agents can interact with modern web applications by identifying and controlling dynamic HTML elements.

## Future Improvements

* Add support for quizzes with different numbers of questions
* Improve browser resource management
* Add a graphical user interface
* Store results in a database
* Add configurable quiz settings
* Improve detection of quiz states

## Disclaimer

This project was created for educational purposes to explore Selenium automation, browser control, and web technologies.
